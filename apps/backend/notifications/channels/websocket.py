# apps/backend/notifications/channels/websocket.py

"""
WebSocket notification channel for Univa.

This module provides real-time WebSocket delivery using Django Channels.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class WebSocketChannel:
    """WebSocket notification channel using Django Channels."""
    
    def __init__(self):
        self.channel_layer = None
        self.group_prefix = getattr(
            settings,
            "WEBSOCKET_NOTIFICATION_GROUP_PREFIX",
            "user"
        )
        self.group_suffix = getattr(
            settings,
            "WEBSOCKET_NOTIFICATION_GROUP_SUFFIX",
            "notifications"
        )
        self._initialize_channel_layer()
    
    def _initialize_channel_layer(self):
        """Initialize Django Channels layer."""
        try:
            from channels.layers import get_channel_layer
            self.channel_layer = get_channel_layer()
            logger.debug("WebSocket channel layer initialized")
        except ImportError:
            logger.debug("Django Channels not installed")
            self.channel_layer = None
        except Exception as exc:
            logger.warning("Failed to initialize channel layer: %s", exc)
            self.channel_layer = None
    
    def send_notification(self, notification) -> dict[str, Any]:
        """Send notification via WebSocket."""
        if not self.channel_layer:
            return {
                "success": False,
                "error": "Django Channels not configured",
                "status": "channel_not_configured",
            }
        
        try:
            # Check for duplicates
            if self._is_duplicate(notification.recipient_id, notification.pk):
                return {
                    "success": True,
                    "status": "duplicate_skipped",
                    "notification_id": notification.pk,
                    "recipient_id": notification.recipient_id,
                }
            
            # Build payload
            payload = self._build_payload(notification)
            
            # Get user's WebSocket group
            group_name = self._get_group_name(notification.recipient_id)
            
            # Send to channel layer
            from asgiref.sync import async_to_sync
            
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    "type": "notification.message",
                    "data": payload,
                }
            )
            
            logger.debug(
                "WebSocket notification sent: notification=%s user=%s",
                notification.pk,
                notification.recipient_id
            )
            
            return {
                "success": True,
                "status": "sent",
                "notification_id": notification.pk,
                "recipient_id": notification.recipient_id,
                "channel": "websocket",
            }
            
        except Exception as exc:
            logger.exception(
                "WebSocket notification failed: notification=%s",
                notification.pk
            )
            return {
                "success": False,
                "error": str(exc),
                "status": "failed",
                "notification_id": notification.pk,
                "recipient_id": notification.recipient_id,
            }
    
    def _build_payload(self, notification) -> dict[str, Any]:
        """Build WebSocket payload."""
        return {
            "id": notification.pk,
            "type": "notification",
            "notification_type": notification.notification_type,
            "priority": notification.priority,
            "module": notification.module,
            "title": notification.title,
            "message": notification.message,
            "action_url": notification.action_url,
            "metadata": notification.metadata or {},
            "is_read": notification.is_read,
            "is_archived": notification.is_archived,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "received_at": timezone.now().isoformat(),
        }
    
    def _get_group_name(self, user_id: int) -> str:
        """Get WebSocket group name for a user."""
        return f"{self.group_prefix}_{user_id}_{self.group_suffix}"
    
    def _is_duplicate(self, user_id: int, notification_id: int) -> bool:
        """Check if notification has already been sent via WebSocket."""
        key = f"websocket_sent:{user_id}:{notification_id}"
        if cache.get(key):
            return True
        
        cache.set(key, "sent", 60)
        return False


__all__ = ["WebSocketChannel"]