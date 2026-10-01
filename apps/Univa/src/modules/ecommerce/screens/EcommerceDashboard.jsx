/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/screens/EcommerceDashboard.jsx            */
/* -------------------------------------------------------------------------- */

import React, { useCallback, useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  SafeAreaView,
  Pressable,
  TouchableOpacity,
} from "react-native";
import { Link, useRouter } from "expo-router";
import {
  Store,
  List,
  ShoppingCart,
  User,
  Search,
} from "lucide-react-native";

import useDashboard from "@/modules/ecommerce/hooks/useDashboard";
import { useCart } from "@/modules/ecommerce/context/CartContext";
import { useChannel } from "@/modules/ecommerce/context/ChannelContext";

import CategoryList from "@/modules/ecommerce/components/categories/CategoryList";
import FlashSaleProducts from "@/modules/ecommerce/components/products/FlashSaleProducts";
import FeaturedProducts from "@/modules/ecommerce/components/products/FeaturedProducts";
import RecommendedProducts from "@/modules/ecommerce/components/products/RecommendedProducts";
import TrendingProducts from "@/modules/ecommerce/components/products/TrendingProducts";
import BestSellers from "@/modules/ecommerce/components/products/BestSellers";
import NewArrivals from "@/modules/ecommerce/components/products/NewArrivals";
import RecentlyViewedProducts from "@/modules/ecommerce/components/products/RecentlyViewedProducts";
import ProductCarousel from "@/modules/ecommerce/components/products/ProductCarousel";

import DashboardSkeleton from "@/modules/ecommerce/components/skeleton/DashboardSkeleton";
import ErrorState from "@/modules/ecommerce/components/common/ErrorState";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const SHORTCUTS = [
  { label: "Go to Market", icon: <Store size={20} />, href: "/ecommerce/gotomarket" },
  { label: "Products", icon: <List size={20} />, href: "/ecommerce/productlist" },
  { label: "Cart", icon: <ShoppingCart size={20} />, href: "/ecommerce/cart" },
  { label: "Search", icon: <Search size={20} />, href: "/ecommerce/productlist" },
];

/* -------------------------------------------------------------------------- */
/* Screen                                                                     */
/* -------------------------------------------------------------------------- */

export default function EcommerceDashboard() {
  const router = useRouter();
  const { colors } = theme;
  const { channel, currency } = useChannel();
  const { cartCount, hasItems } = useCart();

  const {
    featuredProducts,
    recommendedProducts,
    trendingProducts,
    recentlyViewed,
    flashSaleProducts,
    bestSellers,
    newArrivals,
    categories,
    loading,
    error,
    refetch,
    isRefreshing,
  } = useDashboard({
    channelSlug: channel?.slug,
    currency: currency,
  });

  /* ------------------------------------------------------------------------ */
  /* Navigation Handlers                                                      */
  /* ------------------------------------------------------------------------ */

  const navigateToProduct = useCallback((product) => {
    if (!product?.id) return;
    router.push({
      pathname: "/ecommerce/[slug]",
      params: {
        slug: product.slug ?? product.id,
      },
    });
  }, [router]);

  const navigateToCategory = useCallback((category) => {
    if (!category?.id) return;
    router.push({
      pathname: "/ecommerce/productlist",
      params: {
        category: category.id,
        categoryName: category.name,
      },
    });
  }, [router]);

  const navigateToSearch = useCallback(() => {
    router.push("/ecommerce/productlist");
  }, [router]);

  const navigateToFlashSale = useCallback(() => {
    router.push({
      pathname: "/ecommerce/productlist",
      params: { filter: "flash-sale" },
    });
  }, [router]);

  const navigateToAllProducts = useCallback(() => {
    router.push("/ecommerce/productlist");
  }, [router]);

  const navigateToCart = useCallback(() => {
    router.push("/ecommerce/cart");
  }, [router]);

  /* ------------------------------------------------------------------------ */
  /* Render Shortcuts                                                         */
  /* ------------------------------------------------------------------------ */

  const renderShortcuts = useCallback(() => {
    return SHORTCUTS.map((item, idx) => (
      <Link key={idx} href={item.href} asChild>
        <Pressable
          style={[
            styles.shortcut,
            { backgroundColor: colors.card || colors.background },
          ]}
        >
          <View style={styles.iconContainer}>
            {React.cloneElement(item.icon, { color: colors.primary })}
            {item.label === "Cart" && cartCount > 0 && (
              <View style={[styles.badge, { backgroundColor: colors.error }]}>
                <Text style={styles.badgeText}>
                  {cartCount > 99 ? "99+" : cartCount}
                </Text>
              </View>
            )}
          </View>
          <Text style={[styles.shortcutText, { color: colors.text }]}>
            {item.label}
          </Text>
        </Pressable>
      </Link>
    ));
  }, [cartCount, colors]);

  /* ------------------------------------------------------------------------ */
  /* Loading State                                                            */
  /* ------------------------------------------------------------------------ */

  if (loading && !featuredProducts.length) {
    return <DashboardSkeleton />;
  }

  /* ------------------------------------------------------------------------ */
  /* Error State                                                              */
  /* ------------------------------------------------------------------------ */

  if (error && !featuredProducts.length) {
    return (
      <ErrorState
        title="Unable to load dashboard"
        description={error.message || "Please try again."}
        onRetry={refetch}
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
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={refetch}
            colors={[colors.primary]}
            tintColor={colors.primary}
          />
        }
        contentContainerStyle={styles.content}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={[styles.title, { color: colors.text }]}>
              Univa Market 🛍️
            </Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              {channel?.name ? `Shopping in ${channel.name}` : "Your shopping destination"}
            </Text>
          </View>
          <TouchableOpacity
            style={[styles.cartButton, { backgroundColor: colors.primary }]}
            onPress={navigateToCart}
          >
            <ShoppingCart size={20} color="#fff" />
            {cartCount > 0 && (
              <View style={[styles.cartBadge, { backgroundColor: colors.error }]}>
                <Text style={styles.cartBadgeText}>
                  {cartCount > 99 ? "99+" : cartCount}
                </Text>
              </View>
            )}
          </TouchableOpacity>
        </View>

        {/* Quick Shortcuts */}
        <View style={styles.shortcutGrid}>
          {renderShortcuts()}
        </View>

        {/* Hero Banner / Carousel */}
        {featuredProducts.length > 0 && (
          <View style={styles.section}>
            <ProductCarousel
              products={featuredProducts}
              onProductPress={navigateToProduct}
            />
          </View>
        )}

        {/* Categories */}
        {categories?.length > 0 && (
          <View style={styles.section}>
            <CategoryList
              categories={categories.slice(0, 8)}
              onPress={navigateToCategory}
            />
          </View>
        )}

        {/* Flash Sale */}
        {flashSaleProducts?.length > 0 && (
          <View style={styles.section}>
            <FlashSaleProducts
              products={flashSaleProducts}
              onProductPress={navigateToProduct}
              onViewAll={navigateToFlashSale}
            />
          </View>
        )}

        {/* Featured Products */}
        {featuredProducts.length > 0 && (
          <View style={styles.section}>
            <FeaturedProducts
              products={featuredProducts}
              title="Featured Products"
              onProductPress={navigateToProduct}
              onViewAll={navigateToAllProducts}
            />
          </View>
        )}

        {/* Best Sellers */}
        {bestSellers?.length > 0 && (
          <View style={styles.section}>
            <BestSellers
              products={bestSellers}
              onProductPress={navigateToProduct}
              onViewAll={navigateToAllProducts}
            />
          </View>
        )}

        {/* New Arrivals */}
        {newArrivals?.length > 0 && (
          <View style={styles.section}>
            <NewArrivals
              products={newArrivals}
              onProductPress={navigateToProduct}
              onViewAll={navigateToAllProducts}
            />
          </View>
        )}

        {/* Trending Products */}
        {trendingProducts?.length > 0 && (
          <View style={styles.section}>
            <TrendingProducts
              products={trendingProducts}
              onProductPress={navigateToProduct}
              onViewAll={navigateToAllProducts}
            />
          </View>
        )}

        {/* Recommended Products */}
        {recommendedProducts?.length > 0 && (
          <View style={styles.section}>
            <RecommendedProducts
              products={recommendedProducts}
              title="Recommended for You"
              onProductPress={navigateToProduct}
              onViewAll={navigateToAllProducts}
            />
          </View>
        )}

        {/* Recently Viewed */}
        {recentlyViewed?.length > 0 && (
          <View style={styles.section}>
            <RecentlyViewedProducts
              products={recentlyViewed}
              onProductPress={navigateToProduct}
            />
          </View>
        )}
      </ScrollView>
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

  content: {
    paddingBottom: 100,
  },

  header: {
    padding: 20,
    paddingTop: 16,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  title: {
    fontSize: 28,
    fontWeight: "700",
    marginBottom: 4,
  },

  subtitle: {
    fontSize: 14,
  },

  cartButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: "center",
    alignItems: "center",
    position: "relative",
  },

  cartBadge: {
    position: "absolute",
    top: -4,
    right: -4,
    borderRadius: 10,
    minWidth: 18,
    height: 18,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 4,
  },

  cartBadgeText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontWeight: "600",
  },

  shortcutGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-around",
    padding: 16,
    marginBottom: 8,
  },

  shortcut: {
    alignItems: "center",
    justifyContent: "center",
    width: "40%",
    marginVertical: 8,
    padding: 12,
    borderRadius: 12,
  },

  iconContainer: {
    position: "relative",
  },

  badge: {
    position: "absolute",
    top: -8,
    right: -8,
    borderRadius: 10,
    minWidth: 18,
    height: 18,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 4,
  },

  badgeText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontWeight: "600",
  },

  shortcutText: {
    marginTop: 6,
    fontSize: 14,
    fontWeight: "600",
  },

  section: {
    paddingHorizontal: 16,
    marginBottom: 8,
  },
});