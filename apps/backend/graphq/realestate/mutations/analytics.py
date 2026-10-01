# apps/backend/realestate/mutations/analytics.py

"""
Analytics Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

from ..models.analytics import (
    MortgageCalculation,
    ROICalculation,
    CMAReport,
    InstantValuation,
)
from ..models.listing import Listing
from ..services.analytics import (
    MortgageCalculator,
    ROIInvestorCalculator,
    CMAReportGenerator,
    InstantValuationService,
)


# =============================================================================
# Mortgage Calculation Mutation
# =============================================================================

class CalculateMortgageMutation(relay.ClientIDMutation):
    """
    Calculate mortgage payments for a property.
    
    Returns monthly payment, total payment, and total interest.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        principal = graphene.Decimal(required=True)
        annual_rate = graphene.Decimal(required=True)
        years = graphene.Int(required=True)
        save = graphene.Boolean(required=False, default_value=False)
    
    mortgage_calculation = graphene.JSONString()
    saved_calculation = graphene.Field(MortgageCalculationNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, listing_id, principal, annual_rate, years, save=False):
        """
        Calculate mortgage.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            listing_id: Listing ID
            principal: Loan amount
            annual_rate: Annual interest rate
            years: Loan term in years
            save: Whether to save the calculation
        
        Returns:
            CalculateMortgageMutation instance
        """
        errors = {}
        
        # Check authentication for save
        user = info.context.user if hasattr(info.context, 'user') else None
        if save and (not user or not user.is_authenticated):
            errors['authentication'] = ['Authentication required to save calculation.']
            return cls(success=False, errors=errors)
        
        # Validate inputs
        if principal <= 0:
            errors['principal'] = ['Principal must be greater than 0.']
            return cls(success=False, errors=errors)
        
        if annual_rate <= 0:
            errors['annual_rate'] = ['Annual rate must be greater than 0.']
            return cls(success=False, errors=errors)
        
        if years <= 0:
            errors['years'] = ['Years must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Resolve listing
        try:
            pk = from_global_id(listing_id)[1]
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['listing_id'] = ['Property not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['listing_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Calculate mortgage
            results = MortgageCalculator.calculate(principal, annual_rate, years)
            
            # Save if requested
            saved_calculation = None
            if save:
                saved_calculation = MortgageCalculator.save_calculation(
                    listing, user, principal, annual_rate, years, results
                )
            
            return cls(
                mortgage_calculation={
                    'monthly_payment': float(results['monthly_payment']),
                    'total_payment': float(results['total_payment']),
                    'total_interest': float(results['total_interest']),
                },
                saved_calculation=saved_calculation,
                success=True,
                errors={}
            )
            
        except ValueError as e:
            errors['calculation'] = [str(e)]
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# ROI Calculation Mutation
# =============================================================================

class CalculateROIMutation(relay.ClientIDMutation):
    """
    Calculate return on investment for a property.
    
    Returns cash-on-cash return, cap rate, total return, and more.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        down_payment = graphene.Decimal(required=True)
        interest_rate = graphene.Decimal(required=True)
        loan_term = graphene.Int(required=True)
        monthly_rent = graphene.Decimal(required=True)
        annual_appreciation = graphene.Decimal(required=True)
        expenses_percent = graphene.Decimal(required=True)
        years = graphene.Int(required=False, default_value=5)
        save = graphene.Boolean(required=False, default_value=False)
    
    roi_calculation = graphene.JSONString()
    saved_calculation = graphene.Field('graphq.realestate.types.ROICalculationNode')
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **kwargs):
        """
        Calculate ROI.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            kwargs: Input parameters
        
        Returns:
            CalculateROIMutation instance
        """
        errors = {}
        
        listing_id = kwargs.get('listing_id')
        down_payment = kwargs.get('down_payment')
        interest_rate = kwargs.get('interest_rate')
        loan_term = kwargs.get('loan_term')
        monthly_rent = kwargs.get('monthly_rent')
        annual_appreciation = kwargs.get('annual_appreciation')
        expenses_percent = kwargs.get('expenses_percent')
        years = kwargs.get('years', 5)
        save = kwargs.get('save', False)
        
        # Check authentication for save
        user = info.context.user if hasattr(info.context, 'user') else None
        if save and (not user or not user.is_authenticated):
            errors['authentication'] = ['Authentication required to save calculation.']
            return cls(success=False, errors=errors)
        
        # Validate inputs
        if down_payment <= 0:
            errors['down_payment'] = ['Down payment must be greater than 0.']
            return cls(success=False, errors=errors)
        
        if interest_rate <= 0:
            errors['interest_rate'] = ['Interest rate must be greater than 0.']
            return cls(success=False, errors=errors)
        
        if loan_term <= 0:
            errors['loan_term'] = ['Loan term must be greater than 0.']
            return cls(success=False, errors=errors)
        
        if monthly_rent <= 0:
            errors['monthly_rent'] = ['Monthly rent must be greater than 0.']
            return cls(success=False, errors=errors)
        
        if annual_appreciation < 0:
            errors['annual_appreciation'] = ['Annual appreciation cannot be negative.']
            return cls(success=False, errors=errors)
        
        if expenses_percent < 0 or expenses_percent > 100:
            errors['expenses_percent'] = ['Expenses percent must be between 0 and 100.']
            return cls(success=False, errors=errors)
        
        if years <= 0:
            errors['years'] = ['Years must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Resolve listing
        try:
            pk = from_global_id(listing_id)[1]
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['listing_id'] = ['Property not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['listing_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Calculate ROI
            results = ROIInvestorCalculator.calculate(
                listing=listing,
                down_payment=down_payment,
                interest_rate=interest_rate,
                loan_term=loan_term,
                monthly_rent=monthly_rent,
                annual_appreciation=annual_appreciation,
                expenses_percent=expenses_percent,
                years=years,
            )
            
            # Save if requested
            saved_calculation = None
            if save:
                saved_calculation = ROIInvestorCalculator.save_calculation(
                    listing, user, down_payment, interest_rate, loan_term,
                    monthly_rent, annual_appreciation, expenses_percent, years, results
                )
            
            return cls(
                roi_calculation={
                    'cash_on_cash_return': float(results['cash_on_cash_return']),
                    'cap_rate': float(results['cap_rate']),
                    'total_return': float(results['total_return']),
                    'annualized_return': float(results['annualized_return']),
                    'monthly_cash_flow': float(results['monthly_cash_flow']),
                },
                saved_calculation=saved_calculation,
                success=True,
                errors={}
            )
            
        except ValueError as e:
            errors['calculation'] = [str(e)]
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Generate CMA Report Mutation
# =============================================================================

class GenerateCMAReportMutation(relay.ClientIDMutation):
    """
    Generate a Comparative Market Analysis report.
    
    Compares the property with similar recently sold properties
    to estimate market value.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        save = graphene.Boolean(required=False, default_value=True)
    
    cma_report = graphene.JSONString()
    saved_report = graphene.Field('graphq.realestate.types.CMAReportNode')
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, listing_id, save=True):
        """
        Generate CMA report.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            listing_id: Listing ID
            save: Whether to save the report
        
        Returns:
            GenerateCMAReportMutation instance
        """
        errors = {}
        
        # Check authentication for save
        user = info.context.user if hasattr(info.context, 'user') else None
        if save and (not user or not user.is_authenticated):
            errors['authentication'] = ['Authentication required to save report.']
            return cls(success=False, errors=errors)
        
        # Resolve listing
        try:
            pk = from_global_id(listing_id)[1]
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['listing_id'] = ['Property not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['listing_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Generate CMA report
            report_data = CMAReportGenerator.generate(listing)
            
            # Save if requested
            saved_report = None
            if save:
                saved_report = CMAReportGenerator.save_report(listing, user, report_data)
            
            # Remove sensitive/debug data before sending
            clean_report = {
                'subject_property': report_data.get('subject_property'),
                'comparables': report_data.get('comparables', []),
                'valuation_range': report_data.get('valuation_range', {}),
            }
            
            return cls(
                cma_report=clean_report,
                saved_report=saved_report,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Instant Valuation Mutation
# =============================================================================

class GetInstantValuationMutation(relay.ClientIDMutation):
    """
    Get instant valuation for a property.
    
    Provides a quick estimate of the property's market value.
    """
    
    class Input:
        listing_id = graphene.ID(required=True)
        save = graphene.Boolean(required=False, default_value=True)
    
    valuation = graphene.JSONString()
    saved_valuation = graphene.Field('graphq.realestate.types.InstantValuationNode')
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, listing_id, save=True):
        """
        Get instant valuation.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            listing_id: Listing ID
            save: Whether to save the valuation
        
        Returns:
            GetInstantValuationMutation instance
        """
        errors = {}
        
        # Check authentication for save
        user = info.context.user if hasattr(info.context, 'user') else None
        if save and (not user or not user.is_authenticated):
            errors['authentication'] = ['Authentication required to save valuation.']
            return cls(success=False, errors=errors)
        
        # Resolve listing
        try:
            pk = from_global_id(listing_id)[1]
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['listing_id'] = ['Property not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['listing_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Get valuation
            valuation_data = InstantValuationService.get_valuation(listing)
            
            # Save if requested
            saved_valuation = None
            if save:
                saved_valuation = InstantValuationService.save_valuation(
                    listing, user, valuation_data
                )
            
            return cls(
                valuation={
                    'estimated_value': float(valuation_data['estimated_value']),
                    'min_value': float(valuation_data.get('min_value', 0)),
                    'max_value': float(valuation_data.get('max_value', 0)),
                    'confidence_score': float(valuation_data.get('confidence_score', 0)),
                    'comparable_count': valuation_data.get('comparable_count', 0),
                },
                saved_valuation=saved_valuation,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Export Mutations
# =============================================================================

class AnalyticsMutations(graphene.ObjectType):
    """All analytics mutations."""
    
    calculate_mortgage = CalculateMortgageMutation.Field()
    calculate_roi = CalculateROIMutation.Field()
    generate_cma_report = GenerateCMAReportMutation.Field()
    get_instant_valuation = GetInstantValuationMutation.Field()