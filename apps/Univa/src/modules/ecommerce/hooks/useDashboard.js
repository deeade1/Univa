/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useDashboard.js                     */
/* -------------------------------------------------------------------------- */

import { useMemo, useCallback, useState } from "react";
import { useQuery } from "@apollo/client/react";

import {
  FEATURED_PRODUCTS_QUERY,
  RECOMMENDED_PRODUCTS_QUERY,
  CATEGORIES_QUERY,
  TRENDING_PRODUCTS_QUERY,
  BEST_SELLERS_QUERY,
  NEW_ARRIVALS_QUERY,
  FLASH_SALE_QUERY,
  RECENTLY_VIEWED_QUERY,
} from "@/modules/ecommerce/api/productQuery/queries/product";

import { useChannel } from "@/modules/ecommerce/context/ChannelContext";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEFAULT_PAGE_SIZE = {
  featured: 10,
  recommended: 10,
  categories: 12,
  trending: 8,
  bestSellers: 8,
  newArrivals: 8,
  flashSale: 8,
  recentlyViewed: 10,
};

const DEFAULT_REFRESH_INTERVAL = 60000; // 1 minute

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

const useDashboard = ({
  featuredFirst = DEFAULT_PAGE_SIZE.featured,
  recommendedFirst = DEFAULT_PAGE_SIZE.recommended,
  categoryFirst = DEFAULT_PAGE_SIZE.categories,
  trendingFirst = DEFAULT_PAGE_SIZE.trending,
  bestSellersFirst = DEFAULT_PAGE_SIZE.bestSellers,
  newArrivalsFirst = DEFAULT_PAGE_SIZE.newArrivals,
  flashSaleFirst = DEFAULT_PAGE_SIZE.flashSale,
  recentlyViewedFirst = DEFAULT_PAGE_SIZE.recentlyViewed,
  enableAutoRefresh = false,
  refreshInterval = DEFAULT_REFRESH_INTERVAL,
  skip = false,
  onDataLoaded,
  onError,
} = {}) => {

  /* ------------------------------------------------------------------------ */
  /* Channel Context                                                          */
  /* ------------------------------------------------------------------------ */

  const { channel, currency, country } = useChannel();

  /* ------------------------------------------------------------------------ */
  /* State                                                                    */
  /* ------------------------------------------------------------------------ */

  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  /* ------------------------------------------------------------------------ */
  /* Featured Products                                                        */
  /* ------------------------------------------------------------------------ */

  const {
    data: featuredData,
    loading: featuredLoading,
    error: featuredError,
    refetch: refetchFeatured,
    networkStatus: featuredNetworkStatus,
  } = useQuery(FEATURED_PRODUCTS_QUERY, {
    variables: {
      first: featuredFirst,
      channel: channel?.slug,
      currency: currency,
    },
    skip,
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
  });

  /* ------------------------------------------------------------------------ */
  /* Recommended Products                                                     */
  /* ------------------------------------------------------------------------ */

  const {
    data: recommendedData,
    loading: recommendedLoading,
    error: recommendedError,
    refetch: refetchRecommended,
    networkStatus: recommendedNetworkStatus,
  } = useQuery(RECOMMENDED_PRODUCTS_QUERY, {
    variables: {
      first: recommendedFirst,
      channel: channel?.slug,
      currency: currency,
      country: country,
    },
    skip,
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
  });

  /* ------------------------------------------------------------------------ */
  /* Categories                                                               */
  /* ------------------------------------------------------------------------ */

  const {
    data: categoryData,
    loading: categoryLoading,
    error: categoryError,
    refetch: refetchCategories,
    networkStatus: categoryNetworkStatus,
  } = useQuery(CATEGORIES_QUERY, {
    variables: {
      first: categoryFirst,
      channel: channel?.slug,
    },
    skip,
    fetchPolicy: "cache-first",
    notifyOnNetworkStatusChange: true,
  });

  /* ------------------------------------------------------------------------ */
  /* Trending Products                                                        */
  /* ------------------------------------------------------------------------ */

  const {
    data: trendingData,
    loading: trendingLoading,
    error: trendingError,
    refetch: refetchTrending,
    networkStatus: trendingNetworkStatus,
  } = useQuery(TRENDING_PRODUCTS_QUERY, {
    variables: {
      first: trendingFirst,
      channel: channel?.slug,
      currency: currency,
    },
    skip,
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
  });

  /* ------------------------------------------------------------------------ */
  /* Best Sellers                                                             */
  /* ------------------------------------------------------------------------ */

  const {
    data: bestSellersData,
    loading: bestSellersLoading,
    error: bestSellersError,
    refetch: refetchBestSellers,
    networkStatus: bestSellersNetworkStatus,
  } = useQuery(BEST_SELLERS_QUERY, {
    variables: {
      first: bestSellersFirst,
      channel: channel?.slug,
      currency: currency,
    },
    skip,
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
  });

  /* ------------------------------------------------------------------------ */
  /* New Arrivals                                                             */
  /* ------------------------------------------------------------------------ */

  const {
    data: newArrivalsData,
    loading: newArrivalsLoading,
    error: newArrivalsError,
    refetch: refetchNewArrivals,
    networkStatus: newArrivalsNetworkStatus,
  } = useQuery(NEW_ARRIVALS_QUERY, {
    variables: {
      first: newArrivalsFirst,
      channel: channel?.slug,
      currency: currency,
    },
    skip,
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
  });

  /* ------------------------------------------------------------------------ */
  /* Flash Sale Products                                                      */
  /* ------------------------------------------------------------------------ */

  const {
    data: flashSaleData,
    loading: flashSaleLoading,
    error: flashSaleError,
    refetch: refetchFlashSale,
    networkStatus: flashSaleNetworkStatus,
  } = useQuery(FLASH_SALE_QUERY, {
    variables: {
      first: flashSaleFirst,
      channel: channel?.slug,
      currency: currency,
      country: country,
    },
    skip,
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
  });

  /* ------------------------------------------------------------------------ */
  /* Recently Viewed Products                                                 */
  /* ------------------------------------------------------------------------ */

  const {
    data: recentlyViewedData,
    loading: recentlyViewedLoading,
    error: recentlyViewedError,
    refetch: refetchRecentlyViewed,
    networkStatus: recentlyViewedNetworkStatus,
  } = useQuery(RECENTLY_VIEWED_QUERY, {
    variables: {
      first: recentlyViewedFirst,
      channel: channel?.slug,
      currency: currency,
    },
    skip,
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
  });

  /* ------------------------------------------------------------------------ */
  /* Memoized Values                                                          */
  /* ------------------------------------------------------------------------ */

  const featuredProducts = useMemo(
    () => featuredData?.featuredProducts?.edges?.map((edge) => edge.node) ?? [],
    [featuredData]
  );

  const recommendedProducts = useMemo(
    () => recommendedData?.recommendedProducts?.edges?.map((edge) => edge.node) ?? [],
    [recommendedData]
  );

  const categories = useMemo(
    () => categoryData?.allCategories?.edges?.map((edge) => edge.node) ?? [],
    [categoryData]
  );

  const trendingProducts = useMemo(
    () => trendingData?.trendingProducts?.edges?.map((edge) => edge.node) ?? [],
    [trendingData]
  );

  const bestSellers = useMemo(
    () => bestSellersData?.bestSellers?.edges?.map((edge) => edge.node) ?? [],
    [bestSellersData]
  );

  const newArrivals = useMemo(
    () => newArrivalsData?.newArrivals?.edges?.map((edge) => edge.node) ?? [],
    [newArrivalsData]
  );

  const flashSaleProducts = useMemo(
    () => flashSaleData?.flashSale?.edges?.map((edge) => edge.node) ?? [],
    [flashSaleData]
  );

  const recentlyViewed = useMemo(
    () => recentlyViewedData?.recentlyViewed?.edges?.map((edge) => edge.node) ?? [],
    [recentlyViewedData]
  );

  /* ------------------------------------------------------------------------ */
  /* Derived Values                                                           */
  /* ------------------------------------------------------------------------ */

  const hasFeatured = featuredProducts.length > 0;
  const hasRecommended = recommendedProducts.length > 0;
  const hasCategories = categories.length > 0;
  const hasTrending = trendingProducts.length > 0;
  const hasBestSellers = bestSellers.length > 0;
  const hasNewArrivals = newArrivals.length > 0;
  const hasFlashSale = flashSaleProducts.length > 0;
  const hasRecentlyViewed = recentlyViewed.length > 0;

  const totalProducts = useMemo(() => {
    return {
      featured: featuredProducts.length,
      recommended: recommendedProducts.length,
      trending: trendingProducts.length,
      bestSellers: bestSellers.length,
      newArrivals: newArrivals.length,
      flashSale: flashSaleProducts.length,
      recentlyViewed: recentlyViewed.length,
    };
  }, [
    featuredProducts,
    recommendedProducts,
    trendingProducts,
    bestSellers,
    newArrivals,
    flashSaleProducts,
    recentlyViewed,
  ]);

  /* ------------------------------------------------------------------------ */
  /* Loading States                                                           */
  /* ------------------------------------------------------------------------ */

  const isLoading = useMemo(() => {
    return (
      featuredLoading ||
      recommendedLoading ||
      categoryLoading ||
      trendingLoading ||
      bestSellersLoading ||
      newArrivalsLoading ||
      flashSaleLoading ||
      recentlyViewedLoading
    );
  }, [
    featuredLoading,
    recommendedLoading,
    categoryLoading,
    trendingLoading,
    bestSellersLoading,
    newArrivalsLoading,
    flashSaleLoading,
    recentlyViewedLoading,
  ]);

  const isRefreshing = useMemo(() => {
    return (
      featuredNetworkStatus === 4 ||
      recommendedNetworkStatus === 4 ||
      categoryNetworkStatus === 4 ||
      trendingNetworkStatus === 4 ||
      bestSellersNetworkStatus === 4 ||
      newArrivalsNetworkStatus === 4 ||
      flashSaleNetworkStatus === 4 ||
      recentlyViewedNetworkStatus === 4
    );
  }, [
    featuredNetworkStatus,
    recommendedNetworkStatus,
    categoryNetworkStatus,
    trendingNetworkStatus,
    bestSellersNetworkStatus,
    newArrivalsNetworkStatus,
    flashSaleNetworkStatus,
    recentlyViewedNetworkStatus,
  ]);

  const loadingStates = useMemo(() => ({
    featured: featuredLoading,
    recommended: recommendedLoading,
    categories: categoryLoading,
    trending: trendingLoading,
    bestSellers: bestSellersLoading,
    newArrivals: newArrivalsLoading,
    flashSale: flashSaleLoading,
    recentlyViewed: recentlyViewedLoading,
  }), [
    featuredLoading,
    recommendedLoading,
    categoryLoading,
    trendingLoading,
    bestSellersLoading,
    newArrivalsLoading,
    flashSaleLoading,
    recentlyViewedLoading,
  ]);

  /* ------------------------------------------------------------------------ */
  /* Error Handling                                                           */
  /* ------------------------------------------------------------------------ */

  const errors = useMemo(() => {
    const errs = {};
    if (featuredError) errs.featured = featuredError;
    if (recommendedError) errs.recommended = recommendedError;
    if (categoryError) errs.categories = categoryError;
    if (trendingError) errs.trending = trendingError;
    if (bestSellersError) errs.bestSellers = bestSellersError;
    if (newArrivalsError) errs.newArrivals = newArrivalsError;
    if (flashSaleError) errs.flashSale = flashSaleError;
    if (recentlyViewedError) errs.recentlyViewed = recentlyViewedError;
    return errs;
  }, [
    featuredError,
    recommendedError,
    categoryError,
    trendingError,
    bestSellersError,
    newArrivalsError,
    flashSaleError,
    recentlyViewedError,
  ]);

  const hasErrors = Object.keys(errors).length > 0;

  const normalizedError = useMemo(() => {
    if (!hasErrors) return null;

    // Get first error for simplicity
    const firstErrorKey = Object.keys(errors)[0];
    const firstError = errors[firstErrorKey];

    return {
      message: firstError?.message ?? "Unable to load dashboard data.",
      details: errors,
      graphQLErrors: firstError?.graphQLErrors ?? [],
      networkError: firstError?.networkError ?? null,
    };
  }, [errors, hasErrors]);

  /* ------------------------------------------------------------------------ */
  /* Refetch Functions                                                        */
  /* ------------------------------------------------------------------------ */

  const refreshAll = useCallback(async () => {
    setRefreshing(true);
    try {
      await Promise.all([
        refetchFeatured(),
        refetchRecommended(),
        refetchCategories(),
        refetchTrending(),
        refetchBestSellers(),
        refetchNewArrivals(),
        refetchFlashSale(),
        refetchRecentlyViewed(),
      ]);
      setLastUpdated(new Date());
      onDataLoaded?.();
    } catch (err) {
      onError?.(err);
    } finally {
      setRefreshing(false);
    }
  }, [
    refetchFeatured,
    refetchRecommended,
    refetchCategories,
    refetchTrending,
    refetchBestSellers,
    refetchNewArrivals,
    refetchFlashSale,
    refetchRecentlyViewed,
    onDataLoaded,
    onError,
  ]);

  const refreshSection = useCallback(async (section) => {
    const refetchMap = {
      featured: refetchFeatured,
      recommended: refetchRecommended,
      categories: refetchCategories,
      trending: refetchTrending,
      bestSellers: refetchBestSellers,
      newArrivals: refetchNewArrivals,
      flashSale: refetchFlashSale,
      recentlyViewed: refetchRecentlyViewed,
    };

    const refetchFn = refetchMap[section];
    if (!refetchFn) {
      console.warn(`Unknown section: ${section}`);
      return;
    }

    try {
      await refetchFn();
      setLastUpdated(new Date());
    } catch (err) {
      onError?.(err);
    }
  }, [
    refetchFeatured,
    refetchRecommended,
    refetchCategories,
    refetchTrending,
    refetchBestSellers,
    refetchNewArrivals,
    refetchFlashSale,
    refetchRecentlyViewed,
    onError,
  ]);

  /* ------------------------------------------------------------------------ */
  /* Auto Refresh                                                             */
  /* ------------------------------------------------------------------------ */

  useMemo(() => {
    if (!enableAutoRefresh || skip) return;

    const interval = setInterval(() => {
      refreshAll();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [enableAutoRefresh, refreshInterval, refreshAll, skip]);

  /* ------------------------------------------------------------------------ */
  /* Format Data for Components                                               */
  /* ------------------------------------------------------------------------ */

  const dashboardData = useMemo(() => ({
    featured: {
      title: "Featured Products",
      products: featuredProducts,
      count: featuredProducts.length,
      hasItems: hasFeatured,
    },
    recommended: {
      title: "Recommended for You",
      products: recommendedProducts,
      count: recommendedProducts.length,
      hasItems: hasRecommended,
    },
    categories: {
      title: "Categories",
      items: categories,
      count: categories.length,
      hasItems: hasCategories,
    },
    trending: {
      title: "Trending Now",
      products: trendingProducts,
      count: trendingProducts.length,
      hasItems: hasTrending,
    },
    bestSellers: {
      title: "Best Sellers",
      products: bestSellers,
      count: bestSellers.length,
      hasItems: hasBestSellers,
    },
    newArrivals: {
      title: "New Arrivals",
      products: newArrivals,
      count: newArrivals.length,
      hasItems: hasNewArrivals,
    },
    flashSale: {
      title: "Flash Sale",
      products: flashSaleProducts,
      count: flashSaleProducts.length,
      hasItems: hasFlashSale,
    },
    recentlyViewed: {
      title: "Recently Viewed",
      products: recentlyViewed,
      count: recentlyViewed.length,
      hasItems: hasRecentlyViewed,
    },
  }), [
    featuredProducts,
    recommendedProducts,
    categories,
    trendingProducts,
    bestSellers,
    newArrivals,
    flashSaleProducts,
    recentlyViewed,
    hasFeatured,
    hasRecommended,
    hasCategories,
    hasTrending,
    hasBestSellers,
    hasNewArrivals,
    hasFlashSale,
    hasRecentlyViewed,
  ]);

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Data
    featuredProducts,
    recommendedProducts,
    categories,
    trendingProducts,
    bestSellers,
    newArrivals,
    flashSaleProducts,
    recentlyViewed,

    // Dashboard Data (formatted for components)
    dashboardData,

    // Counts
    totalProducts,
    hasFeatured,
    hasRecommended,
    hasCategories,
    hasTrending,
    hasBestSellers,
    hasNewArrivals,
    hasFlashSale,
    hasRecentlyViewed,

    // Loading states
    loading: isLoading,
    isRefreshing,
    refreshing,
    loadingStates,

    // Error
    error: normalizedError,
    errors,
    hasErrors,

    // Actions
    refetch: refreshAll,
    refreshAll,
    refreshSection,

    // Metadata
    lastUpdated,
    channel: channel?.slug,
    currency,
    country,
  };
};

export default useDashboard;