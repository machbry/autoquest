"""Shared conventions for app architecture diagrams.

Every `apps/<app>/docs/architecture.py` builds its diagram with these helpers, so all
apps share one layout and one edge colour code. Render with
`docker compose run --rm --build architecture`.
"""

from html import escape
from pathlib import Path

import diagrams
from diagrams import Cluster, Diagram, Edge, Node

_RESOURCES = Path(diagrams.__file__).parent.parent / "resources"
_ICONS = Path(__file__).parent / "icons"

# Provider logos shown in cluster titles. Prefer the diagrams package's own resources;
# add a PNG to icons/ only when it has none (Graphviz here loads PNG, not SVG).
PROVIDER_ICONS = {
    "Google Cloud": _RESOURCES / "gcp" / "gcp.png",
    "GitHub": _RESOURCES / "onprem" / "vcs" / "github.png",
    "Neon": _ICONS / "neon.png",  # avatar of github.com/neondatabase
}

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
        direction="TB",
        graph_attr={
            "fontsize": "20",
            "labelloc": "t",
            "pad": "0.5",
            "nodesep": "0.6",
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


def provider(name: str) -> Cluster:
    """Return a cluster for a provider, titled with its logo and name."""
    title = (
        '<<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="2"><TR>'
        '<TD FIXEDSIZE="TRUE" WIDTH="20" HEIGHT="20">'
        f'<IMG SRC="{PROVIDER_ICONS[name]}" SCALE="TRUE"/></TD>'
        f"<TD>{escape(name)}</TD></TR></TABLE>>"
    )
    return Cluster(name, graph_attr={"label": title})


def component(
    icon: type[Node],
    name: str,
    feature: str,
    technology: str,
    planned: bool = False,
) -> Node:
    """Return a component node: icon, then resource name, feature and technology.

    The text sits in the node itself (an HTML table), so Graphviz sizes the node around
    it: edges and clusters never run over a label.

    Args:
        icon: diagrams node class whose icon shows the technology (e.g. `Run`).
        name: Resource name, following the cloud resource naming convention
            (`aq-prd-<app>-<resource>`).
        feature: What the component does for the app, in a few words.
        technology: The service or technology it runs on (`Cloud Run Service`...).
        planned: Marks the feature "(later)"; pair it with `planned=True` on its edges.
    """
    image = _RESOURCES.parent / icon._icon_dir / icon._icon
    feature = f"{feature} (later)" if planned else feature
    html = (
        '<<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="1">'
        '<TR><TD FIXEDSIZE="TRUE" WIDTH="64" HEIGHT="64">'
        f'<IMG SRC="{image}" SCALE="TRUE"/></TD></TR>'
        f"<TR><TD><B>{escape(name)}</B></TD></TR>"
        f"<TR><TD>{escape(feature)}</TD></TR>"
        f'<TR><TD><FONT COLOR="{USES}">{escape(technology)}</FONT></TD></TR>'
        "</TABLE>>"
    )
    return Node(html, shape="plain", fixedsize="false", width="0", height="0")
