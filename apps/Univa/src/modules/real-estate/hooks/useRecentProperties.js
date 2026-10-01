import { useMemo } from "react";

import { RECENT_PROPERTIES_QUERY } from "@/modules/real-estate/api/queries";

import useRealEstateQuery from "./useRealEstateQuery";

/* -------------------------------------------------------------------------- */
/* Transform */
/* -------------------------------------------------------------------------- */

function transformRecentProperties(
  properties = []
) {
  return properties.map((property) => ({
    ...property,

    id: property.id,

    title: property.title,

    slug: property.slug,

    thumbnail:
      property.thumbnail ??
      property.image ??
      property.coverImage,

    images:
      property.images ?? [],

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

    price:
      property.price,

    createdAt:
      property.createdAt,

    featured:
      property.featured ?? false,

    verified:
      property.verified ?? false,
  }));
}

/* -------------------------------------------------------------------------- */
/* Hook */
/* -------------------------------------------------------------------------- */

export default function useRecentProperties(
  options = {}
) {
  const {
    variables = {},
    skip = false,
    pollInterval = 0,
  } = options;

  const result = useRealEstateQuery({
    query: RECENT_PROPERTIES_QUERY,

    dataKey: "recentProperties",

    variables,

    skip,

    pollInterval,

    transform:
      transformRecentProperties,
  });

  const recentProperties =
    useMemo(
      () => result.items,
      [result.items]
    );

  return {
    ...result,

    recentProperties,
  };
}