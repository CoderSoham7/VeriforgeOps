"""
Live Google Cloud Pub/Sub integration for the VeriForge Ops Streamlit UI.

Provides thin, UI-friendly helpers to:
  * publish CanonicalUsageEvent payloads to the ingestion topic, and
  * pull events back from a persistent subscription for the live Event Stream.

Credential resolution order:
  1. Streamlit secrets  -> st.secrets["gcp_service_account"] (a service-account dict)
  2. Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS / gcloud ADC)

Every function returns a (ok: bool, message: str, payload) tuple so the UI can
surface clear status without raising.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "cog01k24f1ea555zdv7ynzthxanz5")
TOPIC_ID = os.environ.get("VERIFORGE_PUBSUB_TOPIC", "veriforgeops-telemetry-ingest")
# Persistent subscription so messages published between pulls are retained.
SUBSCRIPTION_ID = os.environ.get("VERIFORGE_PUBSUB_SUB", "veriforgeops-streamlit-live")
# Cloud Logging log name used when routing events through the Log Router sink.
LOG_NAME = os.environ.get("VERIFORGE_LOG_NAME", "veriforgeops-telemetry")


# ── Credential helpers ────────────────────────────────────────────────────────
def _credentials():
    """Return service-account credentials from Streamlit secrets, else None (ADC)."""
    try:
        import streamlit as st  # imported lazily; module is import-safe without it

        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            from google.oauth2 import service_account

            info = dict(st.secrets["gcp_service_account"])
            return service_account.Credentials.from_service_account_info(info)
    except Exception:
        pass
    return None


def _project_id() -> str:
    creds = _credentials()
    if creds is not None and getattr(creds, "project_id", None):
        return creds.project_id
    try:
        import streamlit as st

        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            pid = st.secrets["gcp_service_account"].get("project_id")
            if pid:
                return pid
    except Exception:
        pass
    return PROJECT_ID


def connection_status() -> Tuple[bool, str]:
    """Best-effort check of whether live Pub/Sub credentials are usable."""
    try:
        from google.cloud import pubsub_v1  # noqa: F401
    except Exception as e:
        return False, f"google-cloud-pubsub not importable: {e}"

    creds = _credentials()
    if creds is not None:
        return True, "service account (Streamlit secrets)"
    # Probe ADC without raising.
    try:
        import google.auth

        google.auth.default()
        return True, "application default credentials"
    except Exception:
        return False, "no credentials (set st.secrets['gcp_service_account'] or ADC)"


# ── Client factories ───────────────────────────────────────────────────────────
def _publisher():
    from google.cloud import pubsub_v1

    creds = _credentials()
    return pubsub_v1.PublisherClient(credentials=creds) if creds else pubsub_v1.PublisherClient()


def _subscriber():
    from google.cloud import pubsub_v1

    creds = _credentials()
    return pubsub_v1.SubscriberClient(credentials=creds) if creds else pubsub_v1.SubscriberClient()


def _logging_client(project_id: str):
    from google.cloud import logging_v2

    creds = _credentials()
    if creds:
        return logging_v2.Client(project=project_id, credentials=creds)
    return logging_v2.Client(project=project_id)


# ── Route via Log Router (Cloud Logging -> sink -> topic) ───────────────────────
def log_events(event_payloads: List[Dict[str, Any]]) -> Tuple[bool, str, int]:
    """
    Write canonical event payloads to Cloud Logging as structured entries that
    match the 'vertex-ai-telemetry-sink' filter (resource.type='audited_resource',
    service='aiplatform.googleapis.com'). The Log Router then forwards them to the
    Pub/Sub topic — which is what increments the sink's exported-volume metric.

    Unlike publish_events (which writes straight to the topic and bypasses the
    sink), this path flows through Cloud Logging. Routed messages arrive on the
    topic wrapped as LogEntry JSON, with the canonical event under `jsonPayload`.
    Returns (ok, message, count_written).
    """
    if not event_payloads:
        return False, "No events to route.", 0

    # Best-effort schema validation (skip invalid, keep valid).
    try:
        from src.schemas import CanonicalUsageEvent

        validated = []
        for p in event_payloads:
            try:
                validated.append(CanonicalUsageEvent(**p).model_dump())
            except Exception:
                pass
        if not validated:
            return False, "All events failed schema validation.", 0
    except Exception:
        validated = event_payloads

    project_id = _project_id()
    try:
        client = _logging_client(project_id)
        logger = client.logger(LOG_NAME)
        for payload in validated:
            resource = {
                "type": "audited_resource",
                "labels": {
                    "service": "aiplatform.googleapis.com",
                    "method": str(payload.get("operation", "predict")),
                    "project_id": project_id,
                },
            }
            logger.log_struct(payload, resource=resource, severity="INFO")
        return (
            True,
            f"Routed {len(validated)} event(s) via Cloud Logging → "
            f"Log Router sink → {TOPIC_ID}. (Sink volume will update shortly.)",
            len(validated),
        )
    except Exception as e:
        return False, f"Log Router routing failed: {e}", 0


# ── Publish ─────────────────────────────────────────────────────────────────────
def publish_events(event_payloads: List[Dict[str, Any]]) -> Tuple[bool, str, List[str]]:
    """
    Publish a list of canonical event payload dicts (the inner `data` object) to
    the ingestion topic. Each payload is validated against CanonicalUsageEvent
    before publishing. Returns (ok, message, list_of_message_ids).
    """
    if not event_payloads:
        return False, "No events to publish.", []

    # Validate against the canonical schema (best effort — skips invalid).
    try:
        from src.schemas import CanonicalUsageEvent

        validated: List[Dict[str, Any]] = []
        errors = 0
        for p in event_payloads:
            try:
                validated.append(CanonicalUsageEvent(**p).model_dump())
            except Exception:
                errors += 1
        if not validated:
            return False, f"All {len(event_payloads)} events failed schema validation.", []
    except Exception:
        # If schema import fails, publish payloads as-is.
        validated = event_payloads
        errors = 0

    project_id = _project_id()
    try:
        publisher = _publisher()
        topic_path = publisher.topic_path(project_id, TOPIC_ID)
        message_ids: List[str] = []
        for payload in validated:
            data = json.dumps(payload).encode("utf-8")
            future = publisher.publish(topic_path, data)
            message_ids.append(future.result(timeout=30))
        suffix = f" ({errors} skipped on validation)" if errors else ""
        return True, f"Published {len(message_ids)} event(s) to {TOPIC_ID}{suffix}.", message_ids
    except Exception as e:
        return False, f"Publish failed: {e}", []


# ── Pull ──────────────────────────────────────────────────────────────────────
def _ensure_subscription(subscriber, project_id: str) -> str:
    from google.api_core.exceptions import AlreadyExists

    topic_path = f"projects/{project_id}/topics/{TOPIC_ID}"
    subscription_path = subscriber.subscription_path(project_id, SUBSCRIPTION_ID)
    try:
        subscriber.create_subscription(request={"name": subscription_path, "topic": topic_path})
    except AlreadyExists:
        pass
    return subscription_path


def pull_events(max_messages: int = 50) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Pull up to `max_messages` events from the persistent subscription, acknowledge
    them, and return them shaped like the UI's event records:
        {"message_id": <pubsub id>, "data": <decoded canonical payload>}
    JSON payloads that don't match the canonical shape are still returned raw.
    """
    project_id = _project_id()
    try:
        subscriber = _subscriber()
        subscription_path = _ensure_subscription(subscriber, project_id)
        response = subscriber.pull(
            request={
                "subscription": subscription_path,
                "max_messages": max_messages,
                "return_immediately": True,
            }
        )
    except Exception as e:
        return False, f"Pull failed: {e}", []

    received = response.received_messages
    if not received:
        return True, "No new messages in the Pub/Sub queue.", []

    ack_ids = []
    records: List[Dict[str, Any]] = []
    for msg in received:
        ack_ids.append(msg.ack_id)
        try:
            payload = json.loads(msg.message.data.decode("utf-8"))
        except Exception:
            payload = {"_raw": msg.message.data.decode("utf-8", errors="replace")}
        # Messages routed via the Log Router arrive wrapped as a LogEntry; the
        # canonical event sits under jsonPayload. Unwrap so the UI sees the event.
        if isinstance(payload, dict) and "jsonPayload" in payload:
            inner = payload.get("jsonPayload") or {}
            inner["_routed_via_log_router"] = True
            payload = inner
        records.append({"message_id": msg.message.message_id, "data": payload})

    try:
        subscriber.acknowledge(
            request={"subscription": subscription_path, "ack_ids": ack_ids}
        )
    except Exception:
        pass

    return True, f"Pulled {len(records)} live event(s) from {SUBSCRIPTION_ID}.", records
