# apps/backend/realestate/mutations/transaction.py

"""
Transaction Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import transaction as db_transaction
from django.utils import timezone

from realestate.models.transaction import Transaction
from realestate.models.listing import Listing
from realestate.models.client import Client
from realestate.constants import TransactionStatus
from graphq.realestate.types.transaction import TransactionNode

# =============================================================================
# Input Types
# =============================================================================

class TransactionInput(graphene.InputObjectType):
    """Input for transaction creation."""
    
    property_id = graphene.ID(required=True)
    buyer_id = graphene.ID(required=True)
    seller_id = graphene.ID(required=True)
    offer_price = graphene.Decimal(required=True)
    target_close_date = graphene.Date(required=True)
    notes = graphene.String(required=False)
    escrow_number = graphene.String(required=False)


class TransactionUpdateInput(graphene.InputObjectType):
    """Input for transaction update."""
    
    id = graphene.ID(required=True)
    offer_price = graphene.Decimal(required=False)
    agreed_price = graphene.Decimal(required=False)
    status = graphene.String(required=False)
    target_close_date = graphene.Date(required=False)
    actual_close_date = graphene.Date(required=False)
    notes = graphene.String(required=False)
    escrow_number = graphene.String(required=False)


class TransactionStatusUpdateInput(graphene.InputObjectType):
    """Input for transaction status update."""
    
    transaction_id = graphene.ID(required=True)
    status = graphene.String(required=True)
    agreed_price = graphene.Decimal(required=False)
    actual_close_date = graphene.Date(required=False)


# =============================================================================
# Create Transaction Mutation
# =============================================================================

class CreateTransactionMutation(relay.ClientIDMutation):
    """
    Create a new transaction.
    
    Creates a real estate transaction between a buyer and seller for a property.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        buyer_id = graphene.ID(required=True)
        seller_id = graphene.ID(required=True)
        offer_price = graphene.Decimal(required=True)
        target_close_date = graphene.Date(required=True)
        notes = graphene.String(required=False)
        escrow_number = graphene.String(required=False)
    
    transaction = graphene.Field(TransactionNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new transaction.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: TransactionInput data
        
        Returns:
            CreateTransactionMutation instance
        """
        errors = {}
        
        # Extract input
        property_id = input.get('property_id')
        buyer_id = input.get('buyer_id')
        seller_id = input.get('seller_id')
        offer_price = input.get('offer_price')
        target_close_date = input.get('target_close_date')
        notes = input.get('notes', '')
        escrow_number = input.get('escrow_number', '')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate offer price
        if offer_price <= 0:
            errors['offer_price'] = ['Offer price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate target close date
        if target_close_date < timezone.now().date():
            errors['target_close_date'] = ['Target close date cannot be in the past.']
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
        
        # Check if property is available for transaction
        if property_obj.property_status in ['sold', 'under_contract']:
            errors['property'] = ['Property is not available for transaction.']
            return cls(success=False, errors=errors)
        
        # Resolve buyer
        try:
            pk = from_global_id(buyer_id)[1]
            buyer = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            errors['buyer_id'] = ['Buyer not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['buyer_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Resolve seller
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            pk = from_global_id(seller_id)[1]
            seller = User.objects.get(pk=pk)
        except Exception as e:
            errors['seller_id'] = ['Seller not found.']
            return cls(success=False, errors=errors)
        
        # Check if seller is the property owner
        if property_obj.owner and property_obj.owner != seller:
            errors['seller'] = ['Seller is not the owner of the property.']
            return cls(success=False, errors=errors)
        
        # Check if buyer and seller are the same
        if buyer.user == seller:
            errors['participants'] = ['Buyer and seller cannot be the same person.']
            return cls(success=False, errors=errors)
        
        # Check if transaction can be created
        can_create, message = Transaction.can_create_transaction(property_obj, buyer, seller)
        if not can_create:
            errors['transaction'] = [message]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be involved or staff
        is_participant = (
            user.is_staff or
            buyer.user == user or
            seller == user
        )
        
        if not is_participant:
            errors['permission'] = ['You do not have permission to create this transaction.']
            return cls(success=False, errors=errors)
        
        try:
            # Create transaction
            transaction = Transaction.objects.create(
                property=property_obj,
                buyer=buyer,
                seller=seller,
                offer_price=offer_price,
                target_close_date=target_close_date,
                status=TransactionStatus.PRE_OFFER,
                notes=notes,
                escrow_number=escrow_number,
            )
            
            return cls(
                transaction=transaction,
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
# Update Transaction Mutation
# =============================================================================

class UpdateTransactionMutation(relay.ClientIDMutation):
    """
    Update an existing transaction.
    
    Allows updating transaction details including prices, dates, and notes.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        buyer_id = graphene.ID(required=True)
        seller_id = graphene.ID(required=True)
        offer_price = graphene.Decimal(required=True)
        target_close_date = graphene.Date(required=True)
        notes = graphene.String(required=False)
        escrow_number = graphene.String(required=False)
    
    transaction = graphene.Field(TransactionNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing transaction.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: TransactionUpdateInput data
        
        Returns:
            UpdateTransactionMutation instance
        """
        errors = {}
        
        # Extract input
        transaction_id = input.get('id')
        offer_price = input.get('offer_price')
        agreed_price = input.get('agreed_price')
        status = input.get('status')
        target_close_date = input.get('target_close_date')
        actual_close_date = input.get('actual_close_date')
        notes = input.get('notes')
        escrow_number = input.get('escrow_number')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve transaction
        try:
            pk = from_global_id(transaction_id)[1]
            transaction = Transaction.objects.get(pk=pk)
        except Transaction.DoesNotExist:
            errors['id'] = ['Transaction not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        is_participant = (
            user.is_staff or
            transaction.buyer.user == user or
            transaction.seller == user
        )
        
        if not is_participant:
            errors['permission'] = ['You do not have permission to update this transaction.']
            return cls(success=False, errors=errors)
        
        # Validate offer price if provided
        if offer_price is not None and offer_price <= 0:
            errors['offer_price'] = ['Offer price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate agreed price if provided
        if agreed_price is not None and agreed_price <= 0:
            errors['agreed_price'] = ['Agreed price must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate target close date if provided
        if target_close_date is not None and target_close_date < timezone.now().date():
            errors['target_close_date'] = ['Target close date cannot be in the past.']
            return cls(success=False, errors=errors)
        
        # Validate actual close date if provided
        if actual_close_date is not None:
            if status and status != TransactionStatus.CLOSED:
                errors['actual_close_date'] = ['Actual close date can only be set for closed transactions.']
                return cls(success=False, errors=errors)
        
        # Validate status if provided
        if status is not None:
            valid_statuses = [choice[0] for choice in TransactionStatus.CHOICES]
            if status not in valid_statuses:
                errors['status'] = [f'Invalid status. Must be one of: {", ".join(valid_statuses)}']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if offer_price is not None:
                transaction.offer_price = offer_price
            if agreed_price is not None:
                transaction.agreed_price = agreed_price
            if status is not None:
                transaction.status = status
            if target_close_date is not None:
                transaction.target_close_date = target_close_date
            if actual_close_date is not None:
                transaction.actual_close_date = actual_close_date
            if notes is not None:
                transaction.notes = notes
            if escrow_number is not None:
                transaction.escrow_number = escrow_number
            
            transaction.full_clean()
            transaction.save()
            
            return cls(
                transaction=transaction,
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
# Delete Transaction Mutation
# =============================================================================

class DeleteTransactionMutation(relay.ClientIDMutation):
    """
    Delete a transaction.
    
    Removes a transaction. Only PRE_OFFER or CANCELLED transactions can be deleted.
    """
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(required=False, default_value=False)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, force=False):
        """
        Delete a transaction.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Transaction ID to delete
            force: Force deletion even if active
        
        Returns:
            DeleteTransactionMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve transaction
        try:
            pk = from_global_id(id)[1]
            transaction = Transaction.objects.get(pk=pk)
        except Transaction.DoesNotExist:
            errors['id'] = ['Transaction not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        is_participant = (
            user.is_staff or
            transaction.buyer.user == user or
            transaction.seller == user
        )
        
        if not is_participant:
            errors['permission'] = ['You do not have permission to delete this transaction.']
            return cls(success=False, errors=errors)
        
        # Check if transaction can be deleted
        deletable_statuses = [
            TransactionStatus.PRE_OFFER,
            TransactionStatus.OFFER_PENDING,
            TransactionStatus.CANCELLED,
        ]
        
        if transaction.status not in deletable_statuses and not force:
            errors['status'] = [
                f'Cannot delete transaction with status "{transaction.status}". '
                'Only PRE_OFFER, OFFER_PENDING, or CANCELLED transactions can be deleted. '
                'Use force=True to override.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            
            # Store property for status update
            property_obj = transaction.property
            
            transaction.delete()
            
            # Update property status if needed
            property_obj.save(update_fields=['property_status'])
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Transaction Status Mutation
# =============================================================================

class UpdateTransactionStatusMutation(relay.ClientIDMutation):
    """
    Update transaction status with validation.
    
    Validates status transitions and updates related fields like agreed price
    and actual close date when closing a transaction.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        buyer_id = graphene.ID(required=True)
        seller_id = graphene.ID(required=True)
        offer_price = graphene.Decimal(required=True)
        target_close_date = graphene.Date(required=True)
        notes = graphene.String(required=False)
        escrow_number = graphene.String(required=False)
    
    transaction = graphene.Field(TransactionNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update transaction status.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: TransactionStatusUpdateInput data
        
        Returns:
            UpdateTransactionStatusMutation instance
        """
        errors = {}
        
        # Extract input
        transaction_id = input.get('transaction_id')
        status = input.get('status')
        agreed_price = input.get('agreed_price')
        actual_close_date = input.get('actual_close_date')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve transaction
        try:
            pk = from_global_id(transaction_id)[1]
            transaction = Transaction.objects.get(pk=pk)
        except Transaction.DoesNotExist:
            errors['transaction_id'] = ['Transaction not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['transaction_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        is_participant = (
            user.is_staff or
            transaction.buyer.user == user or
            transaction.seller == user
        )
        
        if not is_participant:
            errors['permission'] = ['You do not have permission to update this transaction.']
            return cls(success=False, errors=errors)
        
        # Validate status
        valid_statuses = [choice[0] for choice in TransactionStatus.CHOICES]
        if status not in valid_statuses:
            errors['status'] = [f'Invalid status. Must be one of: {", ".join(valid_statuses)}']
            return cls(success=False, errors=errors)
        
        # Validate agreed price if closing
        if status == TransactionStatus.CLOSED:
            if agreed_price is None:
                agreed_price = transaction.offer_price
            
            if agreed_price <= 0:
                errors['agreed_price'] = ['Agreed price must be greater than 0 for closed transactions.']
                return cls(success=False, errors=errors)
        
        try:
            # Update status using the model's update_status method
            transaction.update_status(
                status,
                agreed_price=agreed_price,
                actual_close_date=actual_close_date or timezone.now().date()
            )
            
            return cls(
                transaction=transaction,
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
# Bulk Operations
# =============================================================================

class BulkUpdateTransactionStatusMutation(relay.ClientIDMutation):
    """
    Bulk update transaction statuses.
    
    Allows updating statuses for multiple transactions at once.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        buyer_id = graphene.ID(required=True)
        seller_id = graphene.ID(required=True)
        offer_price = graphene.Decimal(required=True)
        target_close_date = graphene.Date(required=True)
        notes = graphene.String(required=False)
        escrow_number = graphene.String(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @db_transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk update transaction statuses.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            transactions: List of transaction status updates
        
        Returns:
            BulkUpdateTransactionStatusMutation instance
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
        
        for idx, update_data in enumerate(transactions):
            try:
                # Use the status update mutation for each transaction
                result = UpdateTransactionStatusMutation.mutate_and_get_payload(
                    root, info, update_data
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'transaction_id': result.transaction.id if result.transaction else None,
                    })
                else:
                    failure_count += 1
                    errors[f'transaction_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'transaction_{idx}'] = [str(e)]
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

class TransactionMutations(graphene.ObjectType):
    """All transaction mutations."""
    
    # CRUD operations
    create_transaction = CreateTransactionMutation.Field()
    update_transaction = UpdateTransactionMutation.Field()
    delete_transaction = DeleteTransactionMutation.Field()
    
    # Status management
    update_transaction_status = UpdateTransactionStatusMutation.Field()
    
    # Bulk operations
    bulk_update_transaction_status = BulkUpdateTransactionStatusMutation.Field()