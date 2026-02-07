"""JSON schemas for structured artifact outputs."""
from .architecture_schema import (
    ArchitectureSchema,
    Component,
    DataFlow,
    NFRs,
    DeploymentView,
    Diagram,
    ArchitectureOption,
    CapabilityOptions,
    ComponentType,
    ARCHITECTURE_JSON_SCHEMA,
    validate_component_type,
    get_valid_component_types,
)

__all__ = [
    "ArchitectureSchema",
    "Component",
    "DataFlow",
    "NFRs",
    "DeploymentView",
    "Diagram",
    "ArchitectureOption",
    "CapabilityOptions",
    "ComponentType",
    "ARCHITECTURE_JSON_SCHEMA",
    "validate_component_type",
    "get_valid_component_types",
]
