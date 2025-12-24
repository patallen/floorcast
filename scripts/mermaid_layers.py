#!/usr/bin/env python3
"""Convert tach mermaid output to grouped subgraphs by layer."""

import sys
from pathlib import Path

LAYERS = {
    "domain": "Domain",
    "infrastructure": "Infrastructure",
    "adapters": "Adapters",
    "services": "Services",
    "repositories": "Repositories",
    "api": "API",
}


def parse_mermaid(content: str) -> tuple[list[str], set[str]]:
    """Parse mermaid content, return (edges, nodes)."""
    edges = []
    nodes = set()

    for line in content.strip().splitlines():
        line = line.strip()
        if "-->" in line:
            edges.append(line)
            parts = line.split("-->")
            nodes.add(parts[0].strip())
            nodes.add(parts[1].strip())

    return edges, nodes


def get_layer(node: str) -> str | None:
    """Get layer name for a node."""
    if node.startswith("floorcast."):
        parts = node.split(".")
        if len(parts) >= 2:
            return parts[1]
    return None


def group_by_layer(nodes: set[str]) -> dict[str, list[str]]:
    """Group nodes by layer."""
    groups: dict[str, list[str]] = {layer: [] for layer in LAYERS}
    groups["other"] = []

    for node in sorted(nodes):
        layer = get_layer(node)
        if layer in LAYERS:
            groups[layer].append(node)
        else:
            groups["other"].append(node)

    return groups


def generate_grouped_mermaid(edges: list[str], nodes: set[str]) -> str:
    """Generate mermaid with subgraphs."""
    groups = group_by_layer(nodes)
    lines = ["graph TD"]

    # Add subgraphs for each layer
    for layer_key, layer_name in LAYERS.items():
        layer_nodes = groups[layer_key]
        if layer_nodes:
            lines.append(f"    subgraph {layer_key}[{layer_name}]")
            for node in layer_nodes:
                short = node.replace("floorcast.", "")
                lines.append(f"        {node}[{short}]")
            lines.append("    end")
            lines.append("")

    # Add other nodes (main, floorcast.ingest, etc.)
    if groups["other"]:
        lines.append("    %% Other")
        for node in groups["other"]:
            lines.append(f"    {node}")
        lines.append("")

    # Add edges
    lines.append("    %% Dependencies")
    for edge in edges:
        lines.append(f"    {edge}")

    return "\n".join(lines)


def main() -> None:
    input_file = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tach_module_graph.mmd")
    )
    content = input_file.read_text()
    edges, nodes = parse_mermaid(content)
    output = generate_grouped_mermaid(edges, nodes)
    print(output)


if __name__ == "__main__":
    main()
