/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useSearch.js                        */
/* -------------------------------------------------------------------------- */

import { useState, useMemo, useCallback, useEffect } from "react";
import { useQuery } from "@apollo/client";

import {
  PRODUCTS_QUERY,
  CATEGORIES_QUERY,
} from "@/modules/ecommerce/api/productQuery/queries/product";

import { useChannel } from "@/modules/ecommerce/context/ChannelContext";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEFAULT_PAGE_SIZE = 20;
const DEFAULT_FILTERS = {
  search: "",
  category: null,
  minPrice: 0,
  maxPrice: null,
  inStock: false,
  sortBy: "DATE",
  sortDirection: "DESC",
};

const SORT_OPTIONS = [
  { value: 'DATE', label: 'Date Added' },
  { value: 'NAME', label: 'Name' },
  { value: 'PRICE', label: 'Price' },
  { value: 'RATING', label: 'Rating' },
  { value: 'RELEVANCE', label: 'Relevance' },
];

const SORT_DIRECTIONS = [
  { value: 'ASC', label: 'Low to High' },
  { value: 'DESC', label: 'High to Low' },
];

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

export default function useSearch({
  initialQuery = "",
  initialFilters = {},
  pageSize = DEFAULT_PAGE_SIZE,
  skip = false,
  onCompleted,
  onError,
} = {}) {

  /* ------------------------------------------------------------------------ */
  /* Channel Context                                                          */
  /* ------------------------------------------------------------------------ */

  const { channel, currency, country } = useChannel();

  /* ------------------------------------------------------------------------ */
  /* State                                                                    */
  /* ------------------------------------------------------------------------ */

  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [filters, setFilters] = useState({
    ...DEFAULT_FILTERS,
    ...initialFilters,
  });
  const [cursor, setCursor] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  /* ------------------------------------------------------------------------ */
  /* Products Query                                                           */
  /* ------------------------------------------------------------------------ */

  const {
    data: productsData,
    loading: productsLoading,
    error: productsError,
    refetch: refetchProducts,
    fetchMore,
    networkStatus,
  } = useQuery(PRODUCTS_QUERY, {
    variables: {
      first: pageSize,
      after: cursor,
      filter: {
        search: searchQuery || undefined,
        categories: filters.category ? [filters.category] : undefined,
        channel: channel?.slug,
        priceGte: filters.minPrice || undefined,
        priceLte: filters.maxPrice || undefined,
      },
      sortBy: {
        field: filters.sortBy || 'DATE',
        direction: filters.sortDirection || 'DESC',
      },
    },
    skip: skip || (!searchQuery && !hasSearched),
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
    onCompleted: (data) => {
      setHasSearched(true);
      onCompleted?.(data);
    },
    onError,
  });

  /* ------------------------------------------------------------------------ */
  /* Categories Query                                                         */
  /* ------------------------------------------------------------------------ */

  const {
    data: categoriesData,
    loading: categoriesLoading,
    error: categoriesError,
  } = useQuery(CATEGORIES_QUERY, {
    variables: {
      first: 100,
      channel: channel?.slug,
    },
    skip,
    fetchPolicy: "cache-first",
  });

  /* ------------------------------------------------------------------------ */
  /* Memoized Data                                                            */
  /* ------------------------------------------------------------------------ */

  const products = useMemo(
    () => productsData?.products?.edges?.map(edge => edge.node) ?? [],
    [productsData]
  );

  const totalCount = productsData?.products?.totalCount ?? 0;
  const hasNextPage = productsData?.products?.pageInfo?.hasNextPage ?? false;
  const endCursor = productsData?.products?.pageInfo?.endCursor;

  const categories = useMemo(
    () => categoriesData?.allCategories?.edges?.map(edge => edge.node) ?? [],
    [categoriesData]
  );

  /* ------------------------------------------------------------------------ */
  /* Filters                                                                  */
  /* ------------------------------------------------------------------------ */

  const updateFilter = useCallback((key, value) => {
    setCursor(null);
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const updateFilters = useCallback((values) => {
    setCursor(null);
    setFilters(prev => ({ ...prev, ...values }));
  }, []);

  const resetFilters = useCallback(() => {
    setCursor(null);
    setFilters(DEFAULT_FILTERS);
  }, []);

  const setSearch = useCallback((query) => {
    setCursor(null);
    setSearchQuery(query);
    if (query.length >= 2) {
      setHasSearched(true);
    }
  }, []);

  const clearSearch = useCallback(() => {
    setSearchQuery("");
    setCursor(null);
    setHasSearched(false);
  }, []);

  const setCategory = useCallback((categoryId) => {
    updateFilter('category', categoryId);
  }, [updateFilter]);

  const setPriceRange = useCallback((minPrice, maxPrice) => {
    updateFilters({ minPrice, maxPrice });
  }, [updateFilters]);

  const toggleInStock = useCallback(() => {
    updateFilter('inStock', !filters.inStock);
  }, [filters.inStock, updateFilter]);

  const setSort = useCallback((sortBy, sortDirection) => {
    updateFilters({ sortBy, sortDirection });
  }, [updateFilters]);

  /* ------------------------------------------------------------------------ */
  /* Pagination                                                               */
  /* ------------------------------------------------------------------------ */

  const loadMore = useCallback(async () => {
    if (!hasNextPage || productsLoading) return;

    await fetchMore({
      variables: {
        after: endCursor,
        filter: {
          search: searchQuery || undefined,
          categories: filters.category ? [filters.category] : undefined,
          channel: channel?.slug,
          priceGte: filters.minPrice || undefined,
          priceLte: filters.maxPrice || undefined,
        },
        sortBy: {
          field: filters.sortBy || 'DATE',
          direction: filters.sortDirection || 'DESC',
        },
      },
    });

    setCursor(endCursor);
  }, [hasNextPage, productsLoading, fetchMore, endCursor, searchQuery, filters, channel]);

  /* ------------------------------------------------------------------------ */
  /* Refresh                                                                  */
  /* ------------------------------------------------------------------------ */

  const refreshSearch = useCallback(async () => {
    setCursor(null);
    return refetchProducts({
      first: pageSize,
      after: null,
      filter: {
        search: searchQuery || undefined,
        categories: filters.category ? [filters.category] : undefined,
        channel: channel?.slug,
        priceGte: filters.minPrice || undefined,
        priceLte: filters.maxPrice || undefined,
      },
      sortBy: {
        field: filters.sortBy || 'DATE',
        direction: filters.sortDirection || 'DESC',
      },
    });
  }, [refetchProducts, pageSize, searchQuery, filters, channel]);

  /* ------------------------------------------------------------------------ */
  /* Auto-search on query change                                              */
  /* ------------------------------------------------------------------------ */

  useEffect(() => {
    if (searchQuery.length >= 2) {
      const timer = setTimeout(() => {
        refreshSearch();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [searchQuery, refreshSearch]);

  /* ------------------------------------------------------------------------ */
  /* Error Normalization                                                      */
  /* ------------------------------------------------------------------------ */

  const normalizedError = useMemo(() => {
    const currentError = productsError || categoriesError;
    if (!currentError) return null;
    return {
      message: currentError.message ?? "Search failed.",
      graphQLErrors: currentError.graphQLErrors ?? [],
      networkError: currentError.networkError ?? null,
    };
  }, [productsError, categoriesError]);

  /* ------------------------------------------------------------------------ */
  /* Derived Values                                                           */
  /* ------------------------------------------------------------------------ */

  const isLoading = productsLoading && products.length === 0;
  const isRefreshing = networkStatus === 4;
  const isEmpty = !isLoading && products.length === 0 && hasSearched;
  const hasResults = products.length > 0;

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Results
    products,
    totalCount,
    hasResults,
    isEmpty,

    // Search
    searchQuery,
    setSearch,
    clearSearch,
    hasSearched,

    // Filters
    filters,
    categories,
    selectedCategory: filters.category,
    setCategory,
    setPriceRange,
    toggleInStock,
    setSort,
    updateFilter,
    updateFilters,
    resetFilters,
    clearFilters: resetFilters,

    // Sorting
    sortOptions: SORT_OPTIONS,
    sortDirections: SORT_DIRECTIONS,
    sortBy: filters.sortBy,
    sortDirection: filters.sortDirection,

    // Pagination
    hasNextPage,
    loadMore,
    pageSize,

    // Loading
    loading: isLoading,
    productsLoading,
    categoriesLoading,
    isRefreshing,

    // Error
    error: normalizedError,

    // Actions
    refreshSearch,
    refetch: refreshSearch,
  };
}