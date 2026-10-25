from django.db import models


class ComplianceStandard(models.Model):
    """
    Represents an Engineering or Regulatory Compliance Standard
    (e.g., ISO 9001:2015, ASME Boiler and Pressure Vessel Code Section VIII, IEC 61508).
    """
    code = models.CharField(max_length=64, unique=True, help_text="Standard Code (e.g., ISO-9001, ASME-VIII)")
    name = models.CharField(max_length=255, help_text="Full title of the standard")
    authority = models.CharField(max_length=128, default="ISO", help_text="Standards Organization (ISO, ASME, IEC, OSHA)")
    version = models.CharField(max_length=32, blank=True, null=True, help_text="Standard edition/year")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Compliance Standard'
        verbose_name_plural = 'Compliance Standards'

    def __str__(self):
        return f"{self.code} - {self.name}"


class ComplianceDocument(models.Model):
    """
    Represents a specific document or specification manual ingested into the RAG vector store.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Ingestion'),
        ('PROCESSING', 'Processing & Embedding'),
        ('INDEXED', 'Indexed in ChromaDB'),
        ('FAILED', 'Ingestion Failed'),
    ]

    standard = models.ForeignKey(
        ComplianceStandard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    title = models.CharField(max_length=255)
    source_identifier = models.CharField(max_length=255, help_text="File name, URL, or document reference ID")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING')
    total_chunks = models.PositiveIntegerField(default=0)
    document_metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Compliance Document'
        verbose_name_plural = 'Compliance Documents'

    def __str__(self):
        return f"{self.title} ({self.status})"


class ComplianceAuditLog(models.Model):
    """
    Full audit trail for compliance verification queries, LLM reasoning,
    citations, and confidence scores.
    """
    VERDICT_CHOICES = [
        ('COMPLIANT', 'Compliant'),
        ('NON_COMPLIANT', 'Non-Compliant'),
        ('PARTIALLY_COMPLIANT', 'Partially Compliant'),
        ('NEEDS_REVIEW', 'Needs Review / Inconclusive'),
    ]

    query_text = models.TextField()
    verdict = models.CharField(max_length=32, choices=VERDICT_CHOICES, default='NEEDS_REVIEW')
    confidence_score = models.FloatField(default=0.0)
    answer_text = models.TextField()
    citations = models.JSONField(default=list, help_text="Array of cited sections, clauses, and similarity scores")
    standard_filter = models.CharField(max_length=64, blank=True, null=True)
    latency_ms = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Compliance Audit Log'
        verbose_name_plural = 'Compliance Audit Logs'

    def __str__(self):
        return f"[{self.verdict}] {self.query_text[:50]}... ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
