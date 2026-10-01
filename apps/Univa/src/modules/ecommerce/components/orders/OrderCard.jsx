/* -------------------------------------------------------------------------- */
/*                              OrderCard.jsx                                 */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from 'react';

import PropTypes from 'prop-types';

import {
  View,
  Text,
  StyleSheet,
  Pressable,
} from 'react-native';

import {
  MaterialCommunityIcons,
} from '@expo/vector-icons';

import {
  colors,
  spacing,
  radius,
  typography,
} from '../../../theme';

import Money from '../common/Money';
import NetworkImage from '../common/NetworkImage';

import OrderStatusBadge from './OrderStatusBadge';
import OrderActions from './OrderActions';

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

function OrderCard({
  order,
  loading,
  showActions,
  onPress,
  onTrack,
  onDetails,
  onBuyAgain,
  onCancel,
}) {
  /* ---------------------------------------------------------------------- */
  /* Early Return - No Order                                                */
  /* ---------------------------------------------------------------------- */

  if (!order) {
    return null;
  }

  /* ---------------------------------------------------------------------- */
  /* Derived Values                                                         */
  /* ---------------------------------------------------------------------- */

  const items = useMemo(
    () => order?.lines ?? order?.items ?? [],
    [order]
  );

  const previewItems = useMemo(
    () => items.slice(0, 2),
    [items]
  );

  const remainingItems = useMemo(
    () => Math.max(items.length - 2, 0),
    [items]
  );

  const totalQuantity = useMemo(
    () =>
      items.reduce(
        (sum, item) =>
          sum + Number(item.quantity ?? 0),
        0
      ),
    [items]
  );

  const orderNumber = useMemo(
    () =>
      order?.orderNumber ??
      order?.number ??
      (order?.id ? `#${order.id}` : '-'),
    [order]
  );

  const orderDate = useMemo(() => {
    const dateString = order?.createdAt ?? order?.created;

    if (!dateString) {
      return '--';
    }

    try {
      const date = new Date(dateString);
      if (!Number.isNaN(date.getTime())) {
        return date.toLocaleDateString();
      }
      return '--';
    } catch {
      return '--';
    }
  }, [order?.createdAt, order?.created]);

  const hasItems = previewItems.length > 0;

  /* ---------------------------------------------------------------------- */
  /* Handlers                                                               */
  /* ---------------------------------------------------------------------- */

  const handlePress = useCallback(() => {
    onPress?.(order);
  }, [order, onPress]);

  const handleTrack = useCallback(() => {
    onTrack?.(order);
  }, [order, onTrack]);

  const handleDetails = useCallback(() => {
    onDetails?.(order);
  }, [order, onDetails]);

  const handleBuyAgain = useCallback(() => {
    onBuyAgain?.(order);
  }, [order, onBuyAgain]);

  const handleCancel = useCallback(() => {
    onCancel?.(order);
  }, [order, onCancel]);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View style={styles.card}>
      {/* ------------------------------------------------------------------ */}
      {/* Pressable Area - Header, Items, Summary                            */}
      {/* ------------------------------------------------------------------ */}

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Order ${orderNumber}`}
        style={({ pressed }) => [
          pressed && styles.pressed,
        ]}
        onPress={handlePress}
      >
        {/* ---------------------------------------------------------------- */}
        {/* Header                                                           */}
        {/* ---------------------------------------------------------------- */}

        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Text
              numberOfLines={1}
              style={styles.orderNumber}
            >
              {orderNumber}
            </Text>

            <View style={styles.dateRow}>
              <MaterialCommunityIcons
                name="calendar-outline"
                size={14}
                color={colors.textSecondary}
              />

              <Text style={styles.orderDate}>
                {orderDate}
              </Text>
            </View>
          </View>

          <OrderStatusBadge
            status={order?.status}
          />
        </View>

        {/* ---------------------------------------------------------------- */}
        {/* Order Items Preview                                              */}
        {/* ---------------------------------------------------------------- */}

        {hasItems ? (
          <View style={styles.itemsContainer}>
            {previewItems.map((item, index) => {
              const image =
                item?.thumbnail?.url ??
                item?.product?.thumbnail?.url ??
                item?.variant?.product?.thumbnail?.url ??
                item?.image;

              const name =
                item?.productName ??
                item?.product?.name ??
                item?.variant?.product?.name ??
                'Product';

              return (
                <View
                  key={item.id ?? index}
                  style={styles.itemRow}
                >
                  <NetworkImage
                    source={image}
                    style={styles.image}
                    resizeMode="cover"
                  />

                  <View style={styles.itemContent}>
                    <Text
                      numberOfLines={2}
                      style={styles.productName}
                    >
                      {name}
                    </Text>

                    <View style={styles.itemMetaRow}>
                      <Text style={styles.quantity}>
                        Qty: {item.quantity ?? 1}
                      </Text>

                      {item.variantName && (
                        <Text
                          numberOfLines={1}
                          style={styles.variant}
                        >
                          {item.variantName}
                        </Text>
                      )}
                    </View>
                  </View>
                </View>
              );
            })}

            {remainingItems > 0 && (
              <View style={styles.moreItemsContainer}>
                <MaterialCommunityIcons
                  name="dots-horizontal-circle-outline"
                  size={18}
                  color={colors.primary}
                />

                <Text style={styles.moreItemsText}>
                  +{remainingItems} more item
                  {remainingItems > 1 ? 's' : ''}
                </Text>
              </View>
            )}
          </View>
        ) : (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>
              No items found
            </Text>
          </View>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Order Statistics                                                 */}
        {/* ---------------------------------------------------------------- */}

        <View style={styles.statisticsRow}>
          <View style={styles.statItem}>
            <MaterialCommunityIcons
              name="package-variant-closed"
              size={16}
              color={colors.primary}
            />

            <Text style={styles.statText}>
              {totalQuantity} item
              {totalQuantity !== 1 ? 's' : ''}
            </Text>
          </View>

          {order?.trackingNumber && (
            <View style={styles.statItem}>
              <MaterialCommunityIcons
                name="truck-fast-outline"
                size={16}
                color={colors.success}
              />

              <Text
                numberOfLines={1}
                style={styles.statText}
              >
                {order.trackingNumber}
              </Text>
            </View>
          )}
        </View>

        {/* ---------------------------------------------------------------- */}
        {/* Summary                                                          */}
        {/* ---------------------------------------------------------------- */}

        <View style={styles.summary}>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>
              Total
            </Text>

            <Money
              amount={
                order?.total?.gross?.amount ??
                order?.total?.amount ??
                order?.total ??
                0
              }
              currency={
                order?.total?.gross?.currency ??
                order?.currency ??
                'NGN'
              }
              style={styles.totalAmount}
            />
          </View>

          {order?.paymentMethod && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>
                Payment
              </Text>

              <Text style={styles.summaryValue}>
                {order.paymentMethod}
              </Text>
            </View>
          )}

          {order?.shippingMethod && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>
                Delivery
              </Text>

              <Text style={styles.summaryValue}>
                {order.shippingMethod}
              </Text>
            </View>
          )}
        </View>
      </Pressable>

      {/* ------------------------------------------------------------------ */}
      {/* Actions - Outside Pressable to prevent event conflicts             */}
      {/* ------------------------------------------------------------------ */}

      {showActions && (
        <OrderActions
          order={order}
          loading={loading}
          showTrack={
            !!order?.trackingNumber &&
            order?.status !== 'DELIVERED'
          }
          showDetails
          showBuyAgain={
            order?.status === 'DELIVERED'
          }
          showCancel={[
            'UNCONFIRMED',
            'UNFULFILLED',
            'PROCESSING',
          ].includes(order?.status ?? '')}
          onTrack={handleTrack}
          onDetails={handleDetails}
          onBuyAgain={handleBuyAgain}
          onCancel={handleCancel}
        />
      )}
    </View>
  );
}

/* -------------------------------------------------------------------------- */
/*                                   Styles                                   */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginHorizontal: spacing.lg,
    marginVertical: spacing.sm,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border || '#E5E7EB',
  },

  pressed: {
    opacity: 0.85,
  },

  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing.lg,
  },

  headerLeft: {
    flex: 1,
    marginRight: spacing.md,
  },

  orderNumber: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
    color: colors.text,
    marginBottom: spacing.xs,
  },

  dateRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },

  orderDate: {
    marginLeft: spacing.xs,
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
  },

  itemsContainer: {
    marginBottom: spacing.lg,
  },

  itemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
  },

  image: {
    width: 64,
    height: 64,
    borderRadius: radius.md,
    backgroundColor: colors.surface || '#F5F5F5',
  },

  itemContent: {
    flex: 1,
    marginLeft: spacing.md,
  },

  productName: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.medium,
    color: colors.text,
    marginBottom: spacing.xs,
  },

  itemMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },

  quantity: {
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
    marginRight: spacing.md,
  },

  variant: {
    fontSize: typography.fontSize.sm,
    color: colors.primary,
  },

  moreItemsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.xs,
  },

  moreItemsText: {
    marginLeft: spacing.xs,
    fontSize: typography.fontSize.sm,
    color: colors.primary,
    fontWeight: typography.fontWeight.medium,
  },

  emptyContainer: {
    paddingVertical: spacing.md,
    alignItems: 'center',
  },

  emptyText: {
    color: colors.textSecondary,
    fontSize: typography.fontSize.sm,
    textAlign: 'center',
  },

  statisticsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.lg,
  },

  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },

  statText: {
    marginLeft: spacing.xs,
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
  },

  summary: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border || '#E5E7EB',
    paddingVertical: spacing.md,
  },

  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginVertical: spacing.xs,
  },

  summaryLabel: {
    fontSize: typography.fontSize.md,
    color: colors.textSecondary,
  },

  summaryValue: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.medium,
    color: colors.text,
  },

  totalAmount: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary,
  },
});

/* -------------------------------------------------------------------------- */
/*                         PropTypes & Default Props                          */
/* -------------------------------------------------------------------------- */

OrderCard.propTypes = {
  /* ---------------------------------------------------------------------- */
  /* Order                                                                  */
  /* ---------------------------------------------------------------------- */

  order: PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    number: PropTypes.string,

    orderNumber: PropTypes.string,

    created: PropTypes.string,

    createdAt: PropTypes.string,

    status: PropTypes.string,

    trackingNumber: PropTypes.string,

    currency: PropTypes.string,

    paymentMethod: PropTypes.string,

    shippingMethod: PropTypes.string,

    total: PropTypes.oneOfType([
      PropTypes.number,

      PropTypes.shape({
        amount: PropTypes.oneOfType([
          PropTypes.number,
          PropTypes.string,
        ]),

        gross: PropTypes.shape({
          amount: PropTypes.oneOfType([
            PropTypes.number,
            PropTypes.string,
          ]),

          currency: PropTypes.string,
        }),
      }),
    ]),

    subtotal: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.string,
    ]),

    shipping: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.string,
    ]),

    tax: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.string,
    ]),

    discount: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.string,
    ]),

    lines: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.oneOfType([
          PropTypes.string,
          PropTypes.number,
        ]),

        quantity: PropTypes.number,

        productName: PropTypes.string,

        variantName: PropTypes.string,

        image: PropTypes.string,

        thumbnail: PropTypes.shape({
          url: PropTypes.string,
        }),

        product: PropTypes.shape({
          name: PropTypes.string,

          thumbnail: PropTypes.shape({
            url: PropTypes.string,
          }),
        }),

        variant: PropTypes.shape({
          product: PropTypes.shape({
            name: PropTypes.string,

            thumbnail: PropTypes.shape({
              url: PropTypes.string,
            }),
          }),
        }),
      })
    ),

    items: PropTypes.array,
  }),

  /* ---------------------------------------------------------------------- */
  /* State                                                                  */
  /* ---------------------------------------------------------------------- */

  loading: PropTypes.bool,

  showActions: PropTypes.bool,

  /* ---------------------------------------------------------------------- */
  /* Callbacks                                                              */
  /* ---------------------------------------------------------------------- */

  onPress: PropTypes.func,

  onTrack: PropTypes.func,

  onDetails: PropTypes.func,

  onBuyAgain: PropTypes.func,

  onCancel: PropTypes.func,
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

OrderCard.defaultProps = {
  order: null,

  loading: false,

  showActions: true,

  onPress: undefined,

  onTrack: undefined,

  onDetails: undefined,

  onBuyAgain: undefined,

  onCancel: undefined,
};

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default memo(OrderCard);