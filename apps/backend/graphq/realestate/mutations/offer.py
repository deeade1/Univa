# apps/backend/realestate/mutations/offer.py

"""
Offer Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import transaction
from django.utils import timezone

from realestate.models.offer import Offer
from realestate.models.listing import Listing
from realestate.models.client import Client
from graphq.realestate.types.offer import OfferNode

# =============================================================================
# Input Types
# =============================================================================

class OfferInput(graphene.InputObjectType):
    """Input for offer creation."""
    
    property_id = graphene.ID(required=True)
    offer_price = graphene.Decimal(required=True)
    message = graphene.String(required=False)
    expiration_days = graphene.Int(required=False, default_value=7)


class OfferUpdateInput(graphene.InputObjectType):
    """Input for offer update."""
    
    id = graphene.ID(required=True)
    offer_price = graphene.Decimal(required=False)
    status = graphene.String(required=False)
    message = graphene.String(required=False)
    expiration_date = graphene.DateTime(required=False)


# =============================================================================
# Create Offer Mutation
# =============================================================================

class CreateOfferMutation(relay.ClientIDMutation):
    """
    Create a new offer for a property.
    
    Allows a buyer to submit an offer on a property. The offer includes
    price, message, and expiration date.
    """
    
    class Input:
        id = graphene.ID(required=True)
        offer_price = graphene.Decimal(required=False)
        status = graphene.String(required=False)
        message = graphene.String(required=False)
        expiration_date = graphene.DateTime(required=False)
    
    offer = graphene.Field(OfferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: OfferInput data
        
        Returns:
            CreateOfferMutation instance
        """
        errors = {}
        
        # Extract input
        property_id = input.get('property_id')
        offer_price = input.get('offer_price')
        message = input.get('message', '')
        expiration_days = input.get('expiration_days', 7)
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate offer price
        if offer_price <= 0:
            errors['offer_price'] = ['Offer price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate expiration days
        if expiration_days <= 0:
            errors['expiration_days'] = ['Expiration days must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Resolve property
        try:
            pk = from_global_id(property_id)[1]
            property_obj = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            errors['property_id'] = ['Property not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['property_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if property is available for offers
        if not property_obj.is_published:
            errors['property'] = ['Property is not published.']
            return cls(success=False, errors=errors)
        
        if property_obj.property_for != 'S':
            errors['property'] = ['Property is not available for sale.']
            return cls(success=False, errors=errors)
        
        # Get client profile for the user
        try:
            client = Client.objects.get(user=user)
        except Client.DoesNotExist:
            errors['client'] = ['Client profile not found. Please create a client profile first.']
            return cls(success=False, errors=errors)
        
        # Check if user is the owner of the property
        if property_obj.owner and property_obj.owner == user:
            errors['property'] = ['You cannot make an offer on your own property.']
            return cls(success=False, errors=errors)
        
        # Check for existing pending offer
        if Offer.objects.filter(
            property=property_obj,
            buyer=client,
            status='pending'
        ).exists():
            errors['offer'] = ['You already have a pending offer for this property.']
            return cls(success=False, errors=errors)
        
        try:
            # Calculate expiration date
            expiration_date = timezone.now() + timezone.timedelta(days=expiration_days)
            
            # Create offer
            offer = Offer.objects.create(
                property=property_obj,
                buyer=client,
                offer_price=offer_price,
                message=message,
                status='pending',
                expiration_date=expiration_date,
            )
            
            return cls(
                offer=offer,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Offer Mutation
# =============================================================================

class UpdateOfferMutation(relay.ClientIDMutation):
    """
    Update an existing offer.
    
    Allows updating the price, status, message, or expiration date of an offer.
    """
    
    class Input:
        id = graphene.ID(required=True)
        offer_price = graphene.Decimal(required=False)
        status = graphene.String(required=False)
        message = graphene.String(required=False)
        expiration_date = graphene.DateTime(required=False)
    
    offer = graphene.Field(OfferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: OfferUpdateInput data
        
        Returns:
            UpdateOfferMutation instance
        """
        errors = {}
        
        # Extract input
        offer_id = input.get('id')
        offer_price = input.get('offer_price')
        status = input.get('status')
        message = input.get('message')
        expiration_date = input.get('expiration_date')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve offer
        try:
            pk = from_global_id(offer_id)[1]
            offer = Offer.objects.get(pk=pk)
        except Offer.DoesNotExist:
            errors['id'] = ['Offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only buyer or staff can update
        if offer.buyer.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this offer.']
            return cls(success=False, errors=errors)
        
        # Validate offer price if provided
        if offer_price is not None and offer_price <= 0:
            errors['offer_price'] = ['Offer price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate status if provided
        if status is not None:
            valid_statuses = ['pending', 'accepted', 'rejected', 'countered', 'withdrawn', 'expired']
            if status not in valid_statuses:
                errors['status'] = [
                    f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                ]
                return cls(success=False, errors=errors)
            
            # Check for expired offer
            if offer.is_expired():
                errors['status'] = ['Cannot update status of an expired offer.']
                return cls(success=False, errors=errors)
        
        # Validate expiration date
        if expiration_date and expiration_date <= timezone.now():
            errors['expiration_date'] = ['Expiration date must be in the future.']
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if offer_price is not None:
                offer.offer_price = offer_price
            if status is not None:
                offer.status = status
            if message is not None:
                offer.message = message
            if expiration_date is not None:
                offer.expiration_date = expiration_date
            
            offer.full_clean()
            offer.save()
            
            return cls(
                offer=offer,
                success=True,
                errors={}
            )
            
        except ValidationError as e:
            errors['validation'] = e.message_dict
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Accept Offer Mutation
# =============================================================================

class AcceptOfferMutation(relay.ClientIDMutation):
    """
    Accept an offer.
    
    This is a convenience mutation for accepting an offer and updating
    the property status accordingly.
    """
    
    class Input:
        offer_id = graphene.ID(required=True)
    
    offer = graphene.Field(OfferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, offer_id):
        """
        Accept an offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            offer_id: Offer ID to accept
        
        Returns:
            AcceptOfferMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve offer
        try:
            pk = from_global_id(offer_id)[1]
            offer = Offer.objects.get(pk=pk)
        except Offer.DoesNotExist:
            errors['offer_id'] = ['Offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['offer_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only property owner or staff can accept
        property_obj = offer.property
        if property_obj.owner != user and not user.is_staff:
            errors['permission'] = ['Only the property owner can accept offers.']
            return cls(success=False, errors=errors)
        
        # Check if offer is still pending
        if offer.status != 'pending':
            errors['status'] = [f'Offer is already {offer.status}.']
            return cls(success=False, errors=errors)
        
        # Check if offer is expired
        if offer.is_expired():
            errors['status'] = ['Cannot accept an expired offer.']
            return cls(success=False, errors=errors)
        
        try:
            # Accept the offer
            offer.status = 'accepted'
            offer.save()
            
            # Reject all other pending offers for this property
            Offer.objects.filter(
                property=property_obj,
                status='pending'
            ).exclude(pk=offer.pk).update(status='rejected')
            
            # Update property status
            property_obj.property_status = 'sold'
            property_obj.is_published = False
            property_obj.save()
            
            return cls(
                offer=offer,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Reject Offer Mutation
# =============================================================================

class RejectOfferMutation(relay.ClientIDMutation):
    """
    Reject an offer.
    
    This is a convenience mutation for rejecting an offer.
    """
    
    class Input:
        offer_id = graphene.ID(required=True)
        reason = graphene.String(required=False)
    
    offer = graphene.Field(OfferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, offer_id, reason=None):
        """
        Reject an offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            offer_id: Offer ID to reject
            reason: Optional rejection reason
        
        Returns:
            RejectOfferMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve offer
        try:
            pk = from_global_id(offer_id)[1]
            offer = Offer.objects.get(pk=pk)
        except Offer.DoesNotExist:
            errors['offer_id'] = ['Offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['offer_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only property owner or staff can reject
        property_obj = offer.property
        if property_obj.owner != user and not user.is_staff:
            errors['permission'] = ['Only the property owner can reject offers.']
            return cls(success=False, errors=errors)
        
        # Check if offer is still pending
        if offer.status != 'pending':
            errors['status'] = [f'Offer is already {offer.status}.']
            return cls(success=False, errors=errors)
        
        try:
            # Reject the offer
            offer.status = 'rejected'
            if reason:
                offer.message = f"{offer.message}\n\nRejection reason: {reason}"
            offer.save()
            
            return cls(
                offer=offer,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Withdraw Offer Mutation
# =============================================================================

class WithdrawOfferMutation(relay.ClientIDMutation):
    """
    Withdraw an offer.
    
    Allows the buyer to withdraw their pending offer.
    """
    
    class Input:
        offer_id = graphene.ID(required=True)
        reason = graphene.String(required=False)
    
    offer = graphene.Field(OfferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, offer_id, reason=None):
        """
        Withdraw an offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            offer_id: Offer ID to withdraw
            reason: Optional withdrawal reason
        
        Returns:
            WithdrawOfferMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve offer
        try:
            pk = from_global_id(offer_id)[1]
            offer = Offer.objects.get(pk=pk)
        except Offer.DoesNotExist:
            errors['offer_id'] = ['Offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['offer_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only buyer can withdraw
        if offer.buyer.user != user and not user.is_staff:
            errors['permission'] = ['Only the buyer can withdraw their offer.']
            return cls(success=False, errors=errors)
        
        # Check if offer is still pending
        if offer.status != 'pending':
            errors['status'] = [f'Cannot withdraw an offer that is {offer.status}.']
            return cls(success=False, errors=errors)
        
        try:
            # Withdraw the offer
            offer.status = 'withdrawn'
            if reason:
                offer.message = f"{offer.message}\n\nWithdrawal reason: {reason}"
            offer.save()
            
            return cls(
                offer=offer,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Offer Mutation
# =============================================================================

class DeleteOfferMutation(relay.ClientIDMutation):
    """
    Delete an offer.
    
    Only pending offers can be deleted. Accepted, rejected, or withdrawn
    offers should be preserved for audit.
    """
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(required=False, default_value=False)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, force=False):
        """
        Delete an offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Offer ID to delete
            force: Force deletion even if not pending
        
        Returns:
            DeleteOfferMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve offer
        try:
            pk = from_global_id(id)[1]
            offer = Offer.objects.get(pk=pk)
        except Offer.DoesNotExist:
            errors['id'] = ['Offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only buyer or staff can delete
        if offer.buyer.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this offer.']
            return cls(success=False, errors=errors)
        
        # Check if offer is pending (or force delete)
        if offer.status != 'pending' and not force:
            errors['status'] = [
                f'Cannot delete an offer that is {offer.status}. '
                'Only pending offers can be deleted. Use force=True to override.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            offer.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkCreateOffersMutation(relay.ClientIDMutation):
    """
    Bulk create multiple offers.
    
    Allows creating multiple offers at once for different properties.
    """
    
    class Input:
        id = graphene.ID(required=True)
        offer_price = graphene.Decimal(required=False)
        status = graphene.String(required=False)
        message = graphene.String(required=False)
        expiration_date = graphene.DateTime(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk create offers.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            offers: List of offer inputs
        
        Returns:
            BulkCreateOffersMutation instance
        """
        errors = {}
        results = []
        success_count = 0
        failure_count = 0
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        for idx, offer_input in enumerate(offers):
            try:
                # Use the create mutation for each offer
                result = CreateOfferMutation.mutate_and_get_payload(
                    root, info, offer_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'offer_id': result.offer.id if result.offer else None,
                    })
                else:
                    failure_count += 1
                    errors[f'offer_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'offer_{idx}'] = [str(e)]
                results.append({
                    'index': idx,
                    'status': 'failed',
                    'errors': [str(e)],
                })
        
        return cls(
            success_count=success_count,
            failure_count=failure_count,
            results=results,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class OfferMutations(graphene.ObjectType):
    """All offer mutations."""
    
    # CRUD operations
    create_offer = CreateOfferMutation.Field()
    update_offer = UpdateOfferMutation.Field()
    delete_offer = DeleteOfferMutation.Field()
    
    # Status operations
    accept_offer = AcceptOfferMutation.Field()
    reject_offer = RejectOfferMutation.Field()
    withdraw_offer = WithdrawOfferMutation.Field()
    
    # Bulk operations
    bulk_create_offers = BulkCreateOffersMutation.Field()