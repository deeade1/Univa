/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/WishlistScreen.jsx    */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useState,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  SafeAreaView,
  View,
  StyleSheet,
} from "react-native";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Wishlist Components                                                        */
/* -------------------------------------------------------------------------- */

import WishlistHeader from "./WishlistHeader";
import WishlistSummary from "./WishlistSummary";
import WishlistFilters from "./WishlistFilters";
import WishlistSection from "./WishlistSection";
import WishlistGrid from "./WishlistGrid";
import WishlistSkeleton from "./WishlistSkeleton";
import EmptyWishlist from "./EmptyWishlist";
import WishlistShareButton from "./WishlistShareButton";
import WishlistMoveToCart from "./WishlistMoveToCart";

/* -------------------------------------------------------------------------- */
/* Filter Options                                                             */
/* -------------------------------------------------------------------------- */

const FILTER_OPTIONS = [
  {
    label: "All",
    value: "all",
  },
  {
    label: "In Stock",
    value: "inStock",
  },
  {
    label: "On Sale",
    value: "sale",
  },
  {
    label: "Free Shipping",
    value: "shipping",
  },
];

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const WishlistScreen = memo(
  ({
    products = [],

    loading = false,

    refreshing = false,

    selectedFilter = "all",

    onRefresh,

    onProductPress,

    onWishlistPress,

    onAddToCart,

    onMoveAllToCart,

    onShareWishlist,

    onFilterChange,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Local State                                                            */
    /* ---------------------------------------------------------------------- */

    const [
      activeFilter,
      setActiveFilter,
    ] = useState(
      selectedFilter
    );

    /* ---------------------------------------------------------------------- */
    /* Statistics                                                             */
    /* ---------------------------------------------------------------------- */

    const totalItems =
      products.length;

    const inStockCount =
      useMemo(
        () =>
          products.filter(
            (item) =>
              item?.inStock ??
              item?.stock > 0
          ).length,
        [products]
      );

    const saleCount =
      useMemo(
        () =>
          products.filter(
            (item) =>
              !!item?.salePrice ||
              !!item?.discount
          ).length,
        [products]
      );

    /* ---------------------------------------------------------------------- */
    /* Filtered Products                                                     */
    /* ---------------------------------------------------------------------- */

    const filteredProducts =
      useMemo(() => {
        switch (
          activeFilter
        ) {
          case "inStock":
            return products.filter(
              (item) =>
                item?.inStock ??
                item?.stock > 0
            );

          case "sale":
            return products.filter(
              (item) =>
                item?.salePrice ||
                item?.discount
            );

          case "shipping":
            return products.filter(
              (item) =>
                item?.freeShipping
            );

          default:
            return products;
        }
      }, [
        activeFilter,
        products,
      ]);

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleFilterChange =
      useCallback(
        (value) => {
          setActiveFilter(
            value
          );

          onFilterChange?.(
            value
          );
        },
        [onFilterChange]
      );

    const handleMoveAll =
      useCallback(() => {
        onMoveAllToCart?.(
          filteredProducts
        );
      }, [
        filteredProducts,
        onMoveAllToCart,
      ]);

    const handleShare =
      useCallback(() => {
        onShareWishlist?.(
          filteredProducts
        );
      }, [
        filteredProducts,
        onShareWishlist,
      ]);

    /* ---------------------------------------------------------------------- */
    /* Early Returns                                                          */
    /* ---------------------------------------------------------------------- */

    if (loading) {
      return (
        <WishlistSkeleton />
      );
    }

    if (
      !loading &&
      filteredProducts.length ===
        0
    ) {
      return (
        <EmptyWishlist />
      );
    }

    /* ---------------------------------------------------------------------- */
    /* Continue in Part 2...                                                  */
    /* ---------------------------------------------------------------------- */
    /* -------------------------------------------------------------------------- */
/* Render                                                                     */
/* -------------------------------------------------------------------------- */

    return (
      <SafeAreaView
        style={[
          styles.container,
          {
            backgroundColor:
              colors.background,
          },
          style,
        ]}
      >
        <WishlistSection
          title="My Wishlist"
          subtitle={`${totalItems} saved item${
            totalItems === 1
              ? ""
              : "s"
          }`}
          icon="heart"
          badge={totalItems}
        >
          {/* -------------------------------------------------------------- */}
          {/* Header                                                         */}
          {/* -------------------------------------------------------------- */}

          <WishlistHeader
            title="Wishlist"
            subtitle="Save your favourite products for later."
            count={totalItems}
          />

          {/* -------------------------------------------------------------- */}
          {/* Summary                                                        */}
          {/* -------------------------------------------------------------- */}

          <WishlistSummary
            totalItems={
              totalItems
            }
            inStock={
              inStockCount
            }
            onSale={
              saleCount
            }
            style={
              styles.summary
            }
          />

          {/* -------------------------------------------------------------- */}
          {/* Filters                                                        */}
          {/* -------------------------------------------------------------- */}

          <WishlistFilters
            filters={
              FILTER_OPTIONS
            }
            selectedFilter={
              activeFilter
            }
            onSelectFilter={
              handleFilterChange
            }
            style={
              styles.filters
            }
          />

          {/* -------------------------------------------------------------- */}
          {/* Bulk Actions                                                   */}
          {/* -------------------------------------------------------------- */}

          <View
            style={
              styles.bulkActions
            }
          >
            <WishlistMoveToCart
              label="Move All"
              fullWidth={
                false
              }
              inStock={
                inStockCount >
                0
              }
              onPress={
                handleMoveAll
              }
              style={
                styles.actionButton
              }
            />

            <WishlistShareButton
              label="Share"
              fullWidth={
                false
              }
              onPress={
                handleShare
              }
              style={
                styles.actionButton
              }
            />
          </View>

          {/* -------------------------------------------------------------- */}
          {/* Continue in Part 3                                             */}
          {/* -------------------------------------------------------------- */}
          /* -------------------------------------------------------------- */
/* Wishlist Content                                                */
/* -------------------------------------------------------------- */

          <WishlistGrid
            products={
              filteredProducts
            }
            loading={
              loading
            }
            refreshing={
              refreshing
            }
            onRefresh={
              onRefresh
            }
            onProductPress={
              onProductPress
            }
            onWishlistPress={
              onWishlistPress
            }
            onAddToCart={
              onAddToCart
            }
            numColumns={2}
            contentContainerStyle={
              styles.gridContent
            }
            ListFooterComponent={
              <View
                style={
                  styles.footerSpacing
                }
              />
            }
          />
        </WishlistSection>
      </SafeAreaView>
    );
  }
);

WishlistScreen.displayName =
  "WishlistScreen";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

WishlistScreen.propTypes = {
  /**
   * Wishlist products.
   */
  products: PropTypes.arrayOf(
    PropTypes.object
  ),

  /**
   * Loading state.
   */
  loading: PropTypes.bool,

  /**
   * Pull-to-refresh state.
   */
  refreshing:
    PropTypes.bool,

  /**
   * Initially selected filter.
   */
  selectedFilter:
    PropTypes.string,

  /**
   * Refresh callback.
   */
  onRefresh:
    PropTypes.func,

  /**
   * Product selected.
   */
  onProductPress:
    PropTypes.func,

  /**
   * Wishlist icon pressed.
   */
  onWishlistPress:
    PropTypes.func,

  /**
   * Single add-to-cart.
   */
  onAddToCart:
    PropTypes.func,

  /**
   * Move all products.
   */
  onMoveAllToCart:
    PropTypes.func,

  /**
   * Share wishlist.
   */
  onShareWishlist:
    PropTypes.func,

  /**
   * Filter changed.
   */
  onFilterChange:
    PropTypes.func,

  /**
   * Container style.
   */
  style:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

WishlistScreen.defaultProps = {
  products: [],

  loading: false,

  refreshing: false,

  selectedFilter: "all",

  onRefresh: null,

  onProductPress: null,

  onWishlistPress: null,

  onAddToCart: null,

  onMoveAllToCart: null,

  onShareWishlist: null,

  onFilterChange: null,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flex: 1,
    },

    summary: {
      marginTop: 20,
    },

    filters: {
      marginTop: 18,
      marginBottom: 20,
    },

    bulkActions: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent:
        "space-between",
      marginBottom: 20,
    },

    actionButton: {
      flex: 1,
      marginHorizontal: 6,
    },

    gridContent: {
      paddingBottom: 32,
    },

    footerSpacing: {
      height: 40,
    },
  });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default WishlistScreen;