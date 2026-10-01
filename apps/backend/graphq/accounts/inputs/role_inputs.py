import graphene


class UserRoleInput(graphene.InputObjectType):
    """
    Reusable role-assignment input.

    Used by account mutations that need to assign
    an existing role to a user.
    """

    role_name = graphene.String(
        required=True,
        description="Role name.",
    )

    app_name = graphene.String(
        required=True,
        description="Application that owns the role.",
    )

    is_active = graphene.Boolean(
        default_value=True,
        description="Whether the assigned role is active.",
    ) 

    expires_at = graphene.DateTime(
        required=False,
        description="Optional role expiration timestamp.",
    )