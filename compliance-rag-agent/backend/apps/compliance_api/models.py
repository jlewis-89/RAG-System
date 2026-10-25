"""
Database Models for Compliance API & Audit Logging.
Tracks field surveyor queries, operational inspection context, full reasoning audit trails,
and field engineer accuracy feedback.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class InspectionContext(models.TextChoices):
    """
    Operational installation context for engineering compliance evaluation.
    Directly affects statutory requirements (e.g. BS 7671 RCD requirements for domestic socket-outlets
    versus industrial supervised installations under skilled personnel).
    """
    DOMESTIC = 'Domestic', _('Domestic / Residential')
    COMMERCIAL = 'Commercial', _('Commercial / Retail / Office')
    INDUSTRIAL = 'Industrial', _('Industrial / Manufacturing / Heavy Duty')
    AGRICULTURAL = 'Agricultural', _('Agricultural / Horticultural')
    SPECIAL_INSTALLATION = 'Special Installation', _('Special Installation (Solar PV, EV Charging, Medical)')
    GENERAL = 'General', _('General Electrical / Unspecified')


class UserFeedback(models.TextChoices):
    """
    Engineer accuracy review status for compliance verdicts.
    Enables field engineers to flag potential hallucinations, cite deviations, or approve accurate findings.
    """
    PENDING = 'pending', _('Pending Review')
    APPROVED = 'approved', _('Approved (Accurate & Compliant)')
    FLAGGED = 'flagged', _('Flagged (Inaccurate / Needs Auditor Review)')
    REJECTED = 'rejected', _('Rejected / Hallucination Suspected')


class ComplianceQuery(models.Model):
    """
    Stores individual surveyor or compliance engineer queries,
    operational inspection context, and metadata.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_queries',
        help_text="Surveyor or compliance engineer who initiated the query"
    )
    query_text = models.TextField(
        help_text="Surveyor compliance query or technical specification to evaluate"
    )
    inspection_context = models.CharField(
        max_length=64,
        choices=InspectionContext.choices,
        default=InspectionContext.DOMESTIC,
        db_index=True,
        help_text="Operational environment context (e.g. Domestic, Commercial, Industrial)"
    )
    standard_filter = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Optional target standard filter (e.g. EAWR, BS 7671, BPG4)"
    )
    duty_filter = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="Optional statutory duty holder filter (e.g. Absolute, Reasonably Practicable)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when query was submitted"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Compliance Query'
        verbose_name_plural = 'Compliance Queries'

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"Query #{self.id} [{self.inspection_context}] by {user_str}: {self.query_text[:40]}..."


class ComplianceAuditLog(models.Model):
    """
    Complete audit trail record storing:
    - Full input payload (query, filters, inspection context)
    - Retrieved context chunk IDs used for grounding
    - Complete generated compliance response (verdict, citations, checks)
    - Execution response time (latency)
    - Field engineer accuracy feedback (approved, flagged, notes)
    """
    query = models.ForeignKey(
        ComplianceQuery,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        help_text="Associated compliance query"
    )
    full_input = models.JSONField(
        default=dict,
        help_text="Complete input payload including query text, inspection context, filters, and model options"
    )
    retrieved_context_ids = models.JSONField(
        default=list,
        help_text="List of retrieved regulatory chunk IDs or citation references used for grounding"
    )
    generated_response = models.JSONField(
        default=dict,
        help_text="Complete structured compliance response (status, verdict, cited_clauses, mandatory_requirements, inspection_checks, confidence_score)"
    )
    response_time_ms = models.FloatField(
        default=0.0,
        help_text="Inference and retrieval latency in milliseconds"
    )
    user_feedback = models.CharField(
        max_length=32,
        choices=UserFeedback.choices,
        default=UserFeedback.PENDING,
        db_index=True,
        help_text="Engineer validation feedback: approved, flagged, pending, or rejected"
    )
    feedback_notes = models.TextField(
        blank=True,
        default='',
        help_text="Remarks from field engineer explaining reasons for approval or flagging"
    )
    feedback_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_audit_feedbacks',
        help_text="Field engineer who logged feedback"
    )
    feedback_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when feedback was submitted"
    )
    model_used = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text="Model or reasoning engine provider name used"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when audit log was generated"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Compliance Audit Log'
        verbose_name_plural = 'Compliance Audit Logs'

    def __str__(self):
        status = self.generated_response.get('compliance_status', 'UNKNOWN')
        return f"AuditLog #{self.id} for Query #{self.query_id} [{status}] Feedback: {self.user_feedback}"
