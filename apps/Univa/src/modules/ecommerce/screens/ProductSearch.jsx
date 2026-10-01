/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/screens/ProductSearch.jsx                 */
/* -------------------------------------------------------------------------- */

import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TextInput,
  FlatList,
  RefreshControl,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { Search, X, Filter, ArrowLeft } from "lucide-react-native";

import useSearch from "@/modules/ecommerce/hooks/useSearch";
import { useChannel } from "@/modules/ecommerce/context/ChannelContext";

import ProductCard from "@/modules/ecommerce/components/products/ProductCard";
import SearchEmpty from "@/modules/ecommerce/components/search/SearchEmpty";
import SearchSkeleton from "@/modules/ecommerce/components/search/SearchSkeleton";
import SearchFilters from "@/modules/ecommerce/components/search/SearchFilters";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEFAULT_PAGE_SIZE = 20;

/* -------------------------------------------------------------------------- */
/* Screen                                                                     */
/* -------------------------------------------------------------------------- */

export default function ProductSearchScreen() {
  const router = useRouter();
  const { colors } = theme;
  const { channel } = useChannel();
  const [showFilters, setShowFilters] = useState(false);

  const {
    products,
    searchQuery,
    setSearch,
    clearSearch,
    filters,
    totalCount,
    loading,
    isRefreshing,
    hasNextPage,
    loadMore,
    setSort,
    setCategory,
    setPriceRange,
    toggleInStock,
    resetFilters,
    refreshSearch,
  } = useSearch({
    pageSize: DEFAULT_PAGE_SIZE,
    channelSlug: channel?.slug,
  });

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

  const handleSearch = useCallback((text) => {
    setSearch(text);
  }, [setSearch]);

  const handleClear = useCallback(() => {
    clearSearch();
  }, [clearSearch]);

  const handleRefresh = useCallback(() => {
    refreshSearch();
  }, [refreshSearch]);

  const handleLoadMore = useCallback(() => {
    if (!loading && hasNextPage) {
      loadMore();
    }
  }, [loading, hasNextPage, loadMore]);

  const toggleFilters = useCallback(() => {
    setShowFilters((prev) => !prev);
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Render Item                                                              */
  /* ------------------------------------------------------------------------ */

  const renderItem = useCallback(
    ({ item }) => (
      <ProductCard
        product={item}
        onPress={handleProductPress}
        style={styles.productCard}
      />
    ),
    [handleProductPress]
  );

  const ListEmptyComponent = useCallback(() => {
    if (loading) {
      return (
        <View style={styles.skeletonContainer}>
          <SearchSkeleton />
          <SearchSkeleton />
          <SearchSkeleton />
        </View>
      );
    }
    return <SearchEmpty onRefresh={handleRefresh} />;
  }, [loading, handleRefresh]);

  const ListFooterComponent = useCallback(() => {
    if (loading && products.length > 0) {
      return (
        <View style={styles.footerLoader}>
          <ActivityIndicator size="small" color={colors.primary} />
        </View>
      );
    }
    if (!hasNextPage && products.length > 0) {
      return (
        <View style={styles.footerText}>
          <Text style={[styles.endText, { color: colors.textSecondary }]}>
            No more products
          </Text>
        </View>
      );
    }
    return null;
  }, [loading, products.length, hasNextPage, colors]);

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

        <View style={[styles.searchContainer, { backgroundColor: colors.card || "#F3F4F6" }]}>
          <Search size={20} color={colors.textSecondary} />
          <TextInput
            style={[styles.searchInput, { color: colors.text }]}
            placeholder="Search products..."
            placeholderTextColor={colors.textSecondary}
            value={searchQuery}
            onChangeText={handleSearch}
            autoFocus
            returnKeyType="search"
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={handleClear}>
              <X size={18} color={colors.textSecondary} />
            </TouchableOpacity>
          )}
        </View>

        <TouchableOpacity onPress={toggleFilters} style={styles.filterButton}>
          <Filter size={22} color={colors.text} />
        </TouchableOpacity>
      </View>

      {/* Results Count */}
      {products.length > 0 && (
        <View style={styles.resultsCount}>
          <Text style={[styles.resultsText, { color: colors.textSecondary }]}>
            {totalCount} results found
          </Text>
        </View>
      )}

      {/* Filters Sheet */}
      <SearchFilters
        visible={showFilters}
        onClose={() => setShowFilters(false)}
        filters={filters}
        onApply={setSort}
        onReset={resetFilters}
      />

      {/* Results */}
      <FlatList
        data={products}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        numColumns={2}
        columnWrapperStyle={styles.columnWrapper}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.3}
        ListEmptyComponent={ListEmptyComponent}
        ListFooterComponent={ListFooterComponent}
        showsVerticalScrollIndicator={false}
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
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
  },

  backButton: {
    padding: 4,
  },

  searchContainer: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 10,
    paddingHorizontal: 12,
    height: 44,
    gap: 10,
  },

  searchInput: {
    flex: 1,
    fontSize: 16,
    paddingVertical: 8,
  },

  filterButton: {
    padding: 8,
  },

  resultsCount: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },

  resultsText: {
    fontSize: 14,
  },

  listContent: {
    paddingHorizontal: 12,
    paddingBottom: 80,
  },

  columnWrapper: {
    justifyContent: "space-between",
    paddingHorizontal: 4,
  },

  productCard: {
    width: "48%",
    marginBottom: 12,
  },

  skeletonContainer: {
    paddingHorizontal: 8,
  },

  footerLoader: {
    paddingVertical: 20,
    alignItems: "center",
  },

  footerText: {
    paddingVertical: 20,
    alignItems: "center",
  },

  endText: {
    fontSize: 14,
  },
});