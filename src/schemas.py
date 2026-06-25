from pydantic import BaseModel, Field, field_validator
from typing import Dict, Union, Optional
from datetime import datetime
import re

class CanonicalUsageEvent(BaseModel):
    """
    Canonical usage event schema for VeriForge Ops ingestion pipeline.
    This schema corresponds to the data structure ingested into the canonical
    data mart and published to the ingestion Pub/Sub topic.
    """
    timestamp: str = Field(
        ..., 
        description="ISO 8601 timestamp of when the event occurred",
        examples=["2026-06-19T11:46:02Z"]
    )
    cloud: str = Field(
        ..., 
        description="Cloud provider name (e.g., Azure, GCP, AWS, Sanas, AI Tools Data Mart)"
    )
    service: str = Field(
        ..., 
        description="Specific service name (e.g., Azure OpenAI, Vertex AI, AWS Bedrock, Sanas AI, Claude Code)"
    )
    region: str = Field(
        ..., 
        description="Region where the service was called (e.g., eastus, us-central1, us-east-1)"
    )
    account_id: str = Field(
        ..., 
        description="Subscription ID, Project ID, or Account ID associated with the resource"
    )
    resource_id: str = Field(
        ..., 
        description="Identifier of the specific resource used (e.g., model name, deployment ID)"
    )
    operation: str = Field(
        ..., 
        description="The type of operation (e.g., chat, completion, embedding, translate, transcribe, ocr)"
    )
    associate_id: str = Field(
        ..., 
        description="Associate identity (employee ID) stamped by the API gateway or resolved"
    )
    cost_centre: str = Field(
        ..., 
        description="Billing cost center associated with the associate"
    )
    project_code: str = Field(
        ..., 
        description="Project billing code associated with the task"
    )
    request_units: Dict[str, Union[int, float]] = Field(
        ..., 
        description="Dictionary representing the usage metrics (e.g., input_tokens, output_tokens, characters, duration_seconds)"
    )
    cost: float = Field(
        ..., 
        description="Calculated cost of the operation in USD (float)"
    )
    model_version: Optional[str] = Field(
        default=None, 
        description="Specific model version/snapshot tag (e.g. '001', '002', 'exp')"
    )
    model_type: Optional[str] = Field(
        default=None, 
        description="General category of the model (e.g. 'LLM', 'Multimodal', 'Embedding', 'Speech')"
    )
    latency_ms: Optional[int] = Field(
        default=None, 
        description="API execution latency in milliseconds"
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_iso8601(cls, v: str) -> str:
        # Standard ISO 8601 check: verify it parses
        try:
            # Handle standard formats
            if v.endswith('Z'):
                datetime.fromisoformat(v[:-1] + '+00:00')
            else:
                datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("Timestamp must be a valid ISO 8601 string (e.g., 'YYYY-MM-DDTHH:MM:SSZ')")
        return v

    @field_validator("associate_id")
    @classmethod
    def validate_associate_id(cls, v: str) -> str:
        # Cognizant employee ID check (optional standard, e.g. numeric ID)
        if not v.strip():
            raise ValueError("Associate ID cannot be empty")
        return v

    @field_validator("cost")
    @classmethod
    def validate_cost_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Cost cannot be negative")
        return v
