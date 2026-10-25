from django.contrib import admin
from apps.rag.models import ComplianceStandard, ComplianceDocument, ComplianceAuditLog


@admin.register(ComplianceStandard)
class ComplianceStandardAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'authority', 'version', 'is_active', 'created_at')
    search_fields = ('code', 'name', 'authority')
    list_filter = ('authority', 'is_active')


@admin.register(ComplianceDocument)
class ComplianceDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'standard', 'status', 'total_chunks', 'uploaded_at')
    search_fields = ('title', 'source_identifier')
    list_filter = ('status', 'standard')


@admin.register(ComplianceAuditLog)
class ComplianceAuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'verdict', 'confidence_score', 'latency_ms', 'created_at')
    search_fields = ('query_text', 'answer_text')
    list_filter = ('verdict',)
    readonly_fields = ('created_at',)
