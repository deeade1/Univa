/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/screens/Cart.jsx                          */
/* -------------------------------------------------------------------------- */

import React, { useCallback, useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  SafeAreaView,
  TouchableOpacity,
  FlatList,
} from "react-native";
import { useRouter } from "expo-router";
import { Trash2, ShoppingBag, ChevronRight } from "lucide-react-native";

import { useCart } from "@/modules/ecommerce/context/CartContext";
import { useChannel } from "@/modules/ecommerce/context/ChannelContext";

import CartItem from "@/modules/ecommerce/components/cart/CartItem";
import CartSummary from "@/modules/ecommerce/components/cart/CartSummary";
import EmptyCart from "@/modules/ecommerce/components/cart/EmptyCart";
import CartSkeleton from "@/modules/ecommerce/components/cart/CartSkeleton";
import CouponSection from "@/modules/ecommerce/components/cart/CouponSection";
import SavedForLater from "@/modules/ecommerce/components/cart/SavedForLater";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Screen                                                                     */
/* -------------------------------------------------------------------------- */

export default function CartScreen() {
  const router = useRouter();
  const { colors } = theme;
  const { channel, currency } = useChannel();

  const {
    items,
    checkout,
    checkoutLines,
    totals,
    cartCount,
    loading,
    error,
    hasItems,
    isEmpty,
    addToCart,
    removeFromCart,
    updateQuantity,
    applyDiscount,
    removeDiscount,
    applyGiftCard,
    removeGiftCard,
    setShippingMethod,
    clearCart,
    refreshCart,
    placeOrder,
  } = useCart();

  /* ------------------------------------------------------------------------ */
  /* Handlers                                                                 */
  /* ------------------------------------------------------------------------ */

  const handleCheckout = useCallback(() => {
    if (!hasItems) return;
    router.push("/ecommerce/checkout");
  }, [hasItems, router]);

  const handleProductPress = useCallback((productId) => {
    router.push({
      pathname: "/ecommerce/[slug]",
      params: { id: productId },
    });
  }, [router]);

  const handleUpdateQuantity = useCallback((variantId, quantity) => {
    updateQuantity(variantId, quantity);
  }, [updateQuantity]);

  const handleRemoveItem = useCallback((variantId) => {
    removeFromCart(variantId);
  }, [removeFromCart]);

  const handleApplyCoupon = useCallback(async (code) => {
    return applyDiscount(code);
  }, [applyDiscount]);

  const handleRemoveCoupon = useCallback(() => {
    removeDiscount();
  }, [removeDiscount]);

  const handleApplyGiftCard = useCallback(async (code) => {
    return applyGiftCard(code);
  }, [applyGiftCard]);

  const handleRemoveGiftCard = useCallback((cardId) => {
    removeGiftCard(cardId);
  }, [removeGiftCard]);

  const handleRefresh = useCallback(() => {
    refreshCart();
  }, [refreshCart]);

  const handleClearCart = useCallback(() => {
    clearCart();
  }, [clearCart]);

  /* ------------------------------------------------------------------------ */
  /* Memoized Data                                                            */
  /* ------------------------------------------------------------------------ */

  const displayItems = useMemo(() => {
    return checkoutLines?.length > 0 ? checkoutLines : items;
  }, [checkoutLines, items]);

  const displayTotals = useMemo(() => {
    return checkout ? {
      subtotal: checkout.subtotal?.gross?.amount || 0,
      shipping: checkout.shippingPrice?.gross?.amount || 0,
      tax: (checkout.total?.gross?.amount || 0) - (checkout.total?.net?.amount || 0),
      total: checkout.total?.gross?.amount || 0,
      discount: checkout.discount?.amount || 0,
    } : totals;
  }, [checkout, totals]);

  const currencyCode = useMemo(() => {
    return checkout?.currency || currency || 'USD';
  }, [checkout, currency]);

  /* ------------------------------------------------------------------------ */
  /* Render Item                                                              */
  /* ------------------------------------------------------------------------ */

  const renderItem = useCallback(({ item }) => {
    const cartItem = {
      id: item.id || item.variantId,
      variantId: item.variantId,
      productId: item.productId,
      name: item.name || item.productName,
      variantName: item.variantName,
      sku: item.sku,
      price: item.unitPrice?.gross?.amount || item.price || 0,
      currency: item.currency || currencyCode,
      image: item.variant?.product?.thumbnail?.url || item.image,
      quantity: item.quantity,
      stock: item.variant?.stockQuantity || item.stock || 0,
    };

    return (
      <CartItem
        item={cartItem}
        onUpdateQuantity={handleUpdateQuantity}
        onRemove={handleRemoveItem}
        onPress={handleProductPress}
      />
    );
  }, [currencyCode, handleUpdateQuantity, handleRemoveItem, handleProductPress]);

  /* ------------------------------------------------------------------------ */
  /* Loading State                                                            */
  /* ------------------------------------------------------------------------ */

  if (loading) {
    return <CartSkeleton />;
  }

  /* ------------------------------------------------------------------------ */
  /* Empty State                                                              */
  /* ------------------------------------------------------------------------ */

  if (isEmpty || displayItems.length === 0) {
    return (
      <EmptyCart
        onShopNow={() => router.push("/ecommerce/shop")}
      />
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
        <Text style={[styles.title, { color: colors.text }]}>
          My Cart ({cartCount})
        </Text>
        <TouchableOpacity onPress={handleClearCart}>
          <Text style={[styles.clearButton, { color: colors.error }]}>
            Clear All
          </Text>
        </TouchableOpacity>
      </View>

      {/* Cart Items */}
      <FlatList
        data={displayItems}
        renderItem={renderItem}
        keyExtractor={(item) => item.id || item.variantId}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={handleRefresh}
            colors={[colors.primary]}
            tintColor={colors.primary}
          />
        }
        ListFooterComponent={
          <View style={styles.footer}>
            {/* Coupon Section */}
            <CouponSection
              onApplyCoupon={handleApplyCoupon}
              onRemoveCoupon={handleRemoveCoupon}
              onApplyGiftCard={handleApplyGiftCard}
              onRemoveGiftCard={handleRemoveGiftCard}
            />

            {/* Cart Summary */}
            <CartSummary
              subtotal={displayTotals.subtotal}
              shipping={displayTotals.shipping}
              tax={displayTotals.tax}
              discount={displayTotals.discount}
              total={displayTotals.total}
              currency={currencyCode}
              itemCount={cartCount}
              onCheckout={handleCheckout}
              checkoutDisabled={!hasItems || loading}
            />

            {/* Continue Shopping */}
            <TouchableOpacity
              style={styles.continueShopping}
              onPress={() => router.push("/ecommerce/shop")}
            >
              <ShoppingBag size={20} color={colors.primary} />
              <Text style={[styles.continueText, { color: colors.primary }]}>
                Continue Shopping
              </Text>
              <ChevronRight size={20} color={colors.primary} />
            </TouchableOpacity>
          </View>
        }
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
    paddingVertical: 16,
  },

  title: {
    fontSize: 24,
    fontWeight: "700",
  },

  clearButton: {
    fontSize: 14,
    fontWeight: "500",
  },

  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 100,
  },

  footer: {
    marginTop: 16,
    paddingBottom: 40,
  },

  continueShopping: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 16,
    marginTop: 8,
  },

  continueText: {
    fontSize: 16,
    fontWeight: "600",
    marginHorizontal: 8,
  },
});