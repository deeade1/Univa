import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useLazyQuery } from "@apollo/client";

import { SEARCH_PROPERTIES_QUERY } from "@/modules/real-estate/api/queries";

/* -------------------------------------------------------------------------- */
/* Constants */
/* -------------------------------------------------------------------------- */

const DEFAULT_FILTERS = {
  category: null,
  propertyType: null,
  listingType: null,

  minPrice: null,
  maxPrice: null,

  bedrooms: null,
  bathrooms: null,

  minArea: null,
  maxArea: null,

  city: null,
  state: null,
  country: null,

  latitude: null,
  longitude: null,
  radius: null,

  verified: false,
  featured: false,

  furnished: false,
  parking: false,
  petsAllowed: false,

  sortBy: "latest",
};

const SEARCH_DELAY = 500;

/* -------------------------------------------------------------------------- */
/* Hook */
/* -------------------------------------------------------------------------- */

export default function usePropertySearch({
  initialKeyword = "",
  initialFilters = {},
  debounce = SEARCH_DELAY,
  autoSearch = true,
} = {}) {
  const [keyword, setKeyword] =
    useState(initialKeyword);

  const [filters, setFilters] =
    useState({
      ...DEFAULT_FILTERS,
      ...initialFilters,
    });

  const [history, setHistory] =
    useState([]);

  const [refreshing, setRefreshing] =
    useState(false);

  const [search, query] =
    useLazyQuery(
      SEARCH_PROPERTIES_QUERY,
      {
        fetchPolicy:
          "cache-and-network",

        nextFetchPolicy:
          "cache-first",

        notifyOnNetworkStatusChange:
          true,
      }
    );

  /* ---------------------------------------------------------------------- */
  /* Variables */
  /* ---------------------------------------------------------------------- */

  const variables = useMemo(
    () => ({
      keyword,

      ...filters,
    }),
    [keyword, filters]
  );

  /* ---------------------------------------------------------------------- */
  /* Search */
  /* ---------------------------------------------------------------------- */

  const executeSearch =
    useCallback(async () => {
      return search({
        variables,
      });
    }, [search, variables]);

  /* ---------------------------------------------------------------------- */
  /* Debounce */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {
    if (!autoSearch) return;

    const timer =
      setTimeout(() => {
        executeSearch();
      }, debounce);

    return () =>
      clearTimeout(timer);
  }, [
    keyword,
    filters,
    debounce,
    autoSearch,
    executeSearch,
  ]);

  /* ---------------------------------------------------------------------- */
  /* Refresh */
  /* ---------------------------------------------------------------------- */

  const refresh =
    useCallback(async () => {
      try {
        setRefreshing(true);

        await query.refetch?.(
          variables
        );
      } finally {
        setRefreshing(false);
      }
    }, [query, variables]);

  /* ---------------------------------------------------------------------- */
  /* Keyword */
  /* ---------------------------------------------------------------------- */

  const updateKeyword =
    useCallback((value) => {
      setKeyword(value);
    }, []);

  const clearKeyword =
    useCallback(() => {
      setKeyword("");
    }, []);

  /* ---------------------------------------------------------------------- */
  /* Filters */
  /* ---------------------------------------------------------------------- */

  const updateFilter =
    useCallback(
      (key, value) => {
        setFilters((prev) => ({
          ...prev,
          [key]: value,
        }));
      },
      []
    );

  const updateFilters =
    useCallback((values) => {
      setFilters((prev) => ({
        ...prev,
        ...values,
      }));
    }, []);

  const resetFilters =
    useCallback(() => {
      setFilters(
        DEFAULT_FILTERS
      );
    }, []);

  /* ---------------------------------------------------------------------- */
  /* History */
  /* ---------------------------------------------------------------------- */

  const addHistory =
    useCallback((text) => {
      if (!text?.trim()) return;

      setHistory((prev) => {
        const list = [
          text,
          ...prev.filter(
            (item) =>
              item !== text
          ),
        ];

        return list.slice(0, 10);
      });
    }, []);

  const clearHistory =
    useCallback(() => {
      setHistory([]);
    }, []);

  /* ---------------------------------------------------------------------- */
  /* Pagination */
  /* ---------------------------------------------------------------------- */

  const loadMore =
    useCallback(
      async (
        moreVariables = {}
      ) => {
        if (
          !query.fetchMore
        )
          return;

        return query.fetchMore({
          variables: {
            ...variables,
            ...moreVariables,
          },
        });
      },
      [query, variables]
    );

  /* ---------------------------------------------------------------------- */
  /* Results */
  /* ---------------------------------------------------------------------- */

  const properties =
    useMemo(() => {
      return (
        query.data
          ?.searchProperties ??
        []
      );
    }, [query.data]);

  const hasFilters =
    useMemo(() => {
      return Object.entries(
        filters
      ).some(
        ([, value]) =>
          value !== null &&
          value !== false &&
          value !== ""
      );
    }, [filters]);

  /* ---------------------------------------------------------------------- */
  /* API */
  /* ---------------------------------------------------------------------- */

  return {
    keyword,

    setKeyword:
      updateKeyword,

    clearKeyword,

    filters,

    setFilter:
      updateFilter,

    setFilters:
      updateFilters,

    resetFilters,

    variables,

    search:
      executeSearch,

    refresh,

    loadMore,

    history,

    addHistory,

    clearHistory,

    properties,

    data: query.data,

    loading:
      query.loading,

    error:
      query.error,

    called:
      query.called,

    networkStatus:
      query.networkStatus,

    refreshing,

    hasFilters,

    empty:
      !query.loading &&
      properties.length === 0,
  };
}