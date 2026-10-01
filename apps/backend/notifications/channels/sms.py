# apps/backend/notifications/channels/sms.py

"""
SMS notification channel for Univa.

This module provides SMS delivery routing to various providers:
    - Twilio
    - Africa's Talking
    - Termii
    - Vonage (future)
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SMSChannel:
    """SMS notification channel with provider routing."""
    
    def __init__(self):
        self.provider = getattr(settings, "SMS_PROVIDER", "").lower()
        self.client = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize provider client."""
        if not self.provider:
            return
        
        if self.provider == "twilio":
            self._init_twilio()
        elif self.provider == "termii":
            self._init_termii()
        elif self.provider == "africastalking":
            self._init_africastalking()
        else:
            logger.warning("Unsupported SMS provider: %s", self.provider)
    
    def _init_twilio(self):
        """Initialize Twilio client."""
        try:
            from twilio.rest import Client
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.from_number = settings.TWILIO_PHONE_NUMBER
            self.provider_type = "twilio"
        except (ImportError, AttributeError) as e:
            logger.warning("Twilio library not installed or misconfigured: %s", e)
            self.client = None
    
    def _init_termii(self):
        """Initialize Termii client."""
        try:
            self.api_key = settings.TERMII_API_KEY
            self.sender_id = settings.TERMII_SENDER_ID
            self.base_url = getattr(settings, "TERMII_BASE_URL", "https://api.termii.com/api")
            self.provider_type = "termii"
        except (ImportError, AttributeError) as e:
            logger.warning("Termii not configured: %s", e)
            self.api_key = None
    
    def _init_africastalking(self):
        """Initialize Africa's Talking client."""
        try:
            from africastalking import initialize, SMS
            initialize(
                username=settings.AFRICASTALKING_USERNAME,
                api_key=settings.AFRICASTALKING_API_KEY
            )
            self.sms = SMS
            self.provider_type = "africastalking"
        except (ImportError, AttributeError) as e:
            logger.warning("Africa's Talking not configured: %s", e)
            self.sms = None
    
    def send_to_recipient(
        self,
        *,
        notification,
        phone_number: str,
    ) -> dict[str, Any]:
        """Send SMS via configured provider."""
        # Check rate limit
        if not self._check_rate_limit(phone_number):
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "permanent": False,
                "retry_after": 3600,
            }
        
        # Validate provider
        if not self.provider:
            return {
                "success": False,
                "error": "No SMS provider configured",
                "permanent": True,
            }
        
        # Route to provider
        if self.provider == "twilio":
            return self._send_via_twilio(notification, phone_number)
        elif self.provider == "termii":
            return self._send_via_termii(notification, phone_number)
        elif self.provider == "africastalking":
            return self._send_via_africastalking(notification, phone_number)
        else:
            return {
                "success": False,
                "error": f"Unsupported SMS provider: {self.provider}",
                "permanent": True,
            }
    
    def _send_via_twilio(self, notification, phone_number: str) -> dict[str, Any]:
        """Send SMS via Twilio."""
        if not self.client:
            return {
                "success": False,
                "error": "Twilio client not initialized",
                "permanent": True,
            }
        
        try:
            message = self.client.messages.create(
                body=self._build_message(notification),
                from_=self.from_number,
                to=phone_number,
            )
            
            return {
                "success": True,
                "provider": "twilio",
                "message_id": message.sid,
                "status": message.status,
            }
        except Exception as exc:
            logger.exception("Twilio SMS failed: %s", exc)
            error_str = str(exc).lower()
            return {
                "success": False,
                "error": str(exc),
                "permanent": "invalid" in error_str or "not found" in error_str,
            }
    
    def _send_via_termii(self, notification, phone_number: str) -> dict[str, Any]:
        """Send SMS via Termii."""
        if not hasattr(self, 'api_key') or not self.api_key:
            return {
                "success": False,
                "error": "Termii API key not configured",
                "permanent": True,
            }
        
        try:
            import requests
            
            url = f"{self.base_url}/sms/send"
            payload = {
                "to": phone_number,
                "from": self.sender_id,
                "sms": self._build_message(notification),
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }
            
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            
            if data.get("status") == "success":
                return {
                    "success": True,
                    "provider": "termii",
                    "message_id": data.get("message_id", ""),
                }
            else:
                error_msg = data.get("message", "Termii delivery failed")
                return {
                    "success": False,
                    "error": error_msg,
                    "permanent": "balance" in str(data).lower(),
                }
        except Exception as exc:
            logger.exception("Termii SMS failed: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "permanent": False,
            }
    
    def _send_via_africastalking(self, notification, phone_number: str) -> dict[str, Any]:
        """Send SMS via Africa's Talking."""
        if not hasattr(self, 'sms') or not self.sms:
            return {
                "success": False,
                "error": "Africa's Talking not initialized",
                "permanent": True,
            }
        
        try:
            response = self.sms.send(
                self._build_message(notification),
                [phone_number],
                sender_id=getattr(settings, "AFRICASTALKING_SENDER_ID", None)
            )
            
            if response.get("status") == "success":
                return {
                    "success": True,
                    "provider": "africastalking",
                    "message_id": response.get("message_id", ""),
                }
            else:
                error_msg = response.get("message", "Africa's Talking delivery failed")
                return {
                    "success": False,
                    "error": error_msg,
                    "permanent": "failed" in str(response).lower(),
                }
        except Exception as exc:
            logger.exception("Africa's Talking SMS failed: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "permanent": False,
            }
    
    def _build_message(self, notification) -> str:
        """Build SMS message with length limits."""
        parts = []
        if notification.title:
            parts.append(notification.title)
        if notification.message:
            parts.append(notification.message)
        if notification.action_url:
            parts.append(notification.action_url)
        
        message = "\n\n".join(p for p in parts if p)
        
        # Truncate to 160 characters (SMS limit)
        if len(message) > 160:
            truncated = message[:157]
            last_period = truncated.rfind('.')
            if last_period > 80:
                message = truncated[:last_period + 1] + "..."
            else:
                message = truncated + "..."
        
        return message
    
    def _check_rate_limit(self, phone_number: str) -> bool:
        """Check SMS rate limit per phone number."""
        key = f"sms_rate_limit:{phone_number}"
        count = cache.get(key, 0)
        
        limit = getattr(settings, "SMS_RATE_LIMIT", 10)
        if count >= limit:
            logger.warning("SMS rate limit exceeded for %s", phone_number)
            return False
        
        cache.set(key, count + 1, 3600)
        return True


__all__ = ["SMSChannel"]