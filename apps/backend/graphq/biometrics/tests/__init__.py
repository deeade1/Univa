"""
GraphQL Biometrics Tests
"""

from .test_biometrics_mutations import *

__all__ = [
    'BiometricsMutationBaseTest',
    'RegisterFaceMutationTest',
    'VerifyFaceMutationTest',
    'AuthenticateWithFaceMutationTest',
    'VerifyFaceForMagicLinkMutationTest',
    'CompareFacesMutationTest',
    'VerifyLivenessMutationTest',
    'RegisterBiometricDeviceMutationTest',
    'BiometricAuthMutationTest',
    'SetPinMutationTest',
    'VerifyPinMutationTest',
    'PinLoginMutationTest',
    'FaceVerificationStatusMutationTest',
    'BiometricsGraphQLIntegrationTest',
]