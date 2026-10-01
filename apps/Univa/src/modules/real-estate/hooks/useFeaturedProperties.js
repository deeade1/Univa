import { useMemo } from "react";

import { FEATURED_PROPERTIES_QUERY } from "@/modules/real-estate/api/queries";

import useRealEstateQuery from "./useRealEstateQuery";

/* -------------------------------------------------------------------------- */
/* Transform */
/* -------------------------------------------------------------------------- */

function transformFeaturedProperties(properties = []) {
  return properties.map((property) => ({
    ...property,

    id: property.id,
    title: property.title,
    slug: property.slug,

    price: property.price,

    address:
      property.address ??
      property.location ??
      "",

    latitude: property.latitude,
    longitude: property.longitude,

    bedrooms:
      property.bedrooms ?? 0,

    bathrooms:
      property.bathrooms ?? 0,

    area:
      property.area ?? 0,

    featured:
      property.featured ?? true,

    verified:
      property.verified ?? false,

    thumbnail:
      property.thumbnail ??
      property.image ??
      property.coverImage,

    images:
      property.images ?? [],
  }));
}

/* -------------------------------------------------------------------------- */
/* useFeaturedProperties */
/* -------------------------------------------------------------------------- */

export default function useFeaturedProperties(
  options = {}
) {
  const {
    variables = {},
    skip = false,
    pollInterval = 0,
  } = options;

  const result = useRealEstateQuery({
    query: FEATURED_PROPERTIES_QUERY,

    dataKey: "featuredProperties",

    variables,

    skip,

    pollInterval,

    transform:
      transformFeaturedProperties,
  });

  const featuredProperties =
    useMemo(
      () => result.items,
      [result.items]
    );

  return {
    ...result,

    featuredProperties,
  };
}