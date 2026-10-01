import json

class CustomJsonEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for handling Django-specific types.
    Replaces the removed core.utils.json_serializer.CustomJsonEncoder.
    """
    def default(self, obj):
        # Handle Decimal
        if isinstance(obj, Decimal):
            return str(obj)
        # Handle datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Handle UUID
        if hasattr(obj, 'hex'):
            return str(obj)
        # Handle Django models
        if hasattr(obj, 'pk') and hasattr(obj, '_meta'):
            return {
                'id': str(obj.pk),
                'str': str(obj)
            }
        return super().default(obj)

