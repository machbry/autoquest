"""Banking technical architecture, rendered to `architecture.png`.

Render with `docker compose run --rm --build architecture banking`.
"""

from autoquest_diagrams import app_diagram, later, reads, reads_writes, uses
from diagrams import Cluster
from diagrams.gcp.storage import GCS
from diagrams.onprem.analytics import Dbt
from diagrams.onprem.client import User
from diagrams.onprem.database import Postgresql
from diagrams.onprem.iac import Terraform
from diagrams.programming.framework import Fastapi
from diagrams.programming.language import Python

with app_diagram("Banking"):
    user = User("Me, desktop browser")

    with Cluster("Google Cloud"):
        web = Fastapi("Web app\nCloud Run")
        mcp = Python(later("MCP server\nCloud Run"))
        gcs = GCS("Cloud Storage")

    with Cluster("GitHub"):
        Terraform("Deploy\nGitHub Actions")
        backup = Python("Backup\nGitHub Actions")
        dbt = Dbt("Analytics\nGitHub Actions")
        ml = Python(later("Auto-labelling\nGitHub Actions"))

    with Cluster("Neon"):
        banking = Postgresql("banking schema")
        analytics = Postgresql("analytics schema")

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
