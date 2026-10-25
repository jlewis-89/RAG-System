from django.apps import AppConfig


class ComplianceCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # type: ignore[assignment]
    name = 'apps.compliance_core'
    verbose_name = 'Compliance Core & Regulation Ingestion'
