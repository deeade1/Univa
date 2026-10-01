import graphene
from graphq.accounts.mutations.email import EmailMutations
from graphq.accounts.mutations.user import UserMutations
from graphq.accounts.mutations.auth import AuthenticationMutations
from graphq.accounts.mutations.address import AddressMutations
from graphq.accounts.mutations.profile import   UserProfileMutations
from graphq.accounts.mutations.role import RoleMutations

class AccountMutations(
    UserMutations,
    EmailMutations,
    AuthenticationMutations,
    AddressMutations,
    UserProfileMutations,
    RoleMutations,
    # Other account mutation groups...
    graphene.ObjectType,
):
    """
    Account-domain GraphQL mutations.

    Composition only.
    """
    pass






