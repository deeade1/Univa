/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/WishlistItem.jsx      */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";

import {
  View,
  Text,
  Image,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme"

import ProductPrice from "../products/ProductPrice";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const WishlistItem = memo(
  ({
    product,

    showBrand = true,

    showRating = true,

    showStock = true,

    showMoveToCart = true,

    showRemove = true,

    compact = false,

    onPress,

    onMoveToCart,

    onRemove,

    style,
  }) => {
    const { colors } = theme;


    const inStock =
      product?.inStock ??
      (product?.stock ?? 0) > 0;

    return (
      <Pressable
        onPress={() =>
          onPress?.(product)
        }
        style={[
          styles.container,
          {
            backgroundColor:
              colors.card,

            borderColor:
              colors.border,
          },
          compact &&
            styles.compact,
          style,
        ]}
      >
        {/* ---------------------------------------------------------- */}
        {/* Product Image */}
        {/* ---------------------------------------------------------- */}

        <Image
          source={{
            uri:
              product?.image,
          }}
          resizeMode="cover"
          style={styles.image}
        />

        {/* ---------------------------------------------------------- */}
        {/* Product Details */}
        {/* ---------------------------------------------------------- */}

        <View
          style={styles.content}
        >
          <Text
            numberOfLines={2}
            style={[
              styles.name,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {product?.name ??
              "Product"}
          </Text>

          {showBrand &&
            !!product?.brand && (
              <Text
                numberOfLines={1}
                style={[
                  styles.brand,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                {product.brand}
              </Text>
            )}

          {showRating && (
            <View
              style={
                styles.ratingRow
              }
            >
              <MaterialCommunityIcons
                name="star"
                size={15}
                color="#FBBF24"
              />

              <Text
                style={[
                  styles.rating,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                {(
                  product?.rating ??
                  0
                ).toFixed(1)}
              </Text>

              <Text
                style={[
                  styles.reviewCount,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                (
                {product?.reviewCount ??
                  0}
                )
              </Text>
            </View>
          )}

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
          />

          {showStock && (
            <View
              style={
                styles.stockRow
              }
            >
              <MaterialCommunityIcons
                name={
                  inStock
                    ? "check-circle"
                    : "close-circle"
                }
                size={15}
                color={
                  inStock
                    ? "#22C55E"
                    : "#EF4444"
                }
              />

              <Text
                style={[
                  styles.stock,
                  {
                    color:
                      inStock
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
          )}
        </View>

        {/* ---------------------------------------------------------- */}
        {/* Actions */}
        {/* ---------------------------------------------------------- */}

        <View
          style={styles.actions}
        >
          {showRemove && (
            <Pressable
              onPress={() =>
                onRemove?.(
                  product
                )
              }
              style={[
                styles.iconButton,
                {
                  backgroundColor:
                    colors.background,
                },
              ]}
            >
              <MaterialCommunityIcons
                name="heart-remove"
                size={20}
                color="#EF4444"
              />
            </Pressable>
          )}

          {showMoveToCart && (
            <Pressable
              disabled={
                !inStock
              }
              onPress={() =>
                onMoveToCart?.(
                  product
                )
              }
              style={[
                styles.cartButton,
                {
                  backgroundColor:
                    inStock
                      ? colors.primary
                      : colors.border,
                },
              ]}
            >
              <MaterialCommunityIcons
                name="cart-plus"
                size={18}
                color="#FFFFFF"
              />
            </Pressable>
          )}
        </View>
      </Pressable>
    );
  }
);

WishlistItem.displayName =
  "WishlistItem";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flexDirection: "row",

      alignItems: "center",

      borderWidth: 1,

      borderRadius: 18,

      padding: 14,

      marginBottom: 16,
    },

    compact: {
      padding: 10,
    },

    image: {
      width: 90,

      height: 90,

      borderRadius: 12,

      backgroundColor:
        "#E5E7EB",
    },

    content: {
      flex: 1,

      marginLeft: 14,
    },

    name: {
      fontSize: 15,

      fontWeight: "700",
    },

    brand: {
      marginTop: 4,

      fontSize: 13,
    },

    ratingRow: {
      flexDirection: "row",

      alignItems: "center",

      marginTop: 8,
    },

    rating: {
      marginLeft: 4,

      fontWeight: "600",
    },

    reviewCount: {
      marginLeft: 5,

      fontSize: 12,
    },

    stockRow: {
      flexDirection: "row",

      alignItems: "center",

      marginTop: 8,
    },

    stock: {
      marginLeft: 5,

      fontSize: 12,

      fontWeight: "600",
    },

    actions: {
      justifyContent:
        "space-between",

      alignItems: "center",

      marginLeft: 12,

      height: 90,
    },

    iconButton: {
      width: 38,

      height: 38,

      borderRadius: 19,

      justifyContent:
        "center",

      alignItems:
        "center",
    },

    cartButton: {
      width: 42,

      height: 42,

      borderRadius: 21,

      justifyContent:
        "center",

      alignItems:
        "center",
    },
  });

export default WishlistItem;