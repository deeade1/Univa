/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ProductListItem.jsx     */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  Pressable,
  StyleSheet,
  View,
  Text,
} from "react-native";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import ProductImage from "./ProductImage";
import DiscountBadge from "./DiscountBadge";
import VerifiedBadge from "./VerifiedBadge";
import ShippingBadge from "./ShippingBadge";
import StockIndicator from "./StockIndicator";
import Rating from "./Rating";
import FavoriteButton from "./FavoriteButton";
import PriceComparison from "./PriceComparison";
import AvailabilityBadge from "./AvailabilityBadge";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductListItem = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Product                                                                */
    /* ---------------------------------------------------------------------- */

    product,
    disabled = false,

    /* ---------------------------------------------------------------------- */
    /* Visibility                                                             */
    /* ---------------------------------------------------------------------- */

    showFavorite = true,
    showDiscount = true,
    showRating = true,
    showShipping = true,
    showVerification = true,
    showStock = true,
    showDescription = true,
    showSeller = true,
    showSoldCount = true,

    /* ---------------------------------------------------------------------- */
    /* Actions                                                                */
    /* ---------------------------------------------------------------------- */

    showAddToCart = true,
    showBuyNow = true,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onPress,
    onFavorite,
    onAddToCart,
    onBuyNow,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Product Data                                                           */
    /* ---------------------------------------------------------------------- */

    const {
      id,
      name,
      brand,
      images = [],
      thumbnail,
      shortDescription,
      price,
      originalPrice,
      currency,
      discountPercentage,
      rating,
      reviewCount,
      soldCount,
      stock,
      shipping,
      seller,
      isFavorite,
    } = product ?? {};

    /* ---------------------------------------------------------------------- */
    /* Derived Values                                                         */
    /* ---------------------------------------------------------------------- */

    const image = useMemo(() => {
      if (thumbnail) return thumbnail;
      if (images.length) return images[0];
      return null;
    }, [thumbnail, images]);

    const isOutOfStock = useMemo(() => stock <= 0, [stock]);

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handlePress = useCallback(() => {
      if (disabled) return;
      onPress?.(product);
    }, [disabled, onPress, product]);

    const handleFavorite = useCallback(() => {
      onFavorite?.(product);
    }, [onFavorite, product]);

    const handleAddToCart = useCallback(() => {
      if (isOutOfStock || disabled) return;
      onAddToCart?.(product);
    }, [isOutOfStock, disabled, onAddToCart, product]);

    const handleBuyNow = useCallback(() => {
      if (isOutOfStock || disabled) return;
      onBuyNow?.(product);
    }, [isOutOfStock, disabled, onBuyNow, product]);

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <Pressable
        disabled={disabled}
        onPress={handlePress}
        style={({ pressed }) => [
          styles.container,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
          pressed && styles.pressed,
          disabled && styles.disabled,
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Image Section                                                  */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.imageContainer}>
          <ProductImage
            uri={image}
            alt={name}
            width={120}
            height={120}
            resizeMode="cover"
            style={styles.image}
          />

          {/* Discount Badge */}
          {showDiscount && Number(discountPercentage) > 0 && (
            <View style={styles.discountBadge}>
              <DiscountBadge
                percentage={discountPercentage}
                size="small"
              />
            </View>
          )}

          {/* Favorite Button */}
          {showFavorite && (
            <View style={styles.favoriteButton}>
              <FavoriteButton
                active={!!isFavorite}
                size="small"
                onPress={handleFavorite}
              />
            </View>
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Content Section                                               */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.content}>
          {/* Brand */}
          {!!brand && (
            <View style={styles.brandRow}>
              <Text
                numberOfLines={1}
                style={[
                  styles.brand,
                  {
                    color: colors.textSecondary,
                  },
                ]}
              >
                {brand}
              </Text>

              {showVerification && seller?.isVerified && (
                <VerifiedBadge size="small" />
              )}
            </View>
          )}

          {/* Product Name */}
          <Text
            numberOfLines={2}
            style={[
              styles.name,
              {
                color: colors.text,
              },
            ]}
          >
            {name}
          </Text>

          {/* Description */}
          {showDescription && !!shortDescription && (
            <Text
              numberOfLines={2}
              style={[
                styles.description,
                {
                  color: colors.textSecondary,
                },
              ]}
            >
              {shortDescription}
            </Text>
          )}

          {/* Seller */}
          {showSeller && !!seller?.name && (
            <Text
              numberOfLines={1}
              style={[
                styles.seller,
                {
                  color: colors.textSecondary,
                },
              ]}
            >
              Sold by {seller.name}
            </Text>
          )}

          {/* Rating */}
          {showRating && rating > 0 && (
            <View style={styles.ratingRow}>
              <Rating
                rating={Number(rating)}
                size={12}
                showValue={false}
                showReviewCount={false}
              />

              <Text
                style={[
                  styles.ratingText,
                  {
                    color: colors.textSecondary,
                  },
                ]}
              >
                {Number(rating).toFixed(1)}
              </Text>

              {reviewCount > 0 && (
                <Text
                  style={[
                    styles.reviewText,
                    {
                      color: colors.textSecondary,
                    },
                  ]}
                >
                  ({reviewCount})
                </Text>
              )}

              {showSoldCount && !!soldCount && (
                <Text
                  style={[
                    styles.soldText,
                    {
                      color: colors.textSecondary,
                    },
                  ]}
                >
                  • {soldCount} sold
                </Text>
              )}
            </View>
          )}

          {/* Price */}
          <View style={styles.priceSection}>
            <PriceComparison
              price={price}
              originalPrice={originalPrice}
              currency={currency}
              discountPercentage={discountPercentage}
              size="small"
            />
          </View>

          {/* Shipping & Stock */}
          <View style={styles.statusRow}>
            {showShipping && !!shipping && (
              <ShippingBadge shipping={shipping} size="small" />
            )}

            {showStock && stock != null && (
              <View style={styles.stockContainer}>
                <StockIndicator quantity={stock} size="small" />
              </View>
            )}
          </View>

          {/* Availability */}
          <View style={styles.availabilityRow}>
            <View
              style={[
                styles.availabilityDot,
                {
                  backgroundColor: stock > 0 ? colors.success : colors.error,
                },
              ]}
            />
            <Text
              style={[
                styles.availabilityText,
                {
                  color: stock > 0 ? colors.success : colors.error,
                },
              ]}
            >
              {stock > 0 ? "Available" : "Out of Stock"}
            </Text>
          </View>

          {/* Actions */}
          <View style={styles.footer}>
            {showAddToCart && (
              <Pressable
                disabled={disabled || isOutOfStock}
                onPress={handleAddToCart}
                style={({ pressed }) => [
                  styles.cartButton,
                  {
                    backgroundColor: colors.primary,
                  },
                  pressed && styles.buttonPressed,
                  (disabled || isOutOfStock) && styles.buttonDisabled,
                ]}
              >
                <Text style={styles.cartButtonText}>Add to Cart</Text>
              </Pressable>
            )}

            {showBuyNow && (
              <Pressable
                disabled={disabled || isOutOfStock}
                onPress={handleBuyNow}
                style={({ pressed }) => [
                  styles.buyButton,
                  {
                    borderColor: colors.primary,
                  },
                  pressed && styles.buttonPressed,
                  (disabled || isOutOfStock) && styles.buttonDisabled,
                ]}
              >
                <Text
                  style={[
                    styles.buyButtonText,
                    {
                      color: colors.primary,
                    },
                  ]}
                >
                  Buy Now
                </Text>
              </Pressable>
            )}
          </View>
        </View>
      </Pressable>
    );
  }
);

ProductListItem.displayName = "ProductListItem";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const productShape = PropTypes.shape({
  id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  name: PropTypes.string,
  brand: PropTypes.string,
  thumbnail: PropTypes.string,
  images: PropTypes.arrayOf(PropTypes.string),
  shortDescription: PropTypes.string,
  price: PropTypes.number,
  originalPrice: PropTypes.number,
  currency: PropTypes.string,
  discountPercentage: PropTypes.number,
  rating: PropTypes.number,
  reviewCount: PropTypes.number,
  soldCount: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  stock: PropTypes.number,
  shipping: PropTypes.object,
  isFavorite: PropTypes.bool,
  seller: PropTypes.shape({
    name: PropTypes.string,
    isVerified: PropTypes.bool,
  }),
});

ProductListItem.propTypes = {
  product: productShape,
  disabled: PropTypes.bool,

  // Visibility
  showFavorite: PropTypes.bool,
  showDiscount: PropTypes.bool,
  showRating: PropTypes.bool,
  showShipping: PropTypes.bool,
  showVerification: PropTypes.bool,
  showStock: PropTypes.bool,
  showDescription: PropTypes.bool,
  showSeller: PropTypes.bool,
  showSoldCount: PropTypes.bool,

  // Actions
  showAddToCart: PropTypes.bool,
  showBuyNow: PropTypes.bool,

  // Events
  onPress: PropTypes.func,
  onFavorite: PropTypes.func,
  onAddToCart: PropTypes.func,
  onBuyNow: PropTypes.func,

  // Styling
  style: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
};

ProductListItem.defaultProps = {
  product: null,
  disabled: false,
  showFavorite: true,
  showDiscount: true,
  showRating: true,
  showShipping: true,
  showVerification: true,
  showStock: true,
  showDescription: true,
  showSeller: true,
  showSoldCount: true,
  showAddToCart: true,
  showBuyNow: true,
  onPress: null,
  onFavorite: null,
  onAddToCart: null,
  onBuyNow: null,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "flex-start",
    padding: 12,
    marginBottom: 12,
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: "hidden",
  },

  pressed: {
    opacity: 0.96,
  },

  disabled: {
    opacity: 0.6,
  },

  /* ------------------------------------------------------------------ */
  /* Image                                                              */
  /* ------------------------------------------------------------------ */

  imageContainer: {
    position: "relative",
    width: 120,
    height: 120,
    borderRadius: 12,
    overflow: "hidden",
  },

  image: {
    width: "100%",
    height: "100%",
  },

  discountBadge: {
    position: "absolute",
    top: 8,
    left: 8,
  },

  favoriteButton: {
    position: "absolute",
    top: 8,
    right: 8,
  },

  /* ------------------------------------------------------------------ */
  /* Content                                                            */
  /* ------------------------------------------------------------------ */

  content: {
    flex: 1,
    marginLeft: 16,
  },

  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 4,
  },

  brand: {
    flex: 1,
    fontSize: 12,
    fontWeight: "600",
  },

  name: {
    fontSize: 16,
    fontWeight: "700",
    lineHeight: 22,
  },

  description: {
    marginTop: 6,
    fontSize: 13,
    lineHeight: 18,
  },

  seller: {
    marginTop: 6,
    fontSize: 12,
  },

  /* ------------------------------------------------------------------ */
  /* Rating                                                             */
  /* ------------------------------------------------------------------ */

  ratingRow: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    marginTop: 10,
  },

  ratingText: {
    marginLeft: 6,
    fontSize: 12,
    fontWeight: "600",
  },

  reviewText: {
    marginLeft: 4,
    fontSize: 12,
  },

  soldText: {
    marginLeft: 6,
    fontSize: 12,
  },

  /* ------------------------------------------------------------------ */
  /* Price                                                              */
  /* ------------------------------------------------------------------ */

  priceSection: {
    marginTop: 12,
  },

  /* ------------------------------------------------------------------ */
  /* Status                                                             */
  /* ------------------------------------------------------------------ */

  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    marginTop: 12,
  },

  stockContainer: {
    marginLeft: 8,
  },

  availabilityRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 10,
  },

  availabilityDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },

  availabilityText: {
    marginLeft: 6,
    fontSize: 12,
    fontWeight: "600",
  },

  /* ------------------------------------------------------------------ */
  /* Footer                                                             */
  /* ------------------------------------------------------------------ */

  footer: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 16,
  },

  cartButton: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 10,
    paddingVertical: 10,
  },

  cartButtonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 13,
  },

  buyButton: {
    marginLeft: 8,
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },

  buyButtonText: {
    fontSize: 13,
    fontWeight: "700",
  },

  buttonPressed: {
    opacity: 0.8,
  },

  buttonDisabled: {
    opacity: 0.45,
  },
});

export default ProductListItem;