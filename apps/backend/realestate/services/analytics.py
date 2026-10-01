# apps/backend/realestate/services/analytics.py

"""
Analytics services for real estate calculations.
"""

from decimal import Decimal
from datetime import timedelta
from typing import Dict, List, Optional, Any

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import Avg, Max, Min, Q
from django.utils import timezone

from ..models.analytics import (
    MortgageCalculation,
    ROICalculation,
    CMAReport,
    InstantValuation,
)
from ..models.listing import Listing


class MortgageCalculator:
    """Calculate mortgage payments and amortization."""
    
    @staticmethod
    def calculate(
        principal: Decimal,
        annual_rate: Decimal,
        years: int
    ) -> Dict[str, Decimal]:
        """
        Calculate monthly mortgage payment.
        
        Args:
            principal: Loan amount
            annual_rate: Annual interest rate (as percentage, e.g., 5.5)
            years: Loan term in years
        
        Returns:
            Dict with monthly_payment, total_payment, total_interest
        """
        if principal <= 0 or annual_rate <= 0 or years <= 0:
            raise ValueError("All inputs must be positive")
        
        monthly_rate = Decimal(annual_rate / 100 / 12)
        months = years * 12
        
        if monthly_rate == 0:
            monthly_payment = principal / months
        else:
            monthly_payment = principal * (
                monthly_rate * (1 + monthly_rate) ** months
            ) / (
                (1 + monthly_rate) ** months - 1
            )
        
        total_payment = monthly_payment * months
        total_interest = total_payment - principal
        
        return {
            'monthly_payment': monthly_payment,
            'total_payment': total_payment,
            'total_interest': total_interest,
        }
    
    @staticmethod
    def save_calculation(
        listing: Listing,
        user: Any,
        principal: Decimal,
        annual_rate: Decimal,
        years: int,
        results: Dict[str, Decimal]
    ) -> MortgageCalculation:
        """Save mortgage calculation to database."""
        return MortgageCalculation.objects.create(
            listing=listing,
            user=user,
            principal=principal,
            annual_rate=annual_rate,
            years=years,
            monthly_payment=results['monthly_payment'],
            total_payment=results['total_payment'],
            total_interest=results['total_interest'],
        )


class ROIInvestorCalculator:
    """Calculate return on investment for rental properties."""
    
    @staticmethod
    def calculate(
        listing: Listing,
        down_payment: Decimal,
        interest_rate: Decimal,
        loan_term: int,
        monthly_rent: Decimal,
        annual_appreciation: Decimal,
        expenses_percent: Decimal,
        years: int = 5
    ) -> Dict[str, Any]:
        """
        Calculate ROI metrics.
        
        Args:
            listing: The property listing
            down_payment: Down payment amount
            interest_rate: Annual interest rate
            loan_term: Loan term in years
            monthly_rent: Expected monthly rent
            annual_appreciation: Expected annual appreciation %
            expenses_percent: Annual expenses as % of rent
            years: Investment timeframe
        
        Returns:
            Dict with ROI metrics
        """
        if down_payment <= 0:
            raise ValueError("Down payment must be positive")
        
        price = listing.price
        loan_amount = price - down_payment
        
        # Calculate monthly mortgage payment
        mortgage_result = MortgageCalculator.calculate(
            loan_amount,
            interest_rate,
            loan_term
        )
        monthly_mortgage = mortgage_result['monthly_payment']
        
        # Calculate annual cash flow
        annual_rent = monthly_rent * 12
        annual_expenses = annual_rent * (expenses_percent / 100)
        annual_mortgage = monthly_mortgage * 12
        annual_cash_flow = annual_rent - annual_expenses - annual_mortgage
        
        # Calculate cash on cash return
        cash_on_cash_return = (annual_cash_flow / down_payment) * 100
        
        # Calculate cap rate
        net_operating_income = annual_rent - annual_expenses
        cap_rate = (net_operating_income / price) * 100
        
        # Calculate total return over investment period
        # Appreciation
        current_value = price
        for _ in range(years):
            current_value *= (1 + annual_appreciation / 100)
        
        appreciation_gain = current_value - price
        
        # Total cash flow over years
        total_cash_flow = 0
        for _ in range(years):
            total_cash_flow += annual_cash_flow
        
        total_return = appreciation_gain + total_cash_flow
        
        # Annualized return
        if down_payment > 0 and years > 0:
            annualized_return = ((1 + total_return / down_payment) ** (1 / years) - 1) * 100
        else:
            annualized_return = Decimal('0')
        
        # Monthly cash flow
        monthly_cash_flow = annual_cash_flow / 12
        
        return {
            'cash_on_cash_return': cash_on_cash_return,
            'cap_rate': cap_rate,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'monthly_cash_flow': monthly_cash_flow,
            'monthly_mortgage': monthly_mortgage,
            'annual_cash_flow': annual_cash_flow,
        }
    
    @staticmethod
    def save_calculation(
        listing: Listing,
        user: Any,
        down_payment: Decimal,
        interest_rate: Decimal,
        loan_term: int,
        monthly_rent: Decimal,
        annual_appreciation: Decimal,
        expenses_percent: Decimal,
        years: int,
        results: Dict[str, Any]
    ) -> ROICalculation:
        """Save ROI calculation to database."""
        return ROICalculation.objects.create(
            listing=listing,
            user=user,
            down_payment=down_payment,
            interest_rate=interest_rate,
            loan_term=loan_term,
            monthly_rent=monthly_rent,
            annual_appreciation=annual_appreciation,
            expenses_percent=expenses_percent,
            years=years,
            cash_on_cash_return=results['cash_on_cash_return'],
            cap_rate=results['cap_rate'],
            total_return=results['total_return'],
            annualized_return=results['annualized_return'],
            monthly_cash_flow=results['monthly_cash_flow'],
        )


class CMAReportGenerator:
    """Generate Comparative Market Analysis reports."""
    
    @staticmethod
    def generate(listing: Listing) -> Dict[str, Any]:
        """
        Generate a CMA report for a property.
        
        Args:
            listing: The subject property
        
        Returns:
            Dict with report data
        """
        comparables = CMAReportGenerator._find_comparables(listing)
        adjustments = CMAReportGenerator._calculate_adjustments(listing, comparables)
        valuation = CMAReportGenerator._calculate_valuation(comparables, adjustments)
        
        return {
            'subject_property': CMAReportGenerator._property_data(listing),
            'comparables': [CMAReportGenerator._property_data(p) for p in comparables],
            'adjustments': adjustments,
            'valuation_range': valuation,
        }
    
    @staticmethod
    def _find_comparables(listing: Listing, limit: int = 5) -> List[Listing]:
        """Find similar properties sold recently in the area."""
        if not listing.location_point:
            return []
        
        return Listing.objects.filter(
            location_point__distance_lte=(
                listing.location_point,
                D(km=1.5)
            ),
            property_status='sold',
            sold_date__gte=timezone.now() - timedelta(days=90),
            listing_type=listing.listing_type,
        ).exclude(pk=listing.pk).annotate(
            distance=Distance('location_point', listing.location_point)
        ).order_by('sold_date')[:limit]
    
    @staticmethod
    def _calculate_adjustments(
        subject: Listing,
        comparables: List[Listing]
    ) -> List[Dict[str, Any]]:
        """Calculate value adjustments for differences."""
        adjustments = []
        
        for comp in comparables:
            adj = {
                'property_id': comp.id,
                'property_title': comp.title,
                'price_per_sqft': comp.price / comp.square_feet if comp.square_feet else 0,
                'adjustments': {}
            }
            
            # Square footage adjustment
            if subject.square_feet and comp.square_feet and comp.square_feet > 0:
                sqft_diff = subject.square_feet - comp.square_feet
                adj['adjustments']['square_feet'] = Decimal(sqft_diff) * adj['price_per_sqft']
            
            # Age adjustment
            if subject.year_built and comp.year_built:
                age_diff = subject.year_built - comp.year_built
                adj['adjustments']['age'] = Decimal(age_diff) * Decimal('1000')
            
            # Bedroom adjustment
            if subject.bedrooms and comp.bedrooms:
                bed_diff = subject.bedrooms - comp.bedrooms
                adj['adjustments']['bedrooms'] = Decimal(bed_diff) * Decimal('5000')
            
            # Bathroom adjustment
            if subject.bathrooms and comp.bathrooms:
                bath_diff = subject.bathrooms - comp.bathrooms
                adj['adjustments']['bathrooms'] = Decimal(bath_diff) * Decimal('7500')
            
            adjustments.append(adj)
        
        return adjustments
    
    @staticmethod
    def _calculate_valuation(
        comparables: List[Listing],
        adjustments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate estimated value range."""
        adjusted_values = []
        
        for comp, adj in zip(comparables, adjustments):
            total_adjustment = sum(
                Decimal(str(v)) for v in adj['adjustments'].values()
            )
            adjusted_value = comp.price + total_adjustment
            adjusted_values.append(adjusted_value)
        
        if not adjusted_values:
            return {
                'low': None,
                'high': None,
                'avg': None
            }
        
        return {
            'low': min(adjusted_values),
            'high': max(adjusted_values),
            'avg': sum(adjusted_values) / len(adjusted_values)
        }
    
    @staticmethod
    def _property_data(listing: Listing) -> Dict[str, Any]:
        """Extract property data for the report."""
        return {
            'id': listing.id,
            'title': listing.title,
            'price': listing.price,
            'square_feet': listing.square_feet,
            'bedrooms': listing.bedrooms,
            'bathrooms': listing.bathrooms,
            'year_built': listing.year_built,
            'address': listing.location_string,
            'property_type': listing.listing_type.property_type if listing.listing_type else None,
            'sold_date': getattr(listing, 'sold_date', None),
        }
    
    @staticmethod
    def save_report(
        listing: Listing,
        user: Any,
        report_data: Dict[str, Any]
    ) -> CMAReport:
        """Save CMA report to database."""
        valuation = report_data.get('valuation_range', {})
        
        return CMAReport.objects.create(
            listing=listing,
            user=user,
            comparables=report_data.get('comparables', []),
            adjustments=report_data.get('adjustments', {}),
            valuation_range_low=valuation.get('low'),
            valuation_range_high=valuation.get('high'),
            valuation_avg=valuation.get('avg'),
            status='completed',
        )


class InstantValuationService:
    """Generate instant property valuations."""
    
    @staticmethod
    def get_valuation(listing: Listing) -> Dict[str, Any]:
        """
        Get instant valuation for a property.
        
        Args:
            listing: The property to value
        
        Returns:
            Dict with valuation data
        """
        # Find comparables
        comparables = CMAReportGenerator._find_comparables(listing, limit=10)
        
        if not comparables:
            # Fallback: use area average if available
            return InstantValuationService._fallback_valuation(listing)
        
        # Calculate average price per sqft
        avg_price_per_sqft = 0
        count = 0
        for comp in comparables:
            if comp.price and comp.square_feet and comp.square_feet > 0:
                avg_price_per_sqft += comp.price / comp.square_feet
                count += 1
        
        if count == 0:
            return InstantValuationService._fallback_valuation(listing)
        
        avg_price_per_sqft = avg_price_per_sqft / count
        estimated_value = avg_price_per_sqft * (listing.square_feet or 0)
        
        # Calculate confidence score based on comparable count
        confidence_score = min(95, 60 + (len(comparables) * 3))
        
        # Calculate range
        min_value = estimated_value * Decimal('0.90')
        max_value = estimated_value * Decimal('1.10')
        
        return {
            'estimated_value': estimated_value,
            'min_value': min_value,
            'max_value': max_value,
            'confidence_score': confidence_score,
            'comparable_count': len(comparables),
            'valuation_method': 'comparative',
        }
    
    @staticmethod
    def _fallback_valuation(listing: Listing) -> Dict[str, Any]:
        """Fallback valuation when no comparables are found."""
        # Use a simple formula: price * (1 + area adjustment)
        estimated_value = listing.price or Decimal('0')
        
        # Adjust based on area if available
        if listing.square_feet and listing.price and listing.price > 0:
            # Rough estimate: use current price as baseline
            estimated_value = listing.price
        
        return {
            'estimated_value': estimated_value,
            'min_value': estimated_value * Decimal('0.85'),
            'max_value': estimated_value * Decimal('1.15'),
            'confidence_score': Decimal('40.00'),
            'comparable_count': 0,
            'valuation_method': 'algorithm',
        }
    
    @staticmethod
    def save_valuation(
        listing: Listing,
        user: Any,
        valuation_data: Dict[str, Any]
    ) -> InstantValuation:
        """Save instant valuation to database."""
        return InstantValuation.objects.create(
            listing=listing,
            user=user,
            estimated_value=valuation_data['estimated_value'],
            min_value=valuation_data.get('min_value'),
            max_value=valuation_data.get('max_value'),
            confidence_score=valuation_data.get('confidence_score', Decimal('0')),
            comparable_count=valuation_data.get('comparable_count', 0),
            valuation_method=valuation_data.get('valuation_method', 'algorithm'),
        )