# apps/backend/ecommerce/models/enums/channel.py
"""Channel enums."""


class AllocationStrategy:
    PRIORITIZE_SORTING_ORDER = "prioritize-sorting-order"
    PRIORITIZE_HIGH_STOCK = "prioritize-high-stock"
    PRIORITIZE_LOW_STOCK = "prioritize-low-stock"

    CHOICES = [
        (PRIORITIZE_SORTING_ORDER, "Prioritize sorting order"),
        (PRIORITIZE_HIGH_STOCK, "Prioritize high stock"),
        (PRIORITIZE_LOW_STOCK, "Prioritize low stock"),
    ]


class MarkAsPaidStrategy:
    PAYMENT_FLOW = "payment-flow"
    MANUAL = "manual"
    TRANSACTION_FLOW = "transaction-flow"

    CHOICES = [
        (PAYMENT_FLOW, "Payment flow"),
        (MANUAL, "Manual"),
        (TRANSACTION_FLOW, "Transaction flow"),
    ]


class TransactionFlowStrategy:
    CHARGE = "charge"
    AUTHORIZE = "authorize"
    AUTHORIZE_AND_CAPTURE = "authorize-and-capture"

    CHOICES = [
        (CHARGE, "Charge"),
        (AUTHORIZE, "Authorize"),
        (AUTHORIZE_AND_CAPTURE, "Authorize and capture"),
    ]