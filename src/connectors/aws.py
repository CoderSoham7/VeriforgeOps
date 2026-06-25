from typing import Dict, Any, Optional
from datetime import datetime
from src.connectors.base import BaseConnector
from src.schemas import CanonicalUsageEvent

class AWSConnector(BaseConnector):
    """
    Connector for Amazon Web Services (AWS) AI Services (e.g., AWS Bedrock, SageMaker, Comprehend).
    Processes AWS CloudWatch Logs, CloudTrail events, and Cost & Usage Reports (CUR).
    """

    # Estimated pricing dictionary per 1k tokens (in USD) for AWS Bedrock models
    PRICING_PER_1K = {
        "anthropic.claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "anthropic.claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "anthropic.claude-3-opus": {"input": 0.015, "output": 0.075},
        "anthropic.claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "amazon.nova-pro": {"input": 0.0008, "output": 0.0032},
        "default": {"input": 0.003, "output": 0.015}
    }

    def to_canonical(self, raw_data: Dict[str, Any], identity_context: Optional[Dict[str, Any]] = None) -> CanonicalUsageEvent:
        # 1. Extract basic telemetry fields
        timestamp = raw_data.get("eventTime") or datetime.utcnow().isoformat() + "Z"
        region = raw_data.get("awsRegion") or "us-east-1"
        account_id = raw_data.get("recipientAccountId") or "unknown-aws-account"

        request_params = raw_data.get("requestParameters", {})
        response_elements = raw_data.get("responseElements", {})
        
        # Model and operation details
        model_id = request_params.get("modelId") or raw_data.get("modelId", "unknown-model")
        
        # Operation type standardization
        event_name = raw_data.get("eventName", "InvokeModel")
        operation = "completion"
        if "embed" in event_name.lower() or "embedding" in model_id.lower():
            operation = "embedding"
        elif "chat" in event_name.lower():
            operation = "chat"

        # Simplify model ID for storage
        resource_id = model_id.split("/")[-1] if "/" in model_id else model_id

        # 2. Resolve per-associate identity (NFR-M1 requirement: stamp identity)
        # Parse AWS UserIdentity to see if we can resolve the employee ID from IAM role session name
        user_identity = raw_data.get("userIdentity", {})
        principal_id = user_identity.get("principalId", "")
        session_name = ""
        if ":" in principal_id:
            # AssumedRole principalId is typically ARID:session-name
            session_name = principal_id.split(":")[-1]
            if session_name.startswith("session-"):
                session_name = session_name[len("session-"):]

        # Check if stamped in request metadata/agent ARN
        associate_id = (
            user_identity.get("x-employee-id") or
            (identity_context or {}).get("associate_id") or
            (session_name if session_name.isdigit() else None) or
            session_name or
            user_identity.get("arn") or
            "unattributed-aws-principal"
        )
        
        cost_centre = (identity_context or {}).get("cost_centre") or "CC-UNALLOCATED-AWS"
        project_code = (identity_context or {}).get("project_code") or f"PROJ-{account_id}"

        # 3. Calculate usage metrics (request units / tokens)
        input_tokens = 0
        output_tokens = 0

        # Try extracting from responseElements (which contains model response headers or metadata)
        if response_elements:
            # Different response formats have different properties depending on the model
            input_tokens = int(
                response_elements.get("inputTextTokenCount") or 
                response_elements.get("inputTokenCount") or 
                0
            )
            output_tokens = int(
                response_elements.get("outputTextTokenCount") or 
                response_elements.get("outputTokenCount") or 
                0
            )

        # Fallback to direct parameters if supplied in raw_data (e.g. parsed metrics)
        if input_tokens == 0:
            input_tokens = int(raw_data.get("inputTokens", 0))
            output_tokens = int(raw_data.get("outputTokens", 0))

        request_units = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }

        # 4. Calculate cost
        cost = 0.0
        if "cost" in raw_data:
            cost = float(raw_data["cost"])
        else:
            # Normalize model name for lookup
            lookup_key = "default"
            for key in self.PRICING_PER_1K:
                if key in model_id.lower():
                    lookup_key = key
                    break
            
            price_rule = self.PRICING_PER_1K[lookup_key]
            cost = ((input_tokens / 1000.0) * price_rule["input"]) + ((output_tokens / 1000.0) * price_rule["output"])

        return CanonicalUsageEvent(
            timestamp=timestamp,
            cloud="AWS",
            service=raw_data.get("serviceType", "AWS Bedrock"),
            region=region,
            account_id=account_id,
            resource_id=resource_id,
            operation=operation,
            associate_id=str(associate_id),
            cost_centre=cost_centre,
            project_code=project_code,
            request_units=request_units,
            cost=round(cost, 6)
        )
