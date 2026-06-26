import json
import os
import sys
import logging
from google.cloud import pubsub_v1
from google.api_core.exceptions import AlreadyExists, NotFound

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VeriForgeOps.PubSubAnalyzer")


def analyze_pubsub_data(project_id, topic_id, subscription_id):
    # Set environment overrides to resolve invalid default user quota projects
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = project_id

    subscriber = pubsub_v1.SubscriberClient()
    topic_path = f"projects/{project_id}/topics/{topic_id}"
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    # Step 1: Ensure the PERSISTENT subscription exists.
    #
    # IMPORTANT: Pub/Sub only delivers a message to subscriptions that already
    # exist at publish time, and each subscription keeps its own copy until the
    # message is acknowledged. This script therefore uses a *persistent* shared
    # subscription (the same one the Streamlit UI publishes against) and never
    # deletes it — so events published by the UI are visible here.
    logger.info(f"Ensuring persistent subscription '{subscription_id}' on topic '{topic_id}'...")
    try:
        subscriber.create_subscription(
            request={"name": subscription_path, "topic": topic_path}
        )
        logger.info(f"Subscription {subscription_id} created successfully.")
        logger.info(
            "NOTE: this subscription was just created, so it will only capture "
            "events published from now on. Publish again from the UI, then re-run."
        )
    except AlreadyExists:
        logger.info(f"Subscription {subscription_id} already exists. Reusing it.")

    # Step 2: Pull messages from subscription
    logger.info(f"Pulling messages from subscription '{subscription_id}'...")
    try:
        response = subscriber.pull(
            request={
                "subscription": subscription_path,
                "max_messages": 50,
                "return_immediately": True,
            }
        )
    except Exception as e:
        logger.error(f"Failed to pull messages: {e}")
        sys.exit(1)

    received_messages = response.received_messages
    logger.info(f"Pulled {len(received_messages)} messages from topic.")

    analyzed_logs = []

    # Step 3: Parse and analyze messages, then acknowledge them.
    ack_ids = []
    for msg in received_messages:
        ack_ids.append(msg.ack_id)
        try:
            data_str = msg.message.data.decode("utf-8")
            log_data = json.loads(data_str)
            # Events routed via the Log Router arrive wrapped as a LogEntry, with
            # the canonical event under jsonPayload. Unwrap so analysis is uniform.
            if isinstance(log_data, dict) and "jsonPayload" in log_data:
                inner = log_data.get("jsonPayload") or {}
                inner["_routed_via_log_router"] = True
                log_data = inner
            log_data["_message_id"] = msg.message.message_id
            analyzed_logs.append(log_data)
        except Exception as e:
            logger.error(f"Failed to decode message ID {msg.message.message_id}: {e}")

    if ack_ids:
        subscriber.acknowledge(
            request={"subscription": subscription_path, "ack_ids": ack_ids}
        )

    # NOTE: We intentionally do NOT delete the subscription — keeping it
    # persistent is what keeps the UI and this reader in sync.

    # Step 5: Perform and display analysis
    print("\n" + "=" * 80)
    print("                     VERIFORGE OPS - TELEMETRY ANALYSIS                     ")
    print("=" * 80)

    if not analyzed_logs:
        print("\nNo telemetry logs found in the Pub/Sub queue at this moment.")
        print(
            "Publish events from the Streamlit UI (with 'Live GCP Pub/Sub' ON), "
            "then re-run this script."
        )
        print(
            "Reminder: each message is delivered to this subscription only once. "
            "If you already clicked 'Pull Live Events' in the UI, those messages "
            "were consumed there."
        )
        print("=" * 80 + "\n")
        return

    print(f"\nTotal Logs Analyzed: {len(analyzed_logs)}")

    # Detect schema: VeriForge CanonicalUsageEvent vs GCP audit log.
    def is_canonical(log):
        return "cloud" in log and "service" in log and "operation" in log

    if all(is_canonical(l) for l in analyzed_logs):
        _analyze_canonical(analyzed_logs)
    else:
        _analyze_audit(analyzed_logs)

    print("\n" + "=" * 80)


def _analyze_canonical(logs):
    """Summarise VeriForge CanonicalUsageEvent telemetry."""
    clouds, services, operations, associates = {}, {}, {}, {}
    total_cost = 0.0

    print("\n--- Canonical Usage Event Records ---")
    for idx, log in enumerate(logs):
        cloud = log.get("cloud", "unknown-cloud")
        service = log.get("service", "unknown-service")
        operation = log.get("operation", "unknown-op")
        associate = log.get("associate_id", "unknown-associate")
        cost = float(log.get("cost", 0) or 0)
        timestamp = log.get("timestamp", "unknown-time")
        ru = log.get("request_units", {}) or {}

        clouds[cloud] = clouds.get(cloud, 0) + 1
        services[service] = services.get(service, 0) + 1
        operations[operation] = operations.get(operation, 0) + 1
        associates[associate] = associates.get(associate, 0) + 1
        total_cost += cost

        usage_bits = []
        if "total_tokens" in ru or "input_tokens" in ru:
            usage_bits.append(f"{ru.get('total_tokens', ru.get('input_tokens', 0)):,} tok")
        if "input_audio_seconds" in ru:
            usage_bits.append(f"{ru['input_audio_seconds']}s audio")
        if "input_characters" in ru:
            usage_bits.append(f"{ru['input_characters']:,} chars")
        usage = ", ".join(usage_bits) or "—"

        print(f"\n[{idx + 1}] Timestamp: {timestamp}")
        print(f"    Cloud/Service: {cloud} / {service}")
        print(f"    Operation:     {operation}")
        print(f"    Associate:     {associate}  (cost_centre={log.get('cost_centre', '—')}, project={log.get('project_code', '—')})")
        print(f"    Cost:          ${cost:.6f}")
        print(f"    Usage:         {usage}")

    print("\n" + "-" * 50)
    print("Aggregated Statistics")
    print("-" * 50)
    print(f"\nTotal Cost: ${total_cost:.6f}")

    print("\nClouds:")
    for k, v in sorted(clouds.items(), key=lambda x: -x[1]):
        print(f"  - {k}: {v} event(s)")
    print("\nServices:")
    for k, v in sorted(services.items(), key=lambda x: -x[1]):
        print(f"  - {k}: {v} event(s)")
    print("\nOperations:")
    for k, v in sorted(operations.items(), key=lambda x: -x[1]):
        print(f"  - {k}: {v} call(s)")
    print("\nAssociates:")
    for k, v in sorted(associates.items(), key=lambda x: -x[1]):
        print(f"  - {k}: {v} request(s)")


def _analyze_audit(logs):
    """Fallback: summarise GCP Cloud Audit Log style records."""
    methods, principals, severities = {}, {}, {}

    print("\n--- Telemetry Log Records Summary ---")
    for idx, log in enumerate(logs):
        proto_payload = log.get("protoPayload", {})
        resource = log.get("resource", {})
        labels = resource.get("labels", {})

        method = proto_payload.get("methodName") or labels.get("method") or "unknown-method"
        principal = proto_payload.get("authenticationInfo", {}).get("principalEmail") or "unknown-principal"
        severity = log.get("severity", "INFO")
        timestamp = log.get("timestamp") or "unknown-time"

        methods[method] = methods.get(method, 0) + 1
        principals[principal] = principals.get(principal, 0) + 1
        severities[severity] = severities.get(severity, 0) + 1

        print(f"\n[{idx + 1}] Timestamp: {timestamp}")
        print(f"    Service:  {proto_payload.get('serviceName') or labels.get('service')}")
        print(f"    Method:   {method}")
        print(f"    Caller:   {principal}")
        print(f"    Severity: {severity}")

    print("\n" + "-" * 50)
    print("Aggregated Statistics")
    print("-" * 50)
    print("\nMethods Invoked:")
    for method, count in methods.items():
        print(f"  - {method}: {count} execution(s)")
    print("\nCalling Identities (Principals):")
    for princ, count in principals.items():
        print(f"  - {princ}: {count} request(s)")
    print("\nSeverity Levels:")
    for sev, count in severities.items():
        print(f"  - {sev}: {count} event(s)")


if __name__ == "__main__":
    PROJECT_ID = "cog01k24f1ea555zdv7ynzthxanz5"
    TOPIC_ID = "veriforgeops-telemetry-ingest"
    # Persistent subscription shared with the Streamlit UI so both stay in sync.
    SUB_ID = "veriforgeops-streamlit-live"

    analyze_pubsub_data(PROJECT_ID, TOPIC_ID, SUB_ID)
