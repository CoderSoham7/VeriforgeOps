import re
from typing import Dict, Any, Optional
from datetime import datetime
from src.connectors.base import BaseConnector
from src.schemas import CanonicalUsageEvent

class GCPConnector(BaseConnector):
    """
    Connector for Google Cloud Platform (GCP) AI Services (e.g., Vertex AI, Gemini, Cloud Speech/Translation).
    Processes GCP Cloud Audit logs and BigQuery billing exports.
    """

    # Estimated pricing dictionary per 1M units (tokens, characters, seconds, or images)
    # Gemini pricing is typically per 1M input/output/cached tokens or per 1M images/seconds
    PRICING = {
        # Gemini 1.5 Pro
        "gemini-1.5-pro": {
            "token_input": 1.25,        # prompt tokens (<= 128k context)
            "token_input_long": 2.50,   # prompt tokens (> 128k context)
            "token_output": 5.00,       # candidate tokens (<= 128k context)
            "token_output_long": 10.00, # candidate tokens (> 128k context)
            "token_cached": 0.3125,     # prompt caching rate (75% discount)
            "image": 2500.0,            # $0.0025 per image input
            "video_sec": 2000.0,        # $0.002 per video second
            "audio_sec": 125.0,         # $0.000125 per audio second
        },
        # Gemini 1.5 Flash
        "gemini-1.5-flash": {
            "token_input": 0.075,
            "token_input_long": 0.15,
            "token_output": 0.30,
            "token_output_long": 0.60,
            "token_cached": 0.01875,    # 75% discount
            "image": 20.0,              # $0.00002 per image input
            "video_sec": 130.0,         # $0.00013 per video second
            "audio_sec": 12.5,          # $0.0000125 per audio second
        },
        # Gemini 2.0 Flash
        "gemini-2.0-flash": {
            "token_input": 0.075,
            "token_input_long": 0.15,
            "token_output": 0.30,
            "token_output_long": 0.60,
            "token_cached": 0.01875,
            "image": 20.0,
            "video_sec": 130.0,
            "audio_sec": 12.5,
        },
        # Text Embedding models
        "textembedding-gecko": {
            "token_input": 0.10,        # $0.10 per 1M prompt tokens
            "token_output": 0.0,
        },
        # Speech-to-Text APIs
        "speech-to-text": {
            "sec": 400.0,               # $0.0004 per second of audio
        },
        # Translation APIs
        "translation": {
            "char": 20.0,               # $20.00 per 1M characters translated
        },
        # Default fallback
        "default": {
            "token_input": 1.00,
            "token_output": 4.00,
            "token_cached": 0.25,
            "image": 1000.0,
            "video_sec": 1000.0,
            "audio_sec": 100.0,
        }
    }

    def to_canonical(self, raw_data: Dict[str, Any], identity_context: Optional[Dict[str, Any]] = None) -> CanonicalUsageEvent:
        # 1. Extract basic telemetry fields
        timestamp = raw_data.get("timestamp") or datetime.utcnow().isoformat() + "Z"
        
        # Parse resource details
        resource = raw_data.get("resource", {})
        resource_labels = resource.get("labels", {})
        project_id = resource_labels.get("project_id") or raw_data.get("project_id") or "unknown-gcp-project"
        region = resource_labels.get("location") or "us-central1"

        proto_payload = raw_data.get("protoPayload", {})
        json_payload = raw_data.get("jsonPayload", {})
        
        # Resolve resource name / model name
        resource_id = "unknown-endpoint"
        model = "unknown-model"
        
        if json_payload:
            model = json_payload.get("model") or json_payload.get("modelName", model)
            resource_id = json_payload.get("endpoint") or json_payload.get("resourceName", resource_id)
        elif proto_payload:
            request = proto_payload.get("request", {})
            model = request.get("model", model)
            resource_id = proto_payload.get("resourceName", resource_id)

        # Clean resource path identifiers (e.g. projects/.../models/gemini-1.5-pro-001 -> gemini-1.5-pro-001)
        if "/" in resource_id:
            resource_id = resource_id.split("/")[-1]
        if "/" in model:
            model = model.split("/")[-1]

        # Operation type mapping
        method_name = proto_payload.get("methodName", "")
        operation = "predict"
        if "generateContent" in method_name or "generate" in method_name.lower():
            operation = "completion"
        elif "embed" in method_name.lower():
            operation = "embedding"
        elif "speech" in method_name.lower():
            operation = "transcribe"
        elif "translate" in method_name.lower():
            operation = "translate"

        # 2. Resolve per-associate identity
        auth_info = proto_payload.get("authenticationInfo", {})
        principal_email = auth_info.get("principalEmail", "")
        
        parsed_assoc_id = None
        if principal_email and "@" in principal_email:
            email_user = principal_email.split("@")[0]
            if email_user.isdigit() or re.match(r"^[a-zA-Z]\d+$", email_user):
                parsed_assoc_id = email_user
                
        request_metadata = proto_payload.get("requestMetadata", {})
        caller_supplied_id = (
            request_metadata.get("callerSuppliedUserAgent") or 
            request_metadata.get("x-employee-id")
        )

        associate_id = (
            parsed_assoc_id or
            caller_supplied_id or
            (identity_context or {}).get("associate_id") or
            principal_email or
            "unattributed-gcp-principal"
        )
        
        cost_centre = (identity_context or {}).get("cost_centre") or "CC-UNALLOCATED-GCP"
        project_code = (identity_context or {}).get("project_code") or f"PROJ-{project_id.upper()}"

        # 3. Parse additional detailed logs (model version, model type, latency)
        # Parse model version
        base_model = model
        model_version = None
        
        # Specific known base models
        known_base_models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash", "textembedding-gecko"]
        
        found_base = False
        for k_model in known_base_models:
            if model.startswith(k_model):
                base_model = k_model
                version_part = model[len(k_model):].strip("-")
                if version_part:
                    model_version = version_part
                found_base = True
                break
                
        if not found_base:
            # Fallback for unknown models
            parts = model.split("-")
            if len(parts) > 1 and re.match(r'^(\d+|exp|preview|stable)$', parts[-1]):
                base_model = "-".join(parts[:-1])
                model_version = parts[-1]
            else:
                base_model = model

        if not model_version:
            model_version = raw_data.get("model_version") or (json_payload or {}).get("model_version") or "stable"

        # Determine/Extract usage units
        input_tokens = 0
        output_tokens = 0
        cached_tokens = 0
        input_characters = 0
        output_characters = 0
        input_images = 0
        input_audio_seconds = 0.0
        input_video_seconds = 0.0

        if json_payload:
            input_tokens = int(json_payload.get("inputTokenCount") or json_payload.get("prompt_tokens") or 0)
            output_tokens = int(json_payload.get("outputTokenCount") or json_payload.get("candidates_tokens") or 0)
            cached_tokens = int(json_payload.get("cachedTokenCount") or json_payload.get("cached_tokens") or 0)
            input_characters = int(json_payload.get("inputCharacterCount") or json_payload.get("input_characters") or 0)
            output_characters = int(json_payload.get("outputCharacterCount") or json_payload.get("output_characters") or 0)
            input_images = int(json_payload.get("inputImageCount") or json_payload.get("input_images") or 0)
            input_audio_seconds = float(json_payload.get("inputAudioSeconds") or json_payload.get("input_audio_seconds") or 0.0)
            input_video_seconds = float(json_payload.get("inputVideoSeconds") or json_payload.get("input_video_seconds") or 0.0)

        if input_tokens == 0 and proto_payload:
            resp = proto_payload.get("response", {})
            metadata = resp.get("metadata", {}) if isinstance(resp, dict) else {}
            if isinstance(metadata, dict):
                input_tokens = int(metadata.get("tokenMetadata", {}).get("inputTokenCount", 0))
                output_tokens = int(metadata.get("tokenMetadata", {}).get("outputTokenCount", 0))

        # Model type classification
        model_type = raw_data.get("model_type") or (json_payload or {}).get("model_type")
        if not model_type:
            lower_model = base_model.lower()
            if "gemini" in lower_model:
                has_multimodal = (
                    input_images > 0 or 
                    input_audio_seconds > 0.0 or 
                    input_video_seconds > 0.0
                )
                model_type = "Multimodal" if has_multimodal else "LLM"
            elif "embedding" in lower_model or "gecko" in lower_model:
                model_type = "Embedding"
            elif "speech" in lower_model or "transcribe" in lower_model:
                model_type = "Speech"
            elif "translate" in lower_model:
                model_type = "Translation"
            else:
                model_type = "LLM"

        # Latency parsing
        latency_ms = raw_data.get("latency_ms") or (json_payload or {}).get("latency_ms") or (json_payload or {}).get("processing_time_ms")
        if latency_ms is not None:
            latency_ms = int(latency_ms)

        # Assemble canonical request units
        request_units = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        if cached_tokens > 0:
            request_units["cached_tokens"] = cached_tokens
        if input_characters > 0:
            request_units["input_characters"] = input_characters
        if output_characters > 0:
            request_units["output_characters"] = output_characters
        if input_images > 0:
            request_units["input_images"] = input_images
        if input_audio_seconds > 0.0:
            request_units["input_audio_seconds"] = input_audio_seconds
        if input_video_seconds > 0.0:
            request_units["input_video_seconds"] = input_video_seconds

        # 4. Calculate cost based on fine-grained metrics
        cost = 0.0
        if "cost" in raw_data:
            cost = float(raw_data["cost"])
        elif json_payload and "cost" in json_payload:
            cost = float(json_payload["cost"])
        else:
            price_key = base_model.lower().strip()
            if price_key not in self.PRICING:
                matched_key = "default"
                for k in self.PRICING.keys():
                    if k in price_key:
                        matched_key = k
                        break
                price_rule = self.PRICING[matched_key]
            else:
                price_rule = self.PRICING[price_key]

            # Calculation rules
            if "char" in price_rule and (input_characters > 0 or output_characters > 0):
                cost = ((input_characters + output_characters) / 1000000.0) * price_rule["char"]
            elif "sec" in price_rule and (input_audio_seconds > 0.0 or input_video_seconds > 0.0):
                cost = ((input_audio_seconds + input_video_seconds) / 1.0) * (price_rule["sec"] / 1000000.0) # check scaling
            else:
                # Token pricing with context caching and context scaling (NFR cost rules)
                is_long_context = input_tokens > 128000
                in_rate = price_rule.get("token_input_long" if is_long_context else "token_input", 1.00)
                out_rate = price_rule.get("token_output_long" if is_long_context else "token_output", 4.00)
                cached_rate = price_rule.get("token_cached", in_rate * 0.25)

                active_prompt_tokens = max(0, input_tokens - cached_tokens)
                
                # Token cost components
                cost += (active_prompt_tokens / 1000000.0) * in_rate
                cost += (cached_tokens / 1000000.0) * cached_rate
                cost += (output_tokens / 1000000.0) * out_rate

                # Multimodal cost components
                if input_images > 0 and "image" in price_rule:
                    cost += (input_images / 1000000.0) * price_rule["image"]
                if input_audio_seconds > 0.0 and "audio_sec" in price_rule:
                    cost += (input_audio_seconds / 1000000.0) * price_rule["audio_sec"]
                if input_video_seconds > 0.0 and "video_sec" in price_rule:
                    cost += (input_video_seconds / 1000000.0) * price_rule["video_sec"]

        return CanonicalUsageEvent(
            timestamp=timestamp,
            cloud="GCP",
            service=raw_data.get("serviceType", "Vertex AI"),
            region=region,
            account_id=project_id,
            resource_id=resource_id,
            operation=operation,
            associate_id=str(associate_id),
            cost_centre=cost_centre,
            project_code=project_code,
            request_units=request_units,
            cost=round(cost, 6),
            model_version=model_version,
            model_type=model_type,
            latency_ms=latency_ms
        )
