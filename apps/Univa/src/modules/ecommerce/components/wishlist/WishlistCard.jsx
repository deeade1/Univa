/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/WishlistCard.jsx      */
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

const WishlistCard = memo(
  ({
    product,

    compact = false,

    showStock = true,

    showShipping = true,

    showRating = true,

    showDiscount = true,

    showMoveToCart = true,

    onPress,

    onRemove,

    onMoveToCart,

    style,
  }) => {
    const { colors } = theme;


    const inStock =
      product?.inStock ??
      product?.stock > 0;

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

        <View
          style={
            styles.imageContainer
          }
        >
          <Image
            source={{
              uri:
                product?.image,
            }}
            style={styles.image}
            resizeMode="cover"
          />

          <Pressable
            onPress={() =>
              onRemove?.(
                product
              )
            }
            style={[
              styles.removeButton,
              {
                backgroundColor:
                  colors.card,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="heart"
              size={20}
              color="#EF4444"
            />
          </Pressable>
        </View>

        {/* ---------------------------------------------------------- */}
        {/* Content */}
        {/* ---------------------------------------------------------- */}

        <View
          style={
            styles.content
          }
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
            {product?.name}
          </Text>

          {!!product?.brand && (
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
                size={16}
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
              showDiscount
                ? product?.discount
                : null
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
                size={16}
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

          {showShipping &&
            product?.freeShipping && (
              <View
                style={
                  styles.shippingBadge
                }
              >
                <MaterialCommunityIcons
                  name="truck-fast"
                  size={15}
                  color="#3B82F6"
                />

                <Text
                  style={
                    styles.shippingText
                  }
                >
                  Free Shipping
                </Text>
              </View>
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

              <Text
                style={
                  styles.cartText
                }
              >
                Move to Cart
              </Text>
            </Pressable>
          )}
        </View>
      </Pressable>
    );
  }
);

WishlistCard.displayName =
  "WishlistCard";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flexDirection: "row",

      borderWidth: 1,

      borderRadius: 18,

      overflow: "hidden",

      marginBottom: 16,
    },

    compact: {
      minHeight: 130,
    },

    imageContainer: {
      position: "relative",
    },

    image: {
      width: 120,

      height: "100%",

      minHeight: 170,

      backgroundColor:
        "#E5E7EB",
    },

    removeButton: {
      position: "absolute",

      top: 10,

      right: 10,

      width: 34,

      height: 34,

      borderRadius: 17,

      justifyContent:
        "center",

      alignItems:
        "center",

      elevation: 2,
    },

    content: {
      flex: 1,

      padding: 16,
    },

    name: {
      fontSize: 16,

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
      marginLeft: 6,

      fontSize: 13,
    },

    stockRow: {
      flexDirection: "row",

      alignItems: "center",

      marginTop: 10,
    },

    stock: {
      marginLeft: 6,

      fontWeight: "600",

      fontSize: 13,
    },

    shippingBadge: {
      flexDirection: "row",

      alignItems: "center",

      alignSelf:
        "flex-start",

      marginTop: 10,

      paddingHorizontal: 10,

      paddingVertical: 5,

      borderRadius: 999,

      backgroundColor:
        "#DBEAFE",
    },

    shippingText: {
      marginLeft: 5,

      color: "#2563EB",

      fontSize: 12,

      fontWeight: "600",
    },

    cartButton: {
      flexDirection: "row",

      justifyContent:
        "center",

      alignItems: "center",

      marginTop: 16,

      height: 44,

      borderRadius: 12,
    },

    cartText: {
      marginLeft: 8,

      color: "#FFFFFF",

      fontWeight: "700",

      fontSize: 14,
    },
  });

export default WishlistCard;