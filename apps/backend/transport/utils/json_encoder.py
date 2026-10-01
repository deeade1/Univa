# transport/utils/json_encoder.py
import json
from decimal import Decimal
from datetime import datetime, date
from django.core.serializers.json import DjangoJSONEncoder

class TransportJSONEncoder(DjangoJSONEncoder):
    """Custom JSON encoder for Transport models"""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(str(obj))
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)