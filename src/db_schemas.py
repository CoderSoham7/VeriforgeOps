from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from bson.objectid import ObjectId

class PyObjectId(str):
    """
    Helper class to allow Pydantic models to serialise and deserialise
    MongoDB ObjectId values.
    """
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, *args, **kwargs):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        # Format mapping for JSON Schema generation in OpenAPI/FastAPI docs
        json_schema = handler(core_schema)
        json_schema.update(type="string", format="object-id")
        return json_schema

# -------------------------------------------------------------
# 1. MongoDB schemas mapping HLD logical models (§6.1)
# -------------------------------------------------------------

class AgentVersionHistory(BaseModel):
    """Represents a history entry in the Agent document."""
    version: str = Field(..., description="Agent configuration version string (e.g. 'v1.0.2')")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(..., description="Employee username or ID who deployed/configured this version")
    config_snapshot: Dict[str, Any] = Field(..., description="Full system configuration parameters dictionary")


class AgentDocument(BaseModel):
    """
    MongoDB schema for 'agents' collection.
    Tracks status, version history, routing rules, and provider models.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    agent_id: str = Field(..., description="Unique code identifier of the agent")
    name: str = Field(..., description="Friendly display name of the agent")
    provider: str = Field(..., description="Underlying provider service (e.g. AWS, Azure, GCP)")
    model_id: str = Field(..., description="Model ID string (e.g., 'gpt-4o', 'gemini-1.5-pro')")
    status: str = Field("Active", description="Deployment status (Active, Staging, Draining, Inactive)")
    version: str = Field("v1.0.0", description="Active deployment version")
    version_history: List[AgentVersionHistory] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AlertDocument(BaseModel):
    """
    MongoDB schema for 'alerts' collection.
    Logs critical and warning security/quality events.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    alert_id: str = Field(..., description="Unique alert trace ID")
    agent_id: str = Field(..., description="Reference ID of the triggering agent")
    severity: str = Field("warning", description="Severity level: 'critical' or 'warning'")
    anomaly_score: float = Field(..., description="Trigger score (0 - 100) from drift/anomaly logic")
    alert_type: str = Field(..., description="Alert type category (e.g. 'pii_leakage', 'hallucination', 'drift')")
    message: str = Field(..., description="Descriptive notification message detail")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = Field(False, description="Flag indicating if operations team resolved this alert")
    resolved_by: Optional[str] = Field(None, description="Operator user ID resolving this alert")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AnomalyDocument(BaseModel):
    """
    MongoDB schema for 'anomalies' collection.
    Tracks mathematical behavior or semantic drifts.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    agent_id: str = Field(..., description="Reference agent ID")
    score: float = Field(..., description="Behavior deviation score (0 - 100)")
    anomaly_type: str = Field(..., description="Categorisation of anomaly (e.g., 'cost_spike', 'react_loop', 'semantic_drift')")
    details: Dict[str, Any] = Field(default_factory=dict, description="Metadata parameters supporting detection logic")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class CircuitBreakerDocument(BaseModel):
    """
    MongoDB schema for 'circuit_breakers' collection.
    Monitors breaker states and automatic shutdown operations.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    agent_id: str = Field(..., description="Reference agent ID")
    state: str = Field("CLOSED", description="State: CLOSED (normal), OPEN (quarantined/disabled), HALF-OPEN")
    trigger_count: int = Field(0, description="Total automatic trip operations count")
    last_tripped_at: Optional[datetime] = Field(None, description="Timestamp of last trip execution")
    reason: Optional[str] = Field(None, description="Reason or exception triggering the trip")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class AgentCostMetricDocument(BaseModel):
    """
    MongoDB schema for 'agent_cost_metrics' collection.
    Holds cumulative month-to-date (MTD) usage data per agent.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    agent_id: str = Field(..., description="Reference agent ID")
    billing_month: str = Field(..., description="Target billing month string (e.g., '2026-06')")
    mtd_input_tokens: int = Field(0, description="Cumulative input prompt tokens count")
    mtd_output_tokens: int = Field(0, description="Cumulative output response tokens count")
    mtd_cost: float = Field(0.0, description="Total running month-to-date token cost in USD")
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class EpisodeCostDocument(BaseModel):
    """
    MongoDB schema for 'episode_costs' collection.
    Detailed transaction level telemetry capturing individual agentic executions.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    episode_id: str = Field(..., description="Unique runtime invocation span GUID")
    agent_id: str = Field(..., description="Reference agent ID")
    model_id: str = Field(..., description="Model identifier used")
    associate_id: str = Field(..., description="Target employee ID attributed to call")
    input_tokens: int = Field(0)
    output_tokens: int = Field(0)
    cost: float = Field(..., description="Call execution cost in USD")
    duration_ms: int = Field(..., description="Inference API response latency")
    model_version: Optional[str] = Field(default=None, description="Specific version/snapshot of model")
    model_type: Optional[str] = Field(default=None, description="Category of the model (e.g. LLM, Multimodal)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class DailyCostMetricDocument(BaseModel):
    """
    MongoDB schema for 'daily_cost_metrics' collection.
    Tracks rolling 30-day aggregate costs for FinOps trending charts.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    date: str = Field(..., description="Date identifier string (e.g. '2026-06-19')")
    cloud: str = Field(..., description="Provider source (e.g. AWS, Azure, GCP)")
    service: str = Field(..., description="Target service (e.g. Vertex AI, Azure OpenAI)")
    total_tokens: int = Field(0, description="Combined token sum")
    total_cost: float = Field(0.0, description="Aggregate cost for this day in USD")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class CanonicalUsageEventDocument(BaseModel):
    """
    MongoDB schema for 'canonical_usage_events' collection inside the Integrated Data Mart.
    Stores normalized ingestion records.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    timestamp: datetime = Field(..., description="Exact event timestamp parsed from source logs")
    cloud: str = Field(..., description="Azure, GCP, AWS, Sanas, or AI Tools Data Mart")
    service: str = Field(..., description="Detailed service/tool catalog name")
    region: str = Field(..., description="GCP region or zone")
    account_id: str = Field(..., description="GCP project ID or Cloud subscription details")
    resource_id: str = Field(..., description="Resource name or endpoint path identifier")
    operation: str = Field(..., description="Standardized action (completion, translate, transcribe, ocr)")
    associate_id: str = Field(..., description="Attributed employee ID")
    cost_centre: str = Field(..., description="Corporate department billing center")
    project_code: str = Field(..., description="Project code target identifier")
    request_units: Dict[str, Any] = Field(..., description="Metrics metrics dictionary (tokens, seconds)")
    cost: float = Field(..., description="Cost of operation in USD")
    model_version: Optional[str] = Field(default=None, description="Specific model version/snapshot tag (e.g. '001', '002', 'exp')")
    model_type: Optional[str] = Field(default=None, description="General category of the model (e.g. 'LLM', 'Multimodal', 'Embedding', 'Speech')")
    latency_ms: Optional[int] = Field(default=None, description="API execution latency in milliseconds")
    ingested_at: datetime = Field(default_factory=datetime.utcnow, description="Record insertion timestamp")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
