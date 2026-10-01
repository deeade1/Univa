/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useRelatedProducts.js               */
/* -------------------------------------------------------------------------- */

import { useCallback, useMemo } from "react";
import { useQuery } from "@apollo/client";

import { SIMILAR_PRODUCTS_QUERY } from "@/modules/ecommerce/api/productQuery/queries/product";
import { useChannel } from "@/modules/ecommerce/context/ChannelContext";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEFAULT_LIMIT = 10;
const RECOMMENDATION_TYPES = {
  SIMILAR: 'SIMILAR',
  RELATED: 'RELATED',
  RECENTLY_VIEWED: 'RECENTLY_VIEWED',
  TRENDING: 'TRENDING',
};

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

const useRelatedProducts = ({
  productId,
  categoryId,
  limit = DEFAULT_LIMIT,
  first = DEFAULT_LIMIT,
  type = RECOMMENDATION_TYPES.RELATED,
  skip = false,
  onCompleted,
  onError,
} = {}) => {

  /* ------------------------------------------------------------------------ */
  /* Channel Context                                                          */
  /* ------------------------------------------------------------------------ */

  const { channel, currency, country } = useChannel();

  /* ------------------------------------------------------------------------ */
  /* Query Variables                                                          */
  /* ------------------------------------------------------------------------ */

  const variables = useMemo(() => ({
    productId,
    first: first ?? limit,
    channel: channel?.slug,
    currency: currency,
    country: country,
  }), [productId, first, limit, channel, currency, country]);

  /* ------------------------------------------------------------------------ */
  /* Products Query                                                           */
  /* ------------------------------------------------------------------------ */

  const {
    data,
    loading,
    error,
    fetchMore,
    refetch,
    networkStatus,
  } = useQuery(SIMILAR_PRODUCTS_QUERY, {
    variables,
    skip: skip || !productId,
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
    onCompleted,
    onError,
  });

  /* ------------------------------------------------------------------------ */
  /* Raw Products                                                             */
  /* ------------------------------------------------------------------------ */

  const products = useMemo(() => {
    return data?.similarProducts ?? [];
  }, [data]);

  /* ------------------------------------------------------------------------ */
  /* Normalized Products                                                      */
  /* ------------------------------------------------------------------------ */

  const normalizedProducts = useMemo(() => {
    return products.map(product => ({
      id: product.id,
      name: product.name ?? "",
      slug: product.slug ?? null,
      rating: product.rating ?? 0,

      category: product.category ? {
        id: product.category.id,
        name: product.category.name,
        slug: product.category.slug,
      } : null,

      media: product.media?.edges?.map(edge => ({
        id: edge.node.id,
        url: edge.node.url,
        alt: edge.node.alt || product.name,
        type: edge.node.type,
      })) ?? [],

      image: product.media?.edges?.[0]?.node?.url ?? null,

      variants: product.variants?.edges?.map(edge => ({
        id: edge.node.id,
        name: edge.node.name,
        sku: edge.node.sku,
        channelListings: edge.node.channelListings?.edges?.map(l => ({
          id: l.node.id,
          currency: l.node.currency,
          price: l.node.price?.amount ?? 0,
          discountedPrice: l.node.discountedPrice?.amount ?? null,
        })) ?? [],
      })) ?? [],

      price: product.variants?.edges?.[0]?.node?.channelListings?.edges?.[0]?.node?.price?.amount ?? 0,
      currency: product.variants?.edges?.[0]?.node?.channelListings?.edges?.[0]?.node?.currency ?? 'USD',

      discount: product.variants?.edges?.[0]?.node?.channelListings?.edges?.[0]?.node?.discountedPrice?.amount ?? null,

      hasDiscount: product.variants?.edges?.[0]?.node?.channelListings?.edges?.[0]?.node?.discountedPrice?.amount !== null,

      isPreorder: product.variants?.edges?.some(v => v.node.isPreorder) ?? false,

      // Recommendation metadata
      recommendationType: type,
      score: product.score ?? 0,
    }));
  }, [products, type]);

  /* ------------------------------------------------------------------------ */
  /* Grouped Products                                                         */
  /* ------------------------------------------------------------------------ */

  const groupedProducts = useMemo(() => {
    const groups = {
      similar: [],
      related: [],
      recentlyViewed: [],
      trending: [],
      all: normalizedProducts,
    };

    normalizedProducts.forEach(product => {
      switch (product.recommendationType) {
        case RECOMMENDATION_TYPES.SIMILAR:
          groups.similar.push(product);
          break;
        case RECOMMENDATION_TYPES.RECENTLY_VIEWED:
          groups.recentlyViewed.push(product);
          break;
        case RECOMMENDATION_TYPES.TRENDING:
          groups.trending.push(product);
          break;
        default:
          groups.related.push(product);
      }
    });

    return groups;
  }, [normalizedProducts]);

  /* ------------------------------------------------------------------------ */
  /* Loading States                                                           */
  /* ------------------------------------------------------------------------ */

  const isRefreshing = networkStatus === 4;
  const isLoading = loading && normalizedProducts.length === 0;
  const isEmpty = !loading && normalizedProducts.length === 0;

  /* ------------------------------------------------------------------------ */
  /* Actions                                                                  */
  /* ------------------------------------------------------------------------ */

  const refreshProducts = useCallback(async () => {
    try {
      return await refetch();
    } catch (refreshError) {
      console.warn("Related products refresh failed:", refreshError);
      return null;
    }
  }, [refetch]);

  const loadMore = useCallback(async () => {
    const pageInfo = data?.similarProducts?.pageInfo;
    if (!pageInfo?.hasNextPage || loading) return;

    await fetchMore({
      variables: {
        after: pageInfo.endCursor,
        first: limit,
      },
      updateQuery: (prev, { fetchMoreResult }) => {
        if (!fetchMoreResult) return prev;
        return {
          similarProducts: [
            ...prev.similarProducts,
            ...fetchMoreResult.similarProducts,
          ],
        };
      },
    });
  }, [data, fetchMore, loading, limit]);

  /* ------------------------------------------------------------------------ */
  /* Error Normalization                                                      */
  /* ------------------------------------------------------------------------ */

  const normalizedError = useMemo(() => {
    if (!error) return null;
    return {
      message: error.message ?? "Unable to load related products.",
      graphQLErrors: error.graphQLErrors ?? [],
      networkError: error.networkError ?? null,
    };
  }, [error]);

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Products
    products: normalizedProducts,
    groupedProducts,
    rawProducts: products,

    // Recommendation type
    recommendationType: type,
    recommendationTypes: RECOMMENDATION_TYPES,

    // States
    loading: isLoading,
    isRefreshing,
    isEmpty,
    networkStatus,

    // Pagination
    hasNextPage: data?.similarProducts?.pageInfo?.hasNextPage ?? false,
    loadMore,

    // Actions
    refreshProducts,
    refetch,

    // Error
    error: normalizedError,

    // Counts
    total: normalizedProducts.length,
    similarCount: groupedProducts.similar.length,
    relatedCount: groupedProducts.related.length,
    trendingCount: groupedProducts.trending.length,
    recentlyViewedCount: groupedProducts.recentlyViewed.length,
  };
};

export default useRelatedProducts;