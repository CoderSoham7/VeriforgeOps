import json
import logging
import os
from typing import Dict, Any, Optional, Callable, List
from google.cloud import pubsub_v1
from google.api_core.exceptions import GoogleAPICallError, NotFound

from src.schemas import CanonicalUsageEvent
from src.connectors.azure import AzureConnector
from src.connectors.gcp import GCPConnector
from src.connectors.aws import AWSConnector
from src.connectors.sanas import SanasConnector
from src.connectors.ai_tools import AIToolsConnector
from src.connectors.base import BaseConnector

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("VeriForgeOps.PubSubWrapper")

class PubSubTelemetryWrapper:
    """
    Wrapper class to normalise cloud provider and tool usage telemetry,
    and publish it to a Google Cloud Pub/Sub topic for streaming ingestion (Step 2).
    
    Supports mock mode for local testing and development prior to Cloud account provisioning.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        mock_mode: bool = False,
        mock_output_path: Optional[str] = None
    ):
        """
        Initialises the PubSubTelemetryWrapper.

        Args:
            project_id: Google Cloud Project ID. Fallback to GOOGLE_CLOUD_PROJECT env var.
            topic_id: GCP Pub/Sub Topic ID. Fallback to VERIFORGE_PUBSUB_TOPIC env var.
            mock_mode: If True, operates locally without contacting GCP.
            mock_output_path: Local JSONL filepath to write logs in mock mode.
        """
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.topic_id = topic_id or os.environ.get("VERIFORGE_PUBSUB_TOPIC")
        self.mock_mode = mock_mode or os.environ.get("VERIFORGE_MOCK_MODE", "false").lower() == "true"
        self.mock_output_path = mock_output_path or os.environ.get("VERIFORGE_MOCK_OUTPUT_PATH")

        # Invalidate real pubsub if configuration is missing and enforce mock mode
        if not self.mock_mode and (not self.project_id or not self.topic_id):
            logger.warning(
                "GCP Project ID or Pub/Sub Topic ID is missing. Falling back to MOCK MODE. "
                "Set GOOGLE_CLOUD_PROJECT and VERIFORGE_PUBSUB_TOPIC to enable real Pub/Sub publishing."
            )
            self.mock_mode = True

        # Initialize mock storage
        self.mock_published_events: List[Dict[str, Any]] = []

        # Map cloud providers/tools to their respective connectors
        self.connectors: Dict[str, BaseConnector] = {
            "azure": AzureConnector(),
            "gcp": GCPConnector(),
            "aws": AWSConnector(),
            "sanas": SanasConnector(),
            "ai tools data mart": AIToolsConnector(),
            "ai_tools": AIToolsConnector(),  # alias
        }

        # Initialize Pub/Sub Publisher Client if not in mock mode
        self.publisher = None
        self.topic_path = None
        if not self.mock_mode:
            try:
                self.publisher = pubsub_v1.PublisherClient()
                self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
                logger.info(f"Initialized Pub/Sub Publisher client for topic: {self.topic_path}")
            except Exception as e:
                logger.error(f"Failed to initialize GCP Pub/Sub client: {e}. Switching to MOCK MODE.")
                self.mock_mode = True

        if self.mock_mode:
            logger.info("PubSubTelemetryWrapper initialized in MOCK MODE.")
            if self.mock_output_path:
                logger.info(f"Mock outputs will be appended to: {self.mock_output_path}")

    def publish_event(
        self,
        event: CanonicalUsageEvent,
        callback: Optional[Callable[[Any], None]] = None
    ) -> Optional[str]:
        """
        Publishes a validated CanonicalUsageEvent to Google Cloud Pub/Sub.

        Args:
            event: An instance of CanonicalUsageEvent.
            callback: Optional completion callback function for async publishing.

        Returns:
            The message ID if published successfully, or a simulated ID in mock mode.
        """
        event_dict = event.model_dump()
        payload = json.dumps(event_dict).encode("utf-8")

        if self.mock_mode:
            # Simulate message publishing locally
            simulated_message_id = f"mock-msg-{len(self.mock_published_events) + 1:04d}"
            event_record = {
                "message_id": simulated_message_id,
                "data": event_dict
            }
            self.mock_published_events.append(event_record)
            logger.info(f"[MOCK PUBLISHED] Event sent: {event.service} ({event.operation}) - Cost: ${event.cost:.6f}")

            # Append to file if requested
            if self.mock_output_path:
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(self.mock_output_path)), exist_ok=True)
                    with open(self.mock_output_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(event_record) + "\n")
                except Exception as e:
                    logger.error(f"Failed to write to mock output path {self.mock_output_path}: {e}")

            # Call callback immediately in mock mode
            if callback:
                class MockFuture:
                    def result(self):
                        return simulated_message_id
                callback(MockFuture())

            return simulated_message_id

        # Real GCP Pub/Sub Publishing
        try:
            # Publish to Pub/Sub asynchronously
            future = self.publisher.publish(self.topic_path, payload)
            
            # Setup callback if provided
            if callback:
                future.add_done_callback(callback)
            else:
                # Default logging callback
                def default_cb(fut):
                    try:
                        msg_id = fut.result()
                        logger.debug(f"Published message ID: {msg_id}")
                    except Exception as exc:
                        logger.error(f"Publish failed: {exc}")
                future.add_done_callback(default_cb)

            return future.result()  # Blocks briefly to resolve the message ID
        except Exception as e:
            logger.error(f"Error publishing message to Pub/Sub topic {self.topic_path}: {e}")
            raise e

    def publish_raw(
        self,
        cloud_provider: str,
        raw_payload: Dict[str, Any],
        identity_context: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[Any], None]] = None
    ) -> Optional[str]:
        """
        Normalises raw telemetry payload from a specific cloud provider or tool source,
        validates it against the CanonicalUsageEvent schema, and publishes it.

        Args:
            cloud_provider: The cloud source name (e.g., 'azure', 'gcp', 'aws', 'sanas', 'ai_tools')
            raw_payload: The raw dictionary payload from the logs/telemetry source.
            identity_context: Metadata context for associate attribution (employee_id, project, cost center).
            callback: Optional callback when publication finishes.

        Returns:
            The message ID if published successfully.
        """
        provider_key = cloud_provider.lower().strip()
        connector = self.connectors.get(provider_key)
        if not connector:
            raise ValueError(
                f"Unsupported cloud provider: '{cloud_provider}'. "
                f"Supported providers: {list(self.connectors.keys())}"
            )

        try:
            # Step 1: Normalise to Canonical Schema
            canonical_event = connector.to_canonical(raw_payload, identity_context)
            
            # Step 2: Publish validated event
            return self.publish_event(canonical_event, callback=callback)
        except Exception as e:
            logger.error(f"Failed to normalise or publish event from {cloud_provider}: {e}")
            raise e
            
    def get_mock_events(self) -> List[Dict[str, Any]]:
        """Returns the list of events published while in mock mode."""
        return self.mock_published_events

    def clear_mock_events(self):
        """Clears the internal list of mock events."""
        self.mock_published_events.clear()
