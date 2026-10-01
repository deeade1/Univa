import { useMemo } from "react";

import { RECOMMENDED_PROPERTIES_QUERY } from "@/modules/real-estate/api/queries";

import useRealEstateQuery from "./useRealEstateQuery";

/* -------------------------------------------------------------------------- */
/* Transform */
/* -------------------------------------------------------------------------- */

function transformRecommendedProperties(
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

    rating:
      property.rating ?? 0,

    reviews:
      property.reviews ?? 0,

    featured:
      property.featured ?? false,

    verified:
      property.verified ?? false,
  }));
}

/* -------------------------------------------------------------------------- */
/* Hook */
/* -------------------------------------------------------------------------- */

export default function useRecommendedProperties(
  options = {}
) {
  const {
    variables = {},
    skip = false,
    pollInterval = 0,
  } = options;

  const result = useRealEstateQuery({
    query: RECOMMENDED_PROPERTIES_QUERY,

    dataKey: "recommendedProperties",

    variables,

    skip,

    pollInterval,

    transform:
      transformRecommendedProperties,
  });

  const recommendedProperties =
    useMemo(
      () => result.items,
      [result.items]
    );

  return {
    ...result,

    recommendedProperties,
  };
}