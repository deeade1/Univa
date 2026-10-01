/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/WishlistGrid.jsx      */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  StyleSheet,
  RefreshControl,
} from "react-native";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
// Product Components
/* -------------------------------------------------------------------------- */

import ProductGrid from "../products/ProductGrid";
import EmptyWishlist from "./EmptyWishlist";
import WishlistSkeleton from "./WishlistSkeleton";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const WishlistGrid = memo(({
  products = [],
  loading = false,
  refreshing = false,
  error = null,
  numColumns = 2,
  compact = false,
  showWishlist = false, // Wishlist button is hidden in wishlist by default
  showAddToCart = true,
  ListHeaderComponent,
  ListFooterComponent,
  contentContainerStyle,
  style,
  onRefresh,
  onRetry,
  onProductPress,
  onWishlistPress,
  onAddToCart,
  keyExtractor,
}) => {
  const { colors } = theme;

  /* ---------------------------------------------------------------------- */
  /* Memoized Values                                                        */
  /* ---------------------------------------------------------------------- */

  const data = useMemo(
    () => products ?? [],
    [products]
  );

  /* ---------------------------------------------------------------------- */
  /* Memoized Key Extractor                                                 */
  /* ---------------------------------------------------------------------- */

  const defaultKeyExtractor = useCallback(
    (item, index) => {
      if (item?.id) return String(item.id);
      if (item?.pk) return String(item.pk);
      if (item?.uuid) return item.uuid;
      return `wishlist-item-${index}`;
    },
    []
  );

  const extractKey = useCallback(
    (item, index) => {
      if (keyExtractor) {
        return keyExtractor(item, index);
      }
      return defaultKeyExtractor(item, index);
    },
    [keyExtractor, defaultKeyExtractor]
  );

  /* ---------------------------------------------------------------------- */
  /* Memoized Handlers                                                      */
  /* ---------------------------------------------------------------------- */

  const handleRefresh = useCallback(() => {
    onRefresh?.();
  }, [onRefresh]);

  /* ---------------------------------------------------------------------- */
  /* Memoized Empty Component                                               */
  /* ---------------------------------------------------------------------- */

  const EmptyComponent = useMemo(
    () => <EmptyWishlist />,
    []
  );

  /* ---------------------------------------------------------------------- */
  /* Memoized Refresh Control                                               */
  /* ---------------------------------------------------------------------- */

  const RefreshControlComponent = useMemo(
    () => (
      <RefreshControl
        refreshing={refreshing}
        onRefresh={handleRefresh}
        tintColor={colors.primary}
        colors={[colors.primary]}
      />
    ),
    [refreshing, handleRefresh, colors.primary]
  );

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  // Loading state
  if (loading && data.length === 0) {
    return <WishlistSkeleton />;
  }

  // Error state
  if (error && data.length === 0) {
    return (
      <EmptyWishlist
        title="Unable to load wishlist"
        description={error.message || "Please try again"}
        onRetry={onRetry}
      />
    );
  }

  // Use ProductGrid for rendering
  return (
    <ProductGrid
      products={data}
      numColumns={numColumns}
      compact={compact}
      showWishlist={showWishlist}
      showAddToCart={showAddToCart}
      loading={false} // Loading handled above
      ListHeaderComponent={ListHeaderComponent}
      ListFooterComponent={ListFooterComponent}
      ListEmptyComponent={EmptyComponent}
      contentContainerStyle={[
        styles.content,
        data.length === 0 && styles.emptyContent,
        contentContainerStyle,
      ]}
      columnWrapperStyle={numColumns > 1 ? styles.column : undefined}
      refreshControl={RefreshControlComponent}
      onProductPress={onProductPress}
      onWishlistPress={onWishlistPress}
      onAddToCart={onAddToCart}
      keyExtractor={extractKey}
      style={style}
      // Pass through additional ProductGrid props
      removeClippedSubviews
      initialNumToRender={6}
      maxToRenderPerBatch={8}
      windowSize={10}
      updateCellsBatchingPeriod={50}
    />
  );
});

WishlistGrid.displayName = "WishlistGrid";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

WishlistGrid.propTypes = {
  /**
   * Array of product objects in the wishlist
   */
  products: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      pk: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      uuid: PropTypes.string,
      name: PropTypes.string,
      price: PropTypes.number,
      image: PropTypes.string,
    })
  ),

  /**
   * Loading state for skeleton/placeholders
   */
  loading: PropTypes.bool,

  /**
   * Refreshing state for pull-to-refresh
   */
  refreshing: PropTypes.bool,

  /**
   * Error state for error handling
   */
  error: PropTypes.shape({
    message: PropTypes.string,
  }),

  /**
   * Number of columns in the grid
   */
  numColumns: PropTypes.number,

  /**
   * Compact mode for product cards
   */
  compact: PropTypes.bool,

  /**
   * Show wishlist button on product cards
   */
  showWishlist: PropTypes.bool,

  /**
   * Show add to cart button on product cards
   */
  showAddToCart: PropTypes.bool,

  /**
   * Component rendered at the top of the list
   */
  ListHeaderComponent: PropTypes.elementType,

  /**
   * Component rendered at the bottom of the list
   */
  ListFooterComponent: PropTypes.elementType,

  /**
   * Content container style
   */
  contentContainerStyle: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),

  /**
   * Optional style overrides
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),

  /**
   * Refresh handler for pull-to-refresh
   */
  onRefresh: PropTypes.func,

  /**
   * Retry handler for error state
   */
  onRetry: PropTypes.func,

  /**
   * Product press handler
   */
  onProductPress: PropTypes.func,

  /**
   * Wishlist button press handler
   */
  onWishlistPress: PropTypes.func,

  /**
   * Add to cart handler
   */
  onAddToCart: PropTypes.func,

  /**
   * Custom key extractor function
   */
  keyExtractor: PropTypes.func,
};

WishlistGrid.defaultProps = {
  products: [],
  loading: false,
  refreshing: false,
  error: null,
  numColumns: 2,
  compact: false,
  showWishlist: false,
  showAddToCart: true,
  ListHeaderComponent: null,
  ListFooterComponent: null,
  contentContainerStyle: null,
  style: null,
  onRefresh: null,
  onRetry: null,
  onProductPress: null,
  onWishlistPress: null,
  onAddToCart: null,
  keyExtractor: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  content: {
    padding: 16,
  },

  emptyContent: {
    flexGrow: 1,
    justifyContent: "center",
  },

  column: {
    justifyContent: "space-between",
  },
});

export default WishlistGrid;