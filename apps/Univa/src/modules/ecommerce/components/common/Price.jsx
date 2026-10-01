/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/Price.jsx               */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */

const Price = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Pricing                                                                 */
    /* ---------------------------------------------------------------------- */

    price,

    salePrice,

    currency,

    discountPercentage,

    hasDiscount,

    /* ---------------------------------------------------------------------- */
    /* Appearance                                                              */
    /* ---------------------------------------------------------------------- */

    size = "md", // xs | sm | md | lg | xl

    showDiscount = true,

    showCurrency = true,

    strikeThrough = true,

    align = "left",

    color,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const textSize =
      useMemo(() => {
        switch (size) {
          case "xs":
            return 11;

          case "sm":
            return 13;

          case "lg":
            return 20;

          case "xl":
            return 26;

          default:
            return 16;
        }
      }, [size]);

    /* ---------------------------------------------------------------------- */

    const oldPriceSize =
      Math.max(
        textSize - 2,
        10
      );

    /* ---------------------------------------------------------------------- */

    const currentPrice =
      salePrice ??
      price;

    const oldPrice =
      hasDiscount
        ? price
        : null;

    /* ---------------------------------------------------------------------- */

    const formattedCurrent =
      useMemo(() => {
        if (
          currentPrice ==
          null
        ) {
          return "--";
        }

        if (
          typeof currentPrice ===
          "object"
        ) {
          return (
            currentPrice.formatted ??
            currentPrice.amount
          );
        }

        return showCurrency
          ? `${currency ?? "₦"}${Number(
              currentPrice
            ).toLocaleString()}`
          : Number(
              currentPrice
            ).toLocaleString();
      }, [
        currentPrice,
        currency,
        showCurrency,
      ]);

    /* ---------------------------------------------------------------------- */

    const formattedOld =
      useMemo(() => {
        if (
          !oldPrice
        ) {
          return null;
        }

        if (
          typeof oldPrice ===
          "object"
        ) {
          return (
            oldPrice.formatted ??
            oldPrice.amount
          );
        }

        return showCurrency
          ? `${currency ?? "₦"}${Number(
              oldPrice
            ).toLocaleString()}`
          : Number(
              oldPrice
            ).toLocaleString();
      }, [
        oldPrice,
        currency,
        showCurrency,
      ]);

    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,

          {
            justifyContent:
              align ===
              "center"
                ? "center"
                : align ===
                  "right"
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
          numberOfLines={1}
          style={[
            styles.current,

            {
              fontSize:
                textSize,

              color:
                color ??
                colors.primary,
            },
          ]}
        >
          {formattedCurrent}
        </Text>

        {/* -------------------------------------------------------------- */}
        {/* Old Price */}
        {/* -------------------------------------------------------------- */}

        {!!formattedOld && (
          <Text
            numberOfLines={1}
            style={[
              styles.old,

              {
                fontSize:
                  oldPriceSize,

                color:
                  colors.textSecondary,

                textDecorationLine:
                  strikeThrough
                    ? "line-through"
                    : "none",
              },
            ]}
          >
            {formattedOld}
          </Text>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Discount */}
        {/* -------------------------------------------------------------- */}

        {showDiscount &&
          hasDiscount &&
          !!discountPercentage && (
            <View
              style={[
                styles.discount,

                {
                  backgroundColor:
                    colors.error,
                },
              ]}
            >
              <Text
                style={
                  styles.discountText
                }
              >
                -{discountPercentage}%
              </Text>
            </View>
          )}
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */

Price.displayName =
  "Price";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flexDirection:
        "row",

      alignItems:
        "center",

      flexWrap:
        "wrap",
    },

    current: {
      fontWeight: "700",
    },

    old: {
      marginLeft: 8,

      fontWeight: "500",
    },

    discount: {
      marginLeft: 8,

      paddingHorizontal: 8,

      paddingVertical: 3,

      borderRadius: 6,
    },

    discountText: {
      color: "#FFF",

      fontWeight: "700",

      fontSize: 11,
    },
  });

/* -------------------------------------------------------------------------- */

export default Price;