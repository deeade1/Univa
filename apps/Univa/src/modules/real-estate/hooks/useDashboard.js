import { useCallback } from "react";

import useFeaturedProperties from "./useFeaturedProperties";
import useRecommendedProperties from "./useRecommendedProperties";
import useNearbyProperties from "./useNearbyProperties";
import useRecentProperties from "./useRecentProperties";
import usePopularLocations from "./usePopularLocations";
import useFeaturedAgents from "./useFeaturedAgents";
import usePropertyCategories from "./usePropertyCategories";

/* -------------------------------------------------------------------------- */
/* Dashboard */
/* -------------------------------------------------------------------------- */

export default function useDashboard(
  options = {}
) {
  const featured =
    useFeaturedProperties(
      options.featured
    );

  const recommended =
    useRecommendedProperties(
      options.recommended
    );

  const nearby =
    useNearbyProperties(
      options.nearby
    );

  const recent =
    useRecentProperties(
      options.recent
    );

  const locations =
    usePopularLocations(
      options.locations
    );

  const agents =
    useFeaturedAgents(
      options.agents
    );

  const categories =
    usePropertyCategories(
      options.categories
    );

  /* ---------------------------------------------------------------------- */
  /* Refresh Dashboard */
  /* ---------------------------------------------------------------------- */

  const refreshDashboard =
    useCallback(async () => {
      await Promise.all([
        featured.refresh(),
        recommended.refresh(),
        nearby.refresh(),
        recent.refresh(),
        locations.refresh(),
        agents.refresh(),
        categories.refresh(),
      ]);
    }, [
      featured,
      recommended,
      nearby,
      recent,
      locations,
      agents,
      categories,
    ]);

  /* ---------------------------------------------------------------------- */
  /* State */
  /* ---------------------------------------------------------------------- */

  const loading =
    featured.loading ||
    recommended.loading ||
    nearby.loading ||
    recent.loading ||
    locations.loading ||
    agents.loading ||
    categories.loading;

  const refreshing =
    featured.refreshing ||
    recommended.refreshing ||
    nearby.refreshing ||
    recent.refreshing ||
    locations.refreshing ||
    agents.refreshing ||
    categories.refreshing;

  const error =
    featured.error ||
    recommended.error ||
    nearby.error ||
    recent.error ||
    locations.error ||
    agents.error ||
    categories.error;

  return {
    featuredProperties:
      featured.featuredProperties,

    recommendedProperties:
      recommended.recommendedProperties,

    nearbyProperties:
      nearby.nearbyProperties,

    recentProperties:
      recent.recentProperties,

    popularLocations:
      locations.popularLocations,

    featuredAgents:
      agents.featuredAgents,

    propertyCategories:
      categories.propertyCategories,

    featured,

    recommended,

    nearby,

    recent,

    locations,

    agents,

    categories,

    loading,

    refreshing,

    error,

    refreshDashboard,
  };
}