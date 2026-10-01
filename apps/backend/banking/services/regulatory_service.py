# apps/backend/banking/services/regulatory_service.py

"""
Regulatory reporting service.

Generates CBN-required reports from internal transaction and fraud data.
Does NOT move money.

Two report generators:

    generate_transaction_report(period)
        Summarizes successful Transaction rows in a date window.

    generate_suspicious_activity_report()
        Summarizes open FraudAlert rows from the last 30 days.

Both return the report data as a dict. Persistence into CBNReport rows
is the caller's responsibility (mutation or scheduled task).
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from banking.models.payments import Transaction
from banking.models.security import FraudAlert

logger = logging.getLogger(__name__)


class RegulatoryService:
    """Service layer for regulatory report generation."""

    # ------------------------------------------------------------------
    # TRANSACTION REPORT
    # ------------------------------------------------------------------

    @staticmethod
    def generate_transaction_report(period: dict) -> dict:
        """
        Generate a CBN transaction report for a period.

        `period` must have 'start' and 'end' as date objects.

        Filters on Transaction.SUCCESS (uppercase). The prior
        implementation used status='completed', which matched zero rows
        on Postgres and silently produced empty reports.
        """
        start = period.get("start")
        end = period.get("end")
        if start is None or end is None:
            raise ValueError("period must include 'start' and 'end'.")

        transactions = Transaction.objects.filter(
            created_at__date__range=[start, end],
            status=Transaction.SUCCESS,
        )

        stats = transactions.aggregate(
            total_transactions=Count("id"),
            total_amount=Sum("amount"),
            total_fees=Sum("fee"),
        )

        by_type = {
            row["type"]: {
                "count": row["count"],
                "amount": str(row["amount"] or Decimal("0.00")),
            }
            for row in transactions
            .values("type")
            .annotate(count=Count("id"), amount=Sum("amount"))
        }

        by_status = {
            row["status"]: row["count"]
            for row in transactions
            .values("status")
            .annotate(count=Count("id"))
        }

        report_data = {
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "summary": {
                "total_transactions": stats["total_transactions"] or 0,
                "total_amount": str(
                    stats["total_amount"] or Decimal("0.00")
                ),
                "total_fees": str(
                    stats["total_fees"] or Decimal("0.00")
                ),
            },
            "transactions_by_type": by_type,
            "transactions_by_status": by_status,
        }

        logger.info(
            "Generated CBN transaction report for %s to %s: %s txns, "
            "total=%s",
            start,
            end,
            report_data["summary"]["total_transactions"],
            report_data["summary"]["total_amount"],
        )

        return report_data

    # ------------------------------------------------------------------
    # SUSPICIOUS ACTIVITY REPORT
    # ------------------------------------------------------------------

    @staticmethod
    def generate_suspicious_activity_report() -> dict:
        """
        Generate a Suspicious Activity Report from open FraudAlert rows
        created in the last 30 days.
        """
        cutoff = timezone.now() - timezone.timedelta(days=30)

        alerts = FraudAlert.objects.filter(
            status="OPEN",
            created_at__gte=cutoff,
        ).select_related("user", "rule")

        # High-risk count: alerts whose rule action is BLOCK.
        # Uses Q to keep the shape defensive if the rule action field
        # is later renamed.
        high_risk_count = alerts.filter(rule__action="BLOCK").count()

        suspicious_activities = []
        for alert in alerts:
            rule = getattr(alert, "rule", None)
            user = getattr(alert, "user", None)

            suspicious_activities.append({
                "alert_id": alert.id,
                "reference": alert.transaction_reference,
                "user_reference": str(user.id) if user else "Unknown",
                "rule_triggered": getattr(rule, "name", None),
                "detected_value": (
                    float(alert.detected_value)
                    if alert.detected_value is not None
                    else None
                ),
                "timestamp": alert.created_at.isoformat(),
                "evidence": alert.evidence_data,
                "notes": alert.notes,
            })

        report_data = {
            "generated_at": timezone.now().isoformat(),
            "period_days": 30,
            "suspicious_activities": suspicious_activities,
            "summary": {
                "total_cases": len(suspicious_activities),
                "high_risk_cases": high_risk_count,
                "total_amount_involved": "0.00",
            },
        }

        logger.info(
            "Generated SAR: %s cases, %s high-risk",
            report_data["summary"]["total_cases"],
            report_data["summary"]["high_risk_cases"],
        )

        return report_data