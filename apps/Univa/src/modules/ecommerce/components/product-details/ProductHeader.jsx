/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductHeader.jsx                                                          */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
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
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductHeader = memo(
  ({
    product,

    wishlisted = false,

    showBack = true,

    showShare = true,

    showWishlist = true,

    showBrand = true,

    onBack,

    onShare,

    onWishlist,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleBack =
      useCallback(() => {
        onBack?.();
      }, [onBack]);

    const handleShare =
      useCallback(() => {
        onShare?.(product);
      }, [
        product,
        onShare,
      ]);

    const handleWishlist =
      useCallback(() => {
        onWishlist?.(product);
      }, [
        product,
        onWishlist,
      ]);

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,
          {
            backgroundColor:
              colors.background,
          },
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Top Bar                                                       */}
        {/* -------------------------------------------------------------- */}

        <View
          style={styles.topBar}
        >
          {showBack ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Go back"
              onPress={
                handleBack
              }
              style={[
                styles.iconButton,
                {
                  backgroundColor:
                    colors.card,
                },
              ]}
            >
              <MaterialCommunityIcons
                name="arrow-left"
                size={22}
                color={
                  colors.text
                }
              />
            </Pressable>
          ) : (
            <View
              style={
                styles.placeholder
              }
            />
          )}

          <View
            style={
              styles.rightActions
            }
          >
            {showShare && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Share product"
                onPress={
                  handleShare
                }
                style={[
                  styles.iconButton,
                  {
                    backgroundColor:
                      colors.card,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name="share-variant-outline"
                  size={21}
                  color={
                    colors.text
                  }
                />
              </Pressable>
            )}

            {showWishlist && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Add to wishlist"
                onPress={
                  handleWishlist
                }
                style={[
                  styles.iconButton,
                  {
                    backgroundColor:
                      colors.card,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name={
                    wishlisted
                      ? "heart"
                      : "heart-outline"
                  }
                  size={22}
                  color={
                    wishlisted
                      ? "#EF4444"
                      : colors.text
                  }
                />
              </Pressable>
            )}
          </View>
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Product Info                                                  */}
        {/* -------------------------------------------------------------- */}

        <View
          style={styles.info}
        >
          {showBrand &&
            !!product?.brand && (
              <Text
                style={[
                  styles.brand,
                  {
                    color:
                      colors.primary,
                  },
                ]}
              >
                {product.brand}
              </Text>
            )}

          <Text
            style={[
              styles.title,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {product?.name ??
              "Product"}
          </Text>

          {!!product?.subtitle && (
            <Text
              style={[
                styles.subtitle,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {
                product.subtitle
              }
            </Text>
          )}

          {/* ---------------------------------------------------------- */}
          {/* Rating                                                    */}
          {/* ---------------------------------------------------------- */}

          <View
            style={
              styles.ratingRow
            }
          >
            <MaterialCommunityIcons
              name="star"
              size={18}
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
                0}{" "}
              reviews)
            </Text>
          </View>
        </View>
      </View>
    );
  }
);

ProductHeader.displayName =
  "ProductHeader";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductHeader.propTypes = {
  product: PropTypes.object,

  wishlisted:
    PropTypes.bool,

  showBack:
    PropTypes.bool,

  showShare:
    PropTypes.bool,

  showWishlist:
    PropTypes.bool,

  showBrand:
    PropTypes.bool,

  onBack:
    PropTypes.func,

  onShare:
    PropTypes.func,

  onWishlist:
    PropTypes.func,

  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

ProductHeader.defaultProps = {
  product: null,

  wishlisted: false,

  showBack: true,

  showShare: true,

  showWishlist: true,

  showBrand: true,

  onBack: null,

  onShare: null,

  onWishlist: null,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      paddingHorizontal: 16,
      paddingTop: 16,
      paddingBottom: 12,
    },

    topBar: {
      flexDirection: "row",
      justifyContent:
        "space-between",
      alignItems: "center",
    },

    placeholder: {
      width: 46,
    },

    rightActions: {
      flexDirection: "row",
    },

    iconButton: {
      width: 46,
      height: 46,
      borderRadius: 23,
      justifyContent:
        "center",
      alignItems: "center",
      marginLeft: 10,
      elevation: 2,
    },

    info: {
      marginTop: 18,
    },

    brand: {
      fontSize: 13,
      fontWeight: "700",
      textTransform:
        "uppercase",
      letterSpacing: 0.6,
    },

    title: {
      marginTop: 6,
      fontSize: 24,
      fontWeight: "700",
      lineHeight: 32,
    },

    subtitle: {
      marginTop: 8,
      fontSize: 15,
      lineHeight: 22,
    },

    ratingRow: {
      flexDirection: "row",
      alignItems: "center",
      marginTop: 14,
    },

    rating: {
      marginLeft: 6,
      fontSize: 15,
      fontWeight: "700",
    },

    reviewCount: {
      marginLeft: 8,
      fontSize: 14,
    },
  });

export default ProductHeader;