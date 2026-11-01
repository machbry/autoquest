"""Shared conventions for app architecture diagrams.

Every `apps/<app>/docs/architecture.py` builds its diagram with these helpers, so all
apps share one layout and one edge colour code. Render with
`docker compose run --rm --build architecture`.
"""

from diagrams import Diagram, Edge

USES = "#6b7280"
READS_WRITES = "#2563eb"
READS = "#16a34a"


def app_diagram(title: str) -> Diagram:
    """Return the diagram context for an app, written to `architecture.png`."""
    return Diagram(
        title,
        filename="architecture",
        outformat="png",
        show=False,
        direction="LR",
        graph_attr={
            "fontsize": "20",
            "labelloc": "t",
            "pad": "0.5",
            "nodesep": "0.5",
            "ranksep": "1.5",
            "splines": "spline",
        },
        node_attr={"fontsize": "12"},
        edge_attr={"penwidth": "2"},
    )


def _edge(color: str, planned: bool) -> Edge:
    return Edge(color=color, style="dashed" if planned else "solid")


def uses(planned: bool = False) -> Edge:
    """Edge from a client to a service it calls (grey)."""
    return _edge(USES, planned)


def reads_writes(planned: bool = False) -> Edge:
    """Edge to a store the component reads and writes (blue)."""
    return _edge(READS_WRITES, planned)


def reads(planned: bool = False) -> Edge:
    """Edge to a store the component only reads (green)."""
    return _edge(READS, planned)


def later(label: str) -> str:
    """Mark a planned component's label; pair it with `planned=True` on its edges."""
    return f"{label}\n(later)"
