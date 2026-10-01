/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ProductImage.jsx        */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import {
  View,
  StyleSheet,
  Text,
} from "react-native";

import NetworkImage from "./NetworkImage";
import FavoriteButton from "./FavoriteButton";
import DiscountBadge from "./DiscountBadge";
import StockBadge from "./StockBadge";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */

const ProductImage = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Product                                                                 */
    /* ---------------------------------------------------------------------- */

    image,

    images,

    name,

    /* ---------------------------------------------------------------------- */
    /* Badges                                                                  */
    /* ---------------------------------------------------------------------- */

    featured = false,

    isNew = false,

    inStock = true,

    stockQuantity,

    discount,

    /* ---------------------------------------------------------------------- */
    /* Wishlist                                                                */
    /* ---------------------------------------------------------------------- */

    favorite = false,

    showFavorite = false,

    onFavoritePress,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                 */
    /* ---------------------------------------------------------------------- */

    showDiscount = true,

    showStock = false,

    showFeatured = true,

    showNew = true,

    borderRadius = 16,

    resizeMode = "cover",

    width = "100%",

    height = 220,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const imageUri =
      useMemo(() => {
        if (image?.url)
          return image.url;

        if (
          image?.thumbnail
        )
          return image.thumbnail;

        if (
          Array.isArray(
            images
          ) &&
          images.length
        ) {
          return (
            images[0]
              ?.image?.url ??
            images[0]?.url
          );
        }

        return null;
      }, [image, images]);

    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,

          {
            width,
            height,
          },

          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Image */}
        {/* -------------------------------------------------------------- */}

        <NetworkImage
          uri={imageUri}
          alt={name}
          width="100%"
          height="100%"
          resizeMode={
            resizeMode
          }
          borderRadius={
            borderRadius
          }
        />

        {/* -------------------------------------------------------------- */}
        {/* Favorite */}
        {/* -------------------------------------------------------------- */}

        {showFavorite && (
          <FavoriteButton
            favorite={
              favorite
            }
            size="sm"
            style={
              styles.favorite
            }
            onPress={
              onFavoritePress
            }
          />
        )}

        {/* -------------------------------------------------------------- */}
        {/* Discount */}
        {/* -------------------------------------------------------------- */}

        {showDiscount &&
          discount >
            0 && (
            <DiscountBadge
              percentage={
                discount
              }
              size="sm"
              style={
                styles.discount
              }
            />
          )}

        {/* -------------------------------------------------------------- */}
        {/* Featured */}
        {/* -------------------------------------------------------------- */}

        {featured &&
          showFeatured && (
            <View
              style={[
                styles.featured,

                {
                  backgroundColor:
                    colors.primary,
                },
              ]}
            >
              <Text
                style={
                  styles.featuredText
                }
              >
                Featured
              </Text>
            </View>
          )}

        {/* -------------------------------------------------------------- */}
        {/* New */}
        {/* -------------------------------------------------------------- */}

        {isNew &&
          showNew && (
            <View
              style={[
                styles.new,

                {
                  backgroundColor:
                    colors.success ??
                    "#10B981",
                },
              ]}
            >
              <Text
                style={
                  styles.newText
                }
              >
                NEW
              </Text>
            </View>
          )}

        {/* -------------------------------------------------------------- */}
        {/* Stock */}
        {/* -------------------------------------------------------------- */}

        {showStock && (
          <View
            style={
              styles.stock
            }
          >
            <StockBadge
              inStock={
                inStock
              }
              quantity={
                stockQuantity
              }
              size="sm"
              variant="filled"
            />
          </View>
        )}
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */

ProductImage.displayName =
  "ProductImage";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      position:
        "relative",

      overflow:
        "hidden",
    },

    favorite: {
      position:
        "absolute",

      top: 12,

      right: 12,
    },

    discount: {
      position:
        "absolute",

      top: 12,

      left: 12,
    },

    featured: {
      position:
        "absolute",

      bottom: 12,

      left: 12,

      paddingHorizontal: 10,

      paddingVertical: 5,

      borderRadius: 20,
    },

    featuredText: {
      color: "#FFF",

      fontWeight: "700",

      fontSize: 11,
    },

    new: {
      position:
        "absolute",

      bottom: 12,

      right: 12,

      paddingHorizontal: 10,

      paddingVertical: 5,

      borderRadius: 20,
    },

    newText: {
      color: "#FFF",

      fontWeight: "700",

      fontSize: 11,
    },

    stock: {
      position:
        "absolute",

      left: 12,

      right: 12,

      bottom: 48,
    },
  });

/* -------------------------------------------------------------------------- */

export default ProductImage;