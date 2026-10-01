/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchResultsGrid.jsx   */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import {
  View,
  FlatList,
  RefreshControl,
  ActivityIndicator,
  StyleSheet,
} from "react-native";

import theme from "@/theme";

import ProductCard from "../products/ProductCard";
import SearchEmpty from "./SearchEmpty";
import SearchSkeleton from "./SearchSkeleton";

/* -------------------------------------------------------------------------- */

const SearchResultsGrid = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Data                                                                    */
    /* ---------------------------------------------------------------------- */

    products = [],

    /* ---------------------------------------------------------------------- */
    /* Layout                                                                  */
    /* ---------------------------------------------------------------------- */

    columns = 2,

    mode = "grid", // grid | list

    spacing = 16,

    /* ---------------------------------------------------------------------- */
    /* Loading                                                                 */
    /* ---------------------------------------------------------------------- */

    loading = false,

    loadingMore = false,

    refreshing = false,

    /* ---------------------------------------------------------------------- */
    /* Empty State                                                             */
    /* ---------------------------------------------------------------------- */

    query = "",

    emptyTitle,

    emptyMessage,

    /* ---------------------------------------------------------------------- */
    /* Actions                                                                 */
    /* ---------------------------------------------------------------------- */

    onProductPress,

    onAddToCart,

    onWishlistPress,

    onRefresh,

    onLoadMore,

    onRetry,

    /* ---------------------------------------------------------------------- */
    /* Pagination                                                              */
    /* ---------------------------------------------------------------------- */

    hasNextPage = false,

    /* ---------------------------------------------------------------------- */
    /* FlatList                                                                */
    /* ---------------------------------------------------------------------- */

    contentContainerStyle,

    ListHeaderComponent,

    ListFooterComponent,

    ListEmptyComponent,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */
    /* Derived Data                                                            */
    /* ---------------------------------------------------------------------- */

    const data =
      useMemo(
        () => products ?? [],
        [products]
      );

    const isEmpty =
      !loading &&
      data.length === 0;

    /* ---------------------------------------------------------------------- */
    /* Key Extractor                                                           */
    /* ---------------------------------------------------------------------- */

    const keyExtractor =
      useCallback(
        (item, index) =>
          String(
            item?.id ??
              item?.slug ??
              index
          ),
        []
      );

    /* ---------------------------------------------------------------------- */
    /* Refresh                                                                 */
    /* ---------------------------------------------------------------------- */

    const refreshControl =
      useMemo(
        () => (
          <RefreshControl
            refreshing={
              refreshing
            }
            onRefresh={
              onRefresh
            }
            tintColor={
              colors.primary
            }
            colors={[
              colors.primary,
            ]}
          />
        ),
        [
          refreshing,
          onRefresh,
          colors,
        ]
      );

    /* ---------------------------------------------------------------------- */
    /* End Reached                                                             */
    /* ---------------------------------------------------------------------- */

    const handleEndReached =
      useCallback(() => {
        if (
          loading ||
          loadingMore ||
          !hasNextPage
        ) {
          return;
        }

        onLoadMore?.();
      }, [
        loading,
        loadingMore,
        hasNextPage,
        onLoadMore,
      ]);

    /* ---------------------------------------------------------------------- */
    /* Skeleton                                                                */
    /* ---------------------------------------------------------------------- */

    if (loading) {
      return (
        <SearchSkeleton
          mode={mode}
          columns={columns}
          style={style}
        />
      );
    }

    /* ---------------------------------------------------------------------- */
    /* Empty                                                                   */
    /* ---------------------------------------------------------------------- */

    if (isEmpty) {
      return (
        ListEmptyComponent ?? (
          <SearchEmpty
            query={query}
            title={
              emptyTitle
            }
            message={
              emptyMessage
            }
            showButton={
              !!onRetry
            }
            buttonText="Try Again"
            onPress={onRetry}
          />
        )
      );
    }

    /* ---------------------------------------------------------------------- */
    /* Part 2                                                                  */
    /* ---------------------------------------------------------------------- */
        /* ---------------------------------------------------------------------- */
    /* Render Product                                                          */
    /* ---------------------------------------------------------------------- */

    const renderItem =
      useCallback(
        ({ item }) => (
          <ProductCard
            product={item}
            mode={mode}
            onPress={() =>
              onProductPress?.(
                item
              )
            }
            onAddToCart={() =>
              onAddToCart?.(
                item
              )
            }
            onWishlistPress={() =>
              onWishlistPress?.(
                item
              )
            }
          />
        ),
        [
          mode,
          onProductPress,
          onAddToCart,
          onWishlistPress,
        ]
      );

    /* ---------------------------------------------------------------------- */
    /* Footer                                                                  */
    /* ---------------------------------------------------------------------- */

    const renderFooter =
      useCallback(() => {
        if (loadingMore) {
          return (
            <View
              style={
                styles.footerLoader
              }
            >
              <ActivityIndicator
                size="small"
                color={
                  colors.primary
                }
              />
            </View>
          );
        }

        return (
          ListFooterComponent ??
          null
        );
      }, [
        loadingMore,
        colors.primary,
        ListFooterComponent,
      ]);

    /* ---------------------------------------------------------------------- */
    /* Separator                                                               */
    /* ---------------------------------------------------------------------- */

    const renderSeparator =
      useCallback(
        () => (
          <View
            style={{
              height:
                spacing,
            }}
          />
        ),
        [spacing]
      );

    /* ---------------------------------------------------------------------- */
    /* Render                                                                  */
    /* ---------------------------------------------------------------------- */

    return (
      <FlatList
        data={data}
        renderItem={
          renderItem
        }
        keyExtractor={
          keyExtractor
        }
        numColumns={
          mode === "grid"
            ? columns
            : 1
        }
        key={
          mode === "grid"
            ? `grid-${columns}`
            : "list"
        }
        refreshControl={
          refreshControl
        }
        ListHeaderComponent={
          ListHeaderComponent
        }
        ListFooterComponent={
          renderFooter
        }
        ItemSeparatorComponent={
          mode === "list"
            ? renderSeparator
            : undefined
        }
        contentContainerStyle={[
          styles.content,

          {
            padding:
              spacing,
          },

          contentContainerStyle,
        ]}
        columnWrapperStyle={
          mode === "grid"
            ? {
                justifyContent:
                  "space-between",

                marginBottom:
                  spacing,
              }
            : undefined
        }
        showsVerticalScrollIndicator={
          false
        }
        keyboardShouldPersistTaps="handled"
        initialNumToRender={
          8
        }
        maxToRenderPerBatch={
          8
        }
        updateCellsBatchingPeriod={
          50
        }
        windowSize={
          11
        }
        removeClippedSubviews
        onEndReached={
          handleEndReached
        }
        onEndReachedThreshold={
          0.5
        }
        style={style}
      />
    );
    /* ---------------------------------------------------------------------- */
  }
);

/* -------------------------------------------------------------------------- */

SearchResultsGrid.displayName =
  "SearchResultsGrid";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    content: {
      flexGrow: 1,
    },

    footerLoader: {
      paddingVertical: 24,

      justifyContent: "center",

      alignItems: "center",
    },
  });

/* -------------------------------------------------------------------------- */

export default SearchResultsGrid;