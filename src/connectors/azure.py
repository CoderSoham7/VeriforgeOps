from typing import Dict, Any, Optional
from datetime import datetime
from src.connectors.base import BaseConnector
from src.schemas import CanonicalUsageEvent

class AzureConnector(BaseConnector):
    """
    Connector for Microsoft Azure AI Services (e.g., Azure OpenAI, Azure AI Search, Azure Vision).
    Processes Azure Monitor diagnostic logs and subscription metadata.
    """

    # Estimated pricing dictionary per 1k tokens (in USD) for common Azure OpenAI models
    # to compute consumption cost in normalisation step if not pre-calculated
    PRICING_PER_1K = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "default": {"input": 0.01, "output": 0.03}
    }

    def to_canonical(self, raw_data: Dict[str, Any], identity_context: Optional[Dict[str, Any]] = None) -> CanonicalUsageEvent:
        # 1. Extract basic telemetry fields
        timestamp = raw_data.get("time") or datetime.utcnow().isoformat() + "Z"
        
        # Parse resource ID to extract subscription and resource name
        resource_id = raw_data.get("resourceId", "")
        subscription_id = "unknown-subscription"
        resource_name = "unknown-resource"
        if "/subscriptions/" in resource_id:
            parts = resource_id.split("/")
            try:
                sub_idx = parts.index("subscriptions")
                subscription_id = parts[sub_idx + 1]
                res_idx = parts.index("accounts") # for Cognitive Services
                resource_name = parts[res_idx + 1]
            except (ValueError, IndexError):
                pass

        properties = raw_data.get("properties", {})
        
        # Model, operation and region
        model = properties.get("modelName") or properties.get("model", "unknown-model")
        operation_name = raw_data.get("operationName", "unknown-operation")
        
        # Standardize operation type
        operation = "completion"
        if "chat" in operation_name.lower():
            operation = "chat"
        elif "embedding" in operation_name.lower():
            operation = "embedding"
        elif "translation" in operation_name.lower():
            operation = "translate"
            
        region = raw_data.get("location") or properties.get("region") or "eastus"

        # 2. Resolve per-associate identity (NFR-M1 requirement: stamp identity)
        # Check if internal API gateway stamped it in custom properties or headers
        associate_id = (
            properties.get("employeeId") or 
            properties.get("x-employee-id") or 
            properties.get("requestHeaderemployeeId") or
            (identity_context or {}).get("associate_id") or 
            "unattributed-azure-principal"
        )
        
        cost_centre = (
            properties.get("costCentre") or 
            (identity_context or {}).get("cost_centre") or 
            "CC-UNALLOCATED-AZURE"
        )
        
        project_code = (
            properties.get("projectCode") or 
            (identity_context or {}).get("project_code") or 
            "PROJ-GENERIC-AZURE"
        )

        # 3. Calculate usage metrics (request units / tokens)
        input_tokens = int(properties.get("tokensInput") or properties.get("promptTokens") or 0)
        output_tokens = int(properties.get("tokensOutput") or properties.get("completionTokens") or 0)
        total_tokens = input_tokens + output_tokens

        # Fallback if no specific prompt/completion tokens are broken down
        if total_tokens == 0:
            total_tokens = int(properties.get("totalTokens") or 0)
            input_tokens = total_tokens # Default assumption if undivided

        request_units = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        }

        # 4. Calculate cost based on model pricing (or ingest if provided)
        cost = 0.0
        if "cost" in properties:
            cost = float(properties["cost"])
        else:
            # Model lookup pricing
            price_rule = self.PRICING_PER_1K.get(model.lower(), self.PRICING_PER_1K["default"])
            cost = ((input_tokens / 1000.0) * price_rule["input"]) + ((output_tokens / 1000.0) * price_rule["output"])

        return CanonicalUsageEvent(
            timestamp=timestamp,
            cloud="Azure",
            service=raw_data.get("serviceType", "Azure OpenAI"),
            region=region,
            account_id=subscription_id,
            resource_id=resource_name,
            operation=operation,
            associate_id=associate_id,
            cost_centre=cost_centre,
            project_code=project_code,
            request_units=request_units,
            cost=round(cost, 6)
        )
