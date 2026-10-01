/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/products/ProductPrice.jsx      */
/* -------------------------------------------------------------------------- */

import React, { memo, useMemo } from "react";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const formatPrice = (money) => {
  if (!money) return "₦0";

  if (money.formatted) {
    return money.formatted;
  }

  const amount = Number(
    money.amount ?? money.value ?? 0
  );

  const currency =
    money.currency ?? "NGN";

  const symbol =
    currency === "NGN"
      ? "₦"
      : currency === "USD"
      ? "$"
      : currency === "EUR"
      ? "€"
      : currency === "GBP"
      ? "£"
      : `${currency} `;

  return `${symbol}${amount.toLocaleString()}`;
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductPrice = memo(
  ({
    product,

    size = "medium",

    align = "left",

    showDiscount = true,

    showSavings = true,

    style,
  }) => {
    const { colors } = theme;


    const salePrice =
      product?.salePrice;

    const regularPrice =
      product?.price;

    const currentPrice =
      salePrice || regularPrice;

    const discount =
      product?.discountPercentage ??
      0;

    const hasDiscount =
      product?.hasDiscount ||
      (salePrice &&
        regularPrice);

    const savings = useMemo(() => {
      if (
        !salePrice ||
        !regularPrice
      ) {
        return 0;
      }

      return Math.max(
        Number(
          regularPrice.amount ?? 0
        ) -
          Number(
            salePrice.amount ?? 0
          ),
        0
      );
    }, [salePrice, regularPrice]);

    const fontSize =
      size === "large"
        ? 24
        : size === "small"
        ? 15
        : 19;

    return (
      <View
        style={[
          styles.container,
          {
            alignItems:
              align === "center"
                ? "center"
                : align === "right"
                ? "flex-end"
                : "flex-start",
          },
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Current Price */}
        {/* -------------------------------------------------------------- */}

        <Text
          style={[
            styles.currentPrice,
            {
              color:
                colors.primary,
              fontSize,
            },
          ]}
        >
          {formatPrice(
            currentPrice
          )}
        </Text>

        {/* -------------------------------------------------------------- */}
        {/* Previous Price */}
        {/* -------------------------------------------------------------- */}

        {hasDiscount && (
          <View
            style={
              styles.discountRow
            }
          >
            <Text
              style={[
                styles.oldPrice,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {formatPrice(
                regularPrice
              )}
            </Text>

            {showDiscount &&
              discount > 0 && (
                <View
                  style={
                    styles.discountBadge
                  }
                >
                  <Text
                    style={
                      styles.discountText
                    }
                  >
                    -{discount}%
                  </Text>
                </View>
              )}
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Savings */}
        {/* -------------------------------------------------------------- */}

        {showSavings &&
          savings > 0 && (
            <Text
              style={[
                styles.savings,
                {
                  color:
                    "#22C55E",
                },
              ]}
            >
              Save ₦
              {savings.toLocaleString()}
            </Text>
          )}
      </View>
    );
  }
);

ProductPrice.displayName =
  "ProductPrice";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    marginTop: 10,
  },

  currentPrice: {
    fontWeight: "700",
  },

  discountRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 4,
  },

  oldPrice: {
    fontSize: 14,
    textDecorationLine:
      "line-through",
  },

  discountBadge: {
    marginLeft: 8,
    backgroundColor:
      "#EF4444",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },

  discountText: {
    color: "#FFFFFF",
    fontSize: 11,
    fontWeight: "700",
  },

  savings: {
    marginTop: 4,
    fontSize: 13,
    fontWeight: "600",
  },
});

export default ProductPrice;