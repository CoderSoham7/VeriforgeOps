from typing import Dict, Any, Optional
from datetime import datetime
from src.connectors.base import BaseConnector
from src.schemas import CanonicalUsageEvent

class SanasConnector(BaseConnector):
    """
    Connector for Sanas Voice AI accent equalization and speech clarity services.
    Processes custom Webhook/API events from Sanas edge clients and call-center platforms.
    """

    # Sanas pricing is based on duration (cost per audio minute)
    # Default: $0.015 per minute of speech equalization
    COST_PER_MINUTE = 0.015

    def to_canonical(self, raw_data: Dict[str, Any], identity_context: Optional[Dict[str, Any]] = None) -> CanonicalUsageEvent:
        # 1. Extract basic telemetry fields
        timestamp = raw_data.get("timestamp") or datetime.utcnow().isoformat() + "Z"
        region = raw_data.get("region") or "global"
        
        # In voice systems, account_id represents the call center branch or account API key
        account_id = raw_data.get("clientId") or raw_data.get("accountId") or "sanas-cognizant-enterprise"
        resource_id = raw_data.get("sessionId") or raw_data.get("callId", "unknown-session")

        # 2. Resolve per-associate identity
        # The agent identifier in call logs corresponds to the employee ID
        associate_id = (
            raw_data.get("agentId") or
            raw_data.get("employeeId") or
            (identity_context or {}).get("associate_id") or
            "unattributed-sanas-agent"
        )
        
        cost_centre = (
            raw_data.get("costCentre") or 
            (identity_context or {}).get("cost_centre") or 
            "CC-UNALLOCATED-SANAS"
        )
        
        project_code = (
            raw_data.get("projectCode") or 
            (identity_context or {}).get("project_code") or 
            "PROJ-SANAS-GLOBAL"
        )

        # 3. Calculate usage metrics (duration in seconds and count of streams)
        duration_seconds = float(raw_data.get("durationSeconds") or raw_data.get("audioDuration", 0))
        
        request_units = {
            "duration_seconds": duration_seconds,
            "duration_minutes": duration_seconds / 60.0,
            "stream_count": int(raw_data.get("streamCount", 1))
        }

        # 4. Calculate cost
        cost = 0.0
        if "cost" in raw_data:
            cost = float(raw_data["cost"])
        else:
            cost = (duration_seconds / 60.0) * self.COST_PER_MINUTE

        return CanonicalUsageEvent(
            timestamp=timestamp,
            cloud="Sanas",
            service="Sanas AI",
            region=region,
            account_id=account_id,
            resource_id=resource_id,
            operation="speech_clarification",
            associate_id=str(associate_id),
            cost_centre=cost_centre,
            project_code=project_code,
            request_units=request_units,
            cost=round(cost, 6)
        )
