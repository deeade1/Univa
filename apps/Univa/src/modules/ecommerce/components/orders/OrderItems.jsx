/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/orders/OrderItem.jsx           */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";

import {
  View,
  Text,
  Image,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import {
  colors,
  spacing,
  radius,
  typography,
} from "../../../theme";

import Money from "../common/Money";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const OrderItem = memo(
  ({
    item,
    compact = false,
    showImage = true,
    showQuantity = true,
    showPrice = true,
    showTotal = true,
    showVariant = true,
    showStatus = false,
    showChevron = false,
    onPress,
    style,
  }) => {
    if (!item) {
      return null;
    }

    // Safely extract image URL
    const image =
      item?.image ??
      item?.product?.image ??
      item?.product?.thumbnail?.url ??
      null;

    const name =
      item?.name ??
      item?.product?.name ??
      "Product";

    const variant =
      item?.variant ??
      item?.productVariant;

    const quantity = item?.quantity ?? 1;

    // Extract price with proper fallbacks
    const unitPrice = item?.price ?? item?.unitPrice;

    const totalPrice = item?.total ?? item?.subtotal ?? unitPrice;

    // Determine currency
    const currency =
      item?.currency ??
      item?.price?.currency ??
      item?.total?.currency ??
      "NGN";

    return (
      <Pressable
        disabled={!onPress}
        onPress={() => onPress?.(item)}
        style={[
          styles.container,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
          compact && styles.compactContainer,
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Product Image                                                   */}
        {/* -------------------------------------------------------------- */}

        {showImage && (
          image ? (
            <Image
              source={{ uri: image }}
              resizeMode="cover"
              style={[
                styles.image,
                compact && styles.compactImage,
              ]}
            />
          ) : (
            <View
              style={[
                styles.image,
                styles.imagePlaceholder,
                compact && styles.compactImage,
              ]}
            >
              <MaterialCommunityIcons
                name="image-off-outline"
                size={compact ? 24 : 28}
                color={colors.textSecondary}
              />
            </View>
          )
        )}

        {/* -------------------------------------------------------------- */}
        {/* Product Info                                                    */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.content}>
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

          {showVariant && !!variant && (
            <Text
              style={[
                styles.variant,
                {
                  color: colors.textSecondary,
                },
              ]}
            >
              {variant}
            </Text>
          )}

          {showStatus && !!item?.status && (
            <View style={styles.statusRow}>
              <MaterialCommunityIcons
                name="check-circle-outline"
                size={14}
                color={colors.success}
              />

              <Text
                style={[
                  styles.status,
                  {
                    color: colors.textSecondary,
                  },
                ]}
              >
                {item.status}
              </Text>
            </View>
          )}

          <View style={styles.footer}>
            <View>
              {showPrice && (
                <Money
                  amount={unitPrice ?? 0}
                  currency={currency}
                  style={styles.price}
                />
              )}

              {showTotal && quantity > 1 && (
                <Text
                  style={[
                    styles.total,
                    {
                      color: colors.textSecondary,
                    },
                  ]}
                >
                  Total:{" "}
                  <Money
                    amount={totalPrice ?? 0}
                    currency={currency}
                    style={styles.totalAmount}
                  />
                </Text>
              )}
            </View>

            {showQuantity && (
              <View
                style={[
                  styles.quantityBadge,
                  {
                    backgroundColor: `${colors.primary}15`,
                  },
                ]}
              >
                <Text
                  style={[
                    styles.quantity,
                    {
                      color: colors.primary,
                    },
                  ]}
                >
                  ×{quantity}
                </Text>
              </View>
            )}
          </View>
        </View>

        {showChevron && (
          <MaterialCommunityIcons
            name="chevron-right"
            size={22}
            color={colors.textSecondary}
          />
        )}
      </Pressable>
    );
  }
);

OrderItem.displayName = "OrderItem";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

OrderItem.propTypes = {
  /**
   * Order item data
   */
  item: PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    name: PropTypes.string,

    image: PropTypes.string,

    quantity: PropTypes.number,

    status: PropTypes.string,

    variant: PropTypes.string,

    productVariant: PropTypes.string,

    price: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.shape({
        amount: PropTypes.number,
        currency: PropTypes.string,
        formatted: PropTypes.string,
      }),
    ]),

    unitPrice: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.shape({
        amount: PropTypes.number,
        currency: PropTypes.string,
        formatted: PropTypes.string,
      }),
    ]),

    total: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.shape({
        amount: PropTypes.number,
        currency: PropTypes.string,
        formatted: PropTypes.string,
      }),
    ]),

    subtotal: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.shape({
        amount: PropTypes.number,
        currency: PropTypes.string,
        formatted: PropTypes.string,
      }),
    ]),

    currency: PropTypes.string,

    product: PropTypes.shape({
      name: PropTypes.string,
      image: PropTypes.string,
      thumbnail: PropTypes.shape({
        url: PropTypes.string,
      }),
    }),
  }),

  /**
   * Compact mode
   */
  compact: PropTypes.bool,

  /**
   * Show product image
   */
  showImage: PropTypes.bool,

  /**
   * Show quantity
   */
  showQuantity: PropTypes.bool,

  /**
   * Show unit price
   */
  showPrice: PropTypes.bool,

  /**
   * Show total price
   */
  showTotal: PropTypes.bool,

  /**
   * Show variant
   */
  showVariant: PropTypes.bool,

  /**
   * Show status
   */
  showStatus: PropTypes.bool,

  /**
   * Show chevron
   */
  showChevron: PropTypes.bool,

  /**
   * Press callback
   */
  onPress: PropTypes.func,

  /**
   * Style override
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

OrderItem.defaultProps = {
  item: null,
  compact: false,
  showImage: true,
  showQuantity: true,
  showPrice: true,
  showTotal: true,
  showVariant: true,
  showStatus: false,
  showChevron: false,
  onPress: undefined,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },

  compactContainer: {
    padding: spacing.sm,
  },

  image: {
    width: 82,
    height: 82,
    borderRadius: radius.md,
    backgroundColor: colors.surface || "#F3F4F6",
  },

  compactImage: {
    width: 64,
    height: 64,
    borderRadius: radius.sm,
  },

  imagePlaceholder: {
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.surface || "#F3F4F6",
  },

  content: {
    flex: 1,
    marginLeft: spacing.md,
  },

  name: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
  },

  variant: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.sm,
  },

  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: spacing.xs,
  },

  status: {
    marginLeft: spacing.xs,
    fontSize: typography.fontSize.sm,
  },

  footer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    marginTop: spacing.md,
  },

  price: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
  },

  total: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.sm,
  },

  totalAmount: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
  },

  quantityBadge: {
    minWidth: 42,
    height: 30,
    borderRadius: radius.full,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: spacing.sm,
  },

  quantity: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default OrderItem;