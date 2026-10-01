/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useMarket.js                        */
/* -------------------------------------------------------------------------- */

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useQuery,
  useLazyQuery,
} from "@apollo/client/react";

import {
  GET_MARKET_ITEMS,
  GET_MARKET_ITEMS_GROUPED,
  GET_MY_PURCHASES,
} from "@/modules/ecommerce/api/gotomarketQueries/queries";

import {
  CREATE_PURCHASE,
} from "@/modules/ecommerce/api/gotomarketQueries/mutations";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const PAGE_SIZE = 20;

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const normalizeMarketItem = (item = {}) => ({
  id: item.id ?? "",
  name: item.name ?? "",
  category: item.category ?? "General",
  subcategory: item.subcategory ?? "",
  pricePerUnit: Number(item.pricePerUnit ?? 0),
  stock: Number(item.stock ?? 0),
  description: item.description ?? "",
  image: item.image ?? null,
  createdAt: item.createdAt ?? null,
  updatedAt: item.updatedAt ?? null,
});

const normalizePurchase = (purchase = {}) => ({
  id: purchase.id ?? "",
  purchaseNumber: purchase.purchaseNumber ?? "",
  createdAt: purchase.createdAt ?? null,
  subtotal: Number(purchase.subtotal ?? 0),
  vatRate: Number(purchase.vatRate ?? 0),
  vatAmount: Number(purchase.vatAmount ?? 0),
  discount: Number(purchase.discount ?? 0),
  total: Number(purchase.total ?? 0),
  pdfUrl: purchase.pdfUrl ?? "",
  items: purchase.items?.map(normalizePurchaseItem) ?? [],
});

const normalizePurchaseItem = (item = {}) => ({
  id: item.id ?? "",
  productName: item.productName ?? "",
  unitPrice: Number(item.unitPrice ?? 0),
  quantity: Number(item.quantity ?? 0),
  lineTotal: Number(item.lineTotal ?? 0),
});

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

export default function useMarket(options = {}) {
  const {
    category,
    subcategory,
    minPrice,
    maxPrice,
    inStockOnly = true,
    first = PAGE_SIZE,
  } = options;

  /* ------------------------------------------------------------------------ */
  /* State                                                                    */
  /* ------------------------------------------------------------------------ */

  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState(category || null);
  const [selectedSubcategory, setSelectedSubcategory] = useState(subcategory || null);

  /* ------------------------------------------------------------------------ */
  /* Market Items Query                                                       */
  /* ------------------------------------------------------------------------ */

  const {
    data: itemsData,
    loading: itemsLoading,
    error: itemsError,
    refetch: refetchItems,
    fetchMore,
    networkStatus,
  } = useQuery(GET_MARKET_ITEMS, {
    variables: {
      first,
      category: selectedCategory,
      subcategory: selectedSubcategory,
      priceGte: minPrice,
      priceLte: maxPrice,
      stockGt: inStockOnly ? 0 : undefined,
    },
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
  });

  /* ------------------------------------------------------------------------ */
  /* Grouped Items Query (for categorized view)                               */
  /* ------------------------------------------------------------------------ */

  const {
    data: groupedData,
    loading: groupedLoading,
    error: groupedError,
    refetch: refetchGrouped,
  } = useQuery(GET_MARKET_ITEMS_GROUPED, {
    fetchPolicy: "cache-and-network",
    skip: !!selectedCategory, // Skip if filtering by category
  });

  /* ------------------------------------------------------------------------ */
  /* My Purchases Query                                                       */
  /* ------------------------------------------------------------------------ */

  const {
    data: purchasesData,
    loading: purchasesLoading,
    error: purchasesError,
    refetch: refetchPurchases,
  } = useQuery(GET_MY_PURCHASES, {
    fetchPolicy: "cache-and-network",
  });

  /* ------------------------------------------------------------------------ */
  /* Create Purchase Mutation                                                 */
  /* ------------------------------------------------------------------------ */

  const [createPurchaseMutation, {
    loading: creatingPurchase,
    error: createPurchaseError,
  }] = useMutation(CREATE_PURCHASE);

  /* ------------------------------------------------------------------------ */
  /* Memoized Data                                                            */
  /* ------------------------------------------------------------------------ */

  const marketItems = useMemo(
    () => itemsData?.marketItems?.edges?.map(edge => normalizeMarketItem(edge.node)) ?? [],
    [itemsData]
  );

  const groupedItems = useMemo(
    () => groupedData?.marketItemsGrouped ?? [],
    [groupedData]
  );

  const myPurchases = useMemo(
    () => purchasesData?.myPurchases?.edges?.map(edge => normalizePurchase(edge.node)) ?? [],
    [purchasesData]
  );

  /* ------------------------------------------------------------------------ */
  /* Derived Data                                                             */
  /* ------------------------------------------------------------------------ */

  const categories = useMemo(
    () => [...new Set(marketItems.map(item => item.category))],
    [marketItems]
  );

  const subcategories = useMemo(
    () => {
      if (!selectedCategory) return [];
      return [...new Set(
        marketItems
          .filter(item => item.category === selectedCategory)
          .map(item => item.subcategory)
          .filter(Boolean)
      )];
    },
    [marketItems, selectedCategory]
  );

  const inStockItems = useMemo(
    () => marketItems.filter(item => item.stock > 0),
    [marketItems]
  );

  const outOfStockItems = useMemo(
    () => marketItems.filter(item => item.stock <= 0),
    [marketItems]
  );

  /* ------------------------------------------------------------------------ */
  /* Actions                                                                  */
  /* ------------------------------------------------------------------------ */

  const filterByCategory = useCallback((category) => {
    setSelectedCategory(category);
    setSelectedSubcategory(null);
  }, []);

  const filterBySubcategory = useCallback((subcategory) => {
    setSelectedSubcategory(subcategory);
  }, []);

  const clearFilters = useCallback(() => {
    setSelectedCategory(null);
    setSelectedSubcategory(null);
    setSearchTerm("");
  }, []);

  const searchItems = useCallback((term) => {
    setSearchTerm(term);
  }, []);

  const refresh = useCallback(async () => {
    await Promise.all([
      refetchItems(),
      refetchGrouped(),
      refetchPurchases(),
    ]);
  }, [refetchItems, refetchGrouped, refetchPurchases]);

  const loadMore = useCallback(async () => {
    const pageInfo = itemsData?.marketItems?.pageInfo;
    if (!pageInfo?.hasNextPage) return;

    await fetchMore({
      variables: {
        after: pageInfo.endCursor,
      },
      updateQuery: (previous, { fetchMoreResult }) => {
        if (!fetchMoreResult) return previous;
        return {
          ...fetchMoreResult,
          marketItems: {
            ...fetchMoreResult.marketItems,
            edges: [
              ...previous.marketItems.edges,
              ...fetchMoreResult.marketItems.edges,
            ],
          },
        };
      },
    });
  }, [itemsData, fetchMore]);

  /* ------------------------------------------------------------------------ */
  /* Create Purchase                                                          */
  /* ------------------------------------------------------------------------ */

  const createPurchase = useCallback(async (items, options = {}) => {
    const {
      vatRate = 0.07,
      discount = 0,
      sendEmail = false,
      sendWhatsapp = false,
    } = options;

    try {
      const { data } = await createPurchaseMutation({
        variables: {
          input: {
            items: items.map(item => ({
              itemId: item.id,
              quantity: item.quantity,
            })),
            vatRate,
            discount,
            sendEmail,
            sendWhatsapp,
          },
        },
      });

      const result = data?.createPurchase;
      if (result?.success) {
        await refetchPurchases();
        return {
          success: true,
          purchase: normalizePurchase(result.purchase),
          pdfUrl: result.pdfUrl,
          message: result.message,
        };
      }

      return {
        success: false,
        message: result?.message || "Purchase failed",
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    }
  }, [createPurchaseMutation, refetchPurchases]);

  /* ------------------------------------------------------------------------ */
  /* Error Normalization                                                      */
  /* ------------------------------------------------------------------------ */

  const error = useMemo(() => {
    const currentError = itemsError || groupedError || purchasesError || createPurchaseError;
    if (!currentError) return null;
    return {
      message: currentError.message ?? "Failed to load market data.",
      graphQLErrors: currentError.graphQLErrors ?? [],
      networkError: currentError.networkError ?? null,
    };
  }, [itemsError, groupedError, purchasesError, createPurchaseError]);

  /* ------------------------------------------------------------------------ */
  /* Loading States                                                           */
  /* ------------------------------------------------------------------------ */

  const loading = itemsLoading || groupedLoading || purchasesLoading || creatingPurchase;

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Data
    marketItems,
    groupedItems,
    myPurchases,
    categories,
    subcategories,
    inStockItems,
    outOfStockItems,

    // Filters
    selectedCategory,
    selectedSubcategory,
    searchTerm,
    filterByCategory,
    filterBySubcategory,
    clearFilters,
    searchItems,

    // Loading
    loading,
    itemsLoading,
    groupedLoading,
    purchasesLoading,
    creatingPurchase,

    // Error
    error,

    // Actions
    refresh,
    loadMore,
    createPurchase,
    refetchItems,
    refetchGrouped,
    refetchPurchases,

    // Pagination
    hasNextPage: itemsData?.marketItems?.pageInfo?.hasNextPage ?? false,
    endCursor: itemsData?.marketItems?.pageInfo?.endCursor ?? null,
    totalCount: itemsData?.marketItems?.totalCount ?? 0,
  };
}