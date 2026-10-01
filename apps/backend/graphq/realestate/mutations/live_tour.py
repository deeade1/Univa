# apps/backend/realestate/mutations/live_tour_schedule.py

"""
Live Tour Schedule Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from graphq.realestate.types.live_tour import LiveTourScheduleNode
from realestate.models.live_tour import LiveTourSchedule
from realestate.models.listing import Listing
from realestate.models.agent import Agent
from graphq.realestate.types.live_tour import LiveTourScheduleNode


# =============================================================================
# Schedule Live Tour Mutation
# =============================================================================

class ScheduleLiveTourMutation(relay.ClientIDMutation):
    """
    Schedule a new live tour.
    
    Creates a live tour event for a property with an agent, time, and meeting link.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        agent_id = graphene.ID(required=True)
        scheduled_time = graphene.DateTime(required=True)
        duration_minutes = graphene.Int(required=False, default_value=30)
        meeting_link = graphene.String(required=True)
        max_attendees = graphene.Int(required=False, default_value=10)
    
    live_tour = graphene.Field(LiveTourScheduleNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Schedule a new live tour.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: LiveTourScheduleInput data
        
        Returns:
            ScheduleLiveTourMutation instance
        """
        errors = {}
        
        # Extract input
        property_id = input.get('property_id')
        agent_id = input.get('agent_id')
        scheduled_time = input.get('scheduled_time')
        duration_minutes = input.get('duration_minutes', 30)
        meeting_link = input.get('meeting_link')
        max_attendees = input.get('max_attendees', 10)
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate scheduled time
        if scheduled_time <= timezone.now():
            errors['scheduled_time'] = ['Scheduled time must be in the future.']
            return cls(success=False, errors=errors)
        
        # Validate duration
        if duration_minutes <= 0:
            errors['duration_minutes'] = ['Duration must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate max attendees
        if max_attendees <= 0:
            errors['max_attendees'] = ['Max attendees must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate meeting link
        if not meeting_link:
            errors['meeting_link'] = ['Meeting link is required.']
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
        
        # Check permission - user must be staff, agent, or owner
        is_authorized = (
            user.is_staff or
            (hasattr(property_obj, 'agent') and property_obj.agent and 
             hasattr(property_obj.agent, 'profile') and 
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user) or
            (hasattr(property_obj, 'owner') and property_obj.owner and 
             property_obj.owner == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to schedule tours for this property.']
            return cls(success=False, errors=errors)
        
        # Resolve agent
        try:
            pk = from_global_id(agent_id)[1]
            agent = Agent.objects.get(pk=pk)
        except Agent.DoesNotExist:
            errors['agent_id'] = ['Agent not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['agent_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check for scheduling conflicts with the same agent
        conflicting_tours = LiveTourSchedule.objects.filter(
            agent=agent,
            scheduled_time__lt=scheduled_time + timezone.timedelta(minutes=duration_minutes),
            scheduled_time__gt=scheduled_time - timezone.timedelta(minutes=duration_minutes)
        ).exists()
        
        if conflicting_tours:
            errors['scheduled_time'] = ['Agent has a scheduling conflict at this time.']
            return cls(success=False, errors=errors)
        
        try:
            # Create live tour
            live_tour = LiveTourSchedule.objects.create(
                property=property_obj,
                agent=agent,
                scheduled_time=scheduled_time,
                duration_minutes=duration_minutes,
                meeting_link=meeting_link,
                max_attendees=max_attendees,
            )
            
            return cls(
                live_tour=live_tour,
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
# Update Live Tour Schedule Mutation
# =============================================================================

class UpdateLiveTourScheduleMutation(relay.ClientIDMutation):
    """
    Update an existing live tour schedule.
    
    Allows updating tour details including time, duration, and meeting link.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        agent_id = graphene.ID(required=True)
        scheduled_time = graphene.DateTime(required=True)
        duration_minutes = graphene.Int(required=False, default_value=30)
        meeting_link = graphene.String(required=True)
        max_attendees = graphene.Int(required=False, default_value=10)
    
    live_tour = graphene.Field(LiveTourScheduleNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, input):
        """
        Update an existing live tour schedule.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: LiveTourScheduleUpdateInput data
        
        Returns:
            UpdateLiveTourScheduleMutation instance
        """
        errors = {}
        
        # Extract input
        tour_id = input.get('id')
        property_id = input.get('property_id')
        agent_id = input.get('agent_id')
        scheduled_time = input.get('scheduled_time')
        duration_minutes = input.get('duration_minutes')
        meeting_link = input.get('meeting_link')
        max_attendees = input.get('max_attendees')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve live tour
        try:
            pk = from_global_id(tour_id)[1]
            live_tour = LiveTourSchedule.objects.get(pk=pk)
        except LiveTourSchedule.DoesNotExist:
            errors['id'] = ['Live tour not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be staff, agent, or owner
        property_obj = live_tour.property
        is_authorized = (
            user.is_staff or
            (hasattr(property_obj, 'agent') and property_obj.agent and 
             hasattr(property_obj.agent, 'profile') and 
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user) or
            (hasattr(property_obj, 'owner') and property_obj.owner and 
             property_obj.owner == user) or
            (live_tour.agent and live_tour.agent.profile and 
             hasattr(live_tour.agent.profile, 'user') and 
             live_tour.agent.profile.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to update this tour.']
            return cls(success=False, errors=errors)
        
        # Check if tour is in the past
        if live_tour.is_past():
            errors['tour'] = ['Cannot update a past tour.']
            return cls(success=False, errors=errors)
        
        # Validate scheduled time
        if scheduled_time and scheduled_time <= timezone.now():
            errors['scheduled_time'] = ['Scheduled time must be in the future.']
            return cls(success=False, errors=errors)
        
        # Validate duration
        if duration_minutes and duration_minutes <= 0:
            errors['duration_minutes'] = ['Duration must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate max attendees
        if max_attendees and max_attendees <= 0:
            errors['max_attendees'] = ['Max attendees must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Validate meeting link
        if meeting_link is not None and not meeting_link:
            errors['meeting_link'] = ['Meeting link is required.']
            return cls(success=False, errors=errors)
        
        # Resolve property if provided
        if property_id:
            try:
                pk = from_global_id(property_id)[1]
                property_obj = Listing.objects.get(pk=pk)
                live_tour.property = property_obj
            except Listing.DoesNotExist:
                errors['property_id'] = ['Property not found.']
                return cls(success=False, errors=errors)
        
        # Resolve agent if provided
        if agent_id:
            try:
                pk = from_global_id(agent_id)[1]
                agent = Agent.objects.get(pk=pk)
                live_tour.agent = agent
            except Agent.DoesNotExist:
                errors['agent_id'] = ['Agent not found.']
                return cls(success=False, errors=errors)
        
        # Check for scheduling conflicts with the same agent
        if agent_id or scheduled_time or duration_minutes:
            agent = live_tour.agent
            tour_time = scheduled_time or live_tour.scheduled_time
            tour_duration = duration_minutes or live_tour.duration_minutes
            
            conflicting_tours = LiveTourSchedule.objects.filter(
                agent=agent,
                scheduled_time__lt=tour_time + timezone.timedelta(minutes=tour_duration),
                scheduled_time__gt=tour_time - timezone.timedelta(minutes=tour_duration)
            ).exclude(pk=live_tour.pk).exists()
            
            if conflicting_tours:
                errors['scheduled_time'] = ['Agent has a scheduling conflict at this time.']
                return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if scheduled_time is not None:
                live_tour.scheduled_time = scheduled_time
            if duration_minutes is not None:
                live_tour.duration_minutes = duration_minutes
            if meeting_link is not None:
                live_tour.meeting_link = meeting_link
            if max_attendees is not None:
                live_tour.max_attendees = max_attendees
            
            live_tour.full_clean()
            live_tour.save()
            
            return cls(
                live_tour=live_tour,
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
# Cancel Live Tour Mutation
# =============================================================================

class CancelLiveTourMutation(relay.ClientIDMutation):
    """
    Cancel a live tour.
    
    Cancels a scheduled tour and notifies all registered attendees.
    """
    
    class Input:
        id = graphene.ID(required=True)
        reason = graphene.String(required=False)
    
    deleted_id = graphene.ID()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, reason=None):
        """
        Cancel a live tour.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Tour ID to cancel
            reason: Optional cancellation reason
        
        Returns:
            CancelLiveTourMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve live tour
        try:
            pk = from_global_id(id)[1]
            live_tour = LiveTourSchedule.objects.get(pk=pk)
        except LiveTourSchedule.DoesNotExist:
            errors['id'] = ['Live tour not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be staff, agent, or owner
        property_obj = live_tour.property
        is_authorized = (
            user.is_staff or
            (hasattr(property_obj, 'agent') and property_obj.agent and 
             hasattr(property_obj.agent, 'profile') and 
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user) or
            (hasattr(property_obj, 'owner') and property_obj.owner and 
             property_obj.owner == user) or
            (live_tour.agent and live_tour.agent.profile and 
             hasattr(live_tour.agent.profile, 'user') and 
             live_tour.agent.profile.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to cancel this tour.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            live_tour.delete()
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Update Tour Attendee Count Mutation
# =============================================================================

class UpdateTourAttendeeLimitMutation(relay.ClientIDMutation):
    """
    Update the maximum attendees for a live tour.
    
    Allows changing the capacity of a tour.
    """
    
    class Input:
        id = graphene.ID(required=True)
        max_attendees = graphene.Int(required=True)
    
    live_tour = graphene.Field(LiveTourScheduleNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, id, max_attendees):
        """
        Update tour attendee limit.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Tour ID
            max_attendees: New max attendees limit
        
        Returns:
            UpdateTourAttendeeLimitMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Validate max attendees
        if max_attendees <= 0:
            errors['max_attendees'] = ['Max attendees must be greater than 0.']
            return cls(success=False, errors=errors)
        
        # Resolve live tour
        try:
            pk = from_global_id(id)[1]
            live_tour = LiveTourSchedule.objects.get(pk=pk)
        except LiveTourSchedule.DoesNotExist:
            errors['id'] = ['Live tour not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user must be staff, agent, or owner
        property_obj = live_tour.property
        is_authorized = (
            user.is_staff or
            (hasattr(property_obj, 'agent') and property_obj.agent and 
             hasattr(property_obj.agent, 'profile') and 
             hasattr(property_obj.agent.profile, 'user') and 
             property_obj.agent.profile.user == user) or
            (hasattr(property_obj, 'owner') and property_obj.owner and 
             property_obj.owner == user) or
            (live_tour.agent and live_tour.agent.profile and 
             hasattr(live_tour.agent.profile, 'user') and 
             live_tour.agent.profile.user == user)
        )
        
        if not is_authorized:
            errors['permission'] = ['You do not have permission to update this tour.']
            return cls(success=False, errors=errors)
        
        # Check if new limit is less than current attendees
        current_attendees = live_tour.attendees.count()
        if max_attendees < current_attendees:
            errors['max_attendees'] = [
                f'Cannot set max attendees to {max_attendees} as there are '
                f'{current_attendees} already registered.'
            ]
            return cls(success=False, errors=errors)
        
        try:
            live_tour.max_attendees = max_attendees
            live_tour.save()
            
            return cls(
                live_tour=live_tour,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkScheduleLiveToursMutation(relay.ClientIDMutation):
    """
    Bulk schedule multiple live tours.
    
    Allows scheduling multiple tours at once for different properties.
    """
    
    class Input:
        property_id = graphene.ID(required=True)
        agent_id = graphene.ID(required=True)
        scheduled_time = graphene.DateTime(required=True)
        duration_minutes = graphene.Int(required=False, default_value=30)
        meeting_link = graphene.String(required=True)
        max_attendees = graphene.Int(required=False, default_value=10)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Bulk schedule live tours.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            tours: List of tour inputs
        
        Returns:
            BulkScheduleLiveToursMutation instance
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
        
        for idx, tour_input in enumerate(tours):
            try:
                # Use the create mutation for each tour
                result = ScheduleLiveTourMutation.mutate_and_get_payload(
                    root, info, tour_input
                )
                
                if result.success:
                    success_count += 1
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'tour_id': result.live_tour.id if result.live_tour else None,
                    })
                else:
                    failure_count += 1
                    errors[f'tour_{idx}'] = result.errors
                    results.append({
                        'index': idx,
                        'status': 'failed',
                        'errors': result.errors,
                    })
                    
            except Exception as e:
                failure_count += 1
                errors[f'tour_{idx}'] = [str(e)]
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


class BulkCancelLiveToursMutation(relay.ClientIDMutation):
    """
    Bulk cancel multiple live tours.
    
    Allows canceling multiple tours at once.
    """
    
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        reason = graphene.String(required=False)
    
    cancelled_ids = graphene.List(graphene.ID)
    success_count = graphene.Int()
    failure_count = graphene.Int()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, ids, reason=None):
        """
        Bulk cancel live tours.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            ids: List of tour IDs to cancel
            reason: Optional cancellation reason
        
        Returns:
            BulkCancelLiveToursMutation instance
        """
        errors = {}
        cancelled_ids = []
        success_count = 0
        failure_count = 0
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        for tour_id in ids:
            try:
                result = CancelLiveTourMutation.mutate_and_get_payload(
                    root, info, tour_id, reason
                )
                
                if result.success:
                    cancelled_ids.append(tour_id)
                    success_count += 1
                else:
                    failure_count += 1
                    errors[tour_id] = result.errors
                    
            except Exception as e:
                failure_count += 1
                errors[tour_id] = [str(e)]
        
        return cls(
            cancelled_ids=cancelled_ids,
            success_count=success_count,
            failure_count=failure_count,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


# =============================================================================
# Export Mutations
# =============================================================================

class LiveTourScheduleMutations(graphene.ObjectType):
    """All live tour schedule mutations."""
    
    # CRUD operations
    schedule_live_tour = ScheduleLiveTourMutation.Field()
    update_live_tour_schedule = UpdateLiveTourScheduleMutation.Field()
    cancel_live_tour = CancelLiveTourMutation.Field()
    
    # Capacity management
    update_tour_attendee_limit = UpdateTourAttendeeLimitMutation.Field()
    
    # Bulk operations
    bulk_schedule_live_tours = BulkScheduleLiveToursMutation.Field()
    bulk_cancel_live_tours = BulkCancelLiveToursMutation.Field()