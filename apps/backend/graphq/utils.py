from graphql import GraphQLError
from graphql_relay import from_global_id


def get_node_instance(
    global_id,
    *,
    node_type,
    model,
    invalid_id_message="Invalid ID.",
    not_found_message="Object not found.",
):
    """
    Resolve a Relay global ID to a Django model instance.

    Args:
        global_id: Relay global ID supplied by the client.
        node_type: Graphene node class expected for this ID.
        model: Django model class to retrieve.
        invalid_id_message: Error for malformed IDs or wrong node types.
        not_found_message: Error when the referenced object does not exist.

    Returns:
        An instance of the requested Django model.

    Raises:
        GraphQLError: If the ID is invalid or the object does not exist.
    """
    try:
        type_name, object_id = from_global_id(global_id)

        if not type_name or not object_id:
            raise GraphQLError(invalid_id_message)

        if type_name != node_type._meta.name:
            raise GraphQLError(invalid_id_message)

        return model.objects.get(pk=object_id)

    except GraphQLError:
        raise
    except (ValueError, TypeError, model.DoesNotExist):
        raise GraphQLError(not_found_message)
