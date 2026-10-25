"""
Comprehensive Test Suite for Compliance API Layer and Audit Logging.
Tests:
1. ComplianceQuery and ComplianceAuditLog models and relationships.
2. POST /api/v1/compliance/query/ (surveyor query + context -> structured compliance response).
3. GET  /api/v1/compliance/standards/ (listing ingested standards, clause counts, versions).
4. POST /api/v1/compliance/audit/{id}/feedback/ (field engineer accuracy feedback: approved/flagged).
5. Strict request validation and standardized error payloads.
6. Session and Token Authentication with user permission tiers.
"""

import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from apps.compliance_api.models import (
    ComplianceQuery,
    ComplianceAuditLog,
    InspectionContext,
    UserFeedback,
)
from apps.compliance_api.permissions import (
    PermissionTier,
    get_user_permission_tier,
)
from apps.compliance_core.schemas import ComplianceStatus
from apps.rag.models import ComplianceStandard, ComplianceDocument


class ComplianceModelTests(TestCase):
    """
    Unit tests for ComplianceQuery and ComplianceAuditLog data models.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username="surveyor_dave",
            password="testpassword123",
            email="dave@electrical-inspections.co.uk"
        )

    def test_compliance_query_creation(self):
        query = ComplianceQuery.objects.create(
            user=self.user,
            query_text="Is 30mA RCD protection mandatory for domestic socket-outlets?",
            inspection_context=InspectionContext.DOMESTIC,
            standard_filter="BS 7671",
            duty_filter="Absolute"
        )
        self.assertEqual(query.user, self.user)
        self.assertEqual(query.inspection_context, InspectionContext.DOMESTIC)
        self.assertEqual(query.standard_filter, "BS 7671")
        self.assertIn("Query #", str(query))

    def test_compliance_audit_log_creation(self):
        query = ComplianceQuery.objects.create(
            user=self.user,
            query_text="Missing blanking piece on consumer unit danger level",
            inspection_context=InspectionContext.DOMESTIC
        )
        audit_log = ComplianceAuditLog.objects.create(
            query=query,
            full_input={"query": query.query_text, "context": "Domestic"},
            retrieved_context_ids=["BPG4::Section4::CodeC1"],
            generated_response={
                "compliance_status": ComplianceStatus.IMMEDIATE_DANGER.value,
                "summary_verdict": "Immediate danger present. C1 classification mandated.",
                "cited_clauses": [
                    {
                        "standard": "Electrical Safety First BPG4",
                        "clause_number": "Code C1",
                        "verbatim_quote": "A circuit protective device is missing from a consumer unit."
                    }
                ],
                "mandatory_requirements": ["Regulation 4(4) protective barrier requirement."],
                "inspection_checks": ["Isolate immediately and fit approved blanking piece."],
                "confidence_score": 0.98
            },
            response_time_ms=145.2,
            user_feedback=UserFeedback.PENDING,
            model_used="deterministic"
        )
        self.assertEqual(audit_log.query, query)
        self.assertEqual(audit_log.user_feedback, UserFeedback.PENDING)
        self.assertEqual(audit_log.response_time_ms, 145.2)
        self.assertIn(ComplianceStatus.IMMEDIATE_DANGER.value, str(audit_log))


class ComplianceQueryEndpointTests(TestCase):
    """
    Functional tests for POST /api/v1/compliance/query/.
    """
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="field_engineer_alice",
            password="securepassword123"
        )
        self.token = Token.objects.create(user=self.user)
        self.url = reverse('compliance_api:compliance_query')

    def test_query_success_domestic_context(self):
        payload = {
            "query": "missing blanking piece on consumer unit danger exposed parts",
            "inspection_context": "Domestic",
            "provider": "deterministic",
            "top_k": 3
        }
        response = self.client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check returned compliance structure
        self.assertIn("query_id", data)
        self.assertIn("audit_id", data)
        self.assertEqual(data["compliance_status"], ComplianceStatus.IMMEDIATE_DANGER.value)
        self.assertEqual(data["inspection_context"], "Domestic")
        self.assertGreater(len(data["summary_verdict"]), 10)
        self.assertGreater(len(data["cited_clauses"]), 0)
        self.assertGreater(len(data["inspection_checks"]), 0)
        self.assertGreater(data["confidence_score"], 0.8)

        # Verify DB records persisted
        self.assertTrue(ComplianceQuery.objects.filter(id=data["query_id"]).exists())
        self.assertTrue(ComplianceAuditLog.objects.filter(id=data["audit_id"]).exists())

    def test_query_authenticated_via_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        payload = {
            "query": "What does Reg 4(2) require for electrical system maintenance?",
            "inspection_context": "Commercial",
            "provider": "deterministic"
        }
        response = self.client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["compliance_status"], ComplianceStatus.COMPLIANT.value)

        # Verify user association in query record
        query_record = ComplianceQuery.objects.get(id=data["query_id"])
        self.assertEqual(query_record.user, self.user)

    def test_query_validation_error_missing_query(self):
        payload = {
            "inspection_context": "Industrial"
            # Missing query field
        }
        response = self.client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["code"], "VALIDATION_FAILED")
        self.assertIn("query", data["errors"])

    def test_query_validation_error_invalid_inspection_context(self):
        payload = {
            "query": "Is inspection required for circuit breakers?",
            "inspection_context": "DeepSpaceHabitat"  # Invalid choice
        }
        response = self.client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["code"], "VALIDATION_FAILED")
        self.assertIn("inspection_context", data["errors"])

    def test_query_validation_error_top_k_bounds(self):
        payload = {
            "query": "Earthing requirements for transformer enclosures",
            "top_k": 999  # Exceeds max 25
        }
        response = self.client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("top_k", data["errors"])


class ComplianceStandardsEndpointTests(TestCase):
    """
    Tests for GET /api/v1/compliance/standards/.
    """
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('compliance_api:compliance_standards')

        # Create sample standard and document
        self.std = ComplianceStandard.objects.create(
            code="EAWR-1989",
            name="Electricity at Work Regulations 1989",
            authority="HSE / UK Statutory",
            version="S.I. 1989 No. 635",
            description="Primary UK electrical safety statutory instrument."
        )
        ComplianceDocument.objects.create(
            standard=self.std,
            title="EAWR Full Statutory Instrument",
            source_identifier="EAWR_1989.pdf",
            total_chunks=31,
            status="INDEXED"
        )

    def test_get_standards_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("standards", data)
        self.assertGreater(data["total_standards"], 0)

        std_entry = next((s for s in data["standards"] if s["code"] == "EAWR-1989"), None)
        self.assertIsNotNone(std_entry)
        assert std_entry is not None
        self.assertEqual(std_entry["name"], "Electricity at Work Regulations 1989")
        self.assertEqual(std_entry["authority"], "HSE / UK Statutory")
        self.assertEqual(std_entry["clause_count"], 31)
        self.assertEqual(std_entry["document_count"], 1)


class ComplianceAuditFeedbackEndpointTests(TestCase):
    """
    Tests for POST /api/v1/compliance/audit/{id}/feedback/.
    """
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="senior_auditor_tom",
            password="password456"
        )
        self.client.force_authenticate(user=self.user)

        self.query = ComplianceQuery.objects.create(
            user=self.user,
            query_text="Missing blanking piece on consumer unit",
            inspection_context=InspectionContext.DOMESTIC
        )
        self.audit_log = ComplianceAuditLog.objects.create(
            query=self.query,
            full_input={"query": self.query.query_text},
            generated_response={"compliance_status": "IMMEDIATE_DANGER"},
            user_feedback=UserFeedback.PENDING
        )
        self.feedback_url = reverse('compliance_api:audit_feedback', kwargs={'id': self.audit_log.id})

    def test_log_feedback_approved(self):
        payload = {
            "feedback": "approved",
            "notes": "Verified on site. Correct C1 classification and statutory reference to EAWR 4(4)."
        }
        response = self.client.post(self.feedback_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["user_feedback"], "approved")
        self.assertIn("Verified on site", data["feedback_notes"])
        self.assertEqual(data["feedback_by"], self.user.username)

        # Verify DB updated
        self.audit_log.refresh_from_db()
        self.assertEqual(self.audit_log.user_feedback, "approved")
        self.assertEqual(self.audit_log.feedback_by, self.user)

    def test_log_feedback_flagged(self):
        payload = {
            "feedback": "flagged",
            "notes": "Surveyor observed that accessory had secondary enclosure; potentially C2 rather than C1."
        }
        response = self.client.post(self.feedback_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.audit_log.refresh_from_db()
        self.assertEqual(self.audit_log.user_feedback, "flagged")

    def test_feedback_non_existent_audit_log(self):
        bad_url = reverse('compliance_api:audit_feedback', kwargs={'id': 999999})
        payload = {"feedback": "approved"}
        response = self.client.post(bad_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["code"], "RESOURCE_NOT_FOUND")

    def test_feedback_invalid_choice(self):
        payload = {"feedback": "thumbs_up"}  # Invalid choice
        response = self.client.post(self.feedback_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("feedback", data["errors"])


class ComplianceAuditLogsHistoryTests(TestCase):
    """
    Tests for GET /api/v1/compliance/audit/ and GET /api/v1/compliance/audit/{id}/.
    """
    def setUp(self):
        self.client = APIClient()
        self.query = ComplianceQuery.objects.create(
            query_text="RCD tripping time check",
            inspection_context=InspectionContext.DOMESTIC
        )
        self.audit_log = ComplianceAuditLog.objects.create(
            query=self.query,
            full_input={"query": "RCD test"},
            generated_response={"compliance_status": "COMPLIANT"},
            response_time_ms=88.5
        )

    def test_list_audit_logs(self):
        url = reverse('compliance_api:audit_logs_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertGreater(data["count"], 0)

    def test_detail_audit_log(self):
        url = reverse('compliance_api:audit_log_detail', kwargs={'id': self.audit_log.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], self.audit_log.id)
        self.assertEqual(data["query_text"], "RCD tripping time check")


class AuthenticationAndPermissionTierTests(TestCase):
    """
    Tests DRF Token and Session Authentication & Permission Tiers.
    """
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="engineer_bob",
            password="bobpassword123"
        )
        self.auditor_user = User.objects.create_user(
            username="auditor_sarah",
            password="sarahpassword123"
        )
        auditor_group, _ = Group.objects.get_or_create(name=PermissionTier.COMPLIANCE_AUDITOR.value)
        self.auditor_user.groups.add(auditor_group)

        self.admin_user = User.objects.create_superuser(
            username="admin_alex",
            password="adminpassword123",
            email="admin@compliance.gov.uk"
        )

    def test_obtain_auth_token_endpoint(self):
        url = reverse('compliance_api:api_token_auth')
        payload = {
            "username": "engineer_bob",
            "password": "bobpassword123"
        }
        response = self.client.post(url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("token", data)
        self.assertEqual(data["username"], "engineer_bob")
        self.assertEqual(data["permission_tier"], PermissionTier.FIELD_ENGINEER.value)

    def test_permission_tier_resolution(self):
        self.assertEqual(get_user_permission_tier(self.user), PermissionTier.FIELD_ENGINEER.value)
        self.assertEqual(get_user_permission_tier(self.auditor_user), PermissionTier.COMPLIANCE_AUDITOR.value)
        self.assertEqual(get_user_permission_tier(self.admin_user), PermissionTier.COMPLIANCE_ADMIN.value)
        self.assertEqual(get_user_permission_tier(None), "Anonymous")
