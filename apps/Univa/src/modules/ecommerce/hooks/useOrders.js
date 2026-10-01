/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useOrders.js                        */
/* -------------------------------------------------------------------------- */

import { useCallback, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@apollo/client';

import {
  ORDERS_QUERY,
  ORDER_QUERY,
  ORDER_LINES_QUERY,
  FULFILLMENTS_QUERY,
  ORDER_EVENTS_QUERY,
  ORDER_GRANTED_REFUNDS_QUERY,
} from '@/modules/ecommerce/api/productQuery/queries/order';

import {
  UPDATE_ORDER,
  DELETE_ORDER,
  CREATE_ORDER_LINE,
  UPDATE_ORDER_LINE,
  DELETE_ORDER_LINE,
  CREATE_FULFILLMENT,
  UPDATE_FULFILLMENT,
  DELETE_FULFILLMENT,
  CREATE_ORDER_GRANTED_REFUND,
  DELETE_ORDER_GRANTED_REFUND,
} from '@/modules/ecommerce/api/productQuery/mutations/orders';

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEFAULT_PAGE_SIZE = 20;
const DEFAULT_FILTER = 'ALL';
const ORDER_STATUSES = {
  DRAFT: 'DRAFT',
  UNCONFIRMED: 'UNCONFIRMED',
  UNFULFILLED: 'UNFULFILLED',
  PARTIALLY_FULFILLED: 'PARTIALLY_FULFILLED',
  FULFILLED: 'FULFILLED',
  CANCELED: 'CANCELED',
  EXPIRED: 'EXPIRED',
};

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

export default function useOrders({
  pageSize = DEFAULT_PAGE_SIZE,
  initialStatus = DEFAULT_FILTER,
  fetchPolicy = 'cache-and-network',
  skip = false,
  onCompleted,
  onError,
} = {}) {

  /* ------------------------------------------------------------------------ */
  /* Local State                                                              */
  /* ------------------------------------------------------------------------ */

  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [searchTerm, setSearchTerm] = useState('');
  const [cursor, setCursor] = useState(null);
  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [dateRange, setDateRange] = useState({ start: null, end: null });

  /* ------------------------------------------------------------------------ */
  /* Orders Query                                                             */
  /* ------------------------------------------------------------------------ */

  const {
    data,
    loading,
    error,
    refetch,
    fetchMore,
    networkStatus,
  } = useQuery(ORDERS_QUERY, {
    variables: {
      first: pageSize,
      after: cursor,
      status: statusFilter === DEFAULT_FILTER ? null : statusFilter,
      search: searchTerm || null,
      createdAtGte: dateRange.start,
      createdAtLte: dateRange.end,
    },
    skip,
    notifyOnNetworkStatusChange: true,
    fetchPolicy,
    onCompleted,
    onError,
  });

  /* ------------------------------------------------------------------------ */
  /* Selected Order Details                                                   */
  /* ------------------------------------------------------------------------ */

  const {
    data: orderData,
    loading: orderLoading,
    error: orderError,
    refetch: refetchOrder,
  } = useQuery(ORDER_QUERY, {
    skip: !selectedOrderId,
    variables: { id: selectedOrderId },
    fetchPolicy,
  });

  /* ------------------------------------------------------------------------ */
  /* Order Lines Query                                                        */
  /* ------------------------------------------------------------------------ */

  const {
    data: linesData,
    loading: linesLoading,
    error: linesError,
    refetch: refetchLines,
  } = useQuery(ORDER_LINES_QUERY, {
    skip: !selectedOrderId,
    variables: { orderId: selectedOrderId },
    fetchPolicy,
  });

  /* ------------------------------------------------------------------------ */
  /* Fulfillments Query                                                       */
  /* ------------------------------------------------------------------------ */

  const {
    data: fulfillmentsData,
    loading: fulfillmentsLoading,
    error: fulfillmentsError,
    refetch: refetchFulfillments,
  } = useQuery(FULFILLMENTS_QUERY, {
    skip: !selectedOrderId,
    variables: { orderId: selectedOrderId },
    fetchPolicy,
  });

  /* ------------------------------------------------------------------------ */
  /* Order Events Query                                                       */
  /* ------------------------------------------------------------------------ */

  const {
    data: eventsData,
    loading: eventsLoading,
    error: eventsError,
    refetch: refetchEvents,
  } = useQuery(ORDER_EVENTS_QUERY, {
    skip: !selectedOrderId,
    variables: { orderId: selectedOrderId },
    fetchPolicy,
  });

  /* ------------------------------------------------------------------------ */
  /* Order Refunds Query                                                      */
  /* ------------------------------------------------------------------------ */

  const {
    data: refundsData,
    loading: refundsLoading,
    error: refundsError,
    refetch: refetchRefunds,
  } = useQuery(ORDER_GRANTED_REFUNDS_QUERY, {
    skip: !selectedOrderId,
    variables: { orderId: selectedOrderId },
    fetchPolicy,
  });

  /* ------------------------------------------------------------------------ */
  /* Mutations                                                                */
  /* ------------------------------------------------------------------------ */

  const [updateOrder] = useMutation(UPDATE_ORDER);
  const [deleteOrder] = useMutation(DELETE_ORDER);
  const [createOrderLine] = useMutation(CREATE_ORDER_LINE);
  const [updateOrderLine] = useMutation(UPDATE_ORDER_LINE);
  const [deleteOrderLine] = useMutation(DELETE_ORDER_LINE);
  const [createFulfillment] = useMutation(CREATE_FULFILLMENT);
  const [updateFulfillment] = useMutation(UPDATE_FULFILLMENT);
  const [deleteFulfillment] = useMutation(DELETE_FULFILLMENT);
  const [createRefund] = useMutation(CREATE_ORDER_GRANTED_REFUND);
  const [deleteRefund] = useMutation(DELETE_ORDER_GRANTED_REFUND);

  /* ------------------------------------------------------------------------ */
  /* Derived Data                                                             */
  /* ------------------------------------------------------------------------ */

  const ordersConnection = data?.orders ?? {};
  const orders = ordersConnection.edges?.map(({ node }) => node) ?? [];
  const pageInfo = ordersConnection.pageInfo ?? {};
  const hasNextPage = Boolean(pageInfo.hasNextPage);
  const endCursor = pageInfo.endCursor ?? null;
  const totalOrders = ordersConnection.totalCount ?? orders.length;

  const selectedOrder = orderData?.order ?? null;
  const orderLines = linesData?.orderLines?.edges?.map(({ node }) => node) ?? [];
  const fulfillments = fulfillmentsData?.fulfillments?.edges?.map(({ node }) => node) ?? [];
  const events = eventsData?.orderEvents?.edges?.map(({ node }) => node) ?? [];
  const refunds = refundsData?.orderGrantedRefunds?.edges?.map(({ node }) => node) ?? [];

  const isRefreshing = networkStatus === 4;
  const isEmpty = !loading && orders.length === 0;

  /* ------------------------------------------------------------------------ */
  /* Actions                                                                  */
  /* ------------------------------------------------------------------------ */

  const loadMore = useCallback(async () => {
    if (loading || !hasNextPage || !endCursor) return;

    await fetchMore({
      variables: {
        first: pageSize,
        after: endCursor,
        status: statusFilter === DEFAULT_FILTER ? null : statusFilter,
        search: searchTerm || null,
        createdAtGte: dateRange.start,
        createdAtLte: dateRange.end,
      },
    });

    setCursor(endCursor);
  }, [endCursor, fetchMore, hasNextPage, loading, pageSize, searchTerm, statusFilter, dateRange]);

  const refreshOrders = useCallback(async () => {
    setCursor(null);
    await refetch({
      first: pageSize,
      after: null,
      status: statusFilter === DEFAULT_FILTER ? null : statusFilter,
      search: searchTerm || null,
      createdAtGte: dateRange.start,
      createdAtLte: dateRange.end,
    });
  }, [pageSize, refetch, searchTerm, statusFilter, dateRange]);

  const updateSearch = useCallback((value = '') => {
    setCursor(null);
    setSearchTerm(value.trim());
  }, []);

  const updateStatusFilter = useCallback((status = DEFAULT_FILTER) => {
    setCursor(null);
    setStatusFilter(status);
  }, []);

  const updateDateRange = useCallback((start, end) => {
    setCursor(null);
    setDateRange({ start, end });
  }, []);

  const selectOrder = useCallback((orderId) => {
    setSelectedOrderId(orderId);
  }, []);

  const clearSelectedOrder = useCallback(() => {
    setSelectedOrderId(null);
  }, []);

  const refreshSelectedOrder = useCallback(async () => {
    await Promise.all([
      refetchOrder(),
      refetchLines(),
      refetchFulfillments(),
      refetchEvents(),
      refetchRefunds(),
    ]);
  }, [refetchOrder, refetchLines, refetchFulfillments, refetchEvents, refetchRefunds]);

  /* ------------------------------------------------------------------------ */
  /* Order Management Actions                                                 */
  /* ------------------------------------------------------------------------ */

  const updateOrderStatus = useCallback(async (orderId, status) => {
    try {
      const { data } = await updateOrder({
        variables: { input: { id: orderId, status } },
      });

      if (data?.updateOrder?.success) {
        await refreshOrders();
        return { success: true, order: data.updateOrder.order };
      }
      return { success: false, message: 'Failed to update order status' };
    } catch (error) {
      return { success: false, error };
    }
  }, [updateOrder, refreshOrders]);

  const deleteExistingOrder = useCallback(async (orderId) => {
    try {
      const { data } = await deleteOrder({
        variables: { input: { id: orderId } },
      });

      if (data?.deleteOrder?.success) {
        await refreshOrders();
        return { success: true };
      }
      return { success: false, message: 'Failed to delete order' };
    } catch (error) {
      return { success: false, error };
    }
  }, [deleteOrder, refreshOrders]);

  const addOrderLine = useCallback(async (orderId, productSku, quantity, unitPrice) => {
    try {
      const { data } = await createOrderLine({
        variables: {
          input: {
            orderId,
            productSku,
            quantity,
            unitPrice,
          },
        },
      });

      if (data?.createOrderLine?.success) {
        await refreshSelectedOrder();
        return { success: true, orderLine: data.createOrderLine.orderLine };
      }
      return { success: false, message: 'Failed to add order line' };
    } catch (error) {
      return { success: false, error };
    }
  }, [createOrderLine, refreshSelectedOrder]);

  const updateOrderLineItem = useCallback(async (lineId, quantity, unitPrice) => {
    try {
      const { data } = await updateOrderLine({
        variables: {
          input: {
            id: lineId,
            quantity,
            unitPrice,
          },
        },
      });

      if (data?.updateOrderLine?.success) {
        await refreshSelectedOrder();
        return { success: true, orderLine: data.updateOrderLine.orderLine };
      }
      return { success: false, message: 'Failed to update order line' };
    } catch (error) {
      return { success: false, error };
    }
  }, [updateOrderLine, refreshSelectedOrder]);

  const removeOrderLine = useCallback(async (lineId) => {
    try {
      const { data } = await deleteOrderLine({
        variables: { input: { id: lineId } },
      });

      if (data?.deleteOrderLine?.success) {
        await refreshSelectedOrder();
        return { success: true };
      }
      return { success: false, message: 'Failed to remove order line' };
    } catch (error) {
      return { success: false, error };
    }
  }, [deleteOrderLine, refreshSelectedOrder]);

  /* ------------------------------------------------------------------------ */
  /* Fulfillment Actions                                                      */
  /* ------------------------------------------------------------------------ */

  const createNewFulfillment = useCallback(async (orderId, trackingNumber) => {
    try {
      const { data } = await createFulfillment({
        variables: {
          input: {
            orderId,
            trackingNumber,
          },
        },
      });

      if (data?.createFulfillment?.success) {
        await refreshSelectedOrder();
        return { success: true, fulfillment: data.createFulfillment.fulfillment };
      }
      return { success: false, message: 'Failed to create fulfillment' };
    } catch (error) {
      return { success: false, error };
    }
  }, [createFulfillment, refreshSelectedOrder]);

  const updateFulfillmentTracking = useCallback(async (fulfillmentId, trackingNumber, status) => {
    try {
      const { data } = await updateFulfillment({
        variables: {
          input: {
            id: fulfillmentId,
            trackingNumber,
            status,
          },
        },
      });

      if (data?.updateFulfillment?.success) {
        await refreshSelectedOrder();
        return { success: true, fulfillment: data.updateFulfillment.fulfillment };
      }
      return { success: false, message: 'Failed to update fulfillment' };
    } catch (error) {
      return { success: false, error };
    }
  }, [updateFulfillment, refreshSelectedOrder]);

  const deleteExistingFulfillment = useCallback(async (fulfillmentId) => {
    try {
      const { data } = await deleteFulfillment({
        variables: { input: { id: fulfillmentId } },
      });

      if (data?.deleteFulfillment?.success) {
        await refreshSelectedOrder();
        return { success: true };
      }
      return { success: false, message: 'Failed to delete fulfillment' };
    } catch (error) {
      return { success: false, error };
    }
  }, [deleteFulfillment, refreshSelectedOrder]);

  /* ------------------------------------------------------------------------ */
  /* Refund Actions                                                           */
  /* ------------------------------------------------------------------------ */

  const createOrderRefund = useCallback(async (orderId, amount, reason) => {
    try {
      const { data } = await createRefund({
        variables: {
          input: {
            orderId,
            amount,
            reason,
          },
        },
      });

      if (data?.createOrderGrantedRefund?.success) {
        await refreshSelectedOrder();
        return { success: true, refund: data.createOrderGrantedRefund.refund };
      }
      return { success: false, message: 'Failed to create refund' };
    } catch (error) {
      return { success: false, error };
    }
  }, [createRefund, refreshSelectedOrder]);

  const deleteOrderRefund = useCallback(async (refundId) => {
    try {
      const { data } = await deleteRefund({
        variables: { input: { id: refundId } },
      });

      if (data?.deleteOrderGrantedRefund?.success) {
        await refreshSelectedOrder();
        return { success: true };
      }
      return { success: false, message: 'Failed to delete refund' };
    } catch (error) {
      return { success: false, error };
    }
  }, [deleteRefund, refreshSelectedOrder]);

  /* ------------------------------------------------------------------------ */
  /* Helper Functions                                                         */
  /* ------------------------------------------------------------------------ */

  const findOrderById = useCallback((orderId) => {
    return orders.find((order) => String(order.id) === String(orderId)) ?? null;
  }, [orders]);

  const getOrderStatusColor = useCallback((status) => {
    const colors = {
      DRAFT: 'gray',
      UNCONFIRMED: 'yellow',
      UNFULFILLED: 'blue',
      PARTIALLY_FULFILLED: 'purple',
      FULFILLED: 'green',
      CANCELED: 'red',
      EXPIRED: 'gray',
    };
    return colors[status] || 'gray';
  }, []);

  const getOrderStatusLabel = useCallback((status) => {
    const labels = {
      DRAFT: 'Draft',
      UNCONFIRMED: 'Unconfirmed',
      UNFULFILLED: 'Unfulfilled',
      PARTIALLY_FULFILLED: 'Partially Fulfilled',
      FULFILLED: 'Fulfilled',
      CANCELED: 'Canceled',
      EXPIRED: 'Expired',
    };
    return labels[status] || status;
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Error Normalization                                                      */
  /* ------------------------------------------------------------------------ */

  const normalizedError = useMemo(() => {
    const currentError = error || orderError || linesError || fulfillmentsError || eventsError || refundsError;
    if (!currentError) return null;
    return {
      message: currentError.message ?? 'Unable to load orders.',
      graphQLErrors: currentError.graphQLErrors ?? [],
      networkError: currentError.networkError ?? null,
    };
  }, [error, orderError, linesError, fulfillmentsError, eventsError, refundsError]);

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Data
    orders,
    selectedOrder,
    orderLines,
    fulfillments,
    events,
    refunds,
    totalOrders,
    hasNextPage,
    endCursor,
    pageInfo,

    // Filters
    statusFilter,
    searchTerm,
    dateRange,

    // Loading
    loading,
    orderLoading,
    linesLoading,
    fulfillmentsLoading,
    eventsLoading,
    refundsLoading,
    isRefreshing,
    isEmpty,

    // Error
    error: normalizedError,

    // Actions
    refreshOrders,
    loadMore,
    updateSearch,
    updateStatusFilter,
    updateDateRange,
    selectOrder,
    clearSelectedOrder,
    refreshSelectedOrder,

    // Order Management
    updateOrderStatus,
    deleteExistingOrder,
    addOrderLine,
    updateOrderLineItem,
    removeOrderLine,

    // Fulfillment
    createNewFulfillment,
    updateFulfillmentTracking,
    deleteExistingFulfillment,

    // Refunds
    createOrderRefund,
    deleteOrderRefund,

    // Helpers
    findOrderById,
    getOrderStatusColor,
    getOrderStatusLabel,
    ORDER_STATUSES,

    // Clear utilities
    clearSearch: () => updateSearch(''),
    resetFilters: () => {
      setStatusFilter(DEFAULT_FILTER);
      setSearchTerm('');
      setDateRange({ start: null, end: null });
      setCursor(null);
    },
  };
}