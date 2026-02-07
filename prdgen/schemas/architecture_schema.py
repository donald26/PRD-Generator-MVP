"""
JSON Schema and dataclasses for Technical Architecture Reference Diagram artifact.
Defines the structure for architecture documentation including components,
data flows, NFRs, deployment view, and Mermaid diagram generation.
"""
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import re


class ComponentType(str, Enum):
    """Valid component types for architecture diagrams"""
    CLIENT = "client"
    GATEWAY = "gateway"
    SERVICE = "service"
    WORKER = "worker"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    STREAM = "stream"
    ML_MODEL = "ml_model"
    VECTOR_DB = "vector_db"
    IDP = "idp"
    OBSERVABILITY = "observability"
    EXTERNAL_SYSTEM = "external_system"


@dataclass
class Component:
    """Represents a system component in the architecture"""
    id: str
    name: str
    type: str  # ComponentType value
    responsibilities: List[str] = field(default_factory=list)
    data_stores: List[str] = field(default_factory=list)
    security_notes: List[str] = field(default_factory=list)


@dataclass
class DataFlow:
    """Represents data flow between components"""
    from_component: str  # component_id
    to_component: str    # component_id
    description: str
    protocol: str = "Not specified"
    auth: str = "Not specified"
    data: List[str] = field(default_factory=list)


@dataclass
class NFRs:
    """Non-functional requirements"""
    availability: str = "Not specified"
    performance: str = "Not specified"
    security: str = "Not specified"
    compliance: str = "Not specified"
    observability: str = "Not specified"


@dataclass
class DeploymentView:
    """Deployment and scaling information"""
    environment: str = "Not specified"
    scaling_notes: List[str] = field(default_factory=list)
    multi_tenancy: str = "Not specified"


@dataclass
class Diagram:
    """Mermaid diagram content"""
    mermaid: str = ""


@dataclass
class ArchitectureOption:
    """A single architecture option/pattern for a capability"""
    option_id: str
    label: str  # e.g., "Event-Driven Pattern", "Synchronous API Pattern"
    description: str
    assumptions: List[str] = field(default_factory=list)
    tradeoffs: Dict[str, List[str]] = field(default_factory=lambda: {"pros": [], "cons": []})
    when_to_choose: str = "Not specified"
    diagram: Diagram = field(default_factory=Diagram)


@dataclass
class CapabilityOptions:
    """Architecture options for a specific capability"""
    capability_id: str
    capability_name: str
    options: List[ArchitectureOption] = field(default_factory=list)


@dataclass
class ArchitectureSchema:
    """Complete architecture reference schema"""
    title: str
    overview: str
    assumptions: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    components: List[Component] = field(default_factory=list)
    data_flows: List[DataFlow] = field(default_factory=list)
    nfrs: NFRs = field(default_factory=NFRs)
    deployment_view: DeploymentView = field(default_factory=DeploymentView)
    diagram: Diagram = field(default_factory=Diagram)
    # Optional: Architecture options per capability (when enable_architecture_options=True)
    architecture_options: List[CapabilityOptions] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper nested structure"""
        result = {
            "title": self.title,
            "overview": self.overview,
            "assumptions": self.assumptions,
            "open_questions": self.open_questions,
            "components": [asdict(c) for c in self.components],
            "data_flows": [
                {
                    "from": df.from_component,
                    "to": df.to_component,
                    "description": df.description,
                    "protocol": df.protocol,
                    "auth": df.auth,
                    "data": df.data
                }
                for df in self.data_flows
            ],
            "nfrs": asdict(self.nfrs),
            "deployment_view": asdict(self.deployment_view),
            "diagram": asdict(self.diagram)
        }
        # Include architecture_options only if present
        if self.architecture_options:
            result["architecture_options"] = [
                {
                    "capability_id": cap_opt.capability_id,
                    "capability_name": cap_opt.capability_name,
                    "options": [
                        {
                            "option_id": opt.option_id,
                            "label": opt.label,
                            "description": opt.description,
                            "assumptions": opt.assumptions,
                            "tradeoffs": opt.tradeoffs,
                            "when_to_choose": opt.when_to_choose,
                            "diagram": asdict(opt.diagram)
                        }
                        for opt in cap_opt.options
                    ]
                }
                for cap_opt in self.architecture_options
            ]
        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# JSON Schema for validation
ARCHITECTURE_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["title", "overview", "components", "data_flows"],
    "properties": {
        "title": {"type": "string"},
        "overview": {"type": "string"},
        "assumptions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "open_questions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "components": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "type"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": [t.value for t in ComponentType]
                    },
                    "responsibilities": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "data_stores": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "security_notes": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        "data_flows": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["from", "to", "description"],
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "description": {"type": "string"},
                    "protocol": {"type": "string"},
                    "auth": {"type": "string"},
                    "data": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        "nfrs": {
            "type": "object",
            "properties": {
                "availability": {"type": "string"},
                "performance": {"type": "string"},
                "security": {"type": "string"},
                "compliance": {"type": "string"},
                "observability": {"type": "string"}
            }
        },
        "deployment_view": {
            "type": "object",
            "properties": {
                "environment": {"type": "string"},
                "scaling_notes": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "multi_tenancy": {"type": "string"}
            }
        },
        "diagram": {
            "type": "object",
            "properties": {
                "mermaid": {"type": "string"}
            }
        },
        "architecture_options": {
            "type": "array",
            "description": "Optional architecture options per capability",
            "items": {
                "type": "object",
                "required": ["capability_id", "capability_name", "options"],
                "properties": {
                    "capability_id": {"type": "string"},
                    "capability_name": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["option_id", "label", "description"],
                            "properties": {
                                "option_id": {"type": "string"},
                                "label": {"type": "string"},
                                "description": {"type": "string"},
                                "assumptions": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "tradeoffs": {
                                    "type": "object",
                                    "properties": {
                                        "pros": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "cons": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    }
                                },
                                "when_to_choose": {"type": "string"},
                                "diagram": {
                                    "type": "object",
                                    "properties": {
                                        "mermaid": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


def validate_component_type(type_str: str) -> bool:
    """Check if component type is valid"""
    try:
        ComponentType(type_str)
        return True
    except ValueError:
        return False


def get_valid_component_types() -> List[str]:
    """Return list of valid component type values"""
    return [t.value for t in ComponentType]
