from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.schemas import CanonicalUsageEvent

class BaseConnector(ABC):
    """
    Abstract Base Class for all cloud provider and tool data source connectors.
    Each connector is responsible for translating provider-specific raw telemetry
    data into the canonical VeriForge Ops schema.
    """

    @abstractmethod
    def to_canonical(self, raw_data: Dict[str, Any], identity_context: Optional[Dict[str, Any]] = None) -> CanonicalUsageEvent:
        """
        Translates a provider-specific log or telemetry record into a CanonicalUsageEvent.

        Args:
            raw_data: The raw telemetry data dictionary from the cloud provider/tool.
            identity_context: Optional metadata containing associate details (associate_id, 
                              cost_centre, project_code) if not present in the raw logs.

        Returns:
            A validated CanonicalUsageEvent instance.
        """
        pass
