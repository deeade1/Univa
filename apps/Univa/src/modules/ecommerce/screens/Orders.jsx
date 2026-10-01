/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/screens/Orders.jsx                        */
/* -------------------------------------------------------------------------- */

import React, { useCallback } from "react";
import {
  View,
  FlatList,
  RefreshControl,
  StyleSheet,
  SafeAreaView,
  Text,
  TouchableOpacity,
} from "react-native";
import { useRouter } from "expo-router";
import { ArrowLeft } from "lucide-react-native";

import useOrders from "@/modules/ecommerce/hooks/useOrders";

import OrderCard from "@/modules/ecommerce/components/orders/OrderCard";
import OrderSkeleton from "@/modules/ecommerce/components/orders/OrderSkeleton";
import OrdersEmpty from "@/modules/ecommerce/components/orders/OrdersEmpty";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

export default function OrdersScreen() {
  const router = useRouter();
  const { colors } = theme;

  const {
    orders,
    loading,
    isRefreshing,
    hasNextPage,
    refreshOrders,
    loadMore,
    cancelOrder,
    updateOrderStatus,
    getOrderStatusColor,
    getOrderStatusLabel,
    ORDER_STATUSES,
  } = useOrders();

  /* ------------------------------------------------------------------------ */
  /* Navigation                                                               */
  /* ------------------------------------------------------------------------ */

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleOrderPress = useCallback((order) => {
    router.push({
      pathname: "/ecommerce/order-details",
      params: { id: order.id },
    });
  }, [router]);

  const handleTrack = useCallback((order) => {
    // Navigate to tracking
  }, []);

  const handleCancel = useCallback(async (order) => {
    await cancelOrder(order.id);
  }, [cancelOrder]);

  const handleBuyAgain = useCallback((order) => {
    // Implement buy again
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Refresh                                                                  */
  /* ------------------------------------------------------------------------ */

  const handleRefresh = useCallback(() => {
    refreshOrders();
  }, [refreshOrders]);

  /* ------------------------------------------------------------------------ */
  /* List Helpers                                                             */
  /* ------------------------------------------------------------------------ */

  const keyExtractor = useCallback((item) => String(item.id), []);

  const renderItem = useCallback(
    ({ item }) => (
      <OrderCard
        order={item}
        onPress={handleOrderPress}
        onTrack={handleTrack}
        onCancel={handleCancel}
        onBuyAgain={handleBuyAgain}
      />
    ),
    [handleOrderPress, handleTrack, handleCancel, handleBuyAgain]
  );

  const handleEndReached = useCallback(() => {
    if (!loading && hasNextPage) {
      loadMore();
    }
  }, [loading, hasNextPage, loadMore]);

  const ListEmptyComponent = useCallback(() => {
    if (loading) {
      return (
        <View style={styles.skeletonContainer}>
          <OrderSkeleton />
          <OrderSkeleton />
          <OrderSkeleton />
        </View>
      );
    }
    return <OrdersEmpty onRefresh={handleRefresh} />;
  }, [loading, handleRefresh]);

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
          My Orders
        </Text>
        <View style={{ width: 40 }} />
      </View>

      <FlatList
        data={orders}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.contentContainer}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
        onEndReached={handleEndReached}
        onEndReachedThreshold={0.4}
        initialNumToRender={10}
        maxToRenderPerBatch={10}
        windowSize={10}
        removeClippedSubviews
        ListEmptyComponent={ListEmptyComponent}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        keyboardShouldPersistTaps="handled"
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
    borderBottomWidth: 1,
    borderBottomColor: "#E5E7EB",
  },

  backButton: {
    padding: 4,
  },

  headerTitle: {
    fontSize: 18,
    fontWeight: "600",
  },

  contentContainer: {
    flexGrow: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    paddingBottom: 40,
  },

  skeletonContainer: {
    paddingVertical: 8,
  },

  separator: {
    height: 12,
  },
});