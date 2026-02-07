"""
Tests for Technical Architecture Reference Diagram artifact.

Tests schema validation, Mermaid diagram generation, and parsing utilities.
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from prdgen.schemas.architecture_schema import (
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
from prdgen.architecture import (
    parse_architecture_markdown,
    parse_architecture_options_markdown,
    validate_architecture_schema,
    generate_mermaid_from_schema,
    format_architecture_markdown,
    format_architecture_options_markdown,
    has_mermaid_block,
)
from prdgen.config import GenerationConfig
from prdgen.artifact_types import ArtifactType, ARTIFACT_FILENAMES, ARTIFACT_NAMES
from prdgen.prompt_templates import (
    get_system_prompt,
    get_system_prompt_from_file,
    has_system_prompt_file,
    validate_system_prompt_file,
    SYSTEM_PROMPT_DIR,
)


# Sample test data
SAMPLE_ARCHITECTURE_MD = """# Technical Architecture Reference

## Title
E-Commerce Platform Technical Architecture

## Overview
A scalable e-commerce platform supporting web and mobile clients with microservices architecture.

## Assumptions
- Cloud deployment on AWS
- PostgreSQL for primary data storage

## Open Questions
- What is the expected peak load?
- Multi-region deployment needed?

---

## Components

### Web Application
- **ID:** web_app
- **Type:** client
- **Responsibilities:**
  - User interface for browsing products
  - Shopping cart management
- **Data Stores:** None
- **Security Notes:**
  - HTTPS only
  - XSS protection

### API Gateway
- **ID:** api_gateway
- **Type:** gateway
- **Responsibilities:**
  - Request routing
  - Rate limiting
  - Authentication
- **Data Stores:** None
- **Security Notes:**
  - JWT validation
  - Rate limiting per client

### Order Service
- **ID:** order_service
- **Type:** service
- **Responsibilities:**
  - Order processing
  - Inventory management
- **Data Stores:** PostgreSQL
- **Security Notes:**
  - Encrypted at rest

### Primary Database
- **ID:** primary_db
- **Type:** database
- **Responsibilities:**
  - Persistent data storage
- **Data Stores:** PostgreSQL
- **Security Notes:**
  - Encrypted at rest

---

## Data Flows

### Client to Gateway
- **From:** web_app
- **To:** api_gateway
- **Description:** User requests
- **Protocol:** HTTPS
- **Auth:** JWT
- **Data:**
  - User credentials
  - Product queries

### Gateway to Order Service
- **From:** api_gateway
- **To:** order_service
- **Description:** Order operations
- **Protocol:** gRPC
- **Auth:** mTLS
- **Data:**
  - Order details

---

## Non-Functional Requirements

### Availability
99.9% uptime SLA

### Performance
Response time < 200ms for 95th percentile

### Security
All data encrypted in transit and at rest

### Compliance
PCI-DSS compliant for payment processing

### Observability
Centralized logging with ELK stack

---

## Deployment View

### Environment
AWS with multi-AZ deployment

### Scaling Notes
- API Gateway scales horizontally
- Database uses read replicas

### Multi-Tenancy
Single tenant deployment

---

## Architecture Diagram

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        web_app[Web Application]
    end

    subgraph Platform["Core Platform"]
        api_gateway[API Gateway]
        order_service[Order Service]
    end

    subgraph Data["Data Layer"]
        primary_db[(Primary Database)]
    end

    web_app -->|HTTPS| api_gateway
    api_gateway -->|gRPC| order_service
    order_service -->|SQL| primary_db
```
"""


class TestArchitectureSchema:
    """Tests for ArchitectureSchema dataclass"""

    def test_create_valid_schema(self):
        """Test creating a valid architecture schema"""
        component = Component(
            id="api_service",
            name="API Service",
            type="service",
            responsibilities=["Handle API requests"],
            data_stores=["PostgreSQL"],
            security_notes=["JWT auth"]
        )

        data_flow = DataFlow(
            from_component="client",
            to_component="api_service",
            description="API requests",
            protocol="HTTPS",
            auth="JWT",
            data=["User data"]
        )

        schema = ArchitectureSchema(
            title="Test Architecture",
            overview="Test system overview",
            assumptions=["Cloud deployment"],
            open_questions=["Scale requirements?"],
            components=[component],
            data_flows=[data_flow],
            nfrs=NFRs(availability="99.9%", performance="<200ms"),
            deployment_view=DeploymentView(environment="AWS"),
            diagram=Diagram(mermaid="flowchart TB\n  A --> B")
        )

        assert schema.title == "Test Architecture"
        assert len(schema.components) == 1
        assert len(schema.data_flows) == 1

    def test_schema_to_dict(self):
        """Test converting schema to dictionary"""
        schema = ArchitectureSchema(
            title="Test",
            overview="Overview",
            components=[
                Component(id="svc", name="Service", type="service")
            ],
            data_flows=[]
        )

        d = schema.to_dict()

        assert d["title"] == "Test"
        assert d["overview"] == "Overview"
        assert len(d["components"]) == 1
        assert d["components"][0]["id"] == "svc"

    def test_schema_to_json(self):
        """Test converting schema to JSON string"""
        schema = ArchitectureSchema(
            title="Test",
            overview="Overview"
        )

        json_str = schema.to_json()

        assert '"title": "Test"' in json_str
        assert '"overview": "Overview"' in json_str


class TestComponentType:
    """Tests for ComponentType enum"""

    def test_all_component_types_exist(self):
        """Test all expected component types are defined"""
        expected_types = [
            "client", "gateway", "service", "worker", "database",
            "cache", "queue", "stream", "ml_model", "vector_db",
            "idp", "observability", "external_system"
        ]

        for type_str in expected_types:
            assert validate_component_type(type_str), f"Missing component type: {type_str}"

    def test_invalid_component_type(self):
        """Test that invalid component types are rejected"""
        assert not validate_component_type("invalid_type")
        assert not validate_component_type("microservice")
        assert not validate_component_type("")

    def test_get_valid_types(self):
        """Test getting list of valid component types"""
        types = get_valid_component_types()

        assert "service" in types
        assert "database" in types
        assert "ml_model" in types
        assert len(types) == 13


class TestSchemaValidation:
    """Tests for schema validation"""

    def test_valid_schema_passes(self):
        """Test that a valid schema passes validation"""
        data = {
            "title": "Test Architecture",
            "overview": "Test overview",
            "components": [
                {"id": "svc1", "name": "Service 1", "type": "service"},
                {"id": "db1", "name": "Database 1", "type": "database"}
            ],
            "data_flows": [
                {"from": "svc1", "to": "db1", "description": "Data flow"}
            ],
            "diagram": {"mermaid": "flowchart TB\n  svc1 --> db1"}
        }

        is_valid, errors = validate_architecture_schema(data)

        assert is_valid, f"Validation failed: {errors}"

    def test_missing_required_field(self):
        """Test validation fails for missing required fields"""
        data = {
            "overview": "Test overview"
            # missing title
        }

        is_valid, errors = validate_architecture_schema(data)

        assert not is_valid
        assert any("title" in e for e in errors)

    def test_invalid_component_type_rejected(self):
        """Test validation fails for invalid component type"""
        data = {
            "title": "Test",
            "overview": "Test",
            "components": [
                {"id": "svc", "name": "Service", "type": "invalid_type"}
            ],
            "data_flows": []
        }

        is_valid, errors = validate_architecture_schema(data)

        assert not is_valid
        assert any("invalid_type" in e.lower() or "component type" in e.lower() for e in errors)

    def test_duplicate_component_ids_rejected(self):
        """Test validation fails for duplicate component IDs"""
        data = {
            "title": "Test",
            "overview": "Test",
            "components": [
                {"id": "svc", "name": "Service 1", "type": "service"},
                {"id": "svc", "name": "Service 2", "type": "service"}  # Duplicate
            ],
            "data_flows": []
        }

        is_valid, errors = validate_architecture_schema(data)

        assert not is_valid
        assert any("duplicate" in e.lower() for e in errors)

    def test_invalid_data_flow_reference(self):
        """Test validation fails when data flow references unknown component"""
        data = {
            "title": "Test",
            "overview": "Test",
            "components": [
                {"id": "svc", "name": "Service", "type": "service"}
            ],
            "data_flows": [
                {"from": "svc", "to": "unknown_component", "description": "Flow"}
            ]
        }

        is_valid, errors = validate_architecture_schema(data)

        assert not is_valid
        assert any("unknown" in e.lower() for e in errors)


class TestMermaidGeneration:
    """Tests for Mermaid diagram generation"""

    def test_has_mermaid_block(self):
        """Test detection of Mermaid code block"""
        md_with_mermaid = """
# Architecture

```mermaid
flowchart TB
    A --> B
```
"""
        md_without_mermaid = """
# Architecture

No diagram here.
"""

        assert has_mermaid_block(md_with_mermaid)
        assert not has_mermaid_block(md_without_mermaid)

    def test_generate_mermaid_from_components(self):
        """Test generating Mermaid diagram from components"""
        schema = ArchitectureSchema(
            title="Test",
            overview="Test",
            components=[
                Component(id="web", name="Web App", type="client"),
                Component(id="api", name="API", type="service"),
                Component(id="db", name="Database", type="database"),
            ],
            data_flows=[
                DataFlow(from_component="web", to_component="api", description="Requests", protocol="HTTPS"),
                DataFlow(from_component="api", to_component="db", description="Queries", protocol="SQL"),
            ]
        )

        mermaid = generate_mermaid_from_schema(schema)

        assert "flowchart TB" in mermaid
        assert "web" in mermaid
        assert "api" in mermaid
        assert "db" in mermaid
        assert "-->" in mermaid

    def test_mermaid_subgraph_grouping(self):
        """Test that components are grouped into correct subgraphs"""
        schema = ArchitectureSchema(
            title="Test",
            overview="Test",
            components=[
                Component(id="web", name="Web", type="client"),
                Component(id="api", name="API", type="service"),
                Component(id="db", name="DB", type="database"),
            ],
            data_flows=[]
        )

        mermaid = generate_mermaid_from_schema(schema)

        assert 'subgraph Client' in mermaid
        assert 'subgraph Platform' in mermaid or 'subgraph' in mermaid
        assert 'subgraph Data' in mermaid

    def test_ai_layer_only_when_ai_components(self):
        """Test that AI Layer subgraph only appears when AI components exist"""
        schema_no_ai = ArchitectureSchema(
            title="Test",
            overview="Test",
            components=[
                Component(id="api", name="API", type="service"),
            ],
            data_flows=[]
        )

        schema_with_ai = ArchitectureSchema(
            title="Test",
            overview="Test",
            components=[
                Component(id="api", name="API", type="service"),
                Component(id="ml", name="ML Model", type="ml_model"),
            ],
            data_flows=[]
        )

        mermaid_no_ai = generate_mermaid_from_schema(schema_no_ai)
        mermaid_with_ai = generate_mermaid_from_schema(schema_with_ai)

        # AI Layer should not appear without AI components
        assert 'subgraph AI' not in mermaid_no_ai or 'ml' not in mermaid_no_ai
        # AI Layer should appear with AI components
        assert 'ml' in mermaid_with_ai


class TestMarkdownParsing:
    """Tests for parsing architecture markdown"""

    def test_parse_sample_markdown(self):
        """Test parsing the sample architecture markdown"""
        schema = parse_architecture_markdown(SAMPLE_ARCHITECTURE_MD)

        assert "E-Commerce" in schema.title
        assert len(schema.components) >= 3
        assert len(schema.data_flows) >= 1
        assert len(schema.assumptions) >= 1
        assert len(schema.open_questions) >= 1

    def test_parse_extracts_components(self):
        """Test that component extraction works correctly"""
        schema = parse_architecture_markdown(SAMPLE_ARCHITECTURE_MD)

        component_ids = {c.id for c in schema.components}

        assert "web_app" in component_ids
        assert "api_gateway" in component_ids
        assert "order_service" in component_ids

    def test_parse_extracts_data_flows(self):
        """Test that data flow extraction works correctly"""
        schema = parse_architecture_markdown(SAMPLE_ARCHITECTURE_MD)

        assert len(schema.data_flows) >= 1

        flow = schema.data_flows[0]
        assert flow.from_component
        assert flow.to_component
        assert flow.protocol

    def test_parse_extracts_nfrs(self):
        """Test that NFR extraction works correctly"""
        schema = parse_architecture_markdown(SAMPLE_ARCHITECTURE_MD)

        assert schema.nfrs.availability != "Not specified"
        assert schema.nfrs.performance != "Not specified"

    def test_parse_extracts_mermaid(self):
        """Test that Mermaid diagram is extracted"""
        schema = parse_architecture_markdown(SAMPLE_ARCHITECTURE_MD)

        assert schema.diagram.mermaid
        assert "flowchart" in schema.diagram.mermaid


class TestMarkdownFormatting:
    """Tests for formatting architecture to markdown"""

    def test_format_includes_all_sections(self):
        """Test that formatted markdown includes all required sections"""
        schema = ArchitectureSchema(
            title="Test Architecture",
            overview="Test overview",
            assumptions=["Assumption 1"],
            open_questions=["Question 1"],
            components=[
                Component(id="svc", name="Service", type="service", responsibilities=["Handle requests"])
            ],
            data_flows=[
                DataFlow(from_component="client", to_component="svc", description="Requests")
            ],
            nfrs=NFRs(availability="99.9%"),
            deployment_view=DeploymentView(environment="AWS"),
            diagram=Diagram(mermaid="flowchart TB\n  A --> B")
        )

        md = format_architecture_markdown(schema)

        assert "## Title" in md
        assert "## Overview" in md
        assert "## Assumptions" in md
        assert "## Components" in md
        assert "## Data Flows" in md
        assert "## Non-Functional Requirements" in md
        assert "## Deployment View" in md
        assert "## Architecture Diagram" in md
        assert "```mermaid" in md

    def test_format_includes_mermaid_block(self):
        """Test that formatted markdown includes Mermaid code block"""
        schema = ArchitectureSchema(
            title="Test",
            overview="Test",
            diagram=Diagram(mermaid="flowchart TB\n  A --> B")
        )

        md = format_architecture_markdown(schema)

        assert has_mermaid_block(md)


class TestArtifactRegistration:
    """Tests for artifact type registration"""

    def test_technical_architecture_in_artifact_types(self):
        """Test that TECHNICAL_ARCHITECTURE is registered in artifact types"""
        assert hasattr(ArtifactType, 'TECHNICAL_ARCHITECTURE')
        assert ArtifactType.TECHNICAL_ARCHITECTURE.value == "technical_architecture"

    def test_artifact_has_filename(self):
        """Test that artifact has a registered filename"""
        assert ArtifactType.TECHNICAL_ARCHITECTURE in ARTIFACT_FILENAMES
        assert ARTIFACT_FILENAMES[ArtifactType.TECHNICAL_ARCHITECTURE] == "architecture_reference.md"

    def test_artifact_has_display_name(self):
        """Test that artifact has a display name"""
        assert ArtifactType.TECHNICAL_ARCHITECTURE in ARTIFACT_NAMES
        assert "Architecture" in ARTIFACT_NAMES[ArtifactType.TECHNICAL_ARCHITECTURE]


class TestSystemPromptFile:
    """Tests for file-based system prompt loading for architecture artifact"""

    def test_architecture_prompt_file_exists(self):
        """Test that the architecture system prompt file exists"""
        prompt_path = SYSTEM_PROMPT_DIR / "architecture.txt"
        assert prompt_path.exists(), f"System prompt file not found: {prompt_path}"

    def test_architecture_prompt_file_not_empty(self):
        """Test that the architecture system prompt file is not empty"""
        prompt_path = SYSTEM_PROMPT_DIR / "architecture.txt"
        content = prompt_path.read_text(encoding='utf-8').strip()
        assert len(content) > 0, "System prompt file is empty"

    def test_architecture_prompt_loaded_from_file(self):
        """Test that the architecture prompt is loaded from file"""
        assert has_system_prompt_file("architecture"), \
            "Architecture prompt should be loaded from file"

    def test_architecture_prompt_content_correct(self):
        """Test that the loaded prompt has expected content"""
        prompt = get_system_prompt_from_file("architecture")
        assert prompt is not None, "Failed to load architecture prompt from file"
        assert "Principal Software Architect" in prompt, \
            "Prompt should start with 'You are a Principal Software Architect'"
        assert "reference architecture" in prompt.lower(), \
            "Prompt should mention 'reference architecture'"

    def test_validate_system_prompt_file(self):
        """Test the validate_system_prompt_file utility"""
        is_valid = validate_system_prompt_file("architecture")
        assert is_valid, "Architecture system prompt file should be valid"

    def test_get_system_prompt_uses_file(self):
        """Test that get_system_prompt() returns file-based prompt when available"""
        prompt = get_system_prompt("architecture")
        file_prompt = get_system_prompt_from_file("architecture")
        # When file exists, get_system_prompt should return the file content
        assert prompt == file_prompt, \
            "get_system_prompt should return file-based prompt when available"


# Sample architecture options markdown for testing
SAMPLE_OPTIONS_MD = """
### User Management

#### Option 1: Centralized Authentication Service

**Description:** Single authentication service handling all identity operations with centralized session management.

**Assumptions:**
- Organization has existing IdP infrastructure
- SSO is a requirement

**Trade-offs:**
| Pros | Cons |
|------|------|
| Single source of truth for identity | Single point of failure |
| Easier compliance auditing | May require additional HA investment |

**When to Choose:** When enterprise SSO integration is required and centralized audit logging is important.

```mermaid
flowchart TB
    client[Client] --> idp[Central IDP]
    idp --> user_svc[User Service]
```

#### Option 2: Federated Authentication

**Description:** Distributed authentication with service-level token validation and decentralized identity management.

**Assumptions:**
- Services need autonomous operation
- Network partitioning is a concern

**Trade-offs:**
| Pros | Cons |
|------|------|
| High availability | More complex token management |
| Service independence | Eventual consistency in user state |

**When to Choose:** When services must operate independently during network partitions.

```mermaid
flowchart TB
    client[Client] --> svc_a[Service A]
    client --> svc_b[Service B]
    svc_a --> token_validator[Token Validator]
    svc_b --> token_validator
```

### Data Processing

#### Option 1: Batch Processing

**Description:** Traditional batch-oriented data processing with scheduled jobs.

**Assumptions:**
- Data latency of minutes is acceptable
- Processing windows are predictable

**Trade-offs:**
| Pros | Cons |
|------|------|
| Simpler implementation | Higher latency |
| Easier debugging | Resource spikes during batch runs |

**When to Choose:** When real-time processing is not required.

```mermaid
flowchart TB
    source[Data Source] --> batch[Batch Processor]
    batch --> db[(Database)]
```
"""


class TestArchitectureOptions:
    """Tests for architecture options feature"""

    def test_options_disabled_by_default(self):
        """Test that architecture options are disabled by default"""
        cfg = GenerationConfig()
        assert cfg.enable_architecture_options is False, \
            "enable_architecture_options should be False by default"

    def test_options_can_be_enabled(self):
        """Test that architecture options can be enabled"""
        cfg = GenerationConfig(enable_architecture_options=True)
        assert cfg.enable_architecture_options is True

    def test_architecture_option_dataclass(self):
        """Test ArchitectureOption dataclass structure"""
        option = ArchitectureOption(
            option_id="opt_1",
            label="Test Option",
            description="A test option",
            assumptions=["Assumption 1"],
            tradeoffs={"pros": ["Pro 1"], "cons": ["Con 1"]},
            when_to_choose="When testing",
            diagram=Diagram(mermaid="flowchart TB\n  A --> B")
        )

        assert option.option_id == "opt_1"
        assert option.label == "Test Option"
        assert len(option.assumptions) == 1
        assert "pros" in option.tradeoffs
        assert "cons" in option.tradeoffs
        assert option.diagram.mermaid.startswith("flowchart")

    def test_capability_options_dataclass(self):
        """Test CapabilityOptions dataclass structure"""
        option = ArchitectureOption(
            option_id="opt_1",
            label="Option 1",
            description="Test"
        )

        cap_options = CapabilityOptions(
            capability_id="user_mgmt",
            capability_name="User Management",
            options=[option]
        )

        assert cap_options.capability_id == "user_mgmt"
        assert cap_options.capability_name == "User Management"
        assert len(cap_options.options) == 1

    def test_parse_options_extracts_capabilities(self):
        """Test that parsing extracts capability options"""
        options = parse_architecture_options_markdown(SAMPLE_OPTIONS_MD)

        assert len(options) >= 2, "Should extract at least 2 capabilities"

        cap_names = [opt.capability_name for opt in options]
        assert "User Management" in cap_names
        assert "Data Processing" in cap_names

    def test_parse_options_extracts_multiple_options(self):
        """Test that parsing extracts multiple options per capability"""
        options = parse_architecture_options_markdown(SAMPLE_OPTIONS_MD)

        user_mgmt = next((o for o in options if "User" in o.capability_name), None)
        assert user_mgmt is not None
        assert len(user_mgmt.options) >= 2, "User Management should have at least 2 options"

    def test_parse_options_extracts_tradeoffs(self):
        """Test that trade-offs are extracted correctly"""
        options = parse_architecture_options_markdown(SAMPLE_OPTIONS_MD)

        user_mgmt = next((o for o in options if "User" in o.capability_name), None)
        assert user_mgmt is not None

        option = user_mgmt.options[0]
        assert len(option.tradeoffs.get("pros", [])) > 0, "Should have pros"
        assert len(option.tradeoffs.get("cons", [])) > 0, "Should have cons"

    def test_parse_options_extracts_mermaid(self):
        """Test that Mermaid diagrams are extracted for each option"""
        options = parse_architecture_options_markdown(SAMPLE_OPTIONS_MD)

        for cap_opt in options:
            for option in cap_opt.options:
                assert option.diagram.mermaid, f"Option '{option.label}' should have Mermaid diagram"
                assert "flowchart" in option.diagram.mermaid.lower() or "graph" in option.diagram.mermaid.lower()

    def test_format_options_markdown(self):
        """Test formatting options to markdown"""
        option = ArchitectureOption(
            option_id="opt_1",
            label="Test Pattern",
            description="A test pattern for validation",
            assumptions=["Assumption A", "Assumption B"],
            tradeoffs={"pros": ["Pro 1", "Pro 2"], "cons": ["Con 1"]},
            when_to_choose="When testing formatting",
            diagram=Diagram(mermaid="flowchart TB\n    A --> B")
        )

        cap_options = CapabilityOptions(
            capability_id="test_cap",
            capability_name="Test Capability",
            options=[option]
        )

        md = format_architecture_options_markdown([cap_options])

        assert "## Architecture Options by Capability" in md
        assert "### Test Capability" in md
        assert "#### Option 1: Test Pattern" in md
        assert "**Trade-offs:**" in md
        assert "| Pros | Cons |" in md
        assert "```mermaid" in md
        assert "illustrative reference patterns" in md.lower()

    def test_schema_includes_options_in_to_dict(self):
        """Test that ArchitectureSchema.to_dict() includes options"""
        option = ArchitectureOption(
            option_id="opt_1",
            label="Test",
            description="Test option"
        )

        cap_options = CapabilityOptions(
            capability_id="test",
            capability_name="Test Cap",
            options=[option]
        )

        schema = ArchitectureSchema(
            title="Test Architecture",
            overview="Test overview",
            architecture_options=[cap_options]
        )

        d = schema.to_dict()

        assert "architecture_options" in d
        assert len(d["architecture_options"]) == 1
        assert d["architecture_options"][0]["capability_id"] == "test"
        assert len(d["architecture_options"][0]["options"]) == 1

    def test_format_architecture_includes_options(self):
        """Test that format_architecture_markdown includes options section"""
        option = ArchitectureOption(
            option_id="opt_1",
            label="Test Pattern",
            description="Test description",
            diagram=Diagram(mermaid="flowchart TB\n    A --> B")
        )

        cap_options = CapabilityOptions(
            capability_id="test",
            capability_name="Test Capability",
            options=[option]
        )

        schema = ArchitectureSchema(
            title="Test Architecture",
            overview="Test overview",
            components=[Component(id="svc", name="Service", type="service")],
            data_flows=[],
            architecture_options=[cap_options]
        )

        md = format_architecture_markdown(schema)

        assert "## Architecture Options by Capability" in md
        assert "### Test Capability" in md

    def test_options_prompt_file_exists(self):
        """Test that architecture_options system prompt file exists"""
        prompt_path = SYSTEM_PROMPT_DIR / "architecture_options.txt"
        assert prompt_path.exists(), f"System prompt file not found: {prompt_path}"

    def test_options_prompt_file_not_empty(self):
        """Test that architecture_options system prompt file is not empty"""
        prompt_path = SYSTEM_PROMPT_DIR / "architecture_options.txt"
        content = prompt_path.read_text(encoding='utf-8').strip()
        assert len(content) > 0, "System prompt file is empty"

    def test_options_prompt_content_correct(self):
        """Test that options prompt has expected content"""
        prompt = get_system_prompt("architecture_options")
        assert "Principal Software Architect" in prompt
        assert "trade-off" in prompt.lower() or "tradeoff" in prompt.lower()
        assert "illustrative" in prompt.lower() or "reference pattern" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
