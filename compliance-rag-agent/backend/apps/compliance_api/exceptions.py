"""
Custom DRF Exception Handler for Compliance API.
Returns standardized, structured error payloads for validation failures,
authentication errors, and unhandled system exceptions.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, AuthenticationFailed, NotAuthenticated, PermissionDenied, NotFound

logger = logging.getLogger(__name__)


def compliance_exception_handler(exc, context):
    """
    Standardizes all API error responses into formatted JSON:
    {
      "status": "error",
      "code": "ERROR_CODE",
      "message": "Human readable summary",
      "errors": { "field": ["Field error detail"] },
      "status_code": 400
    }
    """
    # Call REST framework's default exception handler first to get standard response
    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code
        error_code = "API_ERROR"
        message = "An error occurred while processing the request."
        errors = {}

        if isinstance(exc, ValidationError):
            error_code = "VALIDATION_FAILED"
            message = "Strict request validation failed. Please review the supplied parameters."
            if isinstance(response.data, dict):
                errors = response.data
            elif isinstance(response.data, list):
                errors = {"non_field_errors": response.data}
            else:
                errors = {"detail": [str(response.data)]}

        elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            error_code = "AUTHENTICATION_REQUIRED"
            message = "Authentication credentials were not provided or are invalid."
            errors = {"detail": [str(exc)]}

        elif isinstance(exc, PermissionDenied):
            error_code = "PERMISSION_DENIED"
            message = "You do not have the required permission tier to perform this action."
            errors = {"detail": [str(exc)]}

        elif isinstance(exc, NotFound):
            error_code = "RESOURCE_NOT_FOUND"
            message = "The requested compliance resource or audit log was not found."
            errors = {"detail": [str(exc)]}

        else:
            if isinstance(response.data, dict):
                errors = response.data
                message = str(response.data.get("detail", message))

        custom_payload = {
            "status": "error",
            "code": error_code,
            "message": message,
            "errors": errors,
            "status_code": status_code
        }
        response.data = custom_payload
        return response

    # Unhandled 500 error fallback
    logger.error(f"Unhandled exception in Compliance API: {exc}", exc_info=True)
    return Response(
        {
            "status": "error",
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred while executing compliance reasoning.",
            "detail": str(exc),
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
