# apps/backend/realestate/mutations/live_tour_registration.py

"""
Live Tour Registration Mutations for Real Estate Relay GraphQL API.
"""

import graphene
from graphene import relay
from graphql_relay import from_global_id

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphq.realestate.types.live_tour_registration import LiveTourRegistrationNode
from realestate.models.live_tour_registration import LiveTourRegistration
from realestate.models.live_tour import LiveTourSchedule



# =============================================================================
# Register for Live Tour Mutation
# =============================================================================

class RegisterForLiveTourMutation(relay.ClientIDMutation):
    """
    Register a user for a live tour.
    
    Creates a registration for a user to attend a scheduled live tour.
    Users can only register once per tour.
    """
    
    class Input:
        id = graphene.ID(required=True)
        tour_id = graphene.ID(required=True)
        attended = graphene.Boolean(required=False)
        
    registration = graphene.Field(LiveTourRegistrationNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Register a user for a live tour.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: LiveTourRegistrationInput data
        
        Returns:
            RegisterForLiveTourMutation instance
        """
        errors = {}
        
        # Extract input
        tour_id = input.get('tour_id')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve tour
        try:
            pk = from_global_id(tour_id)[1]
            tour = LiveTourSchedule.objects.get(pk=pk)
        except LiveTourSchedule.DoesNotExist:
            errors['tour_id'] = ['Live tour not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['tour_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if tour is fully booked
        if tour.is_fully_booked():
            errors['tour'] = ['This tour is fully booked.']
            return cls(success=False, errors=check)
        
        # Check if tour has already started
        if tour.start_time and tour.start_time < timezone.now():
            errors['tour'] = ['This tour has already started.']
            return cls(success=False, errors=errors)
        
        # Check if user is already registered
        if LiveTourRegistration.objects.filter(user=user, tour=tour).exists():
            errors['registration'] = ['You are already registered for this tour.']
            return cls(success=False, errors=errors)
        
        try:
            # Create registration
            registration = LiveTourRegistration.objects.create(
                user=user,
                tour=tour,
                attended=False,
            )
            
            # Update tour participant count if tracking
            # (This assumes the tour has a participants_count field)
            if hasattr(tour, 'participants_count'):
                tour.participants_count = tour.registrations.count()
                tour.save(update_fields=['participants_count'])
            
            return cls(
                registration=registration,
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
# Update Live Tour Registration Mutation
# =============================================================================

class UpdateLiveTourRegistrationMutation(relay.ClientIDMutation):
    """
    Update a live tour registration.
    
    Allows marking attendance status for a registration.
    """
    
    class Input:
        id = graphene.ID(required=True)
        tour_id = graphene.ID(required=True)
        attended = graphene.Boolean(required=False)
    
    registration = graphene.Field(LiveTourRegistrationNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        """
        Update a live tour registration.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            input: LiveTourRegistrationUpdateInput data
        
        Returns:
            UpdateLiveTourRegistrationMutation instance
        """
        errors = {}
        
        # Extract input
        registration_id = input.get('id')
        attended = input.get('attended')
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve registration
        try:
            pk = from_global_id(registration_id)[1]
            registration = LiveTourRegistration.objects.get(pk=pk)
        except LiveTourRegistration.DoesNotExist:
            errors['id'] = ['Registration not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user can update their own, staff can update all
        if registration.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to update this registration.']
            return cls(success=False, errors=errors)
        
        try:
            # Update fields
            if attended is not None:
                registration.attended = attended
            
            registration.full_clean()
            registration.save()
            
            return cls(
                registration=registration,
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
# Cancel Live Tour Registration Mutation
# =============================================================================

class CancelLiveTourRegistrationMutation(relay.ClientIDMutation):
    """
    Cancel a live tour registration.
    
    Removes a user's registration for a live tour.
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
        Cancel a live tour registration.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            id: Registration ID to cancel
            reason: Optional cancellation reason
        
        Returns:
            CancelLiveTourRegistrationMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve registration
        try:
            pk = from_global_id(id)[1]
            registration = LiveTourRegistration.objects.get(pk=pk)
        except LiveTourRegistration.DoesNotExist:
            errors['id'] = ['Registration not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check permission - user can cancel their own, staff can cancel all
        if registration.user != user and not user.is_staff:
            errors['permission'] = ['You do not have permission to cancel this registration.']
            return cls(success=False, errors=errors)
        
        # Check if tour has already started
        if registration.tour.start_time and registration.tour.start_time < timezone.now():
            errors['tour'] = ['Cannot cancel registration for a tour that has already started.']
            return cls(success=False, errors=errors)
        
        try:
            deleted_id = id
            tour = registration.tour
            
            # Delete registration
            registration.delete()
            
            # Update tour participant count if tracking
            if hasattr(tour, 'participants_count'):
                tour.participants_count = tour.registrations.count()
                tour.save(update_fields=['participants_count'])
            
            return cls(
                deleted_id=deleted_id,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Mark Attendance Mutation
# =============================================================================

class MarkLiveTourAttendanceMutation(relay.ClientIDMutation):
    """
    Mark attendance for a live tour registration.
    
    This is a convenience mutation for staff to mark that a user attended.
    """
    
    class Input:
        registration_id = graphene.ID(required=True)
        attended = graphene.Boolean(required=True)
    
    registration = graphene.Field(LiveTourRegistrationNode)
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, registration_id, attended):
        """
        Mark attendance for a live tour registration.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            registration_id: Registration ID
            attended: Attendance status
        
        Returns:
            MarkLiveTourAttendanceMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Only staff can mark attendance
        if not user.is_staff:
            errors['permission'] = ['Only staff members can mark attendance.']
            return cls(success=False, errors=errors)
        
        # Resolve registration
        try:
            pk = from_global_id(registration_id)[1]
            registration = LiveTourRegistration.objects.get(pk=pk)
        except LiveTourRegistration.DoesNotExist:
            errors['registration_id'] = ['Registration not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['registration_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            registration.attended = attended
            registration.save()
            
            return cls(
                registration=registration,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkRegisterForLiveTourMutation(relay.ClientIDMutation):
    """
    Bulk register multiple users for a live tour.
    
    Allows staff to register multiple users at once for a tour.
    """
    
    class Input:
        tour_id = graphene.ID(required=True)
        user_ids = graphene.List(graphene.ID, required=True)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, tour_id, user_ids):
        """
        Bulk register users for a live tour.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            tour_id: Tour ID
            user_ids: List of user IDs to register
        
        Returns:
            BulkRegisterForLiveTourMutation instance
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
        
        # Only staff can bulk register
        if not user.is_staff:
            errors['permission'] = ['Only staff members can bulk register users.']
            return cls(success=False, errors=errors)
        
        # Resolve tour
        try:
            pk = from_global_id(tour_id)[1]
            tour = LiveTourSchedule.objects.get(pk=pk)
        except LiveTourSchedule.DoesNotExist:
            errors['tour_id'] = ['Live tour not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['tour_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        # Check if tour is fully booked
        if tour.is_fully_booked():
            errors['tour'] = ['This tour is fully booked.']
            return cls(success=False, errors=errors)
        
        for user_id in user_ids:
            try:
                # Resolve user
                from django.contrib.auth import get_user_model
                User = get_user_model()
                pk = from_global_id(user_id)[1]
                tour_user = User.objects.get(pk=pk)
                
                # Check if already registered
                if LiveTourRegistration.objects.filter(user=tour_user, tour=tour).exists():
                    failure_count += 1
                    errors[user_id] = ['User already registered for this tour.']
                    results.append({
                        'user_id': user_id,
                        'status': 'failed',
                        'errors': ['Already registered'],
                    })
                    continue
                
                # Create registration
                registration = LiveTourRegistration.objects.create(
                    user=tour_user,
                    tour=tour,
                    attended=False,
                )
                
                success_count += 1
                results.append({
                    'user_id': user_id,
                    'registration_id': registration.id,
                    'status': 'success',
                })
                
            except Exception as e:
                failure_count += 1
                errors[user_id] = [str(e)]
                results.append({
                    'user_id': user_id,
                    'status': 'failed',
                    'errors': [str(e)],
                })
        
        # Update tour participant count if tracking
        if hasattr(tour, 'participants_count'):
            tour.participants_count = tour.registrations.count()
            tour.save(update_fields=['participants_count'])
        
        return cls(
            success_count=success_count,
            failure_count=failure_count,
            results=results,
            success=failure_count == 0,
            errors=errors if errors else {}
        )


class BulkMarkAttendanceMutation(relay.ClientIDMutation):
    """
    Bulk mark attendance for multiple registrations.
    
    Allows staff to mark attendance for multiple users at once.
    """
    
    class Input:
        registration_ids = graphene.List(graphene.ID, required=True)
        attended = graphene.Boolean(required=True)
    
    success_count = graphene.Int()
    failure_count = graphene.Int()
    results = graphene.JSONString()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, registration_ids, attended):
        """
        Bulk mark attendance.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            registration_ids: List of registration IDs
            attended: Attendance status
        
        Returns:
            BulkMarkAttendanceMutation instance
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
        
        # Only staff can bulk mark attendance
        if not user.is_staff:
            errors['permission'] = ['Only staff members can bulk mark attendance.']
            return cls(success=False, errors=errors)
        
        for registration_id in registration_ids:
            try:
                pk = from_global_id(registration_id)[1]
                registration = LiveTourRegistration.objects.get(pk=pk)
                
                registration.attended = attended
                registration.save()
                
                success_count += 1
                results.append({
                    'registration_id': registration_id,
                    'status': 'success',
                })
                
            except LiveTourRegistration.DoesNotExist:
                failure_count += 1
                errors[registration_id] = ['Registration not found.']
                results.append({
                    'registration_id': registration_id,
                    'status': 'failed',
                    'errors': ['Registration not found'],
                })
            except Exception as e:
                failure_count += 1
                errors[registration_id] = [str(e)]
                results.append({
                    'registration_id': registration_id,
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
# Get Tour Registration Status Mutation
# =============================================================================

class GetTourRegistrationStatusMutation(relay.ClientIDMutation):
    """
    Get registration status for a user on a tour.
    
    Checks if a user is registered for a specific tour.
    """
    
    class Input:
        tour_id = graphene.ID(required=True)
    
    is_registered = graphene.Boolean()
    registration = graphene.Field(LiveTourRegistrationNode)
    registration_count = graphene.Int()
    max_capacity = graphene.Int()
    is_fully_booked = graphene.Boolean()
    success = graphene.Boolean()
    errors = graphene.JSONString()
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, tour_id):
        """
        Get registration status for a user on a tour.
        
        Args:
            root: The root query object
            info: GraphQL execution info
            tour_id: Tour ID to check
        
        Returns:
            GetTourRegistrationStatusMutation instance
        """
        errors = {}
        
        # Check authentication
        user = info.context.user if hasattr(info.context, 'user') else None
        if not user or not user.is_authenticated:
            errors['authentication'] = ['Authentication required.']
            return cls(success=False, errors=errors)
        
        # Resolve tour
        try:
            pk = from_global_id(tour_id)[1]
            tour = LiveTourSchedule.objects.get(pk=pk)
        except LiveTourSchedule.DoesNotExist:
            errors['tour_id'] = ['Live tour not found.']
            return cls(success=False, errors=errors)
        except Exception as e:
            errors['tour_id'] = [str(e)]
            return cls(success=False, errors=errors)
        
        try:
            # Get user's registration
            registration = LiveTourRegistration.objects.filter(
                user=user,
                tour=tour
            ).first()
            
            # Get registration count
            registration_count = LiveTourRegistration.objects.filter(tour=tour).count()
            
            # Get max capacity
            max_capacity = tour.max_participants if hasattr(tour, 'max_participants') else 0
            
            return cls(
                is_registered=registration is not None,
                registration=registration,
                registration_count=registration_count,
                max_capacity=max_capacity,
                is_fully_booked=tour.is_fully_booked() if hasattr(tour, 'is_fully_booked') else False,
                success=True,
                errors={}
            )
            
        except Exception as e:
            errors['general'] = [str(e)]
            return cls(success=False, errors=errors)


# =============================================================================
# Export Mutations
# =============================================================================

class LiveTourRegistrationMutations(graphene.ObjectType):
    """All live tour registration mutations."""
    
    # Registration operations
    register_for_live_tour = RegisterForLiveTourMutation.Field()
    update_live_tour_registration = UpdateLiveTourRegistrationMutation.Field()
    cancel_live_tour_registration = CancelLiveTourRegistrationMutation.Field()
    
    # Attendance operations
    mark_live_tour_attendance = MarkLiveTourAttendanceMutation.Field()
    
    # Bulk operations
    bulk_register_for_live_tour = BulkRegisterForLiveTourMutation.Field()
    bulk_mark_attendance = BulkMarkAttendanceMutation.Field()
    
    # Status
    get_tour_registration_status = GetTourRegistrationStatusMutation.Field()