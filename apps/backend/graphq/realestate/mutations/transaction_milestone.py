# apps/backend/realestate/mutations/transaction_milestone.py

"""
Transaction Milestone Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.transaction_milestone import TransactionMilestone
from realestate.models.transaction import Transaction
from realestate.models.document import Document
from graphq.realestate.types.transaction_milestone import TransactionMilestoneNode

# =============================================================================
# Input Types
# =============================================================================

class TransactionMilestoneInput(graphene.InputObjectType):
    """Input for transaction milestone creation."""
    
    transaction_id = graphene.ID(required=True)
    name = graphene.String(required=True)
    description = graphene.String(required=False)
    order = graphene.Int(required=False, default_value=0)
    due_date = graphene.Date(required=True)
    required = graphene.Boolean(required=False, default_value=True)
    document_ids = graphene.List(graphene.ID, required=False)


class TransactionMilestoneUpdateInput(graphene.InputObjectType):
    """Input for transaction milestone update."""
    
    id = graphene.ID(required=True)
    name = graphene.String(required=False)
    description = graphene.String(required=False)
    order = graphene.Int(required=False)
    due_date = graphene.Date(required=False)
    required = graphene.Boolean(required=False)
    document_ids = graphene.List(graphene.ID, required=False)


class CompleteMilestoneInput(graphene.InputObjectType):
    """Input for completing a milestone."""
    
    milestone_id = graphene.ID(required=True)
    completion_date = graphene.Date(required=False)


# =============================================================================
# Create Transaction Milestone Mutation
# =============================================================================

class CreateTransactionMilestoneMutation(relay.ClientIDMutation):
    """
    Create a new transaction milestone.
    
    Milestones represent key stages in a real estate transaction,
    such as inspection, appraisal, closing, etc.
    """
    
    class Input:
        transaction_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        description = graphene.String(required=False)
        order = graphene.Int(required=False, default_value=0)
        due_date = graphene.Date(required=True)
        required = graphene.Boolean(required=False, default_value=True)
        document_ids = graphene.List(graphene.ID, required=False)
    
    milestone = graphene.Field(TransactionMilestoneNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new transaction milestone.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: TransactionMilestoneInput data
        
        Returns:
            CreateTransactionMilestoneMutation instance
        """
        errors = {}
        
        # Extract input
        transaction_id = input.get('transaction_id')
        name = input.get('name')
        description = input.get('description', '')
        order = input.get('order', 0)
        due_date = input.get('due_date')
        required = input.get('required', True)
        document_ids = input.get('document_ids', [])
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate name
        if not name or not name.strip():
            errors['name'] = ['Name is required.']
            return cls(success=False, errors=errors)
        
        # Validate due date
        if due_date < timezone.now().date():
            errors['due_date'] = ['Due date cannot be in the past.']
            return cls(success=False, errors=errors)
        
        # Resolve transaction
        try:
            pk = from_global_id(transaction_id)[1]
            transaction_obj = Transaction.objects.get(pk=pk)
        except Transaction.DoesNotExist:
            errors['transaction_id'] = ['Transaction not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['transaction_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be involved in the transaction or staff
        is_participant = (
            user.is_staff or
            transaction_obj.buyer.user == user or
            transaction_obj.seller.user == user or
            (transaction_obj.agent and transaction_obj.agent.profile and 
             hasattr(transaction_obj.agent.profile, 'user') and 
             transaction_obj.agent.profile.user == user)
        )
        
        if not is_participant:
            errors['permission'] = ['You do not have permission to create milestones for this transaction.']
            return cls(success=False, errors=errors)
        
        # Resolve documents if provided
        documents = []
        for doc_id in document_ids:
            try:
                pk = from_global_id(doc_id)[1]
                doc = Document.objects.get(pk=pk)
                
                # Validate document belongs to the same property
                if doc.package and doc.package.property != transaction_obj.property:
                    errors[f'document_{doc_id}'] = [
                        f'Document "{doc.title}" belongs to a different property.'
                    ]
                    return cls(success=False, errors=errors)
                
                documents.append(doc)
            except Document.DoesNotExist:
                errors[f'document_{doc_id}'] = ['Document not found.']
                return cls(success=False, errors=errors)
            except Exception as e:
                errors[f'document_{doc_id}'] = [str(e)]
                return cls(success=False, errors=errors)
        
        try:
            # Create milestone
            milestone = TransactionMilestone.objects.create(
                transaction=transaction_obj,
                name=name.strip(),
                description=description,
                order=order,
                due_date=due_date,
                required=required,
                is_completed=False,
                completed_date=None,
            )
            
            # Add documents
            if documents:
                milestone.documents.set(documents)
            
            return cls(
                milestone=milestone,
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
# Update Transaction Milestone Mutation
# =============================================================================

class UpdateTransactionMilestoneMutation(relay.ClientIDMutation):
    """
    Update an existing transaction milestone.
    
    Allows updating milestone details including name, description, order,
    due date, required status, and associated documents.
    """
    
    class Input:
        transaction_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        description = graphene.String(required=False)
        order = graphene.Int(required=False, default_value=0)
        due_date = graphene.Date(required=True)
        required = graphene.Boolean(required=False, default_value=True)
        document_ids = graphene.List(graphene.ID, required=False)
    
    milestone = graphene.Field(TransactionMilestoneNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing transaction milestone.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: TransactionMilestoneUpdateInput data
        
        Returns:
            UpdateTransactionMilestoneMutation instance
        """
        errors = {}
        
        # Extract input
        milestone_id = input.get('id')
        name = input.get('name')
        description = input.get('description')
        order = input.get('order')
        due_date = input.get('due_date')
        required = input.get('required')
        document_ids = input.get('document_ids')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve milestone
        try:
            pk = from_global_id(milestone_id)[1]
            milestone = TransactionMilestone.objects.get(pk=pk)
        except TransactionMilestone.DoesNotExist:
            errors['id'] = ['Transaction milestone not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        transaction_obj = milestone.transaction
        is_participant = (
            user.is_staff or
            transaction_obj.buyer.user == user or
            transaction_obj.seller.user == user or
            (transaction_obj.agent and transaction_obj.agent.profile and 
             hasattr(transaction_obj.agent.profile, 'user') and 
             transaction_obj.agent.profile.user == user)
        )
        
        if not is_participant:
            errors['permission'] = ['You do not have permission to update this milestone.']
            return cls(success=False, errors=errors)
        
        # Can't update completed milestones
        if milestone.is_completed:
            errors['milestone'] = ['Cannot update a completed milestone.']
            return cls(success=False, errors=errors)
        
        # Validate name if provided
        if name is not None and not name.strip():
            errors['name'] = ['Name is required.']
            return cls(success=False, errors=errors)
        
        # Validate due date if provided
        if due_date is not None and due_date < timezone.now().date():
            errors['due_date'] = ['Due date cannot be in the past.']
            return cls(success=False, errors=errors)
        
        # Resolve documents if provided
        documents = []
        if document_ids is not None:
            for doc_id in document_ids:
                try:
                    pk = from_global_id(doc_id)[1]
                    doc = Document.objects.get(pk=pk)
                    
                    # Validate document belongs to the same property
                    if doc.package and doc.package.property != transaction_obj.property:
                        errors[f'document_{doc_id}'] = [
                            f'Document "{doc.title}" belongs to a different property.'
                        ]
                        return cls(success=False, errors=errors)
                    
                    documents.append(doc)
                except Document.DoesNotExist:
                    errors[f'document_{doc_id}'] = ['Document not found.']
                    return cls(success=False, errors=errors)
                except Exception as e:
                    errors[f'document_{doc_id}'] = [str(e)]
                    return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if name is not None:
                milestone.name = name.strip()
            if description is not None:
                milestone.description = description
            if order is not None:
                milestone.order = order
            if due_date is not None:
                milestone.due_date = due_date
            if required is not None:
                milestone.required = required
            if document_ids is not None:
                milestone.documents.set(documents)
            
            milestone.full_clean()
            milestone.save()
            
            return cls(
                milestone=milestone,
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
# Delete Transaction Milestone Mutation
# =============================================================================

class DeleteTransactionMilestoneMutation(relay.ClientIDMutation):
    """
    Delete a transaction milestone.
    
    Removes a milestone from the transaction. Only pending milestones
    can be deleted.
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
        Delete a transaction milestone.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Milestone ID to delete
            force: Force deletion even if completed
        
        Returns:
            DeleteTransactionMilestoneMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve milestone
        try:
            pk = from_global_id(id)[1]
            milestone = TransactionMilestone.objects.get(pk=pk)
        except TransactionMilestone.DoesNotExist:
            errors['id'] = ['Transaction milestone not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        transaction_obj = milestone.transaction
        is_participant = (
            user.is_staff or
            transaction_obj.buyer.user == user or
            transaction_obj.seller.user == user or
            (transaction_obj.agent and transaction_obj.agent.profile and 
             hasattr(transaction_obj.agent.profile, 'user') and 
             transaction_obj.agent.profile.user == user)
        )
        
        if not is_participant:
            errors['permission'] = ['You do not have permission to delete this milestone.']
            return cls(success=False, errors=errors)
        
        # Can't delete completed milestones unless force=True
        if milestone.is_completed and not force:
            errors['milestone'] = [
                'Cannot delete a completed milestone. '
                'Use force=True to override.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            milestone.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Complete Transaction Milestone Mutation
# =============================================================================

class CompleteTransactionMilestoneMutation(relay.ClientIDMutation):
    """
    Complete a transaction milestone.
    
    Marks a milestone as completed with the specified completion date.
    """
    
    class Input:
        transaction_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        description = graphene.String(required=False)
        order = graphene.Int(required=False, default_value=0)
        due_date = graphene.Date(required=True)
        required = graphene.Boolean(required=False, default_value=True)
        document_ids = graphene.List(graphene.ID, required=False)
    
    milestone = graphene.Field(TransactionMilestoneNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Complete a transaction milestone.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: CompleteMilestoneInput data
        
        Returns:
            CompleteTransactionMilestoneMutation instance
        """
        errors = {}
        
        # Extract input
        milestone_id = input.get('milestone_id')
        completion_date = input.get('completion_date')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve milestone
        try:
            pk = from_global_id(milestone_id)[1]
            milestone = TransactionMilestone.objects.get(pk=pk)
        except TransactionMilestone.DoesNotExist:
            errors['milestone_id'] = ['Transaction milestone not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['milestone_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        transaction_obj = milestone.transaction
        is_participant = (
            user.is_staff or
            transaction_obj.buyer.user == user or
            transaction_obj.seller.user == user or
            (transaction_obj.agent and transaction_obj.agent.profile and 
             hasattr(transaction_obj.agent.profile, 'user') and 
             transaction_obj.agent.profile.user == user)
        )
        
        if not is_participant:
            errors['permission'] = ['You do not have permission to complete this milestone.']
            return cls(success=False, errors=errors)
        
        # Check if already completed
        if milestone.is_completed:
            errors['milestone'] = ['Milestone is already completed.']
            return cls(success=False, errors=errors)
        
        try:
            # Complete the milestone
            milestone.complete(completion_date)
            
            return cls(
                milestone=milestone,
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
# Reopen Transaction Milestone Mutation
# =============================================================================

class ReopenTransactionMilestoneMutation(relay.ClientIDMutation):
    """
    Reopen a completed transaction milestone.
    
    This allows reopening a milestone that was previously marked as completed.
    """
    
    class Input:
        id = graphene.ID(required=True)
        reason = graphene.String(required=False)
    
    milestone = graphene.Field(TransactionMilestoneNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, reason=None):
        """
        Reopen a completed milestone.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Milestone ID to reopen
            reason: Optional reason for reopening
        
        Returns:
            ReopenTransactionMilestoneMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve milestone
        try:
            pk = from_global_id(id)[1]
            milestone = TransactionMilestone.objects.get(pk=pk)
        except TransactionMilestone.DoesNotExist:
            errors['id'] = ['Transaction milestone not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission
        transaction_obj = milestone.transaction
        is_participant = (
            user.is_staff or
            transaction_obj.buyer.user == user or
            transaction_obj.seller.user == user or
            (transaction_obj.agent and transaction_obj.agent.profile and 
             hasattr(transaction_obj.agent.profile, 'user') and 
             transaction_obj.agent.profile.user == user)
        )
        
        if not is_participant:
            errors['permission'] = ['You do not have permission to reopen this milestone.']
            return cls(success=False, errors=errors)
        
        # Check if already not completed
        if not milestone.is_completed:
            errors['milestone'] = ['Milestone is not completed.']
            return cls(success=False, errors=errors)
        
        try:
            # Reopen the milestone
            milestone.is_completed = False
            milestone.completed_date = None
            if reason:
                milestone.description = f"{milestone.description}\n\nReopened: {reason}"
            milestone.save()
            
            return cls(
                milestone=milestone,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkCompleteMilestonesMutation(relay.ClientIDMutation):
    """
    Bulk complete multiple transaction milestones.
    
    Allows completing multiple milestones at once.
    """
    
    class Input:
        milestone_ids = graphene.List(graphene.ID, required=True)
        completion_date = graphene.Date(required=False)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, milestone_ids, completion_date=None):
        """
        Bulk complete milestones.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            milestone_ids: List of milestone IDs to complete
            completion_date: Optional completion date
        
        Returns:
            BulkCompleteMilestonesMutation instance
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
        
        for milestone_id in milestone_ids:
            try:
                pk = from_global_id(milestone_id)[1]
                milestone = TransactionMilestone.objects.get(pk=pk)
                
                # Check permission
                transaction_obj = milestone.transaction
                is_participant = (
                    user.is_staff or
                    transaction_obj.buyer.user == user or
                    transaction_obj.seller.user == user or
                    (transaction_obj.agent and transaction_obj.agent.profile and 
                     hasattr(transaction_obj.agent.profile, 'user') and 
                     transaction_obj.agent.profile.user == user)
                )
                
                if not is_participant:
                    errors[milestone_id] = ['Permission denied.']
                    failure_count += 1
                    results.append({
                        'id': milestone_id,
                        'status': 'failed',
                        'errors': ['Permission denied'],
                    })
                    continue
                
                # Check if already completed
                if milestone.is_completed:
                    errors[milestone_id] = ['Already completed.']
                    failure_count += 1
                    results.append({
                        'id': milestone_id,
                        'status': 'failed',
                        'errors': ['Already completed'],
                    })
                    continue
                
                # Complete the milestone
                milestone.complete(completion_date)
                success_count += 1
                results.append({
                    'id': milestone_id,
                    'status': 'success',
                })
                
            except TransactionMilestone.DoesNotExist:
                errors[milestone_id] = ['Milestone not found.']
                failure_count += 1
                results.append({
                    'id': milestone_id,
                    'status': 'failed',
                    'errors': ['Not found'],
                })
            except Exception as e:
                errors[milestone_id] = [str(e)]
                failure_count += 1
                results.append({
                    'id': milestone_id,
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

class TransactionMilestoneMutations(graphene.ObjectType):
    """All transaction milestone mutations."""
    
    # CRUD operations
    create_transaction_milestone = CreateTransactionMilestoneMutation.Field()
    update_transaction_milestone = UpdateTransactionMilestoneMutation.Field()
    delete_transaction_milestone = DeleteTransactionMilestoneMutation.Field()
    
    # Status operations
    complete_transaction_milestone = CompleteTransactionMilestoneMutation.Field()
    reopen_transaction_milestone = ReopenTransactionMilestoneMutation.Field()
    
    # Bulk operations
    bulk_complete_milestones = BulkCompleteMilestonesMutation.Field()