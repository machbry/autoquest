"""Banking technical architecture, rendered to `architecture.png`.

Render with `docker compose run --rm --build architecture banking`.
"""

from autoquest_diagrams import (
    app_diagram,
    component,
    provider,
    reads,
    reads_writes,
    uses,
)
from diagrams.gcp.compute import Run
from diagrams.gcp.storage import GCS
from diagrams.onprem.analytics import Dbt
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.client import User
from diagrams.onprem.database import Postgresql
from diagrams.onprem.iac import Terraform

with app_diagram("Banking"):
    user = component(User, "Me", "Every user journey", "Desktop browser")

    with provider("Google Cloud"):
        web = component(
            Run, "aq-prd-banking-web", "Web app and imports", "Cloud Run Service"
        )
        mcp = component(
            Run,
            "aq-prd-banking-mcp",
            "Agent-assisted labelling",
            "Cloud Run Service",
            planned=True,
        )
        gcs = component(
            GCS,
            "aq-prd-banking-data-<project-id>",
            "Backups and models",
            "Cloud Storage bucket",
        )

    with provider("GitHub"):
        component(
            Terraform, "aq-prd-banking-deploy", "Deploy", "Terraform on GitHub Actions"
        )
        backup = component(
            GithubActions, "aq-prd-banking-backup", "Backups", "GitHub Actions"
        )
        dbt = component(
            Dbt, "aq-prd-banking-analytics", "Analysis", "dbt on GitHub Actions"
        )
        ml = component(
            GithubActions,
            "aq-prd-banking-autolabel",
            "Auto-labelling",
            "GitHub Actions",
            planned=True,
        )

    with provider("Neon"):
        banking = component(Postgresql, "banking", "App data", "PostgreSQL schema")
        analytics = component(
            Postgresql, "analytics", "Analysis models", "PostgreSQL schema"
        )

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
