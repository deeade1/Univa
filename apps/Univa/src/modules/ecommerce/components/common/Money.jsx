/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/Money.jsx               */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import {
  Text,
  StyleSheet,
} from "react-native";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */

const Money = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Value                                                                    */
    /* ---------------------------------------------------------------------- */

    value,

    amount,

    currency = "₦",

    locale = "en-NG",

    precision = 2,

    showCurrency = true,

    useFormatted = true,

    /* ---------------------------------------------------------------------- */
    /* Appearance                                                               */
    /* ---------------------------------------------------------------------- */

    size = "md", // xs | sm | md | lg | xl

    weight = "600",

    color,

    align = "left",

    numberOfLines = 1,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const fontSize =
      useMemo(() => {
        switch (size) {
          case "xs":
            return 11;

          case "sm":
            return 13;

          case "lg":
            return 20;

          case "xl":
            return 28;

          default:
            return 16;
        }
      }, [size]);

    /* ---------------------------------------------------------------------- */

    const displayValue =
      useMemo(() => {
        const money =
          value ?? amount;

        if (
          money == null
        ) {
          return "--";
        }

        /* Relay Money object */

        if (
          typeof money ===
          "object"
        ) {
          if (
            useFormatted &&
            money.formatted
          ) {
            return money.formatted;
          }

          const numeric =
            Number(
              money.amount ?? 0
            );

          return showCurrency
            ? `${money.currency ?? currency}${numeric.toLocaleString(
                locale,
                {
                  minimumFractionDigits:
                    precision,

                  maximumFractionDigits:
                    precision,
                }
              )}`
            : numeric.toLocaleString(
                locale,
                {
                  minimumFractionDigits:
                    precision,

                  maximumFractionDigits:
                    precision,
                }
              );
        }

        /* Primitive number */

        const numeric =
          Number(money);

        return showCurrency
          ? `${currency}${numeric.toLocaleString(
              locale,
              {
                minimumFractionDigits:
                  precision,

                maximumFractionDigits:
                  precision,
              }
            )}`
          : numeric.toLocaleString(
              locale,
              {
                minimumFractionDigits:
                  precision,

                maximumFractionDigits:
                  precision,
              }
            );
      }, [
        value,
        amount,
        currency,
        locale,
        precision,
        showCurrency,
        useFormatted,
      ]);

    /* ---------------------------------------------------------------------- */

    return (
      <Text
        numberOfLines={
          numberOfLines
        }
        style={[
          styles.text,

          {
            fontSize,

            fontWeight:
              weight,

            color:
              color ??
              colors.text,

            textAlign:
              align,
          },

          style,
        ]}
      >
        {displayValue}
      </Text>
    );
  }
);

/* -------------------------------------------------------------------------- */

Money.displayName =
  "Money";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    text: {
      includeFontPadding:
        false,
    },
  });

/* -------------------------------------------------------------------------- */

export default Money;