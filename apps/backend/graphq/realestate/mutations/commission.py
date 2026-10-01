# apps/backend/realestate/mutations/commission.py

"""
Commission Plan Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from decimal import Decimal
from graphene_django import DjangoObjectType
from graphql_relay import from_global_id
from graphene import relay
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction

from realestate.models.commission import CommissionPlan

from graphq.realestate.types.commission import CommissionPlanNode

# =============================================================================
# Input Types
# =============================================================================

class CommissionPlanInput(graphene.InputObjectType):
    """Input for commission plan creation."""
    
    name = graphene.String(required=True)
    plan_type = graphene.String(required=True)
    base_percentage = graphene.Decimal(default_value=Decimal("0"))
    min_amount = graphene.Decimal(required=False)
    max_amount = graphene.Decimal(required=False)
    is_active = graphene.Boolean(required=False, default_value=True)


class CommissionPlanUpdateInput(graphene.InputObjectType):
    """Input for commission plan update."""
    
    id = graphene.ID(required=True)
    name = graphene.String(required=False)
    plan_type = graphene.String(required=False)
    base_percentage = graphene.Decimal(required=False)
    min_amount = graphene.Decimal(required=False)
    max_amount = graphene.Decimal(required=False)
    is_active = graphene.Boolean(required=False)


# =============================================================================
# Create Commission Plan Mutation
# =============================================================================

class CreateCommissionPlanMutation(relay.ClientIDMutation):
    """
    Create a new commission plan.
    
    Commission plans define how commissions are calculated for real estate transactions.
    Supports percentage, fixed amount, and tiered commission structures.
    """
    
    class Input:
        name = graphene.String(required=True)
        plan_type = graphene.String(required=True)
        base_percentage = graphene.Decimal(
            required=False,
            default_value=Decimal("0"),
        )
        min_amount = graphene.Decimal(required=False)
        max_amount = graphene.Decimal(required=False)
        is_active = graphene.Boolean(required=False, default_value=True)
    
    commission_plan = graphene.Field(CommissionPlanNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new commission plan.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: CommissionPlanInput data
        
        Returns:
            CreateCommissionPlanMutation instance
        """
        errors = {}
        
        # Extract input
        name = input.get('name')
        plan_type = input.get('plan_type')
        base_percentage = input.get('base_percentage', 0)
        min_amount = input.get('min_amount')
        max_amount = input.get('max_amount')
        is_active = input.get('is_active', True)
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff or admin can create commission plans
        if not user.is_staff:
            errors['permission'] = ['Only staff members can create commission plans.']
            return cls(success=False, errors=errors)
        
        # Validate name
        if not name or not name.strip():
            errors['name'] = ['Name is required.']
            return cls(success=False, errors=errors)
        
        # Validate plan type
        valid_plan_types = ['percentage', 'fixed', 'tiered']
        if plan_type not in valid_plan_types:
            errors['plan_type'] = [
                f'Invalid plan type. Must be one of: {", ".join(valid_plan_types)}'
            ]
            return cls(success=False, errors=errors)
        
        # Validate base percentage
        if base_percentage is not None:
            if base_percentage < 0 or base_percentage > 100:
                errors['base_percentage'] = ['Percentage must be between 0 and 100.']
                return cls(success=False, errors=errors)
        
        # Validate min/max amounts
        if min_amount is not None and min_amount < 0:
            errors['min_amount'] = ['Minimum amount cannot be negative.']
            return cls(success=False, errors=errors)
        
        if max_amount is not None and max_amount < 0:
            errors['max_amount'] = ['Maximum amount cannot be negative.']
            return cls(success=False, errors=errors)
        
        if min_amount is not None and max_amount is not None:
            if min_amount > max_amount:
                errors['amount_range'] = ['Minimum amount cannot be greater than maximum amount.']
                return cls(success=False, errors=errors)
        
        # Check for duplicate name
        if CommissionPlan.objects.filter(name__iexact=name).exists():
            errors['name'] = ['Commission plan with this name already exists.']
            return cls(success=False, errors=errors)
        
        try:
            # Create commission plan
            commission_plan = CommissionPlan.objects.create(
                name=name,
                plan_type=plan_type,
                base_percentage=base_percentage,
                min_amount=min_amount,
                max_amount=max_amount,
                is_active=is_active,
            )
            
            return cls(
                commission_plan=commission_plan,
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
# Update Commission Plan Mutation
# =============================================================================

class UpdateCommissionPlanMutation(relay.ClientIDMutation):
    """
    Update an existing commission plan.
    
    Allows updating any field of a commission plan while maintaining
    data integrity and validation rules.
    """
    
    class Input:
        name = graphene.String(required=True)
        plan_type = graphene.String(required=True)
        base_percentage = graphene.Decimal(default_value=Decimal("0"))
        min_amount = graphene.Decimal(required=False)
        max_amount = graphene.Decimal(required=False)
        is_active = graphene.Boolean(required=False, default_value=True)
    
    commission_plan = graphene.Field(CommissionPlanNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing commission plan.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: CommissionPlanUpdateInput data
        
        Returns:
            UpdateCommissionPlanMutation instance
        """
        errors = {}
        
        # Extract input
        plan_id = input.get('id')
        name = input.get('name')
        plan_type = input.get('plan_type')
        base_percentage = input.get('base_percentage')
        min_amount = input.get('min_amount')
        max_amount = input.get('max_amount')
        is_active = input.get('is_active')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff or admin can update commission plans
        if not user.is_staff:
            errors['permission'] = ['Only staff members can update commission plans.']
            return cls(success=False, errors=errors)
        
        # Resolve commission plan
        try:
            pk = from_global_id(plan_id)[1]
            commission_plan = CommissionPlan.objects.get(pk=pk)
        except CommissionPlan.DoesNotExist:
            errors['id'] = ['Commission plan not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Validate name if provided
        if name is not None:
            if not name or not name.strip():
                errors['name'] = ['Name is required.']
                return cls(success=False, errors=errors)
            
            # Check for duplicate name (excluding current plan)
            if CommissionPlan.objects.filter(name__iexact=name).exclude(pk=pk).exists():
                errors['name'] = ['Commission plan with this name already exists.']
                return cls(success=False, errors=errors)
        
        # Validate plan type if provided
        if plan_type is not None:
            valid_plan_types = ['percentage', 'fixed', 'tiered']
            if plan_type not in valid_plan_types:
                errors['plan_type'] = [
                    f'Invalid plan type. Must be one of: {", ".join(valid_plan_types)}'
                ]
                return cls(success=False, errors=errors)
        
        # Validate base percentage if provided
        if base_percentage is not None:
            if base_percentage < 0 or base_percentage > 100:
                errors['base_percentage'] = ['Percentage must be between 0 and 100.']
                return cls(success=False, errors=errors)
        
        # Validate min/max amounts if provided
        if min_amount is not None and min_amount < 0:
            errors['min_amount'] = ['Minimum amount cannot be negative.']
            return cls(success=False, errors=errors)
        
        if max_amount is not None and max_amount < 0:
            errors['max_amount'] = ['Maximum amount cannot be negative.']
            return cls(success=False, errors=errors)
        
        # Validate amount range if both provided or one is provided
        min_val = min_amount if min_amount is not None else commission_plan.min_amount
        max_val = max_amount if max_amount is not None else commission_plan.max_amount
        
        if min_val is not None and max_val is not None:
            if min_val > max_val:
                errors['amount_range'] = ['Minimum amount cannot be greater than maximum amount.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if name is not None:
                commission_plan.name = name
            if plan_type is not None:
                commission_plan.plan_type = plan_type
            if base_percentage is not None:
                commission_plan.base_percentage = base_percentage
            if min_amount is not None:
                commission_plan.min_amount = min_amount
            if max_amount is not None:
                commission_plan.max_amount = max_amount
            if is_active is not None:
                commission_plan.is_active = is_active
            
            commission_plan.full_clean()
            commission_plan.save()
            
            return cls(
                commission_plan=commission_plan,
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
# Delete Commission Plan Mutation
# =============================================================================

class DeleteCommissionPlanMutation(relay.ClientIDMutation):
    """
    Delete a commission plan.
    
    Soft deletion alternative: Set is_active=False instead of hard delete.
    Hard delete is only allowed if the plan is not referenced by any transactions.
    """
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(
            required=False,
            default_value=False,
            description="Force delete even if referenced by transactions"
        )
        soft_delete = graphene.Boolean(
            required=False,
            default_value=False,
            description="Set is_active=False instead of deleting"
        )
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, force=False, soft_delete=False):
        """
        Delete a commission plan.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Commission plan ID to delete
            force: Force hard delete even if referenced
            soft_delete: Set is_active=False instead of hard deleting
        
        Returns:
            DeleteCommissionPlanMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff or admin can delete commission plans
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete commission plans.']
            return cls(success=False, errors=errors)
        
        # Resolve commission plan
        try:
            pk = from_global_id(id)[1]
            commission_plan = CommissionPlan.objects.get(pk=pk)
        except CommissionPlan.DoesNotExist:
            errors['id'] = ['Commission plan not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Soft delete - just deactivate
        if soft_delete:
            commission_plan.is_active = False
            commission_plan.save()
            
            return cls(
                deleted_id=id,
                success=True,
                errors={}
            )
        
        # Check if plan is referenced by any transactions
        # Note: You'll need to import your Transaction model here
        try:
            # Check if there are any transactions using this commission plan
            # Assuming there's a Transaction model with commission_plan FK
            from ..models.transaction import Transaction
            
            has_references = Transaction.objects.filter(
                commission_plan=commission_plan
            ).exists()
            
            if has_references and not force:
                errors['id'] = [
                    'Cannot delete commission plan that is referenced by transactions. '
                    'Use force=True to delete anyway, or soft_delete=True to deactivate.'
                ]
                return cls(success=False, errors=errors)
                
        except ImportError:
            # Transaction model not found - skip reference check
            pass
        except Exception as e:
            errors['reference_check'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            commission_plan.delete()
            
            return cls(
                deleted_id=deleted_id,
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
# Toggle Commission Plan Status Mutation
# =============================================================================

class ToggleCommissionPlanStatusMutation(relay.ClientIDMutation):
    """
    Toggle the active status of a commission plan.
    
    This is a convenience mutation for enabling/disabling commission plans
    without needing to send a full update.
    """
    
    class Input:
        id = graphene.ID(required=True)
        is_active = graphene.Boolean(required=True)
    
    commission_plan = graphene.Field(CommissionPlanNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, is_active):
        """
        Toggle commission plan active status.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Commission plan ID
            is_active: New active status
        
        Returns:
            ToggleCommissionPlanStatusMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can toggle commission plan status.']
            return cls(success=False, errors=errors)
        
        # Resolve commission plan
        try:
            pk = from_global_id(id)[1]
            commission_plan = CommissionPlan.objects.get(pk=pk)
        except CommissionPlan.DoesNotExist:
            errors['id'] = ['Commission plan not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            commission_plan.is_active = is_active
            commission_plan.save()
            
            return cls(
                commission_plan=commission_plan,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Duplicate Commission Plan Mutation
# =============================================================================

class DuplicateCommissionPlanMutation(relay.ClientIDMutation):
    """
    Duplicate an existing commission plan.
    
    Creates a new commission plan with the same settings as an existing one,
    with a suffix added to the name.
    """
    
    class Input:
        id = graphene.ID(required=True)
        new_name = graphene.String(required=False)
    
    commission_plan = graphene.Field(CommissionPlanNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, new_name=None):
        """
        Duplicate a commission plan.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Commission plan ID to duplicate
            new_name: Optional name for the new plan
        
        Returns:
            DuplicateCommissionPlanMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can duplicate commission plans.']
            return cls(success=False, errors=errors)
        
        # Resolve commission plan
        try:
            pk = from_global_id(id)[1]
            source_plan = CommissionPlan.objects.get(pk=pk)
        except CommissionPlan.DoesNotExist:
            errors['id'] = ['Commission plan not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Generate new name
            if not new_name:
                new_name = f"{source_plan.name} (Copy)"
            
            # Check if name already exists
            if CommissionPlan.objects.filter(name__iexact=new_name).exists():
                # Add a number suffix
                counter = 1
                base_name = new_name
                while CommissionPlan.objects.filter(name__iexact=new_name).exists():
                    new_name = f"{base_name} {counter}"
                    counter += 1
            
            # Create duplicate
            new_plan = CommissionPlan.objects.create(
                name=new_name,
                plan_type=source_plan.plan_type,
                base_percentage=source_plan.base_percentage,
                min_amount=source_plan.min_amount,
                max_amount=source_plan.max_amount,
                is_active=False,  # Duplicates start as inactive
            )
            
            return cls(
                commission_plan=new_plan,
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

class BulkDeleteCommissionPlansMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple commission plans.
    
    Allows deleting multiple commission plans at once with options for
    soft delete or force delete.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        force = graphene.Boolean(required=False, default_value=False)
        soft_delete = graphene.Boolean(required=False, default_value=False)
    
    deleted_ids = graphene.List(graphene.ID)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids, force=False, soft_delete=False):
        """
        Bulk delete multiple commission plans.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of commission plan IDs to delete
            force: Force hard delete even if referenced
            soft_delete: Set is_active=False instead of hard deleting
        
        Returns:
            BulkDeleteCommissionPlansMutation instance
        """
        errors = {}
        deleted_ids = []
        failed_ids = []
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete commission plans.']
            return cls(success=False, errors=errors)
        
        for plan_id in ids:
            try:
                pk = from_global_id(plan_id)[1]
                commission_plan = CommissionPlan.objects.get(pk=pk)
                
                if soft_delete:
                    # Soft delete
                    commission_plan.is_active = False
                    commission_plan.save()
                    deleted_ids.append(plan_id)
                else:
                    # Check references
                    try:
                        from ..models.transaction import Transaction
                        has_references = Transaction.objects.filter(
                            commission_plan=commission_plan
                        ).exists()
                        
                        if has_references and not force:
                            failed_ids.append(plan_id)
                            errors[plan_id] = [
                                'Plan is referenced by transactions. Use force=True or soft_delete=True.'
                            ]
                            continue
                    except ImportError:
                        pass
                    
                    # Hard delete
                    commission_plan.delete()
                    deleted_ids.append(plan_id)
                    
            except CommissionPlan.DoesNotExist:
                failed_ids.append(plan_id)
                errors[plan_id] = ['Commission plan not found.']
            except Exception as e:
                failed_ids.append(plan_id)
                errors[plan_id] = [str(e)]
        
        return cls(
            deleted_ids=deleted_ids,
            success=len(failed_ids) == 0,
            errors=errors if errors else {}
        )


class BulkUpdateCommissionPlansMutation(relay.ClientIDMutation):
    """
    Bulk update multiple commission plans.
    
    Allows updating common fields across multiple commission plans at once.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        name = graphene.String(required=True)
        plan_type = graphene.String(required=True)
        base_percentage = graphene.Decimal(default_value=Decimal("0"))
        min_amount = graphene.Decimal(required=False)
        max_amount = graphene.Decimal(required=False)
        is_active = graphene.Boolean(required=False, default_value=True)
        
    
    updated_ids = graphene.List(graphene.ID)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids, fields):
        """
        Bulk update commission plans.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of commission plan IDs to update
            fields: Fields to update
        
        Returns:
            BulkUpdateCommissionPlansMutation instance
        """
        errors = {}
        updated_ids = []
        failed_ids = []
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can update commission plans.']
            return cls(success=False, errors=errors)
        
        for plan_id in ids:
            try:
                pk = from_global_id(plan_id)[1]
                commission_plan = CommissionPlan.objects.get(pk=pk)
                
                # Apply updates
                if fields.get('base_percentage') is not None:
                    if fields['base_percentage'] < 0 or fields['base_percentage'] > 100:
                        errors[plan_id] = ['Percentage must be between 0 and 100.']
                        failed_ids.append(plan_id)
                        continue
                    commission_plan.base_percentage = fields['base_percentage']
                
                if fields.get('is_active') is not None:
                    commission_plan.is_active = fields['is_active']
                
                if fields.get('min_amount') is not None:
                    if fields['min_amount'] < 0:
                        errors[plan_id] = ['Minimum amount cannot be negative.']
                        failed_ids.append(plan_id)
                        continue
                    commission_plan.min_amount = fields['min_amount']
                
                if fields.get('max_amount') is not None:
                    if fields['max_amount'] < 0:
                        errors[plan_id] = ['Maximum amount cannot be negative.']
                        failed_ids.append(plan_id)
                        continue
                    commission_plan.max_amount = fields['max_amount']
                
                # Validate amount range
                if commission_plan.min_amount is not None and commission_plan.max_amount is not None:
                    if commission_plan.min_amount > commission_plan.max_amount:
                        errors[plan_id] = ['Minimum amount cannot be greater than maximum amount.']
                        failed_ids.append(plan_id)
                        continue
                
                commission_plan.full_clean()
                commission_plan.save()
                updated_ids.append(plan_id)
                
            except CommissionPlan.DoesNotExist:
                failed_ids.append(plan_id)
                errors[plan_id] = ['Commission plan not found.']
            except ValidationError as e:
                failed_ids.append(plan_id)
                errors[plan_id] = e.message_dict
            except Exception as e:
                failed_ids.append(plan_id)
                errors[plan_id] = [str(e)]
        
        return cls(
            updated_ids=updated_ids,
            success=len(failed_ids) == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class CommissionPlanMutations(graphene.ObjectType):
    """All commission plan mutations."""
    
    # CRUD operations
    create_commission_plan = CreateCommissionPlanMutation.Field()
    update_commission_plan = UpdateCommissionPlanMutation.Field()
    delete_commission_plan = DeleteCommissionPlanMutation.Field()
    
    # Additional operations
    toggle_commission_plan_status = ToggleCommissionPlanStatusMutation.Field()
    duplicate_commission_plan = DuplicateCommissionPlanMutation.Field()
    
    # Bulk operations
    bulk_delete_commission_plans = BulkDeleteCommissionPlansMutation.Field()
    bulk_update_commission_plans = BulkUpdateCommissionPlansMutation.Field()