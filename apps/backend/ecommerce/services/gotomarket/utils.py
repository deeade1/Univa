# market/utils.py
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

SIGNER_SALT = "receipt-pdf"

def sign_payload(payload: str) -> str:
    signer = TimestampSigner(salt=SIGNER_SALT)
    return signer.sign(payload)

def unsign_payload(token: str, max_age_seconds: int = 600) -> str:
    signer = TimestampSigner(salt=SIGNER_SALT)
    return signer.unsign(token, max_age=max_age_seconds)
