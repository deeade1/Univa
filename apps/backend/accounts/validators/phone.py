from .validators import validate_possible_number
from phonenumber_field.modelfields import PhoneNumberField

class PossiblePhoneNumberField(PhoneNumberField):
    """Less strict field for phone numbers written to database."""
    default_validators = [validate_possible_number]
