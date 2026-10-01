/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/screens/Wishlist.jsx                      */
/* -------------------------------------------------------------------------- */

import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  FlatList,
  RefreshControl,
  TouchableOpacity,
} from "react-native";
import { useRouter } from "expo-router";
import { ArrowLeft, Heart } from "lucide-react-native";

import useWishlist from "@/modules/ecommerce/hooks/useWishlist";
import { useCart } from "@/modules/ecommerce/context/CartContext";

import WishlistCard from "@/modules/ecommerce/components/wishlist/WishlistCard";
import WishlistEmpty from "@/modules/ecommerce/components/wishlist/EmptyWishlist";
import WishlistSkeleton from "@/modules/ecommerce/components/wishlist/WishlistSkeleton";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Screen                                                                     */
/* -------------------------------------------------------------------------- */

export default function WishlistScreen() {
  const router = useRouter();
  const { colors } = theme;
  const { addToCart } = useCart();

  const {
    wishlistItems,
    loading,
    refreshing,
    error,
    removeFromWishlist,
    refreshWishlist,
    moveToCart,
    isEmpty,
    totalItems,
  } = useWishlist();

  const [movingItemId, setMovingItemId] = useState(null);

  /* ------------------------------------------------------------------------ */
  /* Handlers                                                                 */
  /* ------------------------------------------------------------------------ */

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleProductPress = useCallback((product) => {
    router.push({
      pathname: "/ecommerce/[slug]",
      params: { slug: product.slug || product.id },
    });
  }, [router]);

  const handleRemove = useCallback(async (itemId) => {
    await removeFromWishlist(itemId);
  }, [removeFromWishlist]);

  const handleMoveToCart = useCallback(async (item) => {
    setMovingItemId(item.id);
    const result = await moveToCart(item);
    setMovingItemId(null);
    if (result.success) {
      // Optionally show success message
    }
  }, [moveToCart]);

  const handleRefresh = useCallback(() => {
    refreshWishlist();
  }, [refreshWishlist]);

  /* ------------------------------------------------------------------------ */
  /* Render Item                                                              */
  /* ------------------------------------------------------------------------ */

  const renderItem = useCallback(
    ({ item }) => (
      <WishlistCard
        item={item}
        onPress={handleProductPress}
        onRemove={handleRemove}
        onMoveToCart={handleMoveToCart}
        isMoving={movingItemId === item.id}
      />
    ),
    [handleProductPress, handleRemove, handleMoveToCart, movingItemId]
  );

  const ListEmptyComponent = useCallback(() => {
    if (loading) {
      return <WishlistSkeleton />;
    }
    return <WishlistEmpty onShopNow={() => router.push("/ecommerce/shop")} />;
  }, [loading, router]);

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
        <TouchableOpacity onPress={handleBack} style={styles.backButton}>
          <ArrowLeft size={24} color={colors.text} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.text }]}>
          Wishlist
        </Text>
        <View style={styles.headerRight}>
          {totalItems > 0 && (
            <View style={styles.countBadge}>
              <Text style={styles.countText}>{totalItems}</Text>
            </View>
          )}
        </View>
      </View>

      {/* Empty State with Heart Icon */}
      {isEmpty && !loading && (
        <View style={styles.emptyIconContainer}>
          <Heart size={64} color={colors.textSecondary} strokeWidth={1.5} />
          <Text style={[styles.emptyIconText, { color: colors.textSecondary }]}>
            Your wishlist is empty
          </Text>
        </View>
      )}

      {/* Wishlist Items */}
      <FlatList
        data={wishlistItems}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
        ListEmptyComponent={ListEmptyComponent}
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
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 12,
  },

  backButton: {
    padding: 4,
  },

  headerTitle: {
    fontSize: 18,
    fontWeight: "600",
  },

  headerRight: {
    width: 40,
    alignItems: "center",
    justifyContent: "center",
  },

  countBadge: {
    backgroundColor: "#EF4444",
    borderRadius: 12,
    minWidth: 24,
    height: 24,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 6,
  },

  countText: {
    color: "#FFFFFF",
    fontSize: 12,
    fontWeight: "700",
  },

  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 40,
  },

  emptyIconContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    gap: 16,
  },

  emptyIconText: {
    fontSize: 16,
  },
});