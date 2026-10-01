/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductStickyFooter.jsx                                                    */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
  ActivityIndicator,
} from "react-native";

import { useSafeAreaInsets } from "react-native-safe-area-context";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductStickyFooter =
  memo(
    ({
      product,

      quantity = 1,

      loading = false,

      disabled = false,

      showWishlist = true,

      showBuyNow = true,

      onWishlist,

      onAddToCart,

      onBuyNow,

      style,
    }) => {
      const { colors } =
        theme;

      const insets =
        useSafeAreaInsets();

      /* ------------------------------------------------------------------ */
      /* Pricing                                                            */
      /* ------------------------------------------------------------------ */

      const pricing =
        useMemo(() => {
          const price =
            product?.price ?? 0;

          const originalPrice =
            product?.originalPrice;

          const hasDiscount =
            originalPrice >
            price;

          const discount =
            hasDiscount
              ? Math.round(
                  ((originalPrice -
                    price) /
                    originalPrice) *
                    100
                )
              : 0;

          return {
            price,
            originalPrice,
            hasDiscount,
            discount,
          };
        }, [product]);

      /* ------------------------------------------------------------------ */
      /* Actions                                                            */
      /* ------------------------------------------------------------------ */

      const handleWishlist =
        useCallback(() => {
          onWishlist?.(
            product
          );
        }, [
          product,
          onWishlist,
        ]);

      const handleAddToCart =
        useCallback(() => {
          onAddToCart?.({
            product,
            quantity,
          });
        }, [
          product,
          quantity,
          onAddToCart,
        ]);

      const handleBuyNow =
        useCallback(() => {
          onBuyNow?.({
            product,
            quantity,
          });
        }, [
          product,
          quantity,
          onBuyNow,
        ]);

      return (
        <View
          style={[
            styles.container,
            {
              paddingBottom:
                insets.bottom +
                12,

              backgroundColor:
                colors.card,

              borderTopColor:
                colors.border,
            },
            style,
          ]}
        >
          {/* -------------------------------------------------------------- */}
          {/* Price Section                                                  */}
          {/* -------------------------------------------------------------- */}

          <View
            style={
              styles.priceSection
            }
          >
            <Text
              style={[
                styles.price,
                {
                  color:
                    colors.primary,
                },
              ]}
            >
              {pricing.price}
            </Text>

            {pricing.hasDiscount && (
              <>
                <Text
                  style={[
                    styles.originalPrice,
                    {
                      color:
                        colors.textSecondary,
                    },
                  ]}
                >
                  {pricing.originalPrice}
                </Text>

                <View
                  style={[
                    styles.discountBadge,
                    {
                      backgroundColor:
                        colors.error,
                    },
                  ]}
                >
                  <Text
                    style={
                      styles.discountText
                    }
                  >
                    -{pricing.discount}%
                  </Text>
                </View>
              </>
            )}

            <View
              style={
                styles.stockRow
              }
            >
              <MaterialCommunityIcons
                name={
                  product?.inStock !==
                  false
                    ? "check-circle"
                    : "close-circle"
                }
                size={16}
                color={
                  product?.inStock !==
                  false
                    ? "#2E7D32"
                    : colors.error
                }
              />

              <Text
                style={[
                  styles.stockText,
                  {
                    color:
                      product?.inStock !==
                      false
                        ? "#2E7D32"
                        : colors.error,
                  },
                ]}
              >
                {product?.stockLabel ??
                  (product?.inStock !==
                  false
                    ? "In Stock"
                    : "Out of Stock")}
              </Text>
            </View>
          </View>
                    {/* -------------------------------------------------------------- */}
          {/* Action Buttons                                                 */}
          {/* -------------------------------------------------------------- */}

          <View
            style={
              styles.actionsContainer
            }
          >
            {/* ---------------------------------------------------------- */}
            {/* Wishlist                                                   */}
            {/* ---------------------------------------------------------- */}

            {showWishlist && (
              <Pressable
                onPress={
                  handleWishlist
                }
                disabled={
                  disabled ||
                  loading
                }
                style={[
                  styles.wishlistButton,
                  {
                    borderColor:
                      colors.border,

                    opacity:
                      disabled
                        ? 0.5
                        : 1,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name={
                    product?.isWishlisted
                      ? "heart"
                      : "heart-outline"
                  }
                  size={24}
                  color={
                    product?.isWishlisted
                      ? colors.error
                      : colors.text
                  }
                />
              </Pressable>
            )}

            {/* ---------------------------------------------------------- */}
            {/* Add To Cart                                                */}
            {/* ---------------------------------------------------------- */}

            <Pressable
              onPress={
                handleAddToCart
              }
              disabled={
                disabled ||
                loading ||
                product?.inStock ===
                  false
              }
              style={[
                styles.cartButton,
                {
                  borderColor:
                    colors.primary,

                  opacity:
                    disabled ||
                    product?.inStock ===
                      false
                      ? 0.6
                      : 1,
                },
              ]}
            >
              {loading ? (
                <ActivityIndicator
                  size="small"
                  color={
                    colors.primary
                  }
                />
              ) : (
                <>
                  <MaterialCommunityIcons
                    name="cart-outline"
                    size={20}
                    color={
                      colors.primary
                    }
                  />

                  <Text
                    style={[
                      styles.cartText,
                      {
                        color:
                          colors.primary,
                      },
                    ]}
                  >
                    Add to Cart
                  </Text>
                </>
              )}
            </Pressable>

            {/* ---------------------------------------------------------- */}
            {/* Buy Now                                                    */}
            {/* ---------------------------------------------------------- */}

            {showBuyNow && (
              <Pressable
                onPress={
                  handleBuyNow
                }
                disabled={
                  disabled ||
                  loading ||
                  product?.inStock ===
                    false
                }
                style={[
                  styles.buyButton,
                  {
                    backgroundColor:
                      colors.primary,

                    opacity:
                      disabled ||
                      product?.inStock ===
                        false
                        ? 0.6
                        : 1,
                  },
                ]}
              >
                {loading ? (
                  <ActivityIndicator
                    size="small"
                    color="#FFFFFF"
                  />
                ) : (
                  <>
                    <MaterialCommunityIcons
                      name="lightning-bolt"
                      size={20}
                      color="#FFFFFF"
                    />

                    <Text
                      style={
                        styles.buyText
                      }
                    >
                      Buy Now
                    </Text>
                  </>
                )}
              </Pressable>
            )}
          </View>
                    {/* -------------------------------------------------------------- */}
          {/* Information Bar                                                */}
          {/* -------------------------------------------------------------- */}

          <View
            style={[
              styles.infoContainer,
              {
                borderTopColor:
                  colors.border,
              },
            ]}
          >
            {/* ---------------------------------------------------------- */}
            {/* Delivery                                                   */}
            {/* ---------------------------------------------------------- */}

            <View
              style={
                styles.infoItem
              }
            >
              <MaterialCommunityIcons
                name="truck-fast-outline"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.infoText,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                {product?.deliveryEstimate ??
                  "Fast delivery available"}
              </Text>
            </View>

            {/* ---------------------------------------------------------- */}
            {/* Secure Checkout                                            */}
            {/* ---------------------------------------------------------- */}

            <View
              style={
                styles.infoItem
              }
            >
              <MaterialCommunityIcons
                name="shield-check-outline"
                size={18}
                color="#2E7D32"
              />

              <Text
                style={[
                  styles.infoText,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Secure checkout &
                buyer protection
              </Text>
            </View>

            {/* ---------------------------------------------------------- */}
            {/* Returns                                                    */}
            {/* ---------------------------------------------------------- */}

            <View
              style={
                styles.infoItem
              }
            >
              <MaterialCommunityIcons
                name="refresh-circle"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.infoText,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                {product?.returnPolicy ??
                  "Easy returns available"}
              </Text>
            </View>
          </View>
        </View>
      );
    }
);

ProductStickyFooter.displayName =
  "ProductStickyFooter";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const productShape = PropTypes.shape({
  id: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  name: PropTypes.string,

  price: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  originalPrice:
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

  inStock: PropTypes.bool,

  isWishlisted:
    PropTypes.bool,

  stockLabel:
    PropTypes.string,

  deliveryEstimate:
    PropTypes.string,

  returnPolicy:
    PropTypes.string,
});

ProductStickyFooter.propTypes = {
  product: productShape,

  quantity:
    PropTypes.number,

  loading:
    PropTypes.bool,

  disabled:
    PropTypes.bool,

  showWishlist:
    PropTypes.bool,

  showBuyNow:
    PropTypes.bool,

  onWishlist:
    PropTypes.func,

  onAddToCart:
    PropTypes.func,

  onBuyNow:
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

ProductStickyFooter.defaultProps =
  {
    product: null,

    quantity: 1,

    loading: false,

    disabled: false,

    showWishlist: true,

    showBuyNow: true,

    onWishlist: null,

    onAddToCart: null,

    onBuyNow: null,

    style: null,
  };

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      borderTopWidth: 1,

      paddingHorizontal: 16,

      paddingTop: 14,
    },

    /* ------------------------------------------------------------------ */
    /* Price Section                                                      */
    /* ------------------------------------------------------------------ */

    priceSection: {
      marginBottom: 16,
    },

    price: {
      fontSize: 24,

      fontWeight: "700",
    },

    originalPrice: {
      marginTop: 4,

      fontSize: 15,

      textDecorationLine:
        "line-through",
    },

    discountBadge: {
      alignSelf: "flex-start",

      marginTop: 8,

      borderRadius: 8,

      paddingHorizontal: 8,

      paddingVertical: 4,
    },

    discountText: {
      color: "#FFFFFF",

      fontSize: 12,

      fontWeight: "700",
    },

    stockRow: {
      flexDirection: "row",

      alignItems: "center",

      marginTop: 10,
    },

    stockText: {
      marginLeft: 6,

      fontSize: 13,

      fontWeight: "600",
    },

    /* ------------------------------------------------------------------ */
    /* Buttons                                                            */
    /* ------------------------------------------------------------------ */

    actionsContainer: {
      flexDirection: "row",

      alignItems: "center",

      marginBottom: 16,
    },

    wishlistButton: {
      width: 54,

      height: 54,

      borderWidth: 1,

      borderRadius: 14,

      justifyContent:
        "center",

      alignItems:
        "center",

      marginRight: 10,
    },

    cartButton: {
      flex: 1,

      height: 54,

      borderWidth: 1.5,

      borderRadius: 14,

      flexDirection: "row",

      justifyContent:
        "center",

      alignItems:
        "center",

      marginRight: 10,
    },

    cartText: {
      marginLeft: 8,

      fontSize: 15,

      fontWeight: "700",
    },

    buyButton: {
      flex: 1.2,

      height: 54,

      borderRadius: 14,

      flexDirection: "row",

      justifyContent:
        "center",

      alignItems:
        "center",
    },

    buyText: {
      marginLeft: 8,

      color: "#FFFFFF",

      fontSize: 15,

      fontWeight: "700",
    },

    /* ------------------------------------------------------------------ */
    /* Footer Information                                                 */
    /* ------------------------------------------------------------------ */

    infoContainer: {
      borderTopWidth: 1,

      paddingTop: 14,
    },

    infoItem: {
      flexDirection: "row",

      alignItems: "center",

      marginBottom: 10,
    },

    infoText: {
      flex: 1,

      marginLeft: 8,

      fontSize: 13,

      lineHeight: 18,
    },
  });

export default ProductStickyFooter;