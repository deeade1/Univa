import { useMemo } from "react";

import { POPULAR_LOCATIONS_QUERY } from "@/modules/real-estate/api/queries";

import useRealEstateQuery from "./useRealEstateQuery";

/* -------------------------------------------------------------------------- */
/* Transform */
/* -------------------------------------------------------------------------- */

function transformLocations(locations = []) {
  return locations.map((location) => ({
    ...location,

    id: location.id,

    name: location.name,

    city: location.city,

    state: location.state,

    country: location.country,

    image:
      location.image ??
      location.thumbnail ??
      null,

    propertyCount:
      location.propertyCount ??
      0,

    latitude: location.latitude,

    longitude: location.longitude,
  }));
}

/* -------------------------------------------------------------------------- */
/* Hook */
/* -------------------------------------------------------------------------- */

export default function usePopularLocations(
  options = {}
) {
  const {
    variables = {},
    skip = false,
    pollInterval = 0,
  } = options;

  const result = useRealEstateQuery({
    query: POPULAR_LOCATIONS_QUERY,

    dataKey: "popularLocations",

    variables,

    skip,

    pollInterval,

    transform: transformLocations,
  });

  const popularLocations =
    useMemo(
      () => result.items,
      [result.items]
    );

  return {
    ...result,

    popularLocations,
  };
}