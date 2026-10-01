# apps/backend/realestate/mutations/property_update_log.py

"""
Property Update Log Mutations for Real Estate Relay GraphQL API.
"""

import json
import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from realestate.models.property_update_log import PropertyUpdateLog
from realestate.models.listing import Listing
from graphq.realestate.types.property_update_log import PropertyUpdateLogNode

# =============================================================================
# Input Types
# =============================================================================

class PropertyUpdateLogInput(graphene.InputObjectType):
    """Input for property update log creation."""
    
    property_id = graphene.ID(required=True)
    changed_fields = graphene.JSONString(required=True)


class PropertyUpdateLogUpdateInput(graphene.InputObjectType):
    """Input for property update log update."""
    
    id = graphene.ID(required=True)
    changed_fields = graphene.JSONString(required=False)


# =============================================================================
# Create Property Update Log Mutation
# =============================================================================

class CreatePropertyUpdateLogMutation(relay.ClientIDMutation):
    """
    Create a new property update log.
    
    Records changes made to a property listing for audit purposes.
    Only authorized users can create update logs.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        changed_fields = graphene.JSONString(required=True)
    
    property_update_log = graphene.Field(PropertyUpdateLogNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Create a new property update log.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: PropertyUpdateLogInput data
        
        Returns:
            CreatePropertyUpdateLogMutation instance
        """
        errors = {}
        
        # Extract input
        property_id = input.get('property_id')
        changed_fields = input.get('changed_fields')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate changed_fields
        if not changed_fields:
            errors['changed_fields'] = ['Changed fields are required.']
            return cls(success=False, errors=errors)
        
        # Ensure changed_fields is a dict
        if isinstance(changed_fields, str):
            try:
                changed_fields = json.loads(changed_fields)
            except json.JSONDecodeError:
                errors['changed_fields'] = ['Invalid JSON format for changed fields.']
                return cls(success=False, errors=errors)
        
        if not isinstance(changed_fields, dict):
            errors['changed_fields'] = ['Changed fields must be a JSON object.']
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
        
        # Check permission - only owner, agent, or staff can create logs
        is_authorized = (
            user.is_staff or
            (property_obj.owner and property_obj.owner == user) or
            (property_obj.agent and property_obj.agent.profile and 
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to create update logs for this property.']
            return cls(success=False, errors=errors)
        
        try:
            # Create property update log
            property_update_log = PropertyUpdateLog.objects.create(
                property=property_obj,
                updated_by=user,
                changed_fields=changed_fields,
            )
            
            return cls(
                property_update_log=property_update_log,
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
# Update Property Update Log Mutation
# =============================================================================

class UpdatePropertyUpdateLogMutation(relay.ClientIDMutation):
    """
    Update an existing property update log.
    
    Allows updating the changed fields of a log entry.
    Normally, update logs are immutable, but this allows corrections.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        changed_fields = graphene.JSONString(required=True)
        
    property_update_log = graphene.Field(PropertyUpdateLogNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update an existing property update log.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: PropertyUpdateLogUpdateInput data
        
        Returns:
            UpdatePropertyUpdateLogMutation instance
        """
        errors = {}
        
        # Extract input
        log_id = input.get('id')
        changed_fields = input.get('changed_fields')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve property update log
        try:
            pk = from_global_id(log_id)[1]
            property_update_log = PropertyUpdateLog.objects.get(pk=pk)
        except PropertyUpdateLog.DoesNotExist:
            errors['id'] = ['Property update log not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can update logs (immutable audit trail)
        if not user.is_staff:
            errors['permission'] = ['Only staff members can update update logs.']
            return cls(success=False, errors=errors)
        
        # Validate changed_fields if provided
        if changed_fields is not None:
            if isinstance(changed_fields, str):
                try:
                    changed_fields = json.loads(changed_fields)
                except json.JSONDecodeError:
                    errors['changed_fields'] = ['Invalid JSON format for changed fields.']
                    return cls(success=False, errors=errors)
            
            if not isinstance(changed_fields, dict):
                errors['changed_fields'] = ['Changed fields must be a JSON object.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if changed_fields is not None:
                property_update_log.changed_fields = changed_fields
            
            property_update_log.full_clean()
            property_update_log.save()
            
            return cls(
                property_update_log=property_update_log,
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
# Delete Property Update Log Mutation
# =============================================================================

class DeletePropertyUpdateLogMutation(relay.ClientIDMutation):
    """
    Delete a property update log.
    
    Removes a log entry from the audit trail.
    This should be used sparingly as it removes audit information.
    """
    
    class Input:
        id = graphene.ID(required=True)
        force = graphene.Boolean(
            required=False,
            default_value=False,
            description="Force deletion even if it's the last log"
        )
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, force=False):
        """
        Delete a property update log.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Log ID to delete
            force: Force deletion
        
        Returns:
            DeletePropertyUpdateLogMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission - only staff can delete logs
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete update logs.']
            return cls(success=False, errors=errors)
        
        # Resolve property update log
        try:
            pk = from_global_id(id)[1]
            property_update_log = PropertyUpdateLog.objects.get(pk=pk)
        except PropertyUpdateLog.DoesNotExist:
            errors['id'] = ['Property update log not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if this is the last log for the property
        if not force:
            log_count = PropertyUpdateLog.objects.filter(
                property=property_update_log.property
            ).count()
            
            if log_count <= 1:
                errors['force'] = [
                    'This is the last log for this property. '
                    'Use force=True to delete it.'
                ]
                return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            property_update_log.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Get Property Update Log Summary Mutation
# =============================================================================

class GetPropertyUpdateLogSummaryMutation(relay.ClientIDMutation):
    """
    Get a summary of all updates for a property.
    
    Returns a summary of all changes made to a property over time.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
    
    summary = graphene.JSONString()
    log_count = graphene.Int()
    last_update = graphene.DateTime()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, property_id):
        """
        Get property update log summary.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            property_id: Property ID to get summary for
        
        Returns:
            GetPropertyUpdateLogSummaryMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
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
        
        # Check permission
        is_authorized = (
            user.is_staff or
            (property_obj.owner and property_obj.owner == user) or
            (property_obj.agent and property_obj.agent.profile and 
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to view logs for this property.']
            return cls(success=False, errors=errors)
        
        try:
            # Get all logs for this property
            logs = PropertyUpdateLog.objects.filter(
                property=property_obj
            ).order_by('-timestamp')
            
            log_count = logs.count()
            last_update = logs.first().timestamp if log_count > 0 else None
            
            # Build summary
            summary = {
                'property_id': property_obj.id,
                'property_title': property_obj.title,
                'total_updates': log_count,
                'last_update': last_update.isoformat() if last_update else None,
                'updates': []
            }
            
            for log in logs[:50]:  # Limit to 50 most recent logs
                summary['updates'].append({
                    'timestamp': log.timestamp.isoformat(),
                    'updated_by': log.updated_by.email if log.updated_by else 'System',
                    'changed_fields': log.changed_fields,
                    'change_summary': log.get_change_summary(),
                })
            
            return cls(
                summary=summary,
                log_count=log_count,
                last_update=last_update,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkDeletePropertyUpdateLogsMutation(relay.ClientIDMutation):
    """
    Bulk delete multiple property update logs.
    
    Allows deleting multiple logs at once for administrative purposes.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        force = graphene.Boolean(required=False, default_value=False)
    
    deleted_ids = graphene.List(graphene.ID)
    success_count = graphene.Int()
    failure_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids, force=False):
        """
        Bulk delete property update logs.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of log IDs to delete
            force: Force deletion
        
        Returns:
            BulkDeletePropertyUpdateLogsMutation instance
        """
        errors = {}
        deleted_ids = []
        success_count = 0
        failure_count = 0
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Check permission
        if not user.is_staff:
            errors['permission'] = ['Only staff members can delete update logs.']
            return cls(success=False, errors=errors)
        
        for log_id in ids:
            try:
                pk = from_global_id(log_id)[1]
                property_update_log = PropertyUpdateLog.objects.get(pk=pk)
                
                # Check if this is the last log for the property
                if not force:
                    log_count = PropertyUpdateLog.objects.filter(
                        property=property_update_log.property
                    ).count()
                    
                    if log_count <= 1:
                        errors[log_id] = ['This is the last log for this property. Use force=True to delete.']
                        failure_count += 1
                        continue
                
                property_update_log.delete()
                deleted_ids.append(log_id)
                success_count += 1
                
            except PropertyUpdateLog.DoesNotExist:
                errors[log_id] = ['Property update log not found.']
                failure_count += 1
            except Exception as e:
                errors[log_id] = [str(e)]
                failure_count += 1
        
        return cls(
            deleted_ids=deleted_ids,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class PropertyUpdateLogMutations(graphene.ObjectType):
    """All property update log mutations."""
    
    # CRUD operations
    create_property_update_log = CreatePropertyUpdateLogMutation.Field()
    update_property_update_log = UpdatePropertyUpdateLogMutation.Field()
    delete_property_update_log = DeletePropertyUpdateLogMutation.Field()
    
    # Summary
    get_property_update_log_summary = GetPropertyUpdateLogSummaryMutation.Field()
    
    # Bulk operations
    bulk_delete_property_update_logs = BulkDeletePropertyUpdateLogsMutation.Field()