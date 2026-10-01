/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ProductCard.jsx         */
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


import ProductImage from "@/modules/ecommerce/components/common/ProductImage";
import DiscountBadge from "@/modules/ecommerce/components/common/DiscountBadge";
import VerifiedBadge from "@/modules/ecommerce/components/common/VerifiedBadge";
import ShippingBadge from "@/modules/ecommerce/components/common/ShippingBadge";
import StockIndicator from "@/modules/ecommerce/components/common/StockIndicator";
import ProductTags from "@/modules/ecommerce/components/common/ProductTags";
import Rating from "@/modules/ecommerce/components/common/Rating";
import FavoriteButton from "@/modules/ecommerce/components/common/FavoriteButton";
import PriceComparison from "@/modules/ecommerce/components/common/PriceComparison";
import AvailabilityBadge from "@/modules/ecommerce/components/common/AvailabilityBadge";
import LoadingOverlay from "@/modules/ecommerce/components/common/LoadingOverlay";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductCard = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Product                                                                */
    /* ---------------------------------------------------------------------- */

    product,
    loading = false,
    disabled = false,

    /* ---------------------------------------------------------------------- */
    /* Layout                                                                 */
    /* ---------------------------------------------------------------------- */

    layout = "grid", // grid | list
    imageAspectRatio = 1,

    /* ---------------------------------------------------------------------- */
    /* Visibility                                                             */
    /* ---------------------------------------------------------------------- */

    showFavorite = true,
    showDiscount = true,
    showRating = true,
    showShipping = true,
    showVerification = true,
    showStock = true,
    showTags = true,
    showDescription = true,
    showSeller = true,
    showSoldCount = true,
    showQuickView = false,

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
    onQuickView,

    /* ---------------------------------------------------------------------- */
    /* Rendering Overrides                                                    */
    /* ---------------------------------------------------------------------- */

    renderFooter,
    renderActions,
    renderBadges,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,
    contentStyle,
    imageStyle,
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
      tags,
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
    const isGrid = layout === "grid";

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

    const handleQuickView = useCallback(() => {
      onQuickView?.(product);
    }, [onQuickView, product]);

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <Pressable
        disabled={disabled}
        onPress={handlePress}
        android_ripple={{
          color: colors.surfaceVariant ?? "#E5E7EB",
        }}
        style={({ pressed }) => [
          styles.card,
          isGrid ? styles.gridCard : styles.listCard,
          {
            backgroundColor: colors.surface ?? colors.background,
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

        <View style={[styles.imageContainer, isGrid && styles.gridImageContainer]}>
          <ProductImage
            uri={image}
            alt={name}
            aspectRatio={isGrid ? imageAspectRatio : undefined}
            width={isGrid ? undefined : 120}
            height={isGrid ? undefined : 120}
            resizeMode="cover"
            style={[styles.image, imageStyle]}
          />

          {/* Discount Badge */}
          {showDiscount && Number(discountPercentage) > 0 && (
            <View style={styles.discountBadge}>
              <DiscountBadge
                percentage={discountPercentage}
                size={isGrid ? "medium" : "small"}
              />
            </View>
          )}

          {/* Favorite Button */}
          {showFavorite && (
            <View style={styles.favoriteButton}>
              <FavoriteButton
                active={!!isFavorite}
                size={isGrid ? "medium" : "small"}
                onPress={handleFavorite}
              />
            </View>
          )}

          {/* Loading Overlay */}
          {loading && (
            <LoadingOverlay
              visible
              fullscreen={false}
              transparent
              message={null}
            />
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Content Section                                               */}
        {/* -------------------------------------------------------------- */}

        <View style={[styles.content, isGrid && styles.gridContent, contentStyle]}>
          {/* Brand */}
          {!!brand && (
            <View style={styles.brandRow}>
              <Text
                numberOfLines={1}
                style={[
                  styles.brand,
                  {
                    color: isGrid ? colors.primary : colors.textSecondary,
                  },
                ]}
              >
                {brand}
              </Text>

              {showVerification && seller?.isVerified && (
                <VerifiedBadge size="small" style={styles.verifiedBadge} />
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

          {/* Short Description */}
          {showDescription && !!shortDescription && (
            <Text
              numberOfLines={isGrid ? 2 : 2}
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
              {isGrid ? seller.name : `Sold by ${seller.name}`}
            </Text>
          )}

          {/* Rating & Sold Count */}
          {showRating && rating > 0 && (
            <View style={styles.ratingSection}>
              <Rating
                rating={Number(rating)}
                size={isGrid ? 14 : 12}
                showValue={false}
                showReviewCount={false}
              />

              <Text
                style={[
                  styles.ratingValue,
                  {
                    color: colors.text,
                  },
                ]}
              >
                {Number(rating).toFixed(1)}
              </Text>

              {reviewCount > 0 && (
                <Text
                  style={[
                    styles.reviewCount,
                    {
                      color: colors.textSecondary,
                    },
                  ]}
                >
                  ({reviewCount})
                </Text>
              )}

              {showSoldCount && !!soldCount && (
                <>
                  <View
                    style={[
                      styles.dot,
                      {
                        backgroundColor: colors.outline ?? colors.border,
                      },
                    ]}
                  />
                  <Text
                    style={[
                      styles.soldCount,
                      {
                        color: colors.textSecondary,
                      },
                    ]}
                  >
                    {soldCount} sold
                  </Text>
                </>
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
              size={isGrid ? "medium" : "small"}
              showSavings={isGrid}
              showPercentage={isGrid}
            />
          </View>

          {/* Shipping & Stock */}
          <View style={styles.statusSection}>
            {showShipping && !!shipping && (
              <ShippingBadge shipping={shipping} size="small" />
            )}

            {showStock && stock != null && (
              <StockIndicator
                quantity={stock}
                size="small"
                style={styles.stockIndicator}
              />
            )}

            {/* Availability */}
            <AvailabilityBadge
              available={stock > 0}
              size="small"
              style={styles.availabilityBadge}
            />
          </View>

          {/* Tags */}
          {showTags && Array.isArray(tags) && tags.length > 0 && (
            <View style={styles.tagsSection}>
              <ProductTags
                tags={tags}
                maxVisible={isGrid ? 3 : 2}
                size="small"
              />
            </View>
          )}

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

            {showQuickView && (
              <Pressable
                onPress={handleQuickView}
                style={({ pressed }) => [
                  styles.quickViewButton,
                  pressed && styles.buttonPressed,
                ]}
              >
                <Text
                  style={[
                    styles.quickViewText,
                    {
                      color: colors.textSecondary,
                    },
                  ]}
                >
                  Quick View
                </Text>
              </Pressable>
            )}
          </View>

          {/* Custom Render Overrides */}
          {renderFooter && renderFooter(product)}
          {renderActions && renderActions(product)}
          {renderBadges && renderBadges(product)}
        </View>
      </Pressable>
    );
  }
);

ProductCard.displayName = "ProductCard";

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
  tags: PropTypes.array,
  isFavorite: PropTypes.bool,
  seller: PropTypes.shape({
    name: PropTypes.string,
    isVerified: PropTypes.bool,
  }),
});

ProductCard.propTypes = {
  product: productShape,
  loading: PropTypes.bool,
  disabled: PropTypes.bool,

  // Layout
  layout: PropTypes.oneOf(["grid", "list"]),
  imageAspectRatio: PropTypes.number,

  // Visibility
  showFavorite: PropTypes.bool,
  showDiscount: PropTypes.bool,
  showRating: PropTypes.bool,
  showShipping: PropTypes.bool,
  showVerification: PropTypes.bool,
  showStock: PropTypes.bool,
  showTags: PropTypes.bool,
  showDescription: PropTypes.bool,
  showSeller: PropTypes.bool,
  showSoldCount: PropTypes.bool,
  showQuickView: PropTypes.bool,

  // Actions
  showAddToCart: PropTypes.bool,
  showBuyNow: PropTypes.bool,

  // Events
  onPress: PropTypes.func,
  onFavorite: PropTypes.func,
  onAddToCart: PropTypes.func,
  onBuyNow: PropTypes.func,
  onQuickView: PropTypes.func,

  // Rendering Overrides
  renderFooter: PropTypes.func,
  renderActions: PropTypes.func,
  renderBadges: PropTypes.func,

  // Styling
  style: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
  contentStyle: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
  imageStyle: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
};

ProductCard.defaultProps = {
  product: null,
  loading: false,
  disabled: false,
  layout: "grid",
  imageAspectRatio: 1,
  showFavorite: true,
  showDiscount: true,
  showRating: true,
  showShipping: true,
  showVerification: true,
  showStock: true,
  showTags: true,
  showDescription: true,
  showSeller: true,
  showSoldCount: true,
  showQuickView: false,
  showAddToCart: true,
  showBuyNow: true,
  onPress: null,
  onFavorite: null,
  onAddToCart: null,
  onBuyNow: null,
  onQuickView: null,
  renderFooter: null,
  renderActions: null,
  renderBadges: null,
  style: null,
  contentStyle: null,
  imageStyle: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  /* ------------------------------------------------------------------ */
  /* Card                                                               */
  /* ------------------------------------------------------------------ */

  card: {
    borderRadius: 16,
    overflow: "hidden",
    borderWidth: StyleSheet.hairlineWidth,
    elevation: 3,
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },

  gridCard: {
    margin: 8,
    width: "45%",
  },

  listCard: {
    flexDirection: "row",
    padding: 12,
    marginBottom: 12,
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
    overflow: "hidden",
  },

  gridImageContainer: {
    width: "100%",
  },

  image: {
    width: "100%",
  },

  discountBadge: {
    position: "absolute",
    top: 12,
    left: 12,
  },

  favoriteButton: {
    position: "absolute",
    top: 12,
    right: 12,
  },

  /* ------------------------------------------------------------------ */
  /* Content                                                            */
  /* ------------------------------------------------------------------ */

  content: {
    padding: 16,
  },

  gridContent: {
    padding: 12,
  },

  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 6,
  },

  brand: {
    flex: 1,
    fontSize: 13,
    fontWeight: "600",
  },

  verifiedBadge: {
    marginLeft: 6,
  },

  name: {
    fontSize: 16,
    fontWeight: "700",
    lineHeight: 22,
  },

  description: {
    marginTop: 6,
    fontSize: 13,
    lineHeight: 20,
  },

  seller: {
    marginTop: 6,
    fontSize: 13,
  },

  /* ------------------------------------------------------------------ */
  /* Rating                                                             */
  /* ------------------------------------------------------------------ */

  ratingSection: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 12,
  },

  ratingValue: {
    marginLeft: 6,
    fontSize: 13,
    fontWeight: "700",
  },

  reviewCount: {
    marginLeft: 4,
    fontSize: 13,
  },

  dot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    marginHorizontal: 8,
  },

  soldCount: {
    fontSize: 13,
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

  statusSection: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    marginTop: 12,
  },

  stockIndicator: {
    marginLeft: 8,
  },

  availabilityBadge: {
    marginLeft: 8,
  },

  /* ------------------------------------------------------------------ */
  /* Tags                                                               */
  /* ------------------------------------------------------------------ */

  tagsSection: {
    marginTop: 12,
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
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
    justifyContent: "center",
  },

  cartButtonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 14,
  },

  buyButton: {
    marginLeft: 8,
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },

  buyButtonText: {
    fontWeight: "700",
    fontSize: 14,
  },

  quickViewButton: {
    marginLeft: 8,
    paddingHorizontal: 10,
    paddingVertical: 12,
    alignItems: "center",
    justifyContent: "center",
  },

  quickViewText: {
    fontSize: 13,
    fontWeight: "600",
  },

  buttonPressed: {
    opacity: 0.8,
  },

  buttonDisabled: {
    opacity: 0.45,
  },
});

export default ProductCard;