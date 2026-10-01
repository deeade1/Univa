/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useProductReviews.js                */
/* -------------------------------------------------------------------------- */

import { useCallback, useMemo, useState } from "react";
import { useQuery, useMutation } from "@apollo/client";

import {
  PRODUCT_REVIEWS_QUERY,
} from "@/modules/ecommerce/api/productQuery/queries/product";

import {
  CREATE_PRODUCT_REVIEW,
} from "@/modules/ecommerce/api/productQuery/mutations/products";

import { useChannel } from "@/modules/ecommerce/context/ChannelContext";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEFAULT_PAGE_SIZE = 10;
const SORT_OPTIONS = {
  LATEST: 'LATEST',
  OLDEST: 'OLDEST',
  HIGHEST_RATING: 'HIGHEST_RATING',
  LOWEST_RATING: 'LOWEST_RATING',
  MOST_HELPFUL: 'MOST_HELPFUL',
};

const SORT_LABELS = {
  [SORT_OPTIONS.LATEST]: 'Most Recent',
  [SORT_OPTIONS.OLDEST]: 'Oldest First',
  [SORT_OPTIONS.HIGHEST_RATING]: 'Highest Rated',
  [SORT_OPTIONS.LOWEST_RATING]: 'Lowest Rated',
  [SORT_OPTIONS.MOST_HELPFUL]: 'Most Helpful',
};

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

const useProductReviews = ({
  productId,
  first = DEFAULT_PAGE_SIZE,
  sortBy = SORT_OPTIONS.LATEST,
  ratingFilter = null,
  skip = false,
  onCompleted,
  onError,
} = {}) => {

  /* ------------------------------------------------------------------------ */
  /* Channel Context                                                          */
  /* ------------------------------------------------------------------------ */

  const { channel, currency } = useChannel();

  /* ------------------------------------------------------------------------ */
  /* State                                                                    */
  /* ------------------------------------------------------------------------ */

  const [currentSort, setCurrentSort] = useState(sortBy);
  const [currentRatingFilter, setCurrentRatingFilter] = useState(ratingFilter);
  const [submitting, setSubmitting] = useState(false);

  /* ------------------------------------------------------------------------ */
  /* Query Variables                                                          */
  /* ------------------------------------------------------------------------ */

  const variables = useMemo(() => ({
    productId,
    first,
    sort: currentSort,
    rating: currentRatingFilter,
    channel: channel?.slug,
    currency: currency,
  }), [productId, first, currentSort, currentRatingFilter, channel, currency]);

  /* ------------------------------------------------------------------------ */
  /* Reviews Query                                                            */
  /* ------------------------------------------------------------------------ */

  const {
    data,
    loading,
    error,
    fetchMore,
    refetch,
    networkStatus,
  } = useQuery(PRODUCT_REVIEWS_QUERY, {
    variables,
    skip: skip || !productId,
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
    onCompleted,
    onError,
  });

  /* ------------------------------------------------------------------------ */
  /* Create Review Mutation                                                   */
  /* ------------------------------------------------------------------------ */

  const [createReviewMutation] = useMutation(CREATE_PRODUCT_REVIEW);

  /* ------------------------------------------------------------------------ */
  /* Raw Reviews                                                              */
  /* ------------------------------------------------------------------------ */

  const rawReviews = useMemo(() => {
    return data?.productReviews?.edges?.map(({ node }) => node) ?? [];
  }, [data]);

  /* ------------------------------------------------------------------------ */
  /* Normalized Reviews                                                       */
  /* ------------------------------------------------------------------------ */

  const reviews = useMemo(() => {
    return rawReviews.map((review) => ({
      id: review.id,
      rating: review.rating ?? 0,
      comment: review.comment ?? "",
      createdAt: review.createdAt,
      user: {
        id: review.user?.id,
        email: review.user?.email,
      },
      product: {
        id: review.product?.id,
        name: review.product?.name,
      },
      helpfulCount: review.helpfulCount ?? 0,
      verified: review.verified ?? false,
    }));
  }, [rawReviews]);

  /* ------------------------------------------------------------------------ */
  /* Rating Summary                                                           */
  /* ------------------------------------------------------------------------ */

  const ratingSummary = useMemo(() => {
    if (!reviews.length) {
      return {
        average: 0,
        total: 0,
        distribution: { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 },
      };
    }

    const total = reviews.length;
    const totalRating = reviews.reduce((sum, review) => sum + review.rating, 0);
    const distribution = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };

    reviews.forEach((review) => {
      const rating = Math.round(review.rating);
      if (distribution[rating] !== undefined) {
        distribution[rating] += 1;
      }
    });

    return {
      average: Number((totalRating / total).toFixed(1)),
      total,
      distribution,
    };
  }, [reviews]);

  const ratingPercentages = useMemo(() => {
    const { distribution, total } = ratingSummary;
    if (!total) return {};
    return Object.keys(distribution).reduce((result, key) => {
      result[key] = Math.round((distribution[key] / total) * 100);
      return result;
    }, {});
  }, [ratingSummary]);

  /* ------------------------------------------------------------------------ */
  /* Pagination                                                               */
  /* ------------------------------------------------------------------------ */

  const hasNextPage = data?.productReviews?.pageInfo?.hasNextPage ?? false;
  const endCursor = data?.productReviews?.pageInfo?.endCursor;

  const loadMore = useCallback(async () => {
    if (!hasNextPage || loading) return;

    try {
      await fetchMore({
        variables: { after: endCursor },
        updateQuery: (prev, { fetchMoreResult }) => {
          if (!fetchMoreResult) return prev;
          return {
            productReviews: {
              ...fetchMoreResult.productReviews,
              edges: [
                ...prev.productReviews.edges,
                ...fetchMoreResult.productReviews.edges,
              ],
            },
          };
        },
      });
    } catch (err) {
      console.warn("Failed to load more reviews:", err);
    }
  }, [hasNextPage, endCursor, fetchMore, loading]);

  /* ------------------------------------------------------------------------ */
  /* Submit Review                                                            */
  /* ------------------------------------------------------------------------ */

  const submitReview = useCallback(async ({ rating, comment }) => {
    if (!productId) {
      return {
        success: false,
        message: "Product ID is required.",
      };
    }

    if (!rating || rating < 1 || rating > 5) {
      return {
        success: false,
        message: "Rating must be between 1 and 5.",
      };
    }

    setSubmitting(true);

    try {
      const { data } = await createReviewMutation({
        variables: {
          input: {
            productId,
            rating,
            comment: comment || "",
          },
        },
      });

      const review = data?.productReview?.review;

      if (review) {
        await refetch();
        return {
          success: true,
          review,
        };
      }

      return {
        success: false,
        message: "Failed to submit review.",
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    } finally {
      setSubmitting(false);
    }
  }, [productId, createReviewMutation, refetch]);

  /* ------------------------------------------------------------------------ */
  /* Filter and Sort Actions                                                  */
  /* ------------------------------------------------------------------------ */

  const setSort = useCallback((sort) => {
    setCurrentSort(sort);
  }, []);

  const setRatingFilter = useCallback((rating) => {
    setCurrentRatingFilter(rating);
  }, []);

  const clearFilters = useCallback(() => {
    setCurrentSort(SORT_OPTIONS.LATEST);
    setCurrentRatingFilter(null);
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Refresh                                                                  */
  /* ------------------------------------------------------------------------ */

  const refreshReviews = useCallback(async () => {
    return refetch();
  }, [refetch]);

  /* ------------------------------------------------------------------------ */
  /* Combined Error                                                           */
  /* ------------------------------------------------------------------------ */

  const normalizedError = useMemo(() => {
    if (!error) return null;
    return {
      message: error.message ?? "Unable to load reviews.",
      graphQLErrors: error.graphQLErrors ?? [],
      networkError: error.networkError ?? null,
    };
  }, [error]);

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Reviews
    reviews,
    rawReviews,

    // Rating
    averageRating: ratingSummary.average,
    totalReviews: ratingSummary.total,
    ratingDistribution: ratingSummary.distribution,
    ratingPercentages,

    // Pagination
    hasNextPage,
    loadMore,
    loading,
    isRefetching: networkStatus === 4,

    // Actions
    submitReview,
    refreshReviews,
    setSort,
    setRatingFilter,
    clearFilters,

    // Sort/Filter state
    currentSort,
    currentRatingFilter,
    SORT_OPTIONS,
    SORT_LABELS,
    sortOptions: Object.values(SORT_OPTIONS),

    // Submitting state
    submitting,

    // Error
    error: normalizedError,
  };
};

export default useProductReviews;