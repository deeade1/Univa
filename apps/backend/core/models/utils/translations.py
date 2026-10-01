# core/utils/translations.py
"""
Base translation model for multilingual support.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Translation(models.Model):
    """
    Abstract base model for translations.
    """
    
    language_code = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Language code (e.g., 'en', 'fr', 'es')"
    )
    
    class Meta:
        abstract = True
        ordering = ("language_code",)
    
    def get_translated_object_id(self):
        """Return the object type and ID for the translated object."""
        raise NotImplementedError("Subclasses must implement get_translated_object_id")
    
    def get_translated_keys(self):
        """Return the translated fields as a dictionary."""
        raise NotImplementedError("Subclasses must implement get_translated_keys")