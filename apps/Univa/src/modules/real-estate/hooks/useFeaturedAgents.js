import { useMemo } from "react";

import { FEATURED_AGENTS_QUERY } from "@/modules/real-estate/api/queries";

import useRealEstateQuery from "./useRealEstateQuery";

/* -------------------------------------------------------------------------- */
/* Transform */
/* -------------------------------------------------------------------------- */

function transformAgents(
  agents = []
) {
  return agents.map((agent) => ({
    ...agent,

    id: agent.id,

    name: agent.name,

    avatar:
      agent.avatar ??
      agent.profileImage,

    agency:
      agent.agency,

    email:
      agent.email,

    phone:
      agent.phone,

    location:
      agent.location,

    verified:
      agent.verified ?? false,

    rating:
      agent.rating ?? 0,

    reviews:
      agent.reviews ?? 0,

    propertiesCount:
      agent.propertiesCount ?? 0,
  }));
}

/* -------------------------------------------------------------------------- */
/* Hook */
/* -------------------------------------------------------------------------- */

export default function useFeaturedAgents(
  options = {}
) {
  const {
    variables = {},
    skip = false,
    pollInterval = 0,
  } = options;

  const result = useRealEstateQuery({
    query: FEATURED_AGENTS_QUERY,

    dataKey: "featuredAgents",

    variables,

    skip,

    pollInterval,

    transform:
      transformAgents,
  });

  const featuredAgents =
    useMemo(
      () => result.items,
      [result.items]
    );

  return {
    ...result,

    featuredAgents,
  };
}