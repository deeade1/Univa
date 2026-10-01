import requests
from django.conf import settings

class BVNService:
    """Handles BVN lookup, validation, and verification via supported providers."""

    @staticmethod
    def verify_bvn(bvn: str):
        if settings.BVN_PROVIDER == "verifyme":
            return BVNService._verify_with_verifyme(bvn)
        elif settings.BVN_PROVIDER == "prembly":
            return BVNService._verify_with_prembly(bvn)
        elif settings.BVN_PROVIDER == "nibss":
            return BVNService._verify_with_nibss(bvn)
        else:
            raise ValueError("Unsupported BVN provider")

    @staticmethod
    def _verify_with_verifyme(bvn: str):
        url = "https://api.verifyme.ng/v1/verifications/identities/bvn"
        headers = {"Authorization": f"Bearer {settings.VERIFYME_API_KEY}"}
        payload = {"number": bvn}

        res = requests.post(url, json=payload, headers=headers, timeout=20)
        res.raise_for_status()

        data = res.json()
        return {
            "valid": data.get("status") == "success",
            "first_name": data["data"].get("firstName"),
            "last_name": data["data"].get("lastName"),
            "dob": data["data"].get("dateOfBirth"),
            "phone": data["data"].get("phone"),
        }

    @staticmethod
    def _verify_with_prembly(bvn: str):
        url = "https://api.prembly.com/identity/bvn/verify"
        headers = {"x-api-key": settings.PREMBLY_KEY}

        res = requests.post(url, json={"bvn": bvn}, headers=headers, timeout=20)
        res.raise_for_status()
        data = res.json()

        return {
            "valid": data["success"],
            "full_name": data["data"]["fullName"],
            "dob": data["data"]["birthDate"]
        }

    @staticmethod
    def _verify_with_nibss(bvn: str):
        # NIBSS sandbox pattern (production is HSM-encrypted)
        url = settings.NIBSS_URL + "/bvn/verify"
        headers = {"APIKEY": settings.NIBSS_KEY}

        res = requests.post(url, json={"bvn": bvn}, headers=headers, timeout=20)
        res.raise_for_status()
        data = res.json()

        return {
            "valid": data.get("responseCode") == "00",
            "full_name": data.get("fullName"),
        }
