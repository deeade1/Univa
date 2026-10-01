# apps/backend/graphq/banking/mutations/regulatory.py

"""
GraphQL mutations for Banking regulatory models.

This module contains mutations for:
    - BVNVerification: BVN integration (mandatory for Nigerian fintech)
    - CBNReport: Regulatory reporting to Central Bank of Nigeria
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import re
import graphene
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.db.models import Count, Sum, Q
from django.utils import timezone
from graphene import ID, Boolean, Decimal as GrapheneDecimal, Field, Int, String, relay
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from graphql_relay import from_global_id

from banking.models.regulatory import (
    BVNVerification,
    CBNReport,
)
from banking.services.regulatory_service import RegulatoryService
from banking.models.payments import Transaction
from banking.models.security import FraudAlert
from graphq.accounts.types.user import UserNode
from graphq.banking.types.regulatory import (
    BVNVerificationNode,
    CBNReportNode,
)
from univa_jwt.decorators import login_required

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def _get_authenticated_user(info):
    """Return the authenticated Django user."""
    user = getattr(info.context, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required.")
    return user


def _get_model_by_global_id(global_id, model, model_name):
    """Get a model instance by Relay global ID."""
    if not global_id:
        raise GraphQLError(f"{model_name} ID is required.")
    
    try:
        _, pk = from_global_id(global_id)
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise GraphQLError(f"{model_name} not found.")
    except Exception as exc:
        raise GraphQLError(f"Invalid {model_name} ID.") from exc


def _validate_amount(amount):
    """Validate and normalize a monetary amount."""
    try:
        amount = Decimal(str(amount))
    except (TypeError, ValueError):
        raise GraphQLError("Invalid amount value.")
    
    if amount <= Decimal("0.00"):
        raise GraphQLError("Amount must be greater than zero.")
    
    return amount.quantize(Decimal("0.01"))


def _validate_bvn(bvn):
    """Validate BVN format (11 digits)."""
    if not bvn:
        raise GraphQLError("BVN is required.")
    bvn = re.sub(r'\s+', '', bvn)
    if not re.match(r'^\d{11}$', bvn):
        raise GraphQLError("BVN must be exactly 11 digits.")
    return bvn


def _validate_date(date_str):
    """Validate a date string."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise GraphQLError("Invalid date format. Use YYYY-MM-DD.")


def _validate_datetime(datetime_str):
    """Validate a datetime string."""
    if not datetime_str:
        return None
    try:
        return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    except ValueError:
        raise GraphQLError("Invalid datetime format. Use ISO format.")


# ============================================================================
# BVN VERIFICATION MUTATIONS
# ============================================================================

class CreateBVNVerificationMutation(relay.ClientIDMutation):
    """Create a BVN verification record for a user."""

    class Input:
        user_id = ID(required=True)
        bvn_number = String(required=True)

    bvn_verification = Field(BVNVerificationNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        target_user = _get_model_by_global_id(input["user_id"], User, "User")
        
        # Check if user already has BVN verification
        if hasattr(target_user, 'bvn_verification'):
            raise GraphQLError("User already has a BVN verification record.")
        
        bvn = _validate_bvn(input["bvn_number"])
        
        # Check if BVN is already registered
        if BVNVerification.objects.filter(bvn_number=bvn).exists():
            raise GraphQLError("BVN is already registered with another account.")
        
        try:
            bvn_verification = BVNVerification.objects.create(
                user=target_user,
                bvn_number=bvn,
                verification_status="PENDING",
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            bvn_verification=bvn_verification,
            success=True,
            message="BVN verification record created successfully.",
        )


class VerifyBVNMutation(relay.ClientIDMutation):
    """Verify a BVN (simulated NIBSS verification)."""

    class Input:
        bvn_verification_id = ID(required=True)
        full_name = String()
        date_of_birth = String()
        phone_number = String()
        email = String()
        enrollment_bank = String()
        enrollment_branch = String()

    bvn_verification = Field(BVNVerificationNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        bvn_verification = _get_model_by_global_id(
            input["bvn_verification_id"], BVNVerification, "BVN verification"
        )
        
        # Check if user can attempt verification
        if not bvn_verification.can_attempt_verification():
            raise GraphQLError("BVN verification is locked. Too many failed attempts.")
        
        # In production, this would call NIBSS BVN verification API
        # For now, we simulate verification with provided data
        
        try:
            # Simulate verification - in production, this would be the API response
            is_verified = True  # This would come from NIBSS API
            
            if is_verified:
                bvn_verification.verification_status = "VERIFIED"
                bvn_verification.verified_at = timezone.now()
                bvn_verification.last_verified = timezone.now()
                
                # Update user info from BVN data
                if input.get("full_name"):
                    bvn_verification.full_name = input["full_name"]
                if input.get("date_of_birth"):
                    bvn_verification.date_of_birth = _validate_date(input["date_of_birth"])
                if input.get("phone_number"):
                    bvn_verification.phone_number = input["phone_number"]
                if input.get("email"):
                    bvn_verification.email = input["email"]
                if input.get("enrollment_bank"):
                    bvn_verification.enrollment_bank = input["enrollment_bank"]
                if input.get("enrollment_branch"):
                    bvn_verification.enrollment_branch = input["enrollment_branch"]
            else:
                bvn_verification.verification_status = "FAILED"
            
            bvn_verification.record_attempt(success=is_verified)
            
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            bvn_verification=bvn_verification,
            success=is_verified,
            message="BVN verified successfully." if is_verified else "BVN verification failed.",
        )


class UpdateBVNVerificationMutation(relay.ClientIDMutation):
    """Update BVN verification details (admin only)."""

    class Input:
        bvn_verification_id = ID(required=True)
        verification_status = String(required=True)
        full_name = String()
        date_of_birth = String()
        phone_number = String()
        email = String()
        enrollment_bank = String()
        enrollment_branch = String()

    bvn_verification = Field(BVNVerificationNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Check admin permission
        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("Only admins can update BVN verification.")
        
        bvn_verification = _get_model_by_global_id(
            input["bvn_verification_id"], BVNVerification, "BVN verification"
        )
        
        # Validate status
        valid_statuses = [choice[0] for choice in BVNVerification.VERIFICATION_STATUS]
        if input["verification_status"] not in valid_statuses:
            raise GraphQLError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        bvn_verification.verification_status = input["verification_status"]
        
        if input["verification_status"] == "VERIFIED":
            bvn_verification.verified_at = timezone.now()
            bvn_verification.last_verified = timezone.now()
        
        if input.get("full_name"):
            bvn_verification.full_name = input["full_name"]
        if input.get("date_of_birth"):
            bvn_verification.date_of_birth = _validate_date(input["date_of_birth"])
        if input.get("phone_number"):
            bvn_verification.phone_number = input["phone_number"]
        if input.get("email"):
            bvn_verification.email = input["email"]
        if input.get("enrollment_bank"):
            bvn_verification.enrollment_bank = input["enrollment_bank"]
        if input.get("enrollment_branch"):
            bvn_verification.enrollment_branch = input["enrollment_branch"]
        
        try:
            bvn_verification.save()
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            bvn_verification=bvn_verification,
            success=True,
            message="BVN verification updated successfully.",
        )


class ResendBVNVerificationMutation(relay.ClientIDMutation):
    """Resend BVN verification request (unlock after lockout)."""

    class Input:
        bvn_verification_id = ID(required=True)

    bvn_verification = Field(BVNVerificationNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        bvn_verification = _get_model_by_global_id(
            input["bvn_verification_id"], BVNVerification, "BVN verification"
        )
        
        if bvn_verification.user != user:
            raise GraphQLError("You do not own this BVN verification.")
        
        bvn_verification.lock_until = None
        bvn_verification.verification_attempts = 0
        bvn_verification.save()
        
        return cls(
            bvn_verification=bvn_verification,
            success=True,
            message="BVN verification reset successfully.",
        )


class DeleteBVNVerificationMutation(relay.ClientIDMutation):
    """Delete a BVN verification record."""

    class Input:
        bvn_verification_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        bvn_verification = _get_model_by_global_id(
            input["bvn_verification_id"], BVNVerification, "BVN verification"
        )
        
        if bvn_verification.user != user:
            raise GraphQLError("You do not own this BVN verification.")
        
        bvn_verification.delete()
        
        return cls(
            success=True,
            message="BVN verification deleted successfully.",
        )


# ============================================================================
# CBN REPORT MUTATIONS
# ============================================================================

class GenerateCBNReportMutation(relay.ClientIDMutation):
    """Generate a CBN report for a specific period."""

    class Input:
        report_type = String(required=True)
        reporting_period = String(required=True)
        report_data = GenericScalar()
        summary = GenericScalar()

    cbn_report = Field(CBNReportNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Check admin permission
        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("Only admins can generate CBN reports.")
        
        # Validate report type
        valid_types = [choice[0] for choice in CBNReport.REPORT_TYPES]
        if input["report_type"] not in valid_types:
            raise GraphQLError(f"Invalid report type. Must be one of: {', '.join(valid_types)}")
        
        # Generate reference
        reference = f"CBN-{input['report_type']}-{input['reporting_period']}-{uuid.uuid4().hex[:6].upper()}"
        
        try:
            cbn_report = CBNReport.objects.create(
                report_type=input["report_type"],
                reporting_period=input["reporting_period"],
                reference=reference,
                report_data=input.get("report_data", {}),
                summary=input.get("summary", {}),
                status="GENERATED",
                generated_at=timezone.now(),
            )
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            cbn_report=cbn_report,
            success=True,
            message="CBN report generated successfully.",
        )


class GenerateTransactionReportMutation(relay.ClientIDMutation):
    """Generate a CBN transaction report via RegulatoryService."""

    class Input:
        reporting_period = String(required=True)
        start_date = String(required=True)
        end_date = String(required=True)

    cbn_report = Field(CBNReportNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Check admin permission
        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("Only admins can generate CBN reports.")
        
        # Validate dates
        start_date = _validate_date(input["start_date"])
        end_date = _validate_date(input["end_date"])
        
        if not start_date or not end_date:
            raise GraphQLError("Invalid date format.")
        
        if start_date > end_date:
            raise GraphQLError("Start date cannot be after end date.")
        
        period = {
            'start': start_date,
            'end': end_date,
        }
        
        try:
            # Generate report data
            report_data = RegulatoryService.generate_transaction_report(period)
            
            # Create report
            reference = f"CBN-TRANS-{input['reporting_period']}-{uuid.uuid4().hex[:6].upper()}"
            
            cbn_report = CBNReport.objects.create(
                report_type="TRANSACTION",
                reporting_period=input["reporting_period"],
                reference=reference,
                report_data=report_data,
                summary=report_data.get('summary', {}),
                status="GENERATED",
                generated_at=timezone.now(),
            )
        except Exception as exc:
            raise GraphQLError(f"Failed to generate transaction report: {str(exc)}")
        
        return cls(
            cbn_report=cbn_report,
            success=True,
            message="Transaction report generated successfully.",
        )


class GenerateSuspiciousActivityReportMutation(relay.ClientIDMutation):
    """Generate a Suspicious Activity Report (SAR)."""

    class Input:
        reporting_period = String(required=True)

    cbn_report = Field(CBNReportNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Check admin permission
        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("Only admins can generate CBN reports.")
        
        try:
            # Generate SAR data
            report_data = RegulatoryService.generate_suspicious_activity_report()
            
            # Create report
            reference = f"CBN-SAR-{input['reporting_period']}-{uuid.uuid4().hex[:6].upper()}"
            
            cbn_report = CBNReport.objects.create(
                report_type="SUSPICIOUS",
                reporting_period=input["reporting_period"],
                reference=reference,
                report_data=report_data,
                summary=report_data.get('summary', {}),
                status="GENERATED",
                generated_at=timezone.now(),
            )
        except Exception as exc:
            raise GraphQLError(f"Failed to generate suspicious activity report: {str(exc)}")
        
        return cls(
            cbn_report=cbn_report,
            success=True,
            message="Suspicious Activity Report generated successfully.",
        )


class UpdateCBNReportMutation(relay.ClientIDMutation):
    """Update a CBN report."""

    class Input:
        cbn_report_id = ID(required=True)
        status = String()
        cbn_reference = String()
        cbn_response = GenericScalar()
        report_data = GenericScalar()
        summary = GenericScalar()

    cbn_report = Field(CBNReportNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Check admin permission
        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("Only admins can update CBN reports.")
        
        cbn_report = _get_model_by_global_id(input["cbn_report_id"], CBNReport, "CBN report")
        
        if input.get("status"):
            valid_statuses = [choice[0] for choice in CBNReport.REPORT_STATUS]
            if input["status"] not in valid_statuses:
                raise GraphQLError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            cbn_report.status = input["status"]
            
            if input["status"] == "SUBMITTED":
                cbn_report.submitted_at = timezone.now()
            elif input["status"] == "ACKNOWLEDGED":
                cbn_report.acknowledged_at = timezone.now()
        
        if input.get("cbn_reference") is not None:
            cbn_report.cbn_reference = input["cbn_reference"]
        
        if input.get("cbn_response") is not None:
            cbn_report.cbn_response = input["cbn_response"]
        
        if input.get("report_data") is not None:
            cbn_report.report_data = input["report_data"]
        
        if input.get("summary") is not None:
            cbn_report.summary = input["summary"]
        
        try:
            cbn_report.save()
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            cbn_report=cbn_report,
            success=True,
            message="CBN report updated successfully.",
        )


class SubmitCBNReportMutation(relay.ClientIDMutation):
    """Submit a CBN report to the Central Bank."""

    class Input:
        cbn_report_id = ID(required=True)

    cbn_report = Field(CBNReportNode)
    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Check admin permission
        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("Only admins can submit CBN reports.")
        
        cbn_report = _get_model_by_global_id(input["cbn_report_id"], CBNReport, "CBN report")
        
        if cbn_report.status != "GENERATED":
            raise GraphQLError("Only generated reports can be submitted.")
        
        # In production, this would call the CBN API
        try:
            cbn_report.status = "SUBMITTED"
            cbn_report.submitted_at = timezone.now()
            # Simulate CBN response
            cbn_report.cbn_reference = f"CBN-ACK-{uuid.uuid4().hex[:8].upper()}"
            cbn_report.cbn_response = {
                "status": "RECEIVED",
                "message": "Report received by CBN.",
                "timestamp": timezone.now().isoformat(),
            }
            cbn_report.save()
        except ValidationError as exc:
            raise GraphQLError(str(exc)) from exc
        
        return cls(
            cbn_report=cbn_report,
            success=True,
            message="CBN report submitted successfully.",
        )


class DeleteCBNReportMutation(relay.ClientIDMutation):
    """Delete a CBN report."""

    class Input:
        cbn_report_id = ID(required=True)

    success = Boolean()
    message = String()

    @classmethod
    @login_required
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        user = _get_authenticated_user(info)
        
        # Check admin permission
        if not user.is_staff and not user.is_superuser:
            raise GraphQLError("Only admins can delete CBN reports.")
        
        cbn_report = _get_model_by_global_id(input["cbn_report_id"], CBNReport, "CBN report")
        
        if cbn_report.status in ["SUBMITTED", "ACKNOWLEDGED"]:
            raise GraphQLError("Cannot delete a submitted or acknowledged report.")
        
        cbn_report.delete()
        
        return cls(
            success=True,
            message="CBN report deleted successfully.",
        )


# ============================================================================
# MUTATION REGISTRY
# ============================================================================

class RegulatoryMutations(graphene.ObjectType):
    # BVN Verification
    create_bvn_verification = CreateBVNVerificationMutation.Field()
    verify_bvn = VerifyBVNMutation.Field()
    update_bvn_verification = UpdateBVNVerificationMutation.Field()
    resend_bvn_verification = ResendBVNVerificationMutation.Field()
    delete_bvn_verification = DeleteBVNVerificationMutation.Field()
    
    # CBN Report
    generate_cbn_report = GenerateCBNReportMutation.Field()
    generate_transaction_report = GenerateTransactionReportMutation.Field()
    generate_suspicious_activity_report = GenerateSuspiciousActivityReportMutation.Field()
    update_cbn_report = UpdateCBNReportMutation.Field()
    submit_cbn_report = SubmitCBNReportMutation.Field()
    delete_cbn_report = DeleteCBNReportMutation.Field()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # BVN Verification
    "CreateBVNVerificationMutation",
    "VerifyBVNMutation",
    "UpdateBVNVerificationMutation",
    "ResendBVNVerificationMutation",
    "DeleteBVNVerificationMutation",
    
    # CBN Report
    "GenerateCBNReportMutation",
    "GenerateTransactionReportMutation",
    "GenerateSuspiciousActivityReportMutation",
    "UpdateCBNReportMutation",
    "SubmitCBNReportMutation",
    "DeleteCBNReportMutation",
    
    # Registry
    "RegulatoryMutations",
]