import { useMemo } from "react";

import { PROPERTY_CATEGORIES_QUERY } from "@/modules/real-estate/api/queries";

import useRealEstateQuery from "./useRealEstateQuery";

/* -------------------------------------------------------------------------- */
/* Transform */
/* -------------------------------------------------------------------------- */

function transformCategories(
  categories = []
) {
  return categories.map((category) => ({
    ...category,

    id: category.id,

    name: category.name,

    slug: category.slug,

    icon:
      category.icon,

    image:
      category.image,

    color:
      category.color,

    propertyCount:
      category.propertyCount ?? 0,
  }));
}

/* -------------------------------------------------------------------------- */
/* Hook */
/* -------------------------------------------------------------------------- */

export default function usePropertyCategories(
  options = {}
) {
  const {
    variables = {},
    skip = false,
    pollInterval = 0,
  } = options;

  const result = useRealEstateQuery({
    query: PROPERTY_CATEGORIES_QUERY,

    dataKey: "propertyCategories",

    variables,

    skip,

    pollInterval,

    transform:
      transformCategories,
  });

  const propertyCategories =
    useMemo(
      () => result.items,
      [result.items]
    );

  return {
    ...result,

    propertyCategories,
  };
}