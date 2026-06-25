from typing import Dict, Any, Optional
from datetime import datetime
from src.connectors.base import BaseConnector
from src.schemas import CanonicalUsageEvent

class AIToolsConnector(BaseConnector):
    """
    Connector for corporate AI Tools Data Mart (associate productivity tools:
    e.g., GitHub Copilot, Claude Code, Windsurf, Gemini Workspace, Microsoft Copilot).
    Normalizes corporate licensing and invocation telemetry.
    """

    # Default billing rate per invocation if cost is not explicitly defined in raw records
    DEFAULT_RATE_PER_INVOCATION = 0.002

    def to_canonical(self, raw_data: Dict[str, Any], identity_context: Optional[Dict[str, Any]] = None) -> CanonicalUsageEvent:
        # 1. Extract basic telemetry fields
        timestamp = (
            raw_data.get("timestamp") or 
            raw_data.get("eventTime") or 
            datetime.utcnow().isoformat() + "Z"
        )
        region = raw_data.get("region") or raw_data.get("location") or "corporate-local"
        
        # Tool identity
        tool_name = raw_data.get("toolName") or raw_data.get("tool_name") or "generic-ai-tool"
        
        # The license ID or subscription plan identifier
        account_id = raw_data.get("licenseId") or raw_data.get("subscriptionPlan") or "corporate-license-pool"
        resource_id = raw_data.get("clientType") or raw_data.get("environment") or "desktop-ide"

        # 2. Resolve per-associate identity (Typically clear in internal tools)
        associate_id = (
            raw_data.get("employeeId") or 
            raw_data.get("employee_id") or 
            raw_data.get("associate_id") or
            (identity_context or {}).get("associate_id") or
            "unattributed-associate"
        )
        
        cost_centre = (
            raw_data.get("costCentre") or 
            raw_data.get("cost_centre") or 
            (identity_context or {}).get("cost_centre") or 
            "CC-UNALLOCATED-AITOOLS"
        )
        
        project_code = (
            raw_data.get("projectCode") or 
            raw_data.get("project_code") or 
            (identity_context or {}).get("project_code") or 
            "PROJ-AI-PRODUCTIVITY"
        )

        # 3. Calculate usage metrics (requests, inputs, outputs, etc.)
        prompt_tokens = int(raw_data.get("promptTokens") or raw_data.get("input_tokens") or 0)
        completion_tokens = int(raw_data.get("completionTokens") or raw_data.get("output_tokens") or 0)
        request_count = int(raw_data.get("requestCount") or raw_data.get("invocations", 1))

        request_units = {
            "invocations": request_count,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }

        # 4. Calculate cost
        cost = 0.0
        if "cost" in raw_data:
            cost = float(raw_data["cost"])
        else:
            # If token values exist, we can estimate cost based on typical GPT-4o / Claude rates
            if prompt_tokens > 0 or completion_tokens > 0:
                cost = ((prompt_tokens / 1000.0) * 0.003) + ((completion_tokens / 1000.0) * 0.015)
            else:
                cost = request_count * self.DEFAULT_RATE_PER_INVOCATION

        return CanonicalUsageEvent(
            timestamp=timestamp,
            cloud="AI Tools Data Mart",
            service=tool_name,
            region=region,
            account_id=account_id,
            resource_id=resource_id,
            operation=raw_data.get("operation", "code_generation"),
            associate_id=str(associate_id),
            cost_centre=cost_centre,
            project_code=project_code,
            request_units=request_units,
            cost=round(cost, 6)
        )
