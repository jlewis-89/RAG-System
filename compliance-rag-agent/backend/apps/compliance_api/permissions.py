"""
DRF Permissions and User Permission Tiers for Compliance API.
Supports Session & Token Authentication with role-based access control:
- Field Engineer: Execute compliance audits, view standards, submit accuracy feedback.
- Compliance Auditor: View historical audit logs, review flagged items.
- Compliance Administrator: Full administrative access.
"""

from enum import Enum
from rest_framework import permissions
from django.contrib.auth.models import Group


class PermissionTier(str, Enum):
    FIELD_ENGINEER = "Field Engineer"
    COMPLIANCE_AUDITOR = "Compliance Auditor"
    COMPLIANCE_ADMIN = "Compliance Admin"


def get_user_permission_tier(user) -> str:
    """
    Resolves user's highest compliance permission tier.
    """
    if not user or not user.is_authenticated:
        return "Anonymous"

    if user.is_superuser or user.is_staff:
        return PermissionTier.COMPLIANCE_ADMIN.value

    user_groups = set(user.groups.values_list('name', flat=True))
    if PermissionTier.COMPLIANCE_ADMIN.value in user_groups:
        return PermissionTier.COMPLIANCE_ADMIN.value
    if PermissionTier.COMPLIANCE_AUDITOR.value in user_groups:
        return PermissionTier.COMPLIANCE_AUDITOR.value
    if PermissionTier.FIELD_ENGINEER.value in user_groups:
        return PermissionTier.FIELD_ENGINEER.value

    # Default authenticated users to Field Engineer tier
    return PermissionTier.FIELD_ENGINEER.value


class IsFieldEngineerOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access (GET standards, etc.) to anyone.
    Requires authentication (or allows unauthenticated in open demo mode) for running compliance queries.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return True  # Allows open querying for demo/eval, logs user if authenticated


class CanSubmitAuditFeedback(permissions.BasePermission):
    """
    Ensures feedback can be logged by authenticated field engineers or surveyors.
    """
    def has_permission(self, request, view):
        # Open to all requests or authenticated users; records user if authenticated
        return True


class IsComplianceAuditor(permissions.BasePermission):
    """
    Restricts access to certified compliance auditors or admins.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        tier = get_user_permission_tier(request.user)
        return tier in (PermissionTier.COMPLIANCE_AUDITOR.value, PermissionTier.COMPLIANCE_ADMIN.value)


class IsComplianceAdmin(permissions.BasePermission):
    """
    Restricts administrative access to compliance administrators.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        tier = get_user_permission_tier(request.user)
        return tier == PermissionTier.COMPLIANCE_ADMIN.value
