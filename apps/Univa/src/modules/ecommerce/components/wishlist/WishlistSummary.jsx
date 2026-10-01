/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/WishlistSummary.jsx   */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Summary Card                                                               */
/* -------------------------------------------------------------------------- */

const SummaryCard = memo(
  ({
    icon,
    label,
    value,
    color,
  }) => {
    const { colors } = theme;

    return (
      <View
        style={[
          styles.card,
          {
            backgroundColor:
              colors.card,

            borderColor:
              colors.border,
          },
        ]}
      >
        <View
          style={[
            styles.iconContainer,
            {
              backgroundColor:
                `${color}15`,
            },
          ]}
        >
          <MaterialCommunityIcons
            name={icon}
            size={20}
            color={color}
          />
        </View>

        <Text
          numberOfLines={1}
          style={[
            styles.value,
            {
              color:
                colors.text,
            },
          ]}
        >
          {value}
        </Text>

        <Text
          numberOfLines={2}
          style={[
            styles.label,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          {label}
        </Text>
      </View>
    );
  }
);

SummaryCard.displayName =
  "SummaryCard";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const WishlistSummary = memo(
  ({
    itemCount = 0,

    totalValue = 0,

    totalSavings = 0,

    inStockCount = 0,

    outOfStockCount = 0,

    currency = "$",

    showItems = true,

    showValue = true,

    showSavings = true,

    showStock = true,

    style,
  }) => {
    const summary = useMemo(() => {
      const cards = [];

      if (showItems) {
        cards.push({
          key: "items",
          icon: "heart-outline",
          label: "Saved Items",
          value: itemCount,
          color: "#EF4444",
        });
      }

      if (showValue) {
        cards.push({
          key: "value",
          icon: "cash-multiple",
          label: "Wishlist Value",
          value: `${currency}${Number(
            totalValue
          ).toLocaleString()}`,
          color: "#3B82F6",
        });
      }

      if (showSavings) {
        cards.push({
          key: "savings",
          icon: "sale",
          label: "Savings",
          value: `${currency}${Number(
            totalSavings
          ).toLocaleString()}`,
          color: "#10B981",
        });
      }

      if (showStock) {
        cards.push({
          key: "stock",
          icon: "package-variant",
          label: "In Stock",
          value: `${inStockCount}/${itemCount}`,
          color:
            outOfStockCount > 0
              ? "#F59E0B"
              : "#10B981",
        });
      }

      return cards;
    }, [
      itemCount,
      totalValue,
      totalSavings,
      inStockCount,
      outOfStockCount,
      currency,
      showItems,
      showValue,
      showSavings,
      showStock,
    ]);

    return (
      <View
        style={[
          styles.container,
          style,
        ]}
      >
        {summary.map(
          (item) => (
            <SummaryCard
              key={item.key}
              {...item}
            />
          )
        )}
      </View>
    );
  }
);

WishlistSummary.displayName =
  "WishlistSummary";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

WishlistSummary.propTypes = {
  itemCount:
    PropTypes.number,

  totalValue:
    PropTypes.number,

  totalSavings:
    PropTypes.number,

  inStockCount:
    PropTypes.number,

  outOfStockCount:
    PropTypes.number,

  currency:
    PropTypes.string,

  showItems:
    PropTypes.bool,

  showValue:
    PropTypes.bool,

  showSavings:
    PropTypes.bool,

  showStock:
    PropTypes.bool,

  style:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),
};

WishlistSummary.defaultProps = {
  itemCount: 0,

  totalValue: 0,

  totalSavings: 0,

  inStockCount: 0,

  outOfStockCount: 0,

  currency: "$",

  showItems: true,

  showValue: true,

  showSavings: true,

  showStock: true,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent:
      "space-between",
    marginBottom: 20,
  },

  card: {
    width: "48%",

    borderWidth: 1,

    borderRadius: 18,

    padding: 16,

    marginBottom: 14,
  },

  iconContainer: {
    width: 42,

    height: 42,

    borderRadius: 21,

    justifyContent:
      "center",

    alignItems:
      "center",

    marginBottom: 14,
  },

  value: {
    fontSize: 20,

    fontWeight: "700",
  },

  label: {
    marginTop: 6,

    fontSize: 13,

    lineHeight: 18,
  },
});

export default WishlistSummary;