/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/screens/ProductDetailsScreen.jsx          */
/* -------------------------------------------------------------------------- */

import React, { useState, useMemo, useCallback } from "react";
import {
  View,
  ScrollView,
  SafeAreaView,
  RefreshControl,
  Share,
  StyleSheet,
  TouchableOpacity,
  Text,
  Alert,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { ArrowLeft, Share2, Heart, ShoppingBag } from "lucide-react-native";

import { useProduct } from "@/modules/ecommerce/hooks/useProduct";
import { useProductReviews } from "@/modules/ecommerce/hooks/useProductReviews";
import { useRelatedProducts } from "@/modules/ecommerce/hooks/useRelatedProducts";
import { useCart } from "@/modules/ecommerce/context/CartContext";
import { useChannel } from "@/modules/ecommerce/context/ChannelContext";

import ProductGallery from "@/modules/ecommerce/components/product-details/ProductGallery";
import ProductHeader from "@/modules/ecommerce/components/product-details/ProductHeader";
import ProductPrice from "@/modules/ecommerce/components/products/ProductPrice";
import ProductDescription from "@/modules/ecommerce/components/products/ProductDescription";
import ProductSpecifications from "@/modules/ecommerce/components/product-details/ProductSpecifications";
import ProductReviews from "@/modules/ecommerce/components/reviews/Reviews";
import ProductQuantitySelector from "@/modules/ecommerce/components/common/QuantitySelector";
import ProductVariantSheet from "@/modules/ecommerce/components/product-details/ProductVariantSheet";
import RelatedProducts from "@/modules/ecommerce/components/products/RelatedProducts";
import SellerInfo from "@/modules/ecommerce/components/products/SellerInfo";

import ProductDetailsSkeleton from "@/modules/ecommerce/components/skeleton/ProductDetailsSkeleton";
import ErrorState from "@/modules/ecommerce/components/common/ErrorState";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Screen                                                                     */
/* -------------------------------------------------------------------------- */

export default function ProductDetailsScreen() {
  const router = useRouter();
  const { colors } = theme;
  const { slug } = useLocalSearchParams();
  const { addToCart } = useCart();
  const { channel, currency } = useChannel();

  /* ------------------------------------------------------------------------ */
  /* Product                                                                   */
  /* ------------------------------------------------------------------------ */

  const {
    product,
    loading,
    error,
    refetch,
    isRefetching,
    inStock,
    attributes,
  } = useProduct(slug, {
    fetchAttributes: true,
  });

  /* ------------------------------------------------------------------------ */
  /* Reviews                                                                   */
  /* ------------------------------------------------------------------------ */

  const {
    reviews,
    averageRating,
    totalReviews,
    ratingDistribution,
    loadMore: loadMoreReviews,
    hasNextPage: hasMoreReviews,
    loading: reviewsLoading,
  } = useProductReviews({
    productId: product?.id,
    skip: !product?.id,
  });

  /* ------------------------------------------------------------------------ */
  /* Related Products                                                          */
  /* ------------------------------------------------------------------------ */

  const {
    products: relatedProducts,
    loading: relatedLoading,
  } = useRelatedProducts({
    productId: product?.id,
    categoryId: product?.category?.id,
    skip: !product?.id,
  });

  /* ------------------------------------------------------------------------ */
  /* Local State                                                               */
  /* ------------------------------------------------------------------------ */

  const [selectedVariant, setSelectedVariant] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [variantSheetVisible, setVariantSheetVisible] = useState(false);

  /* ------------------------------------------------------------------------ */
  /* Effects                                                                   */
  /* ------------------------------------------------------------------------ */

  React.useEffect(() => {
    if (product?.variants?.length) {
      setSelectedVariant(product.variants[0]);
    }
  }, [product]);

  /* ------------------------------------------------------------------------ */
  /* Memoized Values                                                           */
  /* ------------------------------------------------------------------------ */

  const images = useMemo(() => {
    if (product?.media?.length) {
      return product.media.map((media) => ({
        id: media.id,
        url: media.url,
        alt: media.alt || product.name,
      }));
    }
    return [];
  }, [product]);

  const effectiveVariant = selectedVariant;
  const availableStock = effectiveVariant?.stockQuantity || product?.stockQuantity || 0;
  const isInStock = availableStock > 0 || !!effectiveVariant?.isPreorder;

  const maxQuantity = effectiveVariant?.quantityLimitPerCustomer || availableStock || 999;

  /* ------------------------------------------------------------------------ */
  /* Handlers                                                                 */
  /* ------------------------------------------------------------------------ */

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleShare = useCallback(async () => {
    if (!product) return;
    try {
      await Share.share({
        title: product.name,
        message: `${product.name}\n${product.description?.substring(0, 100)}...\n\nView on Univa: https://univa.app/ecommerce/${product.slug}`,
      });
    } catch (error) {
      console.log(error);
    }
  }, [product]);

  const handleAddToCart = useCallback(() => {
    if (!product || !effectiveVariant) {
      Alert.alert("Error", "Please select a variant.");
      return;
    }

    if (quantity < 1) {
      Alert.alert("Error", "Quantity must be at least 1.");
      return;
    }

    addToCart(product, effectiveVariant, quantity);
    Alert.alert("Success", `${product.name} added to cart!`);
  }, [product, effectiveVariant, quantity, addToCart]);

  const handleBuyNow = useCallback(() => {
    if (!product || !effectiveVariant) return;
    addToCart(product, effectiveVariant, quantity);
    router.push("/ecommerce/checkout");
  }, [product, effectiveVariant, quantity, addToCart, router]);

  const handleVariantSelect = useCallback((variant) => {
    setSelectedVariant(variant);
    setVariantSheetVisible(false);
  }, []);

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  /* ------------------------------------------------------------------------ */
  /* Loading                                                                  */
  /* ------------------------------------------------------------------------ */

  if (loading && !product) {
    return <ProductDetailsSkeleton />;
  }

  /* ------------------------------------------------------------------------ */
  /* Error                                                                    */
  /* ------------------------------------------------------------------------ */

  if (error) {
    return (
      <ErrorState
        title="Unable to load product"
        description={error.message || "Please try again."}
        onRetry={refetch}
      />
    );
  }

  /* ------------------------------------------------------------------------ */
  /* Empty State                                                              */
  /* ------------------------------------------------------------------------ */

  if (!product) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.header}>
          <TouchableOpacity onPress={handleBack} style={styles.headerButton}>
            <ArrowLeft size={24} color={colors.text} />
          </TouchableOpacity>
        </View>
        <View style={styles.emptyContainer}>
          <Text style={[styles.emptyText, { color: colors.text }]}>
            Product not found
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  /* ------------------------------------------------------------------------ */
  /* Render                                                                   */
  /* ------------------------------------------------------------------------ */

  return (
    <SafeAreaView
      style={[
        styles.container,
        { backgroundColor: colors.background },
      ]}
    >
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={handleBack} style={styles.headerButton}>
          <ArrowLeft size={24} color={colors.text} />
        </TouchableOpacity>
        <TouchableOpacity onPress={handleShare} style={styles.headerButton}>
          <Share2 size={22} color={colors.text} />
        </TouchableOpacity>
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={handleRefresh}
            colors={[colors.primary]}
            tintColor={colors.primary}
          />
        }
      >
        {/* Product Gallery */}
        <ProductGallery
          images={images}
          productName={product.name}
          onImagePress={() => {}}
        />

        {/* Product Content */}
        <View style={styles.contentInner}>
          {/* Product Header */}
          <ProductHeader
            name={product.name}
            rating={product.rating || averageRating}
            reviewCount={totalReviews}
            brand={product.brand}
            sku={effectiveVariant?.sku || product.sku}
          />

          {/* Product Price */}
          <ProductPrice
            price={effectiveVariant?.price?.amount || product.price?.amount || 0}
            comparePrice={effectiveVariant?.comparePrice || product.comparePrice}
            currency={effectiveVariant?.price?.currency || product.price?.currency || currency || "USD"}
            discount={product.discount}
          />

          {/* Variant Selector */}
          {product.variants?.length > 0 && (
            <TouchableOpacity
              style={[
                styles.variantTrigger,
                { borderColor: colors.border || "#E5E7EB" },
              ]}
              onPress={() => setVariantSheetVisible(true)}
            >
              <Text style={[styles.variantTriggerText, { color: colors.text }]}>
                {effectiveVariant?.name || "Select Variant"}
              </Text>
              <Text style={[styles.variantTriggerArrow, { color: colors.textSecondary }]}>
                {effectiveVariant ? "✓" : "▼"}
              </Text>
            </TouchableOpacity>
          )}

          {/* Quantity Selector */}
          <ProductQuantitySelector
            quantity={quantity}
            setQuantity={setQuantity}
            min={1}
            max={maxQuantity}
            stock={availableStock}
            inStock={isInStock}
          />

          {/* Stock Status */}
          <View style={styles.stockContainer}>
            <Text
              style={[
                styles.stockText,
                { color: isInStock ? colors.success : colors.error },
              ]}
            >
              {isInStock ? "✅ In Stock" : "❌ Out of Stock"}
            </Text>
            {isInStock && availableStock > 0 && (
              <Text style={[styles.stockCount, { color: colors.textSecondary }]}>
                {availableStock} units available
              </Text>
            )}
          </View>

          {/* Description */}
          {product.description && (
            <ProductDescription description={product.description} />
          )}

          {/* Attributes/Specifications */}
          {attributes?.length > 0 && (
            <ProductSpecifications attributes={attributes} />
          )}

          {/* Seller Info */}
          {product.seller && (
            <SellerInfo
              seller={product.seller}
              onPress={() => {
                router.push({
                  pathname: "/ecommerce/seller-profile",
                  params: { id: product.seller.id },
                });
              }}
            />
          )}

          {/* Reviews */}
          <ProductReviews
            reviews={reviews}
            averageRating={averageRating}
            totalReviews={totalReviews}
            distribution={ratingDistribution}
            loading={reviewsLoading}
            onLoadMore={loadMoreReviews}
            hasMore={hasMoreReviews}
            onWriteReview={() => {
              router.push({
                pathname: "/ecommerce/write-review",
                params: { productId: product.id },
              });
            }}
          />

          {/* Related Products */}
          {relatedProducts.length > 0 && (
            <RelatedProducts
              products={relatedProducts}
              loading={relatedLoading}
              onProductPress={(product) => {
                router.push({
                  pathname: "/ecommerce/[slug]",
                  params: { slug: product.slug },
                });
              }}
            />
          )}
        </View>

        <View style={styles.bottomSpacing} />
      </ScrollView>

      {/* Bottom Action Bar */}
      <View
        style={[
          styles.bottomBar,
          { backgroundColor: colors.card || colors.background },
          { borderTopColor: colors.border || "#E5E7EB" },
        ]}
      >
        <View style={styles.bottomBarContent}>
          <TouchableOpacity
            style={styles.favoriteButton}
            onPress={() => {}}
          >
            <Heart size={24} color={colors.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.addToCartButton,
              { backgroundColor: colors.primary },
              (!isInStock || !effectiveVariant) && styles.disabledButton,
            ]}
            onPress={handleAddToCart}
            disabled={!isInStock || !effectiveVariant}
          >
            <ShoppingBag size={20} color="#fff" />
            <Text style={styles.addToCartText}>
              {!isInStock ? "Out of Stock" : "Add to Cart"}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.buyNowButton,
              { backgroundColor: colors.success || "#10B981" },
              (!isInStock || !effectiveVariant) && styles.disabledButton,
            ]}
            onPress={handleBuyNow}
            disabled={!isInStock || !effectiveVariant}
          >
            <Text style={styles.buyNowText}>Buy Now</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Variant Sheet */}
      <ProductVariantSheet
        visible={variantSheetVisible}
        variants={product.variants || []}
        selectedVariant={effectiveVariant}
        onSelect={handleVariantSelect}
        onClose={() => setVariantSheetVisible(false)}
      />
    </SafeAreaView>
  );
}

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    zIndex: 10,
  },

  headerButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.9)",
    justifyContent: "center",
    alignItems: "center",
  },

  content: {
    paddingTop: 60,
    paddingBottom: 120,
  },

  contentInner: {
    paddingHorizontal: 16,
  },

  variantTrigger: {
    height: 48,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderRadius: 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 16,
  },

  variantTriggerText: {
    fontSize: 15,
  },

  variantTriggerArrow: {
    fontSize: 16,
  },

  stockContainer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 8,
  },

  stockText: {
    fontSize: 14,
    fontWeight: "600",
  },

  stockCount: {
    fontSize: 12,
  },

  bottomSpacing: {
    height: 80,
  },

  bottomBar: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    paddingBottom: 24,
    borderTopWidth: 1,
  },

  bottomBarContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },

  favoriteButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    justifyContent: "center",
    alignItems: "center",
  },

  addToCartButton: {
    flex: 1,
    flexDirection: "row",
    height: 48,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
  },

  addToCartText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },

  buyNowButton: {
    height: 48,
    paddingHorizontal: 20,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
  },

  buyNowText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },

  disabledButton: {
    opacity: 0.5,
  },

  emptyContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },

  emptyText: {
    fontSize: 16,
  },
});