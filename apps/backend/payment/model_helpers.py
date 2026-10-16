'''from collections.abc import Iterable
from operator import attrgetter
from typing import TYPE_CHECKING

from core.taxes import zero_money, zero_taxed_money
from ecommerce.models.order import OrderLine

def get_subtotal(order_lines: Iterable["OrderLine"], fallback_currency: str):
    subtotal_iterator = (line.total_price for line in order_lines)
    return sum(subtotal_iterator, zero_taxed_money(currency=fallback_currency))'''
