"""Banking technical architecture, rendered to `architecture.png`.

Render with `docker compose run --rm --build architecture banking`.
"""

from autoquest_diagrams import app_diagram, later, reads, reads_writes, uses
from diagrams import Cluster
from diagrams.gcp.compute import Run
from diagrams.gcp.storage import GCS
from diagrams.onprem.analytics import Dbt
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.client import User
from diagrams.onprem.database import Postgresql
from diagrams.programming.framework import Fastapi

with app_diagram("Banking"):
    user = User("Me, desktop browser")

    with Cluster("Cloud Run"):
        web = Fastapi("Web app\n+ importers")
        mcp = Run(later("MCP server"))

    with Cluster("GitHub Actions jobs"):
        GithubActions("Deploy")
        backup = GithubActions("Backup")
        dbt = Dbt("Analytics")
        ml = GithubActions(later("Auto-labelling"))

    with Cluster("Postgres: Neon"):
        banking = Postgresql("banking schema")
        analytics = Postgresql("analytics schema")

    gcs = GCS("Cloud Storage")

    user >> uses() >> web
    web >> reads_writes() >> banking
    web >> reads() >> analytics
    mcp >> reads_writes(planned=True) >> banking
    dbt >> reads() >> banking
    dbt >> reads_writes() >> analytics
    backup >> reads() >> banking
    backup >> reads_writes() >> gcs
    ml >> reads_writes(planned=True) >> banking
    ml >> reads_writes(planned=True) >> gcs
