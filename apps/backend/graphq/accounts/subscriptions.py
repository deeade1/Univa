import graphene
from channels_graphql_ws import Subscription
from .types import (
     UserNode, 
     UserRoleNode, 
     UserProfileNode,
     # AuditLogNode
)
  
from graphq.biometrics.types import FaceVerificationNode, BiometricDeviceNode
from  graphq.support.types import ContactUsNode
# -------------------------------
# User Role Subscription
# -------------------------------
class OnUserRoleChange(Subscription):
    """Subscription triggers when user roles change."""
    
    action = graphene.String()  # 'created', 'updated', 'deleted', 'activated', 'revoked'
    user_role = graphene.Field(UserRoleNode)
    user_id = graphene.ID()
    role_name = graphene.String()
    app_name = graphene.String()

    class Arguments:
        user_id = graphene.ID()
        app_name = graphene.String()

    def subscribe(self, info, user_id=None, app_name=None):
        """Client subscription handler."""
        del info
        groups = []
        if user_id:
            groups.append(f"user_roles_{user_id}")
        if app_name:
            groups.append(f"app_roles_{app_name}")
        return groups if groups else ["user_roles_global"]

    def publish(self, info, user_id=None, app_name=None):
        """Prepare subscription notification."""
        action = self["action"]
        user_role_data = self["user_role"]
        
        # Check if client should receive this notification
        target_user_id = str(user_role_data.user.id)
        target_app_name = user_role_data.role.app_name
        
        if user_id and user_id != target_user_id:
            return None
        if app_name and app_name != target_app_name:
            return None
            
        return OnUserRoleChange(
            action=action,
            user_role=user_role_data,
            user_id=target_user_id,
            role_name=user_role_data.role.name,
            app_name=target_app_name
        )

    @classmethod
    def notify_user_role_change(cls, action, user_role):
        """Notify about user role changes."""
        cls.broadcast(
            group=f"user_roles_{user_role.user.id}",
            payload={
                "action": action,
                "user_role": user_role
            }
        )
        cls.broadcast(
            group=f"app_roles_{user_role.role.app_name}",
            payload={
                "action": action,
                "user_role": user_role
            }
        )

# -------------------------------
# User Profile Subscription
# -------------------------------
class OnUserProfileUpdate(Subscription):
    """Subscription triggers when user profile is updated."""
    
    user_profile = graphene.Field(UserProfileNode)
    user_id = graphene.ID()
    updated_fields = graphene.List(graphene.String)

    class Arguments:
        user_id = graphene.ID()

    def subscribe(self, info, user_id=None):
        """Client subscription handler."""
        del info
        if user_id:
            return [f"user_profile_{user_id}"]
        return None  # Must specify user_id for security

    def publish(self, info, user_id=None):
        """Prepare subscription notification."""
        profile_data = self["user_profile"]
        updated_fields = self["updated_fields"]
        
        # Only allow users to subscribe to their own profile updates
        requesting_user_id = info.context.user.id if info.context.user else None
        profile_user_id = profile_data.user.id
        
        if str(profile_user_id) != str(requesting_user_id):
            return None
            
        return OnUserProfileUpdate(
            user_profile=profile_data,
            user_id=str(profile_user_id),
            updated_fields=updated_fields
        )

    @classmethod
    def notify_profile_update(cls, user_profile, updated_fields):
        """Notify about profile updates."""
        cls.broadcast(
            group=f"user_profile_{user_profile.user.id}",
            payload={
                "user_profile": user_profile,
                "updated_fields": updated_fields
            }
        )

# -------------------------------
# User Online Status Subscription
# -------------------------------
class OnUserStatusChange(Subscription):
    """Subscription triggers when user online status changes."""
    
    user_id = graphene.ID()
    is_online = graphene.Boolean()
    last_active = graphene.DateTime()

    class Arguments:
        user_ids = graphene.List(graphene.ID)

    def subscribe(self, info, user_ids=None):
        """Client subscription handler."""
        del info
        if user_ids:
            return [f"user_status_{user_id}" for user_id in user_ids]
        return ["user_status_global"]

    def publish(self, info, user_ids=None):
        """Prepare subscription notification."""
        target_user_id = self["user_id"]
        is_online = self["is_online"]
        last_active = self["last_active"]
        
        # Check if client subscribed to this specific user
        if user_ids and target_user_id not in user_ids:
            return None
            
        return OnUserStatusChange(
            user_id=target_user_id,
            is_online=is_online,
            last_active=last_active
        )

    @classmethod
    def notify_status_change(cls, user_id, is_online, last_active):
        """Notify about user status changes."""
        cls.broadcast(
            group=f"user_status_{user_id}",
            payload={
                "user_id": user_id,
                "is_online": is_online,
                "last_active": last_active
            }
        )
        cls.broadcast(
            group="user_status_global",
            payload={
                "user_id": user_id,
                "is_online": is_online,
                "last_active": last_active
            }
        )

# -------------------------------
# Face Verification Subscription
# -------------------------------
class OnFaceVerificationUpdate(Subscription):
    """Subscription triggers when face verification status changes."""
    
    face_verification = graphene.Field(FaceVerificationNode)
    user_id = graphene.ID()
    is_verified = graphene.Boolean()
    verification_method = graphene.String()

    class Arguments:
        user_id = graphene.ID()

    def subscribe(self, info, user_id=None):
        """Client subscription handler."""
        del info
        if user_id:
            return [f"face_verification_{user_id}"]
        return ["face_verification_admin"]  # Admin channel

    def publish(self, info, user_id=None):
        """Prepare subscription notification."""
        verification_data = self["face_verification"]
        target_user_id = verification_data.user.id
        
        # Users can only subscribe to their own verification updates
        # Or admins can subscribe to all updates
        requesting_user = info.context.user
        if not requesting_user:
            return None
            
        if user_id and str(target_user_id) != user_id:
            return None
            
        # Check if user has admin privileges for global subscription
        if not user_id and not requesting_user.has_role("admin", "administrator"):
            return None
            
        return OnFaceVerificationUpdate(
            face_verification=verification_data,
            user_id=str(target_user_id),
            is_verified=verification_data.is_verified,
            verification_method=verification_data.verification_method
        )

    @classmethod
    def notify_verification_update(cls, face_verification):
        """Notify about face verification updates."""
        user_id = face_verification.user.id
        cls.broadcast(
            group=f"face_verification_{user_id}",
            payload={"face_verification": face_verification}
        )
        cls.broadcast(
            group="face_verification_admin",
            payload={"face_verification": face_verification}
        )

# -------------------------------
# Biometric Device Subscription
# -------------------------------
class OnBiometricDeviceChange(Subscription):
    """Subscription triggers when biometric devices change."""
    
    action = graphene.String()  # 'registered', 'removed', 'trusted_changed'
    device = graphene.Field(BiometricDeviceNode)
    user_id = graphene.ID()

    class Arguments:
        user_id = graphene.ID()

    def subscribe(self, info, user_id=None):
        """Client subscription handler."""
        del info
        if user_id:
            return [f"biometric_devices_{user_id}"]
        return None

    def publish(self, info, user_id=None):
        """Prepare subscription notification."""
        action = self["action"]
        device_data = self["device"]
        target_user_id = device_data.user.user.id
        
        # Users can only subscribe to their own device changes
        requesting_user_id = info.context.user.id if info.context.user else None
        if str(target_user_id) != str(requesting_user_id):
            return None
            
        return OnBiometricDeviceChange(
            action=action,
            device=device_data,
            user_id=str(target_user_id)
        )

    @classmethod
    def notify_device_change(cls, action, device):
        """Notify about biometric device changes."""
        user_id = device.user.user.id
        cls.broadcast(
            group=f"biometric_devices_{user_id}",
            payload={
                "action": action,
                "device": device
            }
        )

# -------------------------------
# Loyalty Points Subscription
# -------------------------------
class OnLoyaltyPointsChange(Subscription):
    """Subscription triggers when loyalty points change."""
    
    user_id = graphene.ID()
    loyalty_points = graphene.Int()
    change_amount = graphene.Int()
    reason = graphene.String()

    class Arguments:
        user_id = graphene.ID()

    def subscribe(self, info, user_id=None):
        """Client subscription handler."""
        del info
        if user_id:
            return [f"loyalty_points_{user_id}"]
        return None

    def publish(self, info, user_id=None):
        """Prepare subscription notification."""
        target_user_id = self["user_id"]
        loyalty_points = self["loyalty_points"]
        change_amount = self["change_amount"]
        reason = self["reason"]
        
        # Users can only subscribe to their own loyalty points
        requesting_user_id = info.context.user.id if info.context.user else None
        if str(target_user_id) != str(requesting_user_id):
            return None
            
        return OnLoyaltyPointsChange(
            user_id=target_user_id,
            loyalty_points=loyalty_points,
            change_amount=change_amount,
            reason=reason
        )

    @classmethod
    def notify_points_change(cls, user_id, loyalty_points, change_amount, reason=""):
        """Notify about loyalty points changes."""
        cls.broadcast(
            group=f"loyalty_points_{user_id}",
            payload={
                "user_id": user_id,
                "loyalty_points": loyalty_points,
                "change_amount": change_amount,
                "reason": reason
            }
        )

# -------------------------------
# Audit Log Subscription (Admin Only)
# -------------------------------
'''class OnAuditLogCreated(Subscription):
    """Subscription triggers when new audit logs are created (admin only)."""
    
    audit_log = graphene.Field(lambda: AuditLogNode)  # You'll need to create this node
    action = graphene.String()
    actor_email = graphene.String()
    target_user_email = graphene.String()

    class Arguments:
        action_filter = graphene.String()

    def subscribe(self, info, action_filter=None):
        """Client subscription handler."""
        # Only allow authenticated users with admin privileges
        user = info.context.user
        if not user or not user.has_role("admin", "administrator"):
            return []
            
        groups = ["audit_logs_admin"]
        if action_filter:
            groups.append(f"audit_logs_{action_filter}")
            
        return groups

    def publish(self, info, action_filter=None):
        """Prepare subscription notification."""
        audit_log_data = self["audit_log"]
        action = audit_log_data.action
        
        # Filter by action if specified
        if action_filter and action != action_filter:
            return None
            
        return OnAuditLogCreated(
            audit_log=audit_log_data,
            action=action,
            actor_email=audit_log_data.actor.email if audit_log_data.actor else None,
            target_user_email=audit_log_data.target_user.email if audit_log_data.target_user else None
        )

    @classmethod
    def notify_audit_log_created(cls, audit_log):
        """Notify about new audit logs."""
        cls.broadcast(
            group="audit_logs_admin",
            payload={"audit_log": audit_log}
        )
        cls.broadcast(
            group=f"audit_logs_{audit_log.action}",
            payload={"audit_log": audit_log}
        )'''

# -------------------------------
# Contact Us Subscription (Admin Only)
# -------------------------------
class OnContactUsSubmitted(Subscription):
    """Subscription triggers when new contact us forms are submitted (admin only)."""
    
    contact_submission = graphene.Field(ContactUsNode)
    name = graphene.String()
    email = graphene.String()
    submitted_at = graphene.DateTime()

    def subscribe(self, info):
        """Client subscription handler."""
        # Only allow authenticated users with admin privileges
        user = info.context.user
        if not user or not user.has_role("admin", "administrator"):
            return []
        return ["contact_us_submissions"]

    def publish(self, info):
        """Prepare subscription notification."""
        submission_data = self["contact_submission"]
        
        return OnContactUsSubmitted(
            contact_submission=submission_data,
            name=submission_data.name,
            email=submission_data.email,
            submitted_at=submission_data.created_at if hasattr(submission_data, 'created_at') else None
        )

    @classmethod
    def notify_contact_submission(cls, contact_submission):
        """Notify about new contact us submissions."""
        cls.broadcast(
            group="contact_us_submissions",
            payload={"contact_submission": contact_submission}
        )

# -------------------------------
# Main Subscription Class
# -------------------------------
class AccountSubscriptions(graphene.ObjectType):
    """GraphQL subscriptions."""
    
    
    on_user_role_change = OnUserRoleChange.Field()
    on_user_profile_update = OnUserProfileUpdate.Field()
    on_user_status_change = OnUserStatusChange.Field()
    on_face_verification_update = OnFaceVerificationUpdate.Field()
    on_biometric_device_change = OnBiometricDeviceChange.Field()
    on_loyalty_points_change = OnLoyaltyPointsChange.Field()
    #on_audit_log_created = OnAuditLogCreated.Field()
    on_contact_us_submitted = OnContactUsSubmitted.Field()