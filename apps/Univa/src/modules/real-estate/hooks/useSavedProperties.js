import {
  useCallback,
  useMemo,
} from "react";

import {
  useMutation,
} from "@apollo/client";

import {
  SAVED_PROPERTIES_QUERY,
} from "@/modules/real-estate/api/queries";

import {
  SAVE_PROPERTY_MUTATION,
  UNSAVE_PROPERTY_MUTATION,
} from "@/modules/real-estate/api/mutations";

import useRealEstateQuery from "./useRealEstateQuery";

/* -------------------------------------------------------------------------- */
/* Hook */
/* -------------------------------------------------------------------------- */

export default function useSavedProperties(
  options = {}
) {
  const {
    variables = {},
    skip = false,
  } = options;

  const result = useRealEstateQuery({
    query: SAVED_PROPERTIES_QUERY,

    dataKey: "savedProperties",

    variables,

    skip,
  });

  const [saveMutation] =
    useMutation(
      SAVE_PROPERTY_MUTATION
    );

  const [removeMutation] =
    useMutation(
      UNSAVE_PROPERTY_MUTATION
    );

  /* ---------------------------------------------------------------------- */
  /* Save */
  /* ---------------------------------------------------------------------- */

  const saveProperty =
    useCallback(
      async (propertyId) => {
        await saveMutation({
          variables: {
            propertyId,
          },
        });

        await result.refresh();
      },
      [
        saveMutation,
        result,
      ]
    );

  /* ---------------------------------------------------------------------- */
  /* Remove */
  /* ---------------------------------------------------------------------- */

  const removeProperty =
    useCallback(
      async (propertyId) => {
        await removeMutation({
          variables: {
            propertyId,
          },
        });

        await result.refresh();
      },
      [
        removeMutation,
        result,
      ]
    );

  /* ---------------------------------------------------------------------- */
  /* Exists */
  /* ---------------------------------------------------------------------- */

  const isSaved =
    useCallback(
      (propertyId) =>
        result.items.some(
          (property) =>
            property.id ===
            propertyId
        ),
      [result.items]
    );

  const toggleSaved =
    useCallback(
      async (propertyId) => {
        if (
          isSaved(propertyId)
        ) {
          return removeProperty(
            propertyId
          );
        }

        return saveProperty(
          propertyId
        );
      },
      [
        isSaved,
        removeProperty,
        saveProperty,
      ]
    );

  const savedProperties =
    useMemo(
      () => result.items,
      [result.items]
    );

  return {
    ...result,

    savedProperties,

    saveProperty,

    removeProperty,

    toggleSaved,

    isSaved,
  };
}