"""
Utilities for parsing, validating, and formatting Technical Architecture artifacts.
"""
import re
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

from .schemas.architecture_schema import (
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
)

LOG = logging.getLogger("prdgen.architecture")

# Mapping of component types to Mermaid subgraphs
SUBGRAPH_MAPPING: Dict[str, str] = {
    ComponentType.CLIENT.value: "Client",
    ComponentType.GATEWAY.value: "Platform",
    ComponentType.SERVICE.value: "Platform",
    ComponentType.WORKER.value: "Platform",
    ComponentType.DATABASE.value: "Data",
    ComponentType.CACHE.value: "Data",
    ComponentType.QUEUE.value: "Data",
    ComponentType.STREAM.value: "Data",
    ComponentType.ML_MODEL.value: "AI",
    ComponentType.VECTOR_DB.value: "AI",
    ComponentType.IDP.value: "External",
    ComponentType.OBSERVABILITY.value: "External",
    ComponentType.EXTERNAL_SYSTEM.value: "External",
}

# Mermaid node shape templates by component type
NODE_SHAPES: Dict[str, str] = {
    ComponentType.CLIENT.value: "{}[{}]",           # Rectangle
    ComponentType.GATEWAY.value: "{}[{}]",          # Rectangle
    ComponentType.SERVICE.value: "{}[{}]",          # Rectangle
    ComponentType.WORKER.value: "{}[[{}]]",         # Subroutine (stadium)
    ComponentType.DATABASE.value: "{}[({})]",       # Cylinder
    ComponentType.CACHE.value: "{}[({})]",          # Cylinder
    ComponentType.QUEUE.value: "{}>{}]",            # Asymmetric
    ComponentType.STREAM.value: "{}>{}]",           # Asymmetric
    ComponentType.ML_MODEL.value: "{}{{{{{}}}}}",   # Hexagon
    ComponentType.VECTOR_DB.value: "{}[({})]",      # Cylinder
    ComponentType.IDP.value: "{}[/{}\\]",           # Trapezoid
    ComponentType.OBSERVABILITY.value: "{}(({}))", # Circle
    ComponentType.EXTERNAL_SYSTEM.value: "{}[{}]", # Rectangle
}


def parse_architecture_markdown(markdown: str) -> ArchitectureSchema:
    """
    Parse generated architecture markdown into structured ArchitectureSchema.

    Args:
        markdown: Raw markdown output from LLM

    Returns:
        ArchitectureSchema with extracted data
    """
    # Extract title
    title_match = re.search(r'^##?\s*Title\s*\n+(.+?)(?:\n\n|\n##)', markdown, re.MULTILINE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Technical Architecture"

    # Extract overview
    overview_match = re.search(r'^##?\s*Overview\s*\n+(.+?)(?:\n\n##|\n---)', markdown, re.MULTILINE | re.DOTALL)
    overview = overview_match.group(1).strip() if overview_match else ""

    # Extract assumptions
    assumptions = _extract_list_section(markdown, "Assumptions")

    # Extract open questions
    open_questions = _extract_list_section(markdown, "Open Questions")

    # Extract components
    components = _extract_components(markdown)

    # Extract data flows
    data_flows = _extract_data_flows(markdown)

    # Extract NFRs
    nfrs = _extract_nfrs(markdown)

    # Extract deployment view
    deployment_view = _extract_deployment_view(markdown)

    # Extract Mermaid diagram
    mermaid_diagram = _extract_mermaid(markdown)

    return ArchitectureSchema(
        title=title,
        overview=overview,
        assumptions=assumptions,
        open_questions=open_questions,
        components=components,
        data_flows=data_flows,
        nfrs=nfrs,
        deployment_view=deployment_view,
        diagram=Diagram(mermaid=mermaid_diagram)
    )


def _extract_list_section(markdown: str, section_name: str) -> List[str]:
    """Extract bullet list from a section"""
    pattern = rf'^##?\s*{section_name}\s*\n+((?:[-*]\s+.+\n?)+)'
    match = re.search(pattern, markdown, re.MULTILINE)
    if not match:
        return []

    items = []
    for line in match.group(1).split('\n'):
        line = line.strip()
        if line.startswith(('-', '*')):
            item = re.sub(r'^[-*]\s+', '', line).strip()
            if item:
                items.append(item)
    return items


def _extract_components(markdown: str) -> List[Component]:
    """Extract components from markdown"""
    components = []

    # Find the Components section
    components_section = re.search(
        r'^##?\s*Components?\s*\n(.+?)(?:\n---|\n##\s*Data\s*Flows?|\Z)',
        markdown,
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    if not components_section:
        return components

    section_text = components_section.group(1)

    # Find each component block (### Component Name)
    component_blocks = re.split(r'\n###\s+', section_text)

    for block in component_blocks[1:]:  # Skip first empty/header part
        if not block.strip():
            continue

        # Extract component name from first line
        lines = block.split('\n')
        name = lines[0].strip()

        # Extract fields
        id_match = re.search(r'\*\*ID:\*\*\s*(.+)', block)
        type_match = re.search(r'\*\*Type:\*\*\s*(.+)', block)

        component_id = id_match.group(1).strip() if id_match else name.lower().replace(' ', '_')
        component_type = type_match.group(1).strip().lower() if type_match else "service"

        # Validate component type
        if not validate_component_type(component_type):
            LOG.warning(f"Invalid component type '{component_type}' for {name}, defaulting to 'service'")
            component_type = "service"

        # Extract responsibilities
        responsibilities = _extract_nested_list(block, "Responsibilities")

        # Extract data stores
        data_stores_match = re.search(r'\*\*Data Stores:\*\*\s*(.+)', block)
        data_stores = []
        if data_stores_match:
            ds_text = data_stores_match.group(1).strip()
            if ds_text.lower() not in ('none', 'n/a', ''):
                data_stores = [s.strip() for s in ds_text.split(',')]

        # Extract security notes
        security_notes = _extract_nested_list(block, "Security Notes")

        components.append(Component(
            id=component_id,
            name=name,
            type=component_type,
            responsibilities=responsibilities,
            data_stores=data_stores,
            security_notes=security_notes
        ))

    return components


def _extract_nested_list(text: str, field_name: str) -> List[str]:
    """Extract a nested bullet list under a field"""
    pattern = rf'\*\*{field_name}:\*\*\s*\n((?:\s+[-*]\s+.+\n?)+)'
    match = re.search(pattern, text)
    if not match:
        return []

    items = []
    for line in match.group(1).split('\n'):
        line = line.strip()
        if line.startswith(('-', '*')):
            item = re.sub(r'^[-*]\s+', '', line).strip()
            if item:
                items.append(item)
    return items


def _extract_data_flows(markdown: str) -> List[DataFlow]:
    """Extract data flows from markdown"""
    data_flows = []

    # Find the Data Flows section
    flows_section = re.search(
        r'^##?\s*Data\s*Flows?\s*\n(.+?)(?:\n---|\n##\s*Non-Functional|\Z)',
        markdown,
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    if not flows_section:
        return data_flows

    section_text = flows_section.group(1)

    # Find each flow block (### Flow Name)
    flow_blocks = re.split(r'\n###\s+', section_text)

    for block in flow_blocks[1:]:  # Skip first empty/header part
        if not block.strip():
            continue

        # Extract fields
        from_match = re.search(r'\*\*From:\*\*\s*(.+)', block)
        to_match = re.search(r'\*\*To:\*\*\s*(.+)', block)
        desc_match = re.search(r'\*\*Description:\*\*\s*(.+)', block)
        protocol_match = re.search(r'\*\*Protocol:\*\*\s*(.+)', block)
        auth_match = re.search(r'\*\*Auth:\*\*\s*(.+)', block)

        if not from_match or not to_match:
            continue

        # Extract data list
        data_items = _extract_nested_list(block, "Data")

        data_flows.append(DataFlow(
            from_component=from_match.group(1).strip(),
            to_component=to_match.group(1).strip(),
            description=desc_match.group(1).strip() if desc_match else "Data flow",
            protocol=protocol_match.group(1).strip() if protocol_match else "Not specified",
            auth=auth_match.group(1).strip() if auth_match else "Not specified",
            data=data_items
        ))

    return data_flows


def _extract_nfrs(markdown: str) -> NFRs:
    """Extract non-functional requirements from markdown"""
    nfrs = NFRs()

    # Find the NFRs section
    nfr_section = re.search(
        r'^##?\s*Non-Functional\s*Requirements?\s*\n(.+?)(?:\n---|\n##\s*Deployment|\Z)',
        markdown,
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    if not nfr_section:
        return nfrs

    section_text = nfr_section.group(1)

    # Extract each NFR subsection
    for field in ['availability', 'performance', 'security', 'compliance', 'observability']:
        pattern = rf'###\s*{field}\s*\n+(.+?)(?:\n###|\Z)'
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value and value.lower() not in ('not specified', 'n/a', 'tbd'):
                setattr(nfrs, field, value)

    return nfrs


def _extract_deployment_view(markdown: str) -> DeploymentView:
    """Extract deployment view from markdown"""
    deployment = DeploymentView()

    # Find the Deployment section
    deploy_section = re.search(
        r'^##?\s*Deployment\s*View?\s*\n(.+?)(?:\n---|\n##\s*Architecture\s*Diagram|\Z)',
        markdown,
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    if not deploy_section:
        return deployment

    section_text = deploy_section.group(1)

    # Extract environment
    env_match = re.search(r'###\s*Environment\s*\n+(.+?)(?:\n###|\Z)', section_text, re.DOTALL)
    if env_match:
        deployment.environment = env_match.group(1).strip()

    # Extract scaling notes
    deployment.scaling_notes = _extract_nested_list(section_text, "Scaling Notes")
    if not deployment.scaling_notes:
        # Try as subsection
        scaling_match = re.search(r'###\s*Scaling\s*Notes?\s*\n+((?:[-*]\s+.+\n?)+)', section_text)
        if scaling_match:
            for line in scaling_match.group(1).split('\n'):
                line = line.strip()
                if line.startswith(('-', '*')):
                    item = re.sub(r'^[-*]\s+', '', line).strip()
                    if item:
                        deployment.scaling_notes.append(item)

    # Extract multi-tenancy
    mt_match = re.search(r'###\s*Multi-Tenancy\s*\n+(.+?)(?:\n###|\Z)', section_text, re.DOTALL)
    if mt_match:
        deployment.multi_tenancy = mt_match.group(1).strip()

    return deployment


def _extract_mermaid(markdown: str) -> str:
    """Extract Mermaid diagram code from markdown"""
    mermaid_match = re.search(r'```mermaid\n(.+?)\n```', markdown, re.DOTALL)
    if mermaid_match:
        return mermaid_match.group(1).strip()
    return ""


def validate_architecture_schema(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate architecture data against JSON schema.

    Args:
        data: Dictionary representation of architecture

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Check required fields
    for field in ['title', 'overview']:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")

    # Validate components
    if 'components' in data:
        component_ids = set()
        for i, comp in enumerate(data['components']):
            if 'id' not in comp:
                errors.append(f"Component {i} missing 'id' field")
            elif comp['id'] in component_ids:
                errors.append(f"Duplicate component ID: {comp['id']}")
            else:
                component_ids.add(comp['id'])

            if 'type' in comp and not validate_component_type(comp['type']):
                errors.append(f"Invalid component type '{comp['type']}' for component '{comp.get('id', i)}'")

        # Validate data flow references
        if 'data_flows' in data:
            for i, flow in enumerate(data['data_flows']):
                from_id = flow.get('from', '')
                to_id = flow.get('to', '')
                if from_id and from_id not in component_ids:
                    errors.append(f"Data flow {i} references unknown component: {from_id}")
                if to_id and to_id not in component_ids:
                    errors.append(f"Data flow {i} references unknown component: {to_id}")

    # Check for Mermaid diagram
    if 'diagram' in data and 'mermaid' in data['diagram']:
        mermaid = data['diagram']['mermaid']
        if mermaid and not mermaid.strip().startswith(('flowchart', 'graph', 'sequenceDiagram', 'classDiagram')):
            errors.append("Mermaid diagram should start with a valid diagram type (flowchart, graph, etc.)")

    return (len(errors) == 0, errors)


def generate_mermaid_from_schema(schema: ArchitectureSchema) -> str:
    """
    Generate or enhance Mermaid diagram from schema components and data flows.

    Args:
        schema: ArchitectureSchema with components and data flows

    Returns:
        Valid Mermaid flowchart syntax
    """
    if not schema.components:
        return schema.diagram.mermaid or ""

    # If there's already a valid diagram, return it
    if schema.diagram.mermaid and schema.diagram.mermaid.strip().startswith(('flowchart', 'graph')):
        return schema.diagram.mermaid

    lines = ["flowchart TB"]

    # Group components by subgraph
    subgraphs: Dict[str, List[Component]] = {
        "Client": [],
        "Platform": [],
        "Data": [],
        "AI": [],
        "External": []
    }

    for comp in schema.components:
        subgraph = SUBGRAPH_MAPPING.get(comp.type, "Platform")
        subgraphs[subgraph].append(comp)

    # Generate subgraphs (only non-empty ones)
    subgraph_labels = {
        "Client": "Client Layer",
        "Platform": "Core Platform",
        "Data": "Data Layer",
        "AI": "AI Layer",
        "External": "External Integrations"
    }

    for sg_name, sg_label in subgraph_labels.items():
        if subgraphs[sg_name]:
            lines.append(f'    subgraph {sg_name}["{sg_label}"]')
            for comp in subgraphs[sg_name]:
                shape = NODE_SHAPES.get(comp.type, "{}[{}]")
                node = shape.format(comp.id, comp.name)
                lines.append(f"        {node}")
            lines.append("    end")
            lines.append("")

    # Generate data flow arrows
    for flow in schema.data_flows:
        label = flow.protocol if flow.protocol != "Not specified" else ""
        if label:
            lines.append(f"    {flow.from_component} -->|{label}| {flow.to_component}")
        else:
            lines.append(f"    {flow.from_component} --> {flow.to_component}")

    return "\n".join(lines)


def save_architecture_json(schema: ArchitectureSchema, output_path: Path) -> None:
    """
    Save architecture schema to JSON file.

    Args:
        schema: ArchitectureSchema to save
        output_path: Path to output JSON file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    json_content = schema.to_json(indent=2)
    output_path.write_text(json_content, encoding='utf-8')
    LOG.info(f"Saved architecture JSON to {output_path}")


def format_architecture_markdown(schema: ArchitectureSchema) -> str:
    """
    Format ArchitectureSchema back to well-structured markdown.

    Args:
        schema: ArchitectureSchema to format

    Returns:
        Formatted markdown string with embedded Mermaid diagram
    """
    lines = []

    # Title
    lines.append("# Technical Architecture Reference")
    lines.append("")
    lines.append("## Title")
    lines.append(schema.title)
    lines.append("")

    # Overview
    lines.append("## Overview")
    lines.append(schema.overview)
    lines.append("")

    # Assumptions
    if schema.assumptions:
        lines.append("## Assumptions")
        for assumption in schema.assumptions:
            lines.append(f"- {assumption}")
        lines.append("")

    # Open Questions
    if schema.open_questions:
        lines.append("## Open Questions")
        for question in schema.open_questions:
            lines.append(f"- {question}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Components
    lines.append("## Components")
    lines.append("")
    for comp in schema.components:
        lines.append(f"### {comp.name}")
        lines.append(f"- **ID:** {comp.id}")
        lines.append(f"- **Type:** {comp.type}")
        lines.append("- **Responsibilities:**")
        for resp in comp.responsibilities:
            lines.append(f"  - {resp}")
        lines.append(f"- **Data Stores:** {', '.join(comp.data_stores) if comp.data_stores else 'None'}")
        if comp.security_notes:
            lines.append("- **Security Notes:**")
            for note in comp.security_notes:
                lines.append(f"  - {note}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Data Flows
    lines.append("## Data Flows")
    lines.append("")
    for i, flow in enumerate(schema.data_flows, 1):
        lines.append(f"### Flow {i}: {flow.from_component} -> {flow.to_component}")
        lines.append(f"- **From:** {flow.from_component}")
        lines.append(f"- **To:** {flow.to_component}")
        lines.append(f"- **Description:** {flow.description}")
        lines.append(f"- **Protocol:** {flow.protocol}")
        lines.append(f"- **Auth:** {flow.auth}")
        if flow.data:
            lines.append("- **Data:**")
            for d in flow.data:
                lines.append(f"  - {d}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # NFRs
    lines.append("## Non-Functional Requirements")
    lines.append("")
    lines.append("### Availability")
    lines.append(schema.nfrs.availability)
    lines.append("")
    lines.append("### Performance")
    lines.append(schema.nfrs.performance)
    lines.append("")
    lines.append("### Security")
    lines.append(schema.nfrs.security)
    lines.append("")
    lines.append("### Compliance")
    lines.append(schema.nfrs.compliance)
    lines.append("")
    lines.append("### Observability")
    lines.append(schema.nfrs.observability)
    lines.append("")

    lines.append("---")
    lines.append("")

    # Deployment View
    lines.append("## Deployment View")
    lines.append("")
    lines.append("### Environment")
    lines.append(schema.deployment_view.environment)
    lines.append("")
    lines.append("### Scaling Notes")
    for note in schema.deployment_view.scaling_notes:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("### Multi-Tenancy")
    lines.append(schema.deployment_view.multi_tenancy)
    lines.append("")

    lines.append("---")
    lines.append("")

    # Architecture Diagram
    lines.append("## Architecture Diagram")
    lines.append("")

    # Ensure we have a Mermaid diagram
    mermaid_code = schema.diagram.mermaid
    if not mermaid_code:
        mermaid_code = generate_mermaid_from_schema(schema)

    lines.append("```mermaid")
    lines.append(mermaid_code)
    lines.append("```")
    lines.append("")

    # Architecture Options (if present)
    if schema.architecture_options:
        options_md = format_architecture_options_markdown(schema.architecture_options)
        lines.append(options_md)

    return "\n".join(lines)


def has_mermaid_block(markdown: str) -> bool:
    """Check if markdown contains a Mermaid code block"""
    return bool(re.search(r'```mermaid\n.+?\n```', markdown, re.DOTALL))


def parse_architecture_options_markdown(markdown: str) -> List[CapabilityOptions]:
    """
    Parse architecture options markdown into structured CapabilityOptions.

    Args:
        markdown: Raw markdown output from LLM containing architecture options

    Returns:
        List of CapabilityOptions with parsed data
    """
    capability_options = []

    # Split by capability headers (### Capability Name)
    capability_blocks = re.split(r'\n###\s+(?=[A-Z])', markdown)

    for block in capability_blocks[1:]:  # Skip first empty/header part
        if not block.strip():
            continue

        lines = block.split('\n')
        capability_name = lines[0].strip()
        capability_id = capability_name.lower().replace(' ', '_')

        # Parse options within this capability
        options = _parse_options_from_block(block)

        if options:
            capability_options.append(CapabilityOptions(
                capability_id=capability_id,
                capability_name=capability_name,
                options=options
            ))

    return capability_options


def _parse_options_from_block(block: str) -> List[ArchitectureOption]:
    """Parse individual options from a capability block"""
    options = []

    # Split by option headers (#### Option N: Label)
    option_blocks = re.split(r'\n####\s+Option\s+\d+:\s+', block)

    for i, opt_block in enumerate(option_blocks[1:], 1):  # Skip first part
        if not opt_block.strip():
            continue

        lines = opt_block.split('\n')
        label = lines[0].strip()
        option_id = f"option_{i}_{label.lower().replace(' ', '_').replace('-', '_')}"

        # Extract description
        desc_match = re.search(r'\*\*Description:\*\*\s*(.+?)(?:\n\n|\n\*\*)', opt_block, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract assumptions
        assumptions = _extract_nested_list(opt_block, "Assumptions")

        # Extract trade-offs (table format or nested lists)
        tradeoffs = _parse_tradeoffs(opt_block)

        # Extract when to choose
        when_match = re.search(r'\*\*When to Choose:\*\*\s*(.+?)(?:\n\n|\n```|\Z)', opt_block, re.DOTALL)
        when_to_choose = when_match.group(1).strip() if when_match else "Not specified"

        # Extract Mermaid diagram
        mermaid = _extract_mermaid(opt_block)

        options.append(ArchitectureOption(
            option_id=option_id,
            label=label,
            description=description,
            assumptions=assumptions,
            tradeoffs=tradeoffs,
            when_to_choose=when_to_choose,
            diagram=Diagram(mermaid=mermaid)
        ))

    return options


def _parse_tradeoffs(text: str) -> Dict[str, List[str]]:
    """Parse trade-offs from markdown table or nested lists"""
    tradeoffs = {"pros": [], "cons": []}

    # Try table format first: | Pros | Cons |
    table_match = re.search(
        r'\|\s*Pros\s*\|\s*Cons\s*\|.*?\n\|[-\s|]+\|\n((?:\|.+\|\n?)+)',
        text,
        re.IGNORECASE | re.DOTALL
    )

    if table_match:
        rows = table_match.group(1).strip().split('\n')
        for row in rows:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            if len(cells) >= 2:
                if cells[0] and cells[0] not in ('-', ''):
                    tradeoffs["pros"].append(cells[0])
                if cells[1] and cells[1] not in ('-', ''):
                    tradeoffs["cons"].append(cells[1])
    else:
        # Try nested list format
        # Look for **Pros:** or ### Pros section
        pros_match = re.search(
            r'(?:\*\*Pros:\*\*|###\s*Pros)\s*\n((?:\s*[-*]\s+.+\n?)+)',
            text,
            re.IGNORECASE
        )
        if pros_match:
            for line in pros_match.group(1).split('\n'):
                line = line.strip()
                if line.startswith(('-', '*')):
                    item = re.sub(r'^[-*]\s+', '', line).strip()
                    if item:
                        tradeoffs["pros"].append(item)

        cons_match = re.search(
            r'(?:\*\*Cons:\*\*|###\s*Cons)\s*\n((?:\s*[-*]\s+.+\n?)+)',
            text,
            re.IGNORECASE
        )
        if cons_match:
            for line in cons_match.group(1).split('\n'):
                line = line.strip()
                if line.startswith(('-', '*')):
                    item = re.sub(r'^[-*]\s+', '', line).strip()
                    if item:
                        tradeoffs["cons"].append(item)

    return tradeoffs


def format_architecture_options_markdown(options: List[CapabilityOptions]) -> str:
    """
    Format architecture options as markdown section.

    Args:
        options: List of CapabilityOptions to format

    Returns:
        Formatted markdown string
    """
    if not options:
        return ""

    lines = []
    lines.append("---")
    lines.append("")
    lines.append("## Architecture Options by Capability")
    lines.append("")
    lines.append("> **Note:** The following options are illustrative reference patterns.")
    lines.append("> Each option includes explicit assumptions and trade-offs.")
    lines.append("> Review with stakeholders before selecting an approach.")
    lines.append("")

    for cap_opt in options:
        lines.append(f"### {cap_opt.capability_name}")
        lines.append("")

        for i, opt in enumerate(cap_opt.options, 1):
            lines.append(f"#### Option {i}: {opt.label}")
            lines.append("")

            if opt.description:
                lines.append(f"**Description:** {opt.description}")
                lines.append("")

            if opt.assumptions:
                lines.append("**Assumptions:**")
                for assumption in opt.assumptions:
                    lines.append(f"- {assumption}")
                lines.append("")

            if opt.tradeoffs.get("pros") or opt.tradeoffs.get("cons"):
                lines.append("**Trade-offs:**")
                lines.append("| Pros | Cons |")
                lines.append("|------|------|")
                max_len = max(
                    len(opt.tradeoffs.get("pros", [])),
                    len(opt.tradeoffs.get("cons", []))
                )
                for j in range(max_len):
                    pro = opt.tradeoffs.get("pros", [])[j] if j < len(opt.tradeoffs.get("pros", [])) else ""
                    con = opt.tradeoffs.get("cons", [])[j] if j < len(opt.tradeoffs.get("cons", [])) else ""
                    lines.append(f"| {pro} | {con} |")
                lines.append("")

            if opt.when_to_choose and opt.when_to_choose != "Not specified":
                lines.append(f"**When to Choose:** {opt.when_to_choose}")
                lines.append("")

            if opt.diagram.mermaid:
                lines.append("```mermaid")
                lines.append(opt.diagram.mermaid)
                lines.append("```")
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
