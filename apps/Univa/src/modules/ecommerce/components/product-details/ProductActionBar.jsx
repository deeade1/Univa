/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductActionBar.jsx                                                       */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useState,
  useEffect,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import Button from "../common/Button";
import ProductPrice from "../products/ProductPrice";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductActionBar = memo(
  ({
    product,

    quantity = 1,

    visible = true,

    showWishlist = true,

    showPrice = true,

    showQuantity = true,

    loading = false,

    disabled = false,

    onAddToCart,

    onBuyNow,

    onWishlist,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Local State                                                            */
    /* ---------------------------------------------------------------------- */

    const [
      currentQuantity,
      setCurrentQuantity,
    ] = useState(quantity);

    useEffect(() => {
      setCurrentQuantity(
        quantity
      );
    }, [quantity]);

    /* ---------------------------------------------------------------------- */
    /* Derived Values                                                         */
    /* ---------------------------------------------------------------------- */

    const isInStock =
      inStock ??
      product?.inStock ??
      (product?.stock ?? 0) > 0;

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const increment =
      useCallback(() => {
        if (
          !disabled &&
          currentQuantity <
            (product?.stock ??
              99)
        ) {
          setCurrentQuantity(
            (value) =>
              value + 1
          );
        }
      }, [
        currentQuantity,
        disabled,
        product,
      ]);

    const decrement =
      useCallback(() => {
        if (
          !disabled &&
          currentQuantity > 1
        ) {
          setCurrentQuantity(
            (value) =>
              value - 1
          );
        }
      }, [
        currentQuantity,
        disabled,
      ]);

    const handleAddToCart =
      useCallback(() => {
        onAddToCart?.(
          product,
          currentQuantity
        );
      }, [
        onAddToCart,
        product,
        currentQuantity,
      ]);

    const handleBuyNow =
      useCallback(() => {
        onBuyNow?.(
          product,
          currentQuantity
        );
      }, [
        onBuyNow,
        product,
        currentQuantity,
      ]);

    const handleWishlist =
      useCallback(() => {
        onWishlist?.(product);
      }, [
        onWishlist,
        product,
      ]);

    if (!visible) {
      return null;
    }

    return (
      <View
        style={[
          styles.container,
          {
            backgroundColor:
              colors.card,

            borderTopColor:
              colors.border,
          },
          style,
        ]}
      >
                {/* -------------------------------------------------------------- */}
        {/* Left Section                                                   */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.leftSection}>
          {/* ---------------------------------------------------------- */}
          {/* Price                                                      */}
          {/* ---------------------------------------------------------- */}

          {showPrice && (
            <ProductPrice
              price={
                product?.price
              }
              salePrice={
                product?.salePrice
              }
              discount={
                product?.discount
              }
              currency={
                product?.currency
              }
            />
          )}

          {/* ---------------------------------------------------------- */}
          {/* Stock Status                                               */}
          {/* ---------------------------------------------------------- */}

          <View
            style={
              styles.stockRow
            }
          >
            <MaterialCommunityIcons
              name={
                isInStock
                  ? "check-circle"
                  : "close-circle"
              }
              size={16}
              color={
                isInStock
                  ? "#22C55E"
                  : "#EF4444"
              }
            />

            <Text
              style={[
                styles.stockText,
                {
                  color:
                    isInStock
                      ? "#22C55E"
                      : "#EF4444",
                },
              ]}
            >
              {inStock
                ? "In Stock"
                : "Out of Stock"}
            </Text>
          </View>

          {/* ---------------------------------------------------------- */}
          {/* Quantity Selector                                          */}
          {/* ---------------------------------------------------------- */}

          {showQuantity && (
            <View
              style={
                styles.quantityRow
              }
            >
              <Pressable
                disabled={
                  disabled ||
                  currentQuantity <=
                    1
                }
                onPress={
                  decrement
                }
                style={[
                  styles.quantityButton,
                  {
                    borderColor:
                      colors.border,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name="minus"
                  size={18}
                  color={
                    colors.text
                  }
                />
              </Pressable>

              <Text
                style={[
                  styles.quantityText,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                {currentQuantity}
              </Text>

              <Pressable
                disabled={
                  disabled ||
                  !isInStock
                }
                onPress={
                  increment
                }
                style={[
                  styles.quantityButton,
                  {
                    borderColor:
                      colors.border,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name="plus"
                  size={18}
                  color={
                    colors.text
                  }
                />
              </Pressable>
            </View>
          )}

          {/* ---------------------------------------------------------- */}
          {/* Wishlist                                                   */}
          {/* ---------------------------------------------------------- */}

          {showWishlist && (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Add to wishlist"
              onPress={
                handleWishlist
              }
              style={[
                styles.wishlistButton,
                {
                  borderColor:
                    colors.border,
                },
              ]}
            >
              <MaterialCommunityIcons
                name="heart-outline"
                size={20}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.wishlistText,
                  {
                    color:
                      colors.primary,
                  },
                ]}
              >
                Wishlist
              </Text>
            </Pressable>
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Right Section                                                  */}
        {/* -------------------------------------------------------------- */}

        <View
          style={styles.rightSection}
        >        {/* -------------------------------------------------------------- */}
        {/* Add to Cart                                                    */}
        {/* -------------------------------------------------------------- */}

        <Button
          title="Add to Cart"
          icon="cart-plus"
          loading={loading}
          disabled={
            disabled ||
            !isInStock
          }
          variant="outline"
          fullWidth
          onPress={
            handleAddToCart
          }
          style={
            styles.addToCartButton
          }
        />

        {/* -------------------------------------------------------------- */}
        {/* Buy Now                                                        */}
        {/* -------------------------------------------------------------- */}

        <Button
          title="Buy Now"
          icon="lightning-bolt"
          loading={loading}
          disabled={
            disabled ||
            !isInStock
          }
          fullWidth
          onPress={
            handleBuyNow
          }
          style={
            styles.buyNowButton
          }
        >
          {!loading && (
            <View
              style={
                styles.buyNowContent
              }
            >
              <MaterialCommunityIcons
                name="flash"
                size={18}
                color="#FFFFFF"
              />

              <Text
                style={
                  styles.buyNowText
                }
              >
                Buy Now
              </Text>
            </View>
          )}
        </Button>
      </View>
    </View>
  );
});

ProductActionBar.displayName =
  "ProductActionBar";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductActionBar.propTypes = {
  /**
   * Product object
   */
  product: PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    price:
      PropTypes.oneOfType([
        PropTypes.number,
        PropTypes.string,
      ]),

    salePrice:
      PropTypes.oneOfType([
        PropTypes.number,
        PropTypes.string,
      ]),

    discount:
      PropTypes.oneOfType([
        PropTypes.number,
        PropTypes.string,
      ]),

    currency:
      PropTypes.string,

    stock:
      PropTypes.number,

    isInStock:
      PropTypes.bool,
  }),

  quantity:
    PropTypes.number,

  visible:
    PropTypes.bool,

  showWishlist:
    PropTypes.bool,

  showPrice:
    PropTypes.bool,

  showQuantity:
    PropTypes.bool,

  loading:
    PropTypes.bool,

  disabled:
    PropTypes.bool,

  onAddToCart:
    PropTypes.func,

  onBuyNow:
    PropTypes.func,

  onWishlist:
    PropTypes.func,

  style:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ProductActionBar.defaultProps = {
  product: null,

  quantity: 1,

  visible: true,

  showWishlist: true,

  showPrice: true,

  showQuantity: true,

  loading: false,

  disabled: false,

  onAddToCart: null,

  onBuyNow: null,

  onWishlist: null,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flexDirection: "row",

      alignItems: "center",

      justifyContent:
        "space-between",

      borderTopWidth: 1,

      paddingHorizontal: 16,

      paddingVertical: 14,
    },

    /* ------------------------------------------------------------------ */
    /* Left Section                                                       */
    /* ------------------------------------------------------------------ */

    leftSection: {
      flex: 1,

      paddingRight: 16,
    },

    stockRow: {
      flexDirection: "row",

      alignItems: "center",

      marginTop: 8,
    },

    stockText: {
      marginLeft: 6,

      fontSize: 13,

      fontWeight: "600",
    },

    quantityRow: {
      flexDirection: "row",

      alignItems: "center",

      marginTop: 14,
    },

    quantityButton: {
      width: 36,

      height: 36,

      borderWidth: 1,

      borderRadius: 10,

      justifyContent:
        "center",

      alignItems: "center",
    },

    quantityText: {
      minWidth: 42,

      textAlign: "center",

      fontSize: 16,

      fontWeight: "700",
    },

    wishlistButton: {
      flexDirection: "row",

      alignItems: "center",

      alignSelf: "flex-start",

      borderWidth: 1,

      borderRadius: 10,

      marginTop: 16,

      paddingHorizontal: 14,

      paddingVertical: 10,
    },

    wishlistText: {
      marginLeft: 8,

      fontWeight: "600",

      fontSize: 14,
    },

    /* ------------------------------------------------------------------ */
    /* Right Section                                                      */
    /* ------------------------------------------------------------------ */

    rightSection: {
      width: 170,

      justifyContent:
        "center",
    },

    addToCartButton: {
      marginBottom: 12,
    },

    buyNowButton: {
      minHeight: 48,
    },

    buyNowContent: {
      flexDirection: "row",

      alignItems: "center",

      justifyContent:
        "center",
    },

    buyNowText: {
      marginLeft: 8,

      color: "#FFFFFF",

      fontSize: 15,

      fontWeight: "700",
    },
  });

export default ProductActionBar;