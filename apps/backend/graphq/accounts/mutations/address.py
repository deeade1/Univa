# apps/backend/graphq/accounts/mutations/address.py

"""
GraphQL Address Mutations.

Architectural boundary
----------------------

These mutations are GraphQL adapters for the canonical accounts.Address
model.

Address business rules belong to the accounts domain.

This module is responsible for:

    - GraphQL input/output
    - authentication boundary
    - resolving Relay IDs
    - invoking account address operations

The address model itself is country-neutral.

The ``state`` field is therefore free-form and may represent a:

    - state
    - province
    - region
    - territory
    - county
    - prefecture
    - or equivalent first-level administrative division

The country determines the meaning of the value.

This module MUST NOT restrict addresses to Nigerian states.
"""

from __future__ import annotations

from collections.abc import Mapping

import graphene
from django.db import transaction
from graphql import GraphQLError
from graphql_relay import from_global_id
from graphene import Boolean, Field, ID, Int, List, String, relay

from univa_jwt.decorators import login_required

from accounts.models.address import Address
from accounts.models.role import Role

from graphq.accounts.types import AddressNode


# ============================================================================
# CONSTANTS
# ============================================================================

ADDRESS_FIELDS = (
    "street_address_1",
    "street_address_2",
    "city",
    "state",
    "postal_code",
    "address_type",
    "is_default",
    "first_name",
    "last_name",
    "company_name",
)

ADDRESS_TYPE_VALUES = {
    value
    for value, _label in Address.ADDRESS_TYPES
}


# ============================================================================
# HELPERS
# ============================================================================


def _input_value(input_data, field_name, default=None):
    """
    Read a Graphene InputObjectType field or a plain mapping.

    Graphene normally supplies InputObjectType-like objects to mutations,
    while direct unit tests commonly pass dictionaries.

    Supporting both makes the mutation adapter deterministic and keeps
    direct mutation tests useful.
    """

    if isinstance(input_data, Mapping):
        return input_data.get(field_name, default)

    return getattr(
        input_data,
        field_name,
        default,
    )


def _field_supplied(input_data, field_name):
    """
    Determine whether a field was explicitly supplied.
    """

    if isinstance(input_data, Mapping):
        return field_name in input_data

    try:
        return field_name in input_data
    except TypeError:
        return hasattr(input_data, field_name)


def _decode_global_id(global_id, *, expected_type=None):
    """
    Decode a Relay global ID.

    Raises GraphQLError for malformed IDs rather than silently ignoring
    invalid input.
    """

    if not global_id:
        raise GraphQLError("A valid global ID is required.")

    try:
        object_type, object_pk = from_global_id(str(global_id))
    except (TypeError, ValueError):
        raise GraphQLError("Invalid global ID.")

    if not object_type or not object_pk:
        raise GraphQLError("Invalid global ID.")

    if expected_type and object_type != expected_type:
        raise GraphQLError(
            f"Invalid ID type. Expected {expected_type}."
        )

    try:
        return int(object_pk)
    except (TypeError, ValueError):
        raise GraphQLError("Invalid global ID.")


def _normalise_country(country):
    """
    Normalize a country code.

    CountryField expects an ISO 3166-1 alpha-2 country code.
    """

    if country is None:
        return None

    value = str(country).strip().upper()

    if len(value) != 2:
        raise GraphQLError(
            f"Invalid country code: {country}"
        )

    return value


def _normalise_state(state):
    """
    Normalize a country-neutral administrative division.

    No country-specific validation is performed here.
    """

    if state is None:
        return None

    value = str(state).strip()

    if len(value) > 256:
        raise GraphQLError(
            "State/province/region must not exceed 256 characters."
        )

    return value


def _validate_address_type(address_type):
    """
    Validate the canonical Address address_type choices.
    """

    if address_type not in ADDRESS_TYPE_VALUES:
        raise GraphQLError(
            f"Invalid address type: {address_type}"
        )


def _resolve_role_visibility(role_ids):
    """
    Resolve Relay Role IDs.

    Invalid IDs are rejected rather than silently ignored.
    """

    if role_ids is None:
        return None

    resolved_ids = []

    for role_id in role_ids:
        role_pk = _decode_global_id(
            role_id,
            expected_type="Role",
        )
        resolved_ids.append(role_pk)

    roles = list(
        Role.objects.filter(
            pk__in=resolved_ids,
        )
    )

    found_ids = {role.pk for role in roles}

    missing_ids = [
        role_pk
        for role_pk in resolved_ids
        if role_pk not in found_ids
    ]

    if missing_ids:
        raise GraphQLError(
            "One or more roles could not be found."
        )

    return roles


def _get_owned_address(user, global_id):
    """
    Resolve an Address belonging to the authenticated user.
    """

    address_pk = _decode_global_id(
        global_id,
        expected_type="Address",
    )

    try:
        return Address.objects.get(
            pk=address_pk,
            user=user,
        )
    except Address.DoesNotExist:
        raise GraphQLError(
            "Address not found or permission denied"
        )


def _clear_default_for_type(
    *,
    user,
    address_type,
    exclude_pk=None,
):
    """
    Clear the existing default address for a user/address type.
    """

    queryset = Address.objects.filter(
        user=user,
        address_type=address_type,
        is_default=True,
    )

    if exclude_pk is not None:
        queryset = queryset.exclude(
            pk=exclude_pk,
        )

    queryset.update(
        is_default=False,
    )


def _promote_replacement_default(
    *,
    user,
    address_type,
):
    """
    Promote the first remaining address of a type to default.
    """

    replacement = (
        Address.objects
        .filter(
            user=user,
            address_type=address_type,
        )
        .order_by(
            "-updated_at",
            "-pk",
        )
        .first()
    )

    if replacement:
        replacement.is_default = True
        replacement.save(
            update_fields=[
                "is_default",
                "updated_at",
            ],
        )

    return replacement


# ============================================================================
# INPUT TYPES
# ============================================================================


class AddressUpdateInput(graphene.InputObjectType):
    """
    Input for updating an address.
    """

    address_id = graphene.ID(
        required=True,
    )

    street_address_1 = graphene.String()
    street_address_2 = graphene.String()
    city = graphene.String()
    state = graphene.String()
    postal_code = graphene.String()
    country = graphene.String()
    address_type = graphene.String()
    is_default = graphene.Boolean()
    first_name = graphene.String()
    last_name = graphene.String()
    company_name = graphene.String()
    phone = graphene.String()

    role_visibility = graphene.List(
        graphene.ID,
    )


class AddressCreateInput(graphene.InputObjectType):
    """
    Input for creating an address.

    State is intentionally optional because not every address system
    requires a first-level administrative division.
    """

    street_address_1 = graphene.String(
        required=True,
    )

    street_address_2 = graphene.String()

    city = graphene.String(
        required=True,
    )

    state = graphene.String()

    postal_code = graphene.String()

    country = graphene.String(
        required=True,
    )

    address_type = graphene.String(
        required=True,
    )

    is_default = graphene.Boolean(
        default_value=False,
    )

    first_name = graphene.String()
    last_name = graphene.String()
    company_name = graphene.String()
    phone = graphene.String()

    role_visibility = graphene.List(
        graphene.ID,
    )


# ============================================================================
# CREATE
# ============================================================================


class AddressMutation(relay.ClientIDMutation):
    """
    Create a new address for the authenticated user.
    """

    class Input:
        street_address_1 = String(
            required=True,
        )

        street_address_2 = String()

        city = String(
            required=True,
        )

        state = String()

        postal_code = String()

        country = String(
            required=True,
        )

        is_default = Boolean(
            default_value=False,
        )

        address_type = String(
            required=True,
        )

        first_name = String()
        last_name = String()
        company_name = String()
        phone = String()

        role_visibility = List(
            ID,
        )

    address = Field(
        AddressNode,
    )

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        user = info.context.user

        country_code = _normalise_country(
            input.get("country"),
        )

        address_type = input.get(
            "address_type",
            "home",
        )

        _validate_address_type(
            address_type,
        )

        state = _normalise_state(
            input.get("state"),
        )

        role_ids = input.get(
            "role_visibility",
        )

        roles = _resolve_role_visibility(
            role_ids,
        )

        is_default = bool(
            input.get(
                "is_default",
                False,
            )
        )

        if is_default:
            _clear_default_for_type(
                user=user,
                address_type=address_type,
            )

        address = Address.objects.create(
            user=user,
            street_address_1=input.get(
                "street_address_1",
                "",
            ),
            street_address_2=input.get(
                "street_address_2",
                "",
            ),
            city=input.get(
                "city",
                "",
            ),
            state=state or "",
            postal_code=input.get(
                "postal_code",
                "",
            ),
            country=country_code,
            address_type=address_type,
            is_default=is_default,
            first_name=input.get(
                "first_name",
                "",
            ),
            last_name=input.get(
                "last_name",
                "",
            ),
            company_name=input.get(
                "company_name",
                "",
            ),
            phone=input.get(
                "phone",
            ),
        )

        if roles is not None:
            address.role_visibility.set(
                roles,
            )

        return cls(
            address=address,
        )


# ============================================================================
# UPDATE
# ============================================================================


class UpdateAddressMutation(relay.ClientIDMutation):
    """
    Update an existing address owned by the authenticated user.
    """

    class Input:
        address_id = ID(
            required=True,
        )

        street_address_1 = String()
        street_address_2 = String()
        city = String()
        state = String()
        postal_code = String()
        country = String()
        address_type = String()
        is_default = Boolean()
        first_name = String()
        last_name = String()
        company_name = String()
        phone = String()

        role_visibility = List(
            ID,
        )

    address = Field(
        lambda: AddressNode,
    )

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        user = info.context.user

        address = _get_owned_address(
            user,
            input.get("address_id"),
        )

        old_address_type = address.address_type
        old_is_default = address.is_default

        # --------------------------------------------------------------
        # Standard fields
        # --------------------------------------------------------------

        for field in ADDRESS_FIELDS:
            if not _field_supplied(
                input,
                field,
            ):
                continue

            value = _input_value(
                input,
                field,
            )

            if value is None:
                continue

            if field == "state":
                value = _normalise_state(
                    value,
                )

            elif field == "address_type":
                _validate_address_type(
                    value,
                )

            setattr(
                address,
                field,
                value,
            )

        # --------------------------------------------------------------
        # Country
        # --------------------------------------------------------------

        if _field_supplied(
            input,
            "country",
        ):
            country = _input_value(
                input,
                "country",
            )

            if country is not None:
                address.country = _normalise_country(
                    country,
                )

        # --------------------------------------------------------------
        # Phone
        # --------------------------------------------------------------

        if _field_supplied(
            input,
            "phone",
        ):
            address.phone = (
                _input_value(
                    input,
                    "phone",
                )
                or ""
            )

        # --------------------------------------------------------------
        # Default handling
        # --------------------------------------------------------------

        if address.is_default:
            _clear_default_for_type(
                user=user,
                address_type=address.address_type,
                exclude_pk=address.pk,
            )

        address.save()

        # --------------------------------------------------------------
        # If a default address changes type, ensure the old type still
        # has a default address when another address is available.
        # --------------------------------------------------------------

        if (
            old_address_type != address.address_type
            and old_is_default
        ):
            _promote_replacement_default(
                user=user,
                address_type=old_address_type,
            )

        # --------------------------------------------------------------
        # Role visibility
        # --------------------------------------------------------------

        if _field_supplied(
            input,
            "role_visibility",
        ):
            role_ids = _input_value(
                input,
                "role_visibility",
            )

            roles = _resolve_role_visibility(
                role_ids,
            )

            address.role_visibility.set(
                roles or [],
            )

        # --------------------------------------------------------------
        # Metadata cache
        # --------------------------------------------------------------

        if hasattr(
            address,
            "clear_metadata_cache",
        ):
            address.clear_metadata_cache()

        return cls(
            address=address,
        )


# ============================================================================
# DELETE
# ============================================================================


class DeleteAddressMutation(relay.ClientIDMutation):
    """
    Delete a user address.
    """

    class Input:
        address_id = ID(
            required=True,
        )

    success = Boolean()
    deleted_id = ID()

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        user = info.context.user

        address = _get_owned_address(
            user,
            input.get("address_id"),
        )

        address_type = address.address_type
        was_default = address.is_default
        address_id = str(address.pk)

        # Django's deletion collector handles the actual deletion and
        # related objects.
        address.delete()

        if was_default:
            _promote_replacement_default(
                user=user,
                address_type=address_type,
            )

        return cls(
            success=True,
            deleted_id=address_id,
        )


# ============================================================================
# SET DEFAULT
# ============================================================================


class SetDefaultAddressMutation(relay.ClientIDMutation):
    """
    Set an address as the default for its address type.
    """

    class Input:
        address_id = ID(
            required=True,
        )

    address = Field(
        lambda: AddressNode,
    )

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        user = info.context.user

        address = _get_owned_address(
            user,
            input.get("address_id"),
        )

        _clear_default_for_type(
            user=user,
            address_type=address.address_type,
            exclude_pk=address.pk,
        )

        address.is_default = True

        address.save(
            update_fields=[
                "is_default",
                "updated_at",
            ],
        )

        return cls(
            address=address,
        )


# ============================================================================
# BULK UPDATE
# ============================================================================


class BulkUpdateAddressesMutation(relay.ClientIDMutation):
    """
    Update multiple addresses atomically.

    Both Graphene InputObjectType instances and plain dictionaries are
    supported because direct mutation tests commonly use dictionaries.
    """

    class Input:
        updates = List(
            AddressUpdateInput,
            required=True,
        )

    addresses = List(
        lambda: AddressNode,
    )

    updated_count = Int()

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(
        cls,
        root,
        info,
        **input,
    ):
        user = info.context.user

        updates = input.get(
            "updates",
            [],
        )

        updated_addresses = []

        for update in updates:
            address = _get_owned_address(
                user,
                _input_value(
                    update,
                    "address_id",
                ),
            )

            old_address_type = address.address_type
            old_is_default = address.is_default

            # ----------------------------------------------------------
            # Standard fields
            # ----------------------------------------------------------

            for field in ADDRESS_FIELDS:
                if not _field_supplied(
                    update,
                    field,
                ):
                    continue

                value = _input_value(
                    update,
                    field,
                )

                if value is None:
                    continue

                if field == "state":
                    value = _normalise_state(
                        value,
                    )

                elif field == "address_type":
                    _validate_address_type(
                        value,
                    )

                setattr(
                    address,
                    field,
                    value,
                )

            # ----------------------------------------------------------
            # Country
            # ----------------------------------------------------------

            if _field_supplied(
                update,
                "country",
            ):
                country = _input_value(
                    update,
                    "country",
                )

                if country is not None:
                    address.country = _normalise_country(
                        country,
                    )

            # ----------------------------------------------------------
            # Phone
            # ----------------------------------------------------------

            if _field_supplied(
                update,
                "phone",
            ):
                address.phone = (
                    _input_value(
                        update,
                        "phone",
                    )
                    or ""
                )

            # ----------------------------------------------------------
            # Default handling
            # ----------------------------------------------------------

            if address.is_default:
                _clear_default_for_type(
                    user=user,
                    address_type=address.address_type,
                    exclude_pk=address.pk,
                )

            address.save()

            # ----------------------------------------------------------
            # Address type changed while default
            # ----------------------------------------------------------

            if (
                old_address_type != address.address_type
                and old_is_default
            ):
                _promote_replacement_default(
                    user=user,
                    address_type=old_address_type,
                )

            # ----------------------------------------------------------
            # Role visibility
            # ----------------------------------------------------------

            if _field_supplied(
                update,
                "role_visibility",
            ):
                role_ids = _input_value(
                    update,
                    "role_visibility",
                )

                roles = _resolve_role_visibility(
                    role_ids,
                )

                address.role_visibility.set(
                    roles or [],
                )

            # ----------------------------------------------------------
            # Metadata cache
            # ----------------------------------------------------------

            if hasattr(
                address,
                "clear_metadata_cache",
            ):
                address.clear_metadata_cache()

            updated_addresses.append(
                address,
            )

        return cls(
            addresses=updated_addresses,
            updated_count=len(
                updated_addresses,
            ),
        )


# ============================================================================
# REGISTRATION
# ============================================================================


class AddressMutations(graphene.ObjectType):
    """
    All address-related mutations.
    """

    create_address = AddressMutation.Field()

    update_address = UpdateAddressMutation.Field()

    delete_address = DeleteAddressMutation.Field()

    set_default_address = SetDefaultAddressMutation.Field()

    bulk_update_addresses = (
        BulkUpdateAddressesMutation.Field()
    )
