/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/screens/OrderDetailsScreen.jsx            */
/* -------------------------------------------------------------------------- */

import React, { useCallback, useMemo } from "react";
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  RefreshControl,
  SafeAreaView,
  TouchableOpacity,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { ArrowLeft } from "lucide-react-native";

import useOrders from "@/modules/ecommerce/hooks/useOrders";

import OrderCard from "@/modules/ecommerce/components/orders/OrderCard";
import OrderItems from "@/modules/ecommerce/components/orders/OrderItems";
import OrderTimeline from "@/modules/ecommerce/components/orders/OrderTimeline";
import OrderActions from "@/modules/ecommerce/components/orders/OrderActions";
import OrderAddressCard from "@/modules/ecommerce/components/orders/OrderAddressCard";
import OrderPaymentCard from "@/modules/ecommerce/components/orders/OrderPaymentCard";
import OrderSkeleton from "@/modules/ecommerce/components/orders/OrderSkeleton";
import OrdersEmpty from "@/modules/ecommerce/components/orders/OrdersEmpty";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

export default function OrderDetailsScreen() {
  const router = useRouter();
  const { colors } = theme;
  const { id } = useLocalSearchParams();

  const {
    selectedOrder,
    orderLines,
    fulfillments,
    events,
    refunds,
    loading,
    isRefreshing,
    refreshSelectedOrder,
    updateOrderStatus,
    cancelOrder,
    deleteExistingOrder,
    getOrderStatusColor,
    getOrderStatusLabel,
    ORDER_STATUSES,
  } = useOrders({
    selectedOrderId: id,
    autoSelect: true,
  });

  /* ------------------------------------------------------------------------ */
  /* Navigation                                                               */
  /* ------------------------------------------------------------------------ */

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleTrack = useCallback(() => {
    // Navigate to tracking screen
  }, []);

  const handleBuyAgain = useCallback(async () => {
    if (!selectedOrder) return;
    // Implement buy again logic
  }, [selectedOrder]);

  const handleCancel = useCallback(async () => {
    if (!selectedOrder?.id) return;
    await cancelOrder(selectedOrder.id);
    await refreshSelectedOrder();
  }, [selectedOrder, cancelOrder, refreshSelectedOrder]);

  const handleRefresh = useCallback(() => {
    refreshSelectedOrder();
  }, [refreshSelectedOrder]);

  /* ------------------------------------------------------------------------ */
  /* Loading State                                                            */
  /* ------------------------------------------------------------------------ */

  if (loading && !selectedOrder) {
    return <OrderSkeleton details />;
  }

  /* ------------------------------------------------------------------------ */
  /* Empty State                                                              */
  /* ------------------------------------------------------------------------ */

  if (!loading && !selectedOrder) {
    return (
      <OrdersEmpty
        title="Order not found"
        description="This order may have been removed or is no longer available."
        onRefresh={handleRefresh}
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
        <TouchableOpacity onPress={handleBack} style={styles.backButton}>
          <ArrowLeft size={24} color={colors.text} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.text }]}>
          Order #{selectedOrder?.number}
        </Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
      >
        {/* Order Summary */}
        <OrderCard
          order={selectedOrder}
          showActions={false}
        />

        {/* Order Timeline */}
        {events?.length > 0 && (
          <View style={styles.section}>
            <OrderTimeline
              events={events}
              currentStatus={selectedOrder?.status}
            />
          </View>
        )}

        {/* Order Items */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={[styles.sectionTitle, { color: colors.text }]}>
              Order Items
            </Text>
            <Text style={[styles.sectionSubtitle, { color: colors.textSecondary }]}>
              {orderLines?.length || 0} item(s)
            </Text>
          </View>
          <OrderItems
            items={orderLines}
            currency={selectedOrder?.currency || "USD"}
          />
        </View>

        {/* Shipping Address */}
        {selectedOrder?.shippingAddress && (
          <View style={styles.section}>
            <OrderAddressCard
              title="Shipping Address"
              address={selectedOrder.shippingAddress}
            />
          </View>
        )}

        {/* Billing Address */}
        {selectedOrder?.billingAddress && (
          <View style={styles.section}>
            <OrderAddressCard
              title="Billing Address"
              address={selectedOrder.billingAddress}
            />
          </View>
        )}

        {/* Payment Information */}
        <View style={styles.section}>
          <OrderPaymentCard
            payment={{
              status: selectedOrder?.chargeStatus,
              method: selectedOrder?.paymentMethod,
              total: selectedOrder?.totalGrossAmount,
              currency: selectedOrder?.currency || "USD",
            }}
          />
        </View>

        {/* Fulfillments */}
        {fulfillments?.length > 0 && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: colors.text }]}>
              Fulfillment
            </Text>
            {fulfillments.map((fulfillment) => (
              <View key={fulfillment.id} style={styles.fulfillmentCard}>
                <Text style={[styles.fulfillmentText, { color: colors.text }]}>
                  Tracking: {fulfillment.trackingNumber || "N/A"}
                </Text>
                <Text style={[styles.fulfillmentStatus, { color: colors.textSecondary }]}>
                  Status: {fulfillment.status}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Order Actions */}
        <View style={styles.section}>
          <OrderActions
            order={selectedOrder}
            onTrack={handleTrack}
            onBuyAgain={handleBuyAgain}
            onCancel={handleCancel}
            showTrack={
              !!selectedOrder?.trackingNumber &&
              selectedOrder?.status !== ORDER_STATUSES.CANCELED
            }
            showBuyAgain={
              selectedOrder?.status === ORDER_STATUSES.FULFILLED
            }
            showCancel={
              [ORDER_STATUSES.UNCONFIRMED, ORDER_STATUSES.UNFULFILLED].includes(
                selectedOrder?.status
              )
            }
          />
        </View>
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

  content: {
    padding: 16,
    paddingBottom: 40,
  },

  section: {
    marginTop: 16,
  },

  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },

  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
  },

  sectionSubtitle: {
    fontSize: 14,
  },

  fulfillmentCard: {
    padding: 12,
    borderRadius: 8,
    backgroundColor: "#F3F4F6",
    marginTop: 8,
  },

  fulfillmentText: {
    fontSize: 14,
    fontWeight: "500",
  },

  fulfillmentStatus: {
    fontSize: 12,
    marginTop: 4,
  },
});