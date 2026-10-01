# apps/backend/realestate/mutations/counter_offer.py

"""
Counter Offer Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphql_relay import from_global_id

from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import transaction
from django.utils import timezone

from realestate.models.counter_offer import CounterOffer
from realestate.models.offer import Offer

from graphq.realestate.types.counter_offer import CounterOfferNode


# =============================================================================
# Create Counter Offer Mutation
# =============================================================================

class CreateCounterOfferMutation(relay.ClientIDMutation):
    """
    Create a new counter offer.
    
    A counter offer is a response to an existing offer, allowing the
    recipient to propose different terms.
    """
    
    class Input:
        original_offer_id = graphene.ID(required=True)
        counter_price = graphene.Decimal(required=True)
        message = graphene.String(required=False)
        expiration_date = graphene.DateTime(required=False)
    
    counter_offer = graphene.Field(CounterOfferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new counter offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: CounterOfferInput data
        
        Returns:
            CreateCounterOfferMutation instance
        """
        errors = {}
        
        # Extract input
        original_offer_id = input.get('original_offer_id')
        counter_price = input.get('counter_price')
        message = input.get('message', '')
        expiration_date = input.get('expiration_date')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate counter price
        if counter_price is None or counter_price <= 0:
            errors['counter_price'] = ['Counter price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Resolve original offer
        try:
            pk = from_global_id(original_offer_id)[1]
            original_offer = Offer.objects.get(pk=pk)
        except Offer.DoesNotExist:
            errors['original_offer_id'] = ['Original offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['original_offer_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if the original offer is still active
        if original_offer.status not in ['pending', 'countered']:
            errors['original_offer'] = [
                f'Cannot counter offer with status "{original_offer.status}". '
                'Offer must be in pending or countered state.'
            ]
            return cls(success=False, errors=errors)
        
        # Validate expiration date
        if expiration_date and expiration_date <= timezone.now():
            errors['expiration_date'] = ['Expiration date must be in the future.']
            return cls(success=False, errors=errors)
        
        # Set default expiration date if not provided (7 days from now)
        if not expiration_date:
            expiration_date = timezone.now() + timezone.timedelta(days=7)
        
        try:
            # Create counter offer
            counter_offer = CounterOffer.objects.create(
                original_offer=original_offer,
                created_by=user,
                counter_price=counter_price,
                message=message,
                status='pending',
                expiration_date=expiration_date,
            )
            
            # Update the original offer status
            original_offer.status = 'countered'
            original_offer.save()
            
            return cls(
                counter_offer=counter_offer,
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
# Update Counter Offer Mutation
# =============================================================================

class UpdateCounterOfferMutation(relay.ClientIDMutation):
    """
    Update an existing counter offer.
    
    Allows updating price, message, status, or expiration date.
    Status transitions are validated to ensure proper workflow.
    """
    
    class Input:
        original_offer_id = graphene.ID(required=True)
        counter_price = graphene.Decimal(required=True)
        message = graphene.String(required=False)
        expiration_date = graphene.DateTime(required=False)
    
    counter_offer = graphene.Field(CounterOfferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing counter offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: CounterOfferUpdateInput data
        
        Returns:
            UpdateCounterOfferMutation instance
        """
        errors = {}
        
        # Extract input
        counter_offer_id = input.get('id')
        counter_price = input.get('counter_price')
        message = input.get('message')
        status = input.get('status')
        expiration_date = input.get('expiration_date')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve counter offer
        try:
            pk = from_global_id(counter_offer_id)[1]
            counter_offer = CounterOffer.objects.get(pk=pk)
        except CounterOffer.DoesNotExist:
            errors['id'] = ['Counter offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the creator or staff can update
        if counter_offer.created_by != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this counter offer.']
            return cls(success=False, errors=errors)
        
        # Check if counter offer is still pending
        if counter_offer.status != 'pending' and status is None:
            # Only allow status updates if not pending
            pass
        elif counter_offer.status != 'pending' and status is not None:
            # If it's already accepted/rejected, only allow specific transitions
            if counter_offer.status == 'accepted' and status not in ['accepted']:
                errors['status'] = ['Accepted counter offers cannot be changed.']
                return cls(success=False, errors=errors)
            elif counter_offer.status == 'rejected' and status not in ['rejected']:
                errors['status'] = ['Rejected counter offers cannot be changed.']
                return cls(success=False, errors=errors)
            elif counter_offer.status == 'withdrawn' and status not in ['withdrawn']:
                errors['status'] = ['Withdrawn counter offers cannot be changed.']
                return cls(success=False, errors=errors)
            elif counter_offer.status == 'expired' and status not in ['expired']:
                errors['status'] = ['Expired counter offers cannot be changed.']
                return cls(success=False, errors=errors)
        
        # Validate counter price
        if counter_price is not None and counter_price <= 0:
            errors['counter_price'] = ['Counter price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate status
        if status is not None:
            valid_statuses = ['pending', 'accepted', 'rejected', 'withdrawn', 'expired']
            if status not in valid_statuses:
                errors['status'] = [
                    f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                ]
                return cls(success=False, errors=errors)
        
        # Validate expiration date
        if expiration_date and expiration_date <= timezone.now():
            errors['expiration_date'] = ['Expiration date must be in the future.']
            return cls(success=False, errors=errors)
        
        try:
            old_status = counter_offer.status
            
            # Update fields
            if counter_price is not None:
                counter_offer.counter_price = counter_price
            if message is not None:
                counter_offer.message = message
            if status is not None:
                counter_offer.status = status
            if expiration_date is not None:
                counter_offer.expiration_date = expiration_date
            
            counter_offer.full_clean()
            counter_offer.save()
            
            # Handle status transitions that affect the original offer
            if status is not None:
                original_offer = counter_offer.original_offer
                
                if status == 'accepted':
                    # Accepting the counter offer accepts the original offer
                    original_offer.status = 'accepted'
                    original_offer.save()
                    
                    # Update any other counter offers on this offer to rejected
                    CounterOffer.objects.filter(
                        original_offer=original_offer
                    ).exclude(
                        pk=counter_offer.pk
                    ).update(status='rejected')
                    
                elif status == 'rejected' or status == 'withdrawn':
                    # Check if there are any other pending counter offers
                    has_other_pending = CounterOffer.objects.filter(
                        original_offer=original_offer,
                        status='pending'
                    ).exclude(pk=counter_offer.pk).exists()
                    
                    if not has_other_pending:
                        original_offer.status = 'pending'
                        original_offer.save()
            
            return cls(
                counter_offer=counter_offer,
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
# Accept Counter Offer Mutation
# =============================================================================

class AcceptCounterOfferMutation(relay.ClientIDMutation):
    """
    Accept a counter offer.
    
    This is a convenience mutation that accepts a counter offer and
    automatically updates the original offer status.
    """
    
    class Input:
        id = graphene.ID(required=True)
    
    counter_offer = graphene.Field(CounterOfferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Accept a counter offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Counter offer ID to accept
        
        Returns:
            AcceptCounterOfferMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve counter offer
        try:
            pk = from_global_id(id)[1]
            counter_offer = CounterOffer.objects.get(pk=pk)
        except CounterOffer.DoesNotExist:
            errors['id'] = ['Counter offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if counter offer is still pending
        if counter_offer.status != 'pending':
            errors['status'] = [
                f'Cannot accept counter offer with status "{counter_offer.status}". '
                'Only pending counter offers can be accepted.'
            ]
            return cls(success=False, errors=errors)
        
        # Check if expired
        if counter_offer.is_expired():
            errors['status'] = ['Cannot accept expired counter offer.']
            return cls(success=False, errors=errors)
        
        try:
            original_offer = counter_offer.original_offer
            
            # Update counter offer status
            counter_offer.status = 'accepted'
            counter_offer.save()
            
            # Update original offer status
            original_offer.status = 'accepted'
            original_offer.save()
            
            # Reject all other counter offers for this offer
            CounterOffer.objects.filter(
                original_offer=original_offer
            ).exclude(
                pk=counter_offer.pk
            ).update(status='rejected')
            
            return cls(
                counter_offer=counter_offer,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Reject Counter Offer Mutation
# =============================================================================

class RejectCounterOfferMutation(relay.ClientIDMutation):
    """
    Reject a counter offer.
    
    This is a convenience mutation that rejects a counter offer and
    updates the original offer status if no other counter offers are pending.
    """
    
    class Input:
        id = graphene.ID(required=True)
        reason = graphene.String(required=False)
    
    counter_offer = graphene.Field(CounterOfferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, reason=None):
        """
        Reject a counter offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Counter offer ID to reject
            reason: Optional rejection reason
        
        Returns:
            RejectCounterOfferMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve counter offer
        try:
            pk = from_global_id(id)[1]
            counter_offer = CounterOffer.objects.get(pk=pk)
        except CounterOffer.DoesNotExist:
            errors['id'] = ['Counter offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if counter offer is still pending
        if counter_offer.status != 'pending':
            errors['status'] = [
                f'Cannot reject counter offer with status "{counter_offer.status}". '
                'Only pending counter offers can be rejected.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            original_offer = counter_offer.original_offer
            
            # Update counter offer status
            counter_offer.status = 'rejected'
            if reason:
                counter_offer.message = f"{counter_offer.message}\n\nRejection reason: {reason}"
            counter_offer.save()
            
            # Check if there are any other pending counter offers
            has_other_pending = CounterOffer.objects.filter(
                original_offer=original_offer,
                status='pending'
            ).exclude(pk=counter_offer.pk).exists()
            
            if not has_other_pending:
                # Revert original offer status to pending
                original_offer.status = 'pending'
                original_offer.save()
            
            return cls(
                counter_offer=counter_offer,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Withdraw Counter Offer Mutation
# =============================================================================

class WithdrawCounterOfferMutation(relay.ClientIDMutation):
    """
    Withdraw a counter offer.
    
    Allows the creator to withdraw a pending counter offer.
    """
    
    class Input:
        id = graphene.ID(required=True)
        reason = graphene.String(required=False)
    
    counter_offer = graphene.Field(CounterOfferNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, reason=None):
        """
        Withdraw a counter offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Counter offer ID to withdraw
            reason: Optional withdrawal reason
        
        Returns:
            WithdrawCounterOfferMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve counter offer
        try:
            pk = from_global_id(id)[1]
            counter_offer = CounterOffer.objects.get(pk=pk)
        except CounterOffer.DoesNotExist:
            errors['id'] = ['Counter offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the creator can withdraw
        if counter_offer.created_by != user and not user.is_staff:
            errors['permission'] = ['Only the creator can withdraw this counter offer.']
            return cls(success=False, errors=errors)
        
        # Check if counter offer is still pending
        if counter_offer.status != 'pending':
            errors['status'] = [
                f'Cannot withdraw counter offer with status "{counter_offer.status}". '
                'Only pending counter offers can be withdrawn.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            original_offer = counter_offer.original_offer
            
            # Update counter offer status
            counter_offer.status = 'withdrawn'
            if reason:
                counter_offer.message = f"{counter_offer.message}\n\nWithdrawal reason: {reason}"
            counter_offer.save()
            
            # Check if there are any other pending counter offers
            has_other_pending = CounterOffer.objects.filter(
                original_offer=original_offer,
                status='pending'
            ).exclude(pk=counter_offer.pk).exists()
            
            if not has_other_pending:
                # Revert original offer status to pending
                original_offer.status = 'pending'
                original_offer.save()
            
            return cls(
                counter_offer=counter_offer,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Delete Counter Offer Mutation
# =============================================================================

class DeleteCounterOfferMutation(relay.ClientIDMutation):
    """
    Delete a counter offer.
    
    Only pending counter offers can be deleted. Accepted, rejected,
    withdrawn, or expired counter offers should be preserved for audit.
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
        Delete a counter offer.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Counter offer ID to delete
            force: Force deletion even if not pending
        
        Returns:
            DeleteCounterOfferMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve counter offer
        try:
            pk = from_global_id(id)[1]
            counter_offer = CounterOffer.objects.get(pk=pk)
        except CounterOffer.DoesNotExist:
            errors['id'] = ['Counter offer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only the creator or staff can delete
        if counter_offer.created_by != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to delete this counter offer.']
            return cls(success=False, errors=errors)
        
        # Check if counter offer is pending (or force delete)
        if counter_offer.status != 'pending' and not force:
            errors['status'] = [
                f'Cannot delete counter offer with status "{counter_offer.status}". '
                'Only pending counter offers can be deleted. Use force=True to override.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            original_offer = counter_offer.original_offer
            deleted_id = id
            
            # Store original offer for status update after deletion
            # Delete the counter offer
            counter_offer.delete()
            
            # Check if there are any other pending counter offers
            has_other_pending = CounterOffer.objects.filter(
                original_offer=original_offer,
                status='pending'
            ).exists()
            
            if not has_other_pending and original_offer.status == 'countered':
                # Revert original offer status to pending
                original_offer.status = 'pending'
                original_offer.save()
            
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

class BulkUpdateCounterOffersMutation(relay.ClientIDMutation):
    """
    Bulk update multiple counter offers.
    
    Allows updating common fields across multiple counter offers at once.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        status = graphene.String(required=False)
        expiration_date = graphene.DateTime(required=False)
    
    updated_ids = graphene.List(graphene.ID)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids, **input):
        """
        Bulk update counter offers.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of counter offer IDs to update
            kwargs: Fields to update
        
        Returns:
            BulkUpdateCounterOffersMutation instance
        """
        errors = {}
        updated_ids = []
        failed_ids = []
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate status if provided
        status = kwargs.get('status')
        if status is not None:
            valid_statuses = ['pending', 'accepted', 'rejected', 'withdrawn', 'expired']
            if status not in valid_statuses:
                errors['status'] = [
                    f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                ]
                return cls(success=False, errors=errors)
        
        for counter_id in ids:
            try:
                pk = from_global_id(counter_id)[1]
                counter_offer = CounterOffer.objects.get(pk=pk)
                
                # Check permission
                if counter_offer.created_by != user and not user.is_staff:
                    failed_ids.append(counter_id)
                    errors[counter_id] = ['Permission denied.']
                    continue
                
                # Apply updates
                if status is not None:
                    counter_offer.status = status
                if kwargs.get('expiration_date') is not None:
                    if kwargs['expiration_date'] <= timezone.now():
                        errors[counter_id] = ['Expiration date must be in the future.']
                        failed_ids.append(counter_id)
                        continue
                    counter_offer.expiration_date = kwargs['expiration_date']
                
                counter_offer.full_clean()
                counter_offer.save()
                updated_ids.append(counter_id)
                
            except CounterOffer.DoesNotExist:
                failed_ids.append(counter_id)
                errors[counter_id] = ['Counter offer not found.']
            except ValidationError as e:
                failed_ids.append(counter_id)
                errors[counter_id] = e.message_dict
            except Exception as e:
                failed_ids.append(counter_id)
                errors[counter_id] = [str(e)]
        
        return cls(
            updated_ids=updated_ids,
            success=len(failed_ids) == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class CounterOfferMutations(graphene.ObjectType):
    """All counter offer mutations."""
    
    # CRUD operations
    create_counter_offer = CreateCounterOfferMutation.Field()
    update_counter_offer = UpdateCounterOfferMutation.Field()
    delete_counter_offer = DeleteCounterOfferMutation.Field()
    
    # Status operations
    accept_counter_offer = AcceptCounterOfferMutation.Field()
    reject_counter_offer = RejectCounterOfferMutation.Field()
    withdraw_counter_offer = WithdrawCounterOfferMutation.Field()
    
    # Bulk operations
    bulk_update_counter_offers = BulkUpdateCounterOffersMutation.Field()