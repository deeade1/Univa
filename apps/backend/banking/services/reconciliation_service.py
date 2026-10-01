# apps/backend/banking/services/reconciliation_service.py

"""
Reconciliation service.

Runs reconciliation for a set of float accounts over a date range and
records the results.

Reconciliation does NOT move money. It compares internal ledger
records against external bank statements and records matches and
mismatches. Any corrective action (adjustment journal) is a separate,
explicit, staff-initiated operation.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from banking.models.accounting import FloatAccount
from banking.models.payments import Transaction
from banking.models.reconciliation import (
    ReconciliationMatch,
    ReconciliationRun,
    UnreconciledTransaction,
)

logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")


class ReconciliationService:
    """
    Service layer for reconciliation runs.

    Reads internal transactions and matches them against external
    statement lines. Writes ReconciliationMatch and
    UnreconciledTransaction rows. Does NOT post ledger entries.
    """

    @staticmethod
    @db_transaction.atomic
    def start_run(
        *,
        run_date,
        date_from,
        date_to,
        float_accounts: list[FloatAccount],
        created_by=None,
        config: dict | None = None,
    ) -> ReconciliationRun:
        """Create a ReconciliationRun ready to be executed."""
        if not float_accounts:
            raise ValidationError(
                "At least one float account is required."
            )

        if date_from > date_to:
            raise ValidationError(
                "date_from cannot be after date_to."
            )

        for fa in float_accounts:
            if not fa.is_active:
                raise ValidationError(
                    f"Float account {fa.account_number} is not active."
                )

        reference = (
            f"REC-{run_date.strftime('%Y%m%d')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        run = ReconciliationRun.objects.create(
            reference=reference,
            run_date=run_date,
            status="STARTED",
            date_from=date_from,
            date_to=date_to,
            config=config or {},
        )
        run.float_accounts.set(float_accounts)
        return run

    @staticmethod
    @db_transaction.atomic
    def execute_run(
        *, reconciliation_run: ReconciliationRun
    ) -> ReconciliationRun:
        """Execute the reconciliation for every float account in the run."""
        if reconciliation_run.status in ("COMPLETED", "PARTIAL", "FAILED"):
            raise ValidationError(
                "This reconciliation run has already been completed."
            )

        reconciliation_run.status = "IN_PROGRESS"
        reconciliation_run.save(update_fields=["status"])

        try:
            total_matched = 0
            total_unmatched = 0
            total_discrepancy = Decimal("0.00")

            for float_account in reconciliation_run.float_accounts.all():
                result = ReconciliationService._reconcile_float_account(
                    float_account=float_account,
                    reconciliation_run=reconciliation_run,
                )
                total_matched += result["matched"]
                total_unmatched += result["unmatched"]
                total_discrepancy += result["discrepancy"]

            reconciliation_run.total_transactions = (
                total_matched + total_unmatched
            )
            reconciliation_run.matched_transactions = total_matched
            reconciliation_run.unmatched_transactions = total_unmatched
            reconciliation_run.total_discrepancy = total_discrepancy
            reconciliation_run.status = (
                "COMPLETED" if total_unmatched == 0 else "PARTIAL"
            )
            reconciliation_run.completed_at = timezone.now()
            reconciliation_run.duration_seconds = (
                reconciliation_run.completed_at
                - reconciliation_run.started_at
            ).total_seconds()
            reconciliation_run.save()

            logger.info(
                "Reconciliation %s completed: matched=%s unmatched=%s "
                "discrepancy=%s",
                reconciliation_run.reference,
                total_matched,
                total_unmatched,
                total_discrepancy,
            )
            return reconciliation_run

        except Exception as exc:
            reconciliation_run.status = "FAILED"
            reconciliation_run.results = {"error": str(exc)}
            reconciliation_run.save(update_fields=["status", "results"])
            logger.exception(
                "Reconciliation %s failed", reconciliation_run.reference,
            )
            raise

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _reconcile_float_account(
        *,
        float_account: FloatAccount,
        reconciliation_run: ReconciliationRun,
    ) -> dict:
        internal_txns = ReconciliationService._get_internal_transactions(
            float_account, reconciliation_run
        )
        external_txns = ReconciliationService._get_external_transactions(
            float_account, reconciliation_run
        )

        matches, unmatched_internal, unmatched_external = (
            ReconciliationService._match_transactions(
                internal_txns, external_txns
            )
        )

        for match in matches:
            ReconciliationMatch.objects.create(
                reconciliation_run=reconciliation_run,
                float_account=float_account,
                internal_transaction=match["internal"],
                internal_amount=match["internal"].amount,
                internal_date=match["internal"].created_at,
                external_reference=match["external"]["reference"],
                external_amount=match["external"]["amount"],
                external_date=match["external"]["date"],
                external_description=match["external"].get(
                    "description", ""
                ),
                match_type=match["type"],
                match_confidence=match["confidence"],
                amount_difference=match["amount_difference"],
            )

        for txn in unmatched_internal:
            UnreconciledTransaction.objects.create(
                reconciliation_run=reconciliation_run,
                float_account=float_account,
                source="INTERNAL",
                transaction_reference=txn.reference,
                amount=txn.amount,
                transaction_date=txn.created_at,
                description=txn.narration or "",
            )

        for txn in unmatched_external:
            UnreconciledTransaction.objects.create(
                reconciliation_run=reconciliation_run,
                float_account=float_account,
                source="EXTERNAL",
                transaction_reference=txn["reference"],
                amount=txn["amount"],
                transaction_date=txn["date"],
                description=txn.get("description", ""),
            )

        return {
            "matched": len(matches),
            "unmatched": len(unmatched_internal) + len(unmatched_external),
            "discrepancy": sum(
                (m["amount_difference"] for m in matches),
                Decimal("0.00"),
            ),
        }

    @staticmethod
    def _get_internal_transactions(float_account, reconciliation_run):
        """
        Return internal Transaction rows in scope for this run.

        Filters on Transaction.SUCCESS (uppercase), not 'completed'.
        The prior implementation used status='completed', which matched
        zero rows against Postgres's case-sensitive comparison and
        silently reconciled against an empty set.
        """
        return Transaction.objects.filter(
            created_at__date__range=[
                reconciliation_run.date_from,
                reconciliation_run.date_to,
            ],
            status=Transaction.SUCCESS,
        )

    @staticmethod
    def _get_external_transactions(float_account, reconciliation_run):
        """
        Return external statement lines for this float account and window.

        No bank API integration yet — returns an empty list so the run
        records every internal transaction as unreconciled pending a
        real statement source.
        """
        return []

    @staticmethod
    def _match_transactions(internal_txns, external_txns):
        matches = []
        unmatched_internal = list(internal_txns)
        unmatched_external = list(external_txns)

        for internal in list(unmatched_internal):
            for external in list(unmatched_external):
                if ReconciliationService._transactions_match(
                    internal, external
                ):
                    matches.append({
                        "internal": internal,
                        "external": external,
                        "type": "PERFECT",
                        "confidence": 1.0,
                        "amount_difference": Decimal("0.00"),
                    })
                    unmatched_internal.remove(internal)
                    unmatched_external.remove(external)
                    break

        return matches, unmatched_internal, unmatched_external

    @staticmethod
    def _transactions_match(internal, external) -> bool:
        return (
            internal.amount == external["amount"]
            and internal.created_at.date() == external["date"].date()
        )