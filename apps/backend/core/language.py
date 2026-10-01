# apps/backend/core/middleware/language.py
from django.conf import settings
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin


class LanguageMiddleware(MiddlewareMixin):
    """Custom language middleware supporting app headers"""
    
    def process_request(self, request):
        # Check for language in headers (for mobile apps)
        app_language = request.META.get('HTTP_X_APP_LANGUAGE')
        if app_language and app_language in dict(settings.LANGUAGES):
            translation.activate(app_language)
            request.LANGUAGE_CODE = app_language
        else:
            # Fall back to Django's default language detection
            translation.activate(settings.LANGUAGE_CODE)

# apps/backend/transport/models/multilingual.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from modeltranslation.translator import TranslationOptions, translator


class MultilingualService(models.Model):
    """Base model for multilingual content"""
    
    class Meta:
        abstract = True

class ServiceTypeTranslation(TranslationOptions):
    fields = ('name', 'description')

class VehicleTypeTranslation(TranslationOptions):
    fields = ('name', 'description')

# Register translations
translator.register(ServiceType, ServiceTypeTranslation)
translator.register(VehicleType, VehicleTypeTranslation)

from django.conf import settings
# apps/backend/transport/services/notification_i18n.py
from django.utils import translation


class I18nNotificationService:
    """Internationalized notification service"""
    
    SUPPORTED_LANGUAGES = ['en', 'es', 'fr', 'de', 'pt', 'ar', 'zh']
    
    def __init__(self):
        self.templates = self.load_notification_templates()
    
    def load_notification_templates(self):
        """Load notification templates for all supported languages"""
        templates = {}
        
        for lang in self.SUPPORTED_LANGUAGES:
            templates[lang] = {
                'ride_assigned': {
                    'push_title': self._translate(lang, 'Your ride is on the way!'),
                    'push_body': self._translate(lang, 'Driver {driver_name} is coming to pick you up. ETA: {eta}'),
                    'sms': self._translate(lang, 'Your ride is confirmed. Driver: {driver_name}, Vehicle: {vehicle_info}')
                },
                'ride_completed': {
                    'push_title': self._translate(lang, 'Ride completed'),
                    'push_body': self._translate(lang, 'Thank you for riding with us. Fare: {fare}'),
                    'sms': self._translate(lang, 'Ride completed. Amount: {fare}. Thank you!')
                },
                # Add more template types...
            }
        
        return templates
    
    def _translate(self, lang, text):
        """Simple translation helper - in production, use Django's translation system"""
        # This would integrate with your translation backend
        return text  # Placeholder
    
    def send_notification(self, user, notification_type, context, preferred_language=None):
        """Send notification in user's preferred language"""
        lang = preferred_language or user.preferred_language or 'en'
        
        if lang not in self.SUPPORTED_LANGUAGES:
            lang = 'en'  # Fallback to English
        
        template = self.templates[lang].get(notification_type, {})
        
        # Format message with context
        message = template.get('push_body', '').format(**context)
        title = template.get('push_title', '').format(**context)
        
        # Send notification (integrate with your notification system)
        self._send_push_notification(user, title, message, lang)
        
        return True