/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useProduct.js                       */
/* -------------------------------------------------------------------------- */

import { useMemo, useCallback } from "react";
import { useQuery, useLazyQuery } from "@apollo/client/react";

import {
  PRODUCT_QUERY,
  SIMILAR_PRODUCTS_QUERY,
} from "../api/productQuery/queries/product";

import {
  GET_ALL_ATTRIBUTES,
  GET_ATTRIBUTE_VALUES,
} from "../api/productQuery/queries/attribute";

import useProductReviews from "./useProductReviews";

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

export function useProduct(slug, options = {}) {
  const {
    skip = false,
    fetchSimilar = true,
    fetchAttributes = true,
    onCompleted,
    onError,
  } = options;

  /* ------------------------------------------------------------------------ */
  /* Product Query                                                            */
  /* ------------------------------------------------------------------------ */

  const {
    data: productData,
    loading: productLoading,
    error: productError,
    refetch,
    networkStatus,
  } = useQuery(PRODUCT_QUERY, {
    variables: { slug },
    skip: skip || !slug,
    fetchPolicy: "cache-and-network",
    nextFetchPolicy: "cache-first",
    notifyOnNetworkStatusChange: true,
    onCompleted,
    onError,
  });

  /* ------------------------------------------------------------------------ */
  /* Reviews                                                                  */
  /* ------------------------------------------------------------------------ */

  const rawProduct = productData?.productBySlug ?? null;

  const {
    reviews,
    averageRating,
    totalReviews,
    ratingDistribution,
    loadMore: loadMoreReviews,
    hasNextPage: hasMoreReviews,
    loading: reviewsLoading,
    error: reviewsError,
  } = useProductReviews({
    productId: rawProduct?.id,
    skip: !rawProduct?.id,
  });

  /* ------------------------------------------------------------------------ */
  /* Similar Products Query                                                   */
  /* ------------------------------------------------------------------------ */

  const categoryId = rawProduct?.category?.id;

  const {
    data: similarData,
    loading: similarLoading,
    error: similarError,
  } = useQuery(SIMILAR_PRODUCTS_QUERY, {
    variables: {
      categoryId,
      exclude: rawProduct?.id,
      first: 10,
    },
    skip: !fetchSimilar || !categoryId,
    fetchPolicy: "cache-and-network",
  });

  /* ------------------------------------------------------------------------ */
  /* Attributes Query - Lazy Load for On-Demand                               */
  /* ------------------------------------------------------------------------ */

  const [
    getProductAttributes,
    {
      data: attributeData,
      loading: attributesLoading,
      error: attributesError,
      called: attributesCalled,
    },
  ] = useLazyQuery(GET_ALL_ATTRIBUTES, {
    variables: {
      first: 100,
      visibleInStorefront: true,
    },
    fetchPolicy: "cache-and-network",
  });

  /* ------------------------------------------------------------------------ */
  /* Get attributes for a specific product                                    */
  /* ------------------------------------------------------------------------ */

  const getAttributesForProduct = useCallback(async () => {
    if (!rawProduct?.id) {
      return [];
    }

    const { data } = await getProductAttributes();
    const allAttributes = data?.allAttributes?.edges?.map(edge => edge.node) ?? [];

    // Filter attributes that are assigned to this product
    // This depends on how your schema connects attributes to products
    // Adjust based on your actual data structure
    const productAttributes = allAttributes.filter(attr => {
      // Check if this attribute has values assigned to this product
      return attr.values?.edges?.some(valueEdge => {
        const value = valueEdge.node;
        // Check if this value is assigned to the product
        // This field name may vary based on your schema
        return value.assignedProducts?.edges?.some(
          assignment => assignment.node.product?.id === rawProduct.id
        );
      });
    });

    return productAttributes;
  }, [rawProduct?.id, getProductAttributes]);

  /* ------------------------------------------------------------------------ */
  /* Get attribute values for a specific attribute                            */
  /* ------------------------------------------------------------------------ */

  const getAttributeValues = useCallback(async (attributeId) => {
    if (!attributeId) {
      return [];
    }

    try {
      // You can either use the already fetched attributes or make a new query
      const allAttributes = attributeData?.allAttributes?.edges?.map(edge => edge.node) ?? [];
      const attribute = allAttributes.find(attr => attr.id === attributeId);
      
      if (attribute) {
        return attribute.values?.edges?.map(edge => edge.node) ?? [];
      }

      // Fallback: fetch specific attribute values
      // You might want to add a GET_ATTRIBUTE_VALUES query here
      return [];
    } catch (error) {
      console.error("Failed to get attribute values:", error);
      return [];
    }
  }, [attributeData]);

  /* ------------------------------------------------------------------------ */
  /* Derived Values                                                           */
  /* ------------------------------------------------------------------------ */

  const isRefetching = networkStatus === 4;

  const product = useMemo(() => {
    if (!rawProduct) return null;

    // Get attributes for this product
    const attributes = attributeData?.allAttributes?.edges?.map(edge => edge.node) ?? [];
    
    // Filter attributes assigned to this product
    const productAttributes = attributes.filter(attr => {
      return attr.values?.edges?.some(valueEdge => {
        return valueEdge.node.assignedProducts?.edges?.some(
          assignment => assignment.node.product?.id === rawProduct.id
        );
      });
    });

    return {
      ...rawProduct,
      attributes: productAttributes,
      reviewSummary: {
        averageRating,
        totalReviews,
        distribution: ratingDistribution,
      },
    };
  }, [rawProduct, attributeData, averageRating, totalReviews, ratingDistribution]);

  const similarProducts = useMemo(
    () => similarData?.products?.edges?.map((edge) => edge.node) ?? [],
    [similarData]
  );

  /* ------------------------------------------------------------------------ */
  /* Combined State                                                           */
  /* ------------------------------------------------------------------------ */

  const loading = productLoading && !rawProduct;
  const loadingStates = {
    product: productLoading,
    reviews: reviewsLoading,
    similar: similarLoading,
    attributes: attributesLoading,
  };

  const error = productError || reviewsError || similarError || attributesError || null;

  const normalizedError = useMemo(() => {
    if (!error) return null;
    return {
      message: error.message ?? "Unable to load product details.",
      graphQLErrors: error.graphQLErrors ?? [],
      networkError: error.networkError ?? null,
    };
  }, [error]);

  /* ------------------------------------------------------------------------ */
  /* Derived States                                                           */
  /* ------------------------------------------------------------------------ */

  const hasProduct = !!product;
  const isEmpty = !loading && !product && !error;
  const inStock = (product?.stockQuantity ?? 0) > 0;

  /* ------------------------------------------------------------------------ */
  /* Refresh                                                                  */
  /* ------------------------------------------------------------------------ */

  const refreshProduct = useCallback(async () => {
    try {
      const result = await refetch();
      return result.data?.productBySlug ?? null;
    } catch (err) {
      console.warn("Product refresh failed:", err);
      return null;
    }
  }, [refetch]);

  /* ------------------------------------------------------------------------ */
  /* Load Attributes on Demand                                                */
  /* ------------------------------------------------------------------------ */

  const loadAttributes = useCallback(async () => {
    if (!attributesCalled) {
      await getProductAttributes();
    }
    return getAttributesForProduct();
  }, [attributesCalled, getProductAttributes, getAttributesForProduct]);

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Main Product Data
    product,
    rawProduct,

    // Reviews
    reviews,
    loadMoreReviews,
    hasMoreReviews,

    // Similar Products
    similarProducts,

    // Attributes
    attributes: product?.attributes ?? [],
    loadAttributes,
    getAttributesForProduct,
    getAttributeValues,
    attributesLoading,
    attributesCalled,

    // States
    loading,
    loadingStates,
    isRefetching,
    error: normalizedError,
    hasProduct,
    isEmpty,
    inStock,

    // Actions
    refetch,
    refreshProduct,
  };
}

export default useProduct;