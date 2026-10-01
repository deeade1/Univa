import { useMemo } from "react";

import { NEARBY_PROPERTIES_QUERY } from "@/modules/real-estate/api/queries";

import useRealEstateQuery from "./useRealEstateQuery";

/* -------------------------------------------------------------------------- */
/* Transform */
/* -------------------------------------------------------------------------- */

function transformNearbyProperties(
  properties = []
) {
  return properties.map((property) => ({
    ...property,

    id: property.id,
    title: property.title,
    slug: property.slug,

    price: property.price,

    thumbnail:
      property.thumbnail ??
      property.image ??
      property.coverImage,

    images: property.images ?? [],

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

    distance:
      property.distance ?? 0,

    distanceUnit:
      property.distanceUnit ?? "km",

    featured:
      property.featured ?? false,

    verified:
      property.verified ?? false,
  }));
}

/* -------------------------------------------------------------------------- */
/* Hook */
/* -------------------------------------------------------------------------- */

export default function useNearbyProperties(
  options = {}
) {
  const {
    latitude,
    longitude,
    radius = 10,

    variables = {},

    skip = false,

    pollInterval = 0,
  } = options;

  const result = useRealEstateQuery({
    query: NEARBY_PROPERTIES_QUERY,

    dataKey: "nearbyProperties",

    variables: {
      latitude,
      longitude,
      radius,
      ...variables,
    },

    skip,

    pollInterval,

    transform:
      transformNearbyProperties,
  });

  const nearbyProperties =
    useMemo(
      () => result.items,
      [result.items]
    );

  return {
    ...result,

    nearbyProperties,
  };
}