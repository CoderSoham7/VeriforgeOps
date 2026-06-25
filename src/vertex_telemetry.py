import time
from datetime import datetime
from typing import Dict, Any, Optional
import logging

try:
    from google.cloud import aiplatform
    from google.cloud.aiplatform.gapic import PredictionServiceClient
except ImportError:
    # Fallbacks if aiplatform SDK imports change
    pass

from src.pubsub_wrapper import PubSubTelemetryWrapper
from src.schemas import CanonicalUsageEvent

logger = logging.getLogger("VeriForgeOps.VertexTelemetry")

class VertexTelemetryInterceptor:
    """
    Interceptor for inline Vertex AI calls (e.g. Gemini, custom endpoints).
    Intercepts calls, extracts usage metrics (tokens, characters, latencies),
    validates them against the CanonicalUsageEvent schema, and routes them to Pub/Sub.
    """

    def __init__(
        self,
        project_id: str = "cog01k24f1ea555zdv7ynzthxanz5",
        topic_id: str = "veriforgeops-telemetry-ingest",
        user_email: str = "soham.ganguly@cognizant.com",
        mock_mode: bool = False
    ):
        self.project_id = project_id
        self.topic_id = topic_id
        self.user_email = user_email
        
        # Resolve associate employee ID from email
        self.associate_id = user_email.split("@")[0]
        
        # Initialize Pub/Sub telemetry wrapper
        self.telemetry_wrapper = PubSubTelemetryWrapper(
            project_id=self.project_id,
            topic_id=self.topic_id,
            mock_mode=mock_mode
        )
        logger.info(f"Initialized Vertex AI Telemetry Interceptor for user: {user_email}")

    def track_prediction(
        self,
        model_name: str,
        operation: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        input_characters: int = 0,
        output_characters: int = 0,
        input_images: int = 0,
        input_audio_seconds: float = 0.0,
        input_video_seconds: float = 0.0,
        latency_ms: Optional[int] = None,
        endpoint_id: str = "gemini-endpoint",
        region: str = "us-central1",
        cost_centre: str = "CC-UNALLOCATED-GCP",
        project_code: str = "PROJ-GCP-GEMINI",
        cost: Optional[float] = None
    ) -> Optional[str]:
        """
        Manually routes a recorded prediction/generation call telemetry to Pub/Sub.
        """
        # Create standard GCP raw log structure matching GCPConnector interface
        json_payload = {
            "model": model_name,
            "endpoint": endpoint_id,
            "inputTokenCount": input_tokens,
            "outputTokenCount": output_tokens
        }

        if cached_tokens > 0:
            json_payload["cachedTokenCount"] = cached_tokens
        if input_characters > 0:
            json_payload["inputCharacterCount"] = input_characters
        if output_characters > 0:
            json_payload["outputCharacterCount"] = output_characters
        if input_images > 0:
            json_payload["inputImageCount"] = input_images
        if input_audio_seconds > 0.0:
            json_payload["inputAudioSeconds"] = input_audio_seconds
        if input_video_seconds > 0.0:
            json_payload["inputVideoSeconds"] = input_video_seconds
        if latency_ms is not None:
            json_payload["latency_ms"] = latency_ms

        raw_gcp_log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "resource": {
                "labels": {
                    "project_id": self.project_id,
                    "location": region
                }
            },
            "protoPayload": {
                "methodName": f"google.cloud.aiplatform.v1.PredictionService.{operation.capitalize()}",
                "authenticationInfo": {
                    "principalEmail": self.user_email
                }
            },
            "jsonPayload": json_payload
        }

        identity_context = {
            "associate_id": self.associate_id,
            "cost_centre": cost_centre,
            "project_code": project_code
        }

        if cost is not None:
            raw_gcp_log["cost"] = cost

        # Publish through the wrapper
        try:
            return self.telemetry_wrapper.publish_raw(
                cloud_provider="gcp",
                raw_payload=raw_gcp_log,
                identity_context=identity_context
            )
        except Exception as e:
            logger.error(f"Failed to publish inline Vertex AI prediction telemetry: {e}")
            return None

    def generate_content_with_telemetry(
        self,
        generative_model_instance,
        prompt: str,
        generation_config: Optional[Any] = None,
        cost_centre: str = "CC-AI-DEVELOPMENT",
        project_code: str = "PROJ-VERIFORGE-OPS"
    ) -> Any:
        """
        Wraps a Vertex AI GenerativeModel prompt generation, measures execution metrics,
        and automatically dispatches telemetry to Pub/Sub.
        
        Args:
            generative_model_instance: An instance of google.cloud.aiplatform.GenerativeModel
            prompt: Text prompt string.
            generation_config: Configuration dict.
            cost_centre: Associated billing cost centre.
            project_code: Associated project code.
            
        Returns:
            The model response.
        """
        start_time = time.time()
        
        # Invoke actual prediction API call
        try:
            response = generative_model_instance.generate_content(
                prompt,
                generation_config=generation_config
            )
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract usage metadata
            input_tokens = 0
            output_tokens = 0
            cached_tokens = 0
            model_name = getattr(generative_model_instance, "_model_name", "gemini-1.5-flash")
            
            # Extract metrics from response usage metadata
            if hasattr(response, "usage_metadata"):
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
                cached_tokens = getattr(response.usage_metadata, "cached_content_token_count", 0)

            # Record telemetry
            self.track_prediction(
                model_name=model_name,
                operation="generateContent",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
                latency_ms=latency_ms,
                cost_centre=cost_centre,
                project_code=project_code
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error during generative model invocation: {e}")
            raise e
