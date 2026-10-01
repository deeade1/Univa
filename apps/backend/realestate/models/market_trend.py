# apps/backend/realestate/models/market_trend.py

"""
Market Trend model for real estate.
"""

from django.db import models


class MarketTrend(models.Model):
    neighborhood = models.ForeignKey("Neighborhood", on_delete=models.CASCADE, related_name="trends")
    date = models.DateField()
    median_price = models.DecimalField(max_digits=12, decimal_places=2)
    listings_count = models.PositiveIntegerField()
    avg_days_on_market = models.PositiveIntegerField()
    price_per_sqft = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["neighborhood", "-date"], name="market_trend_hood_date_idx"),
            models.Index(fields=["median_price"], name="market_trend_price_idx"),
        ]

    def __str__(self):
        return f"Market Trend for {self.neighborhood.name} on {self.date}"