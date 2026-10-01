import {
  useCallback,
  useMemo,
  useState,
} from "react";

import { useQuery } from "@apollo/client";

/* -------------------------------------------------------------------------- */
/* useRealEstateQuery                                                         */
/* -------------------------------------------------------------------------- */

/**
 * Generic hook for all Real Estate GraphQL queries.
 *
 * @example
 * const result = useRealEstateQuery({
 *   query: FEATURED_PROPERTIES_QUERY,
 *   dataKey: "featuredProperties",
 * });
 *
 * @example
 * const result = useRealEstateQuery({
 *   query: POPULAR_LOCATIONS_QUERY,
 *   dataKey: "popularLocations",
 *   variables: {
 *     first: 20,
 *   },
 * });
 */

export default function useRealEstateQuery({
  query,
  dataKey,
  variables = {},
  skip = false,
  fetchPolicy = "cache-and-network",
  nextFetchPolicy = "cache-first",
  notifyOnNetworkStatusChange = true,
  pollInterval = 0,
  transform,
}) {
  const [refreshing, setRefreshing] =
    useState(false);

  const {
    data,
    loading,
    error,
    refetch,
    fetchMore,
    networkStatus,
    startPolling,
    stopPolling,
  } = useQuery(query, {
    variables,
    skip,
    fetchPolicy,
    nextFetchPolicy,
    notifyOnNetworkStatusChange,
    pollInterval,
    errorPolicy: "all",
    returnPartialData: true,
  });

  /* ---------------------------------------------------------------------- */
  /* Extract Data */
  /* ---------------------------------------------------------------------- */

  const rawData = useMemo(() => {
    if (!data) return [];

    if (!dataKey) return data;

    return data[dataKey] ?? [];
  }, [data, dataKey]);

  /* ---------------------------------------------------------------------- */
  /* Transform Data */
  /* ---------------------------------------------------------------------- */

  const items = useMemo(() => {
    if (!transform) return rawData;

    return transform(rawData);
  }, [rawData, transform]);

  /* ---------------------------------------------------------------------- */
  /* Refresh */
  /* ---------------------------------------------------------------------- */

  const refresh = useCallback(async () => {
    if (!refetch) return;

    try {
      setRefreshing(true);

      await refetch(variables);
    } finally {
      setRefreshing(false);
    }
  }, [refetch, variables]);

  /* ---------------------------------------------------------------------- */
  /* Pagination */
  /* ---------------------------------------------------------------------- */

  const loadMore = useCallback(
    async ({
      variables: moreVariables = {},
      updateQuery,
    }) => {
      if (!fetchMore) return;

      return fetchMore({
        variables: moreVariables,
        updateQuery,
      });
    },
    [fetchMore]
  );

  /* ---------------------------------------------------------------------- */
  /* Polling */
  /* ---------------------------------------------------------------------- */

  const beginPolling = useCallback(
    (interval = 15000) => {
      startPolling?.(interval);
    },
    [startPolling]
  );

  const endPolling = useCallback(() => {
    stopPolling?.();
  }, [stopPolling]);

  /* ---------------------------------------------------------------------- */
  /* State */
  /* ---------------------------------------------------------------------- */

  const isEmpty = useMemo(() => {
    if (Array.isArray(items)) {
      return items.length === 0;
    }

    return !items;
  }, [items]);

  const isRefetching =
    networkStatus === 4;

  const isFetchingMore =
    networkStatus === 3;

  /* ---------------------------------------------------------------------- */
  /* API */
  /* ---------------------------------------------------------------------- */

  return {
    data,
    items,
    rawData,

    loading,
    error,

    refreshing,
    refresh,

    refetch,
    fetchMore: loadMore,

    startPolling: beginPolling,
    stopPolling: endPolling,

    networkStatus,

    isEmpty,
    isLoading: loading,
    isError: !!error,
    isSuccess:
      !loading && !error,

    isRefreshing: refreshing,
    isRefetching,
    isFetchingMore,
  };
}