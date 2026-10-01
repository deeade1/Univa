/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/PriceComparison.jsx     */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useMemo,
} from "react";

import {
    StyleSheet,
    View,
} from "react-native";

import PropTypes
    from "prop-types";

import Price
    from "./Price";

import Money
    from "./Money";

import DiscountBadge
    from "./DiscountBadge";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const calculateSavings = (
    price,
    originalPrice
) => {

    if (
        originalPrice <= price
    ) {
        return 0;
    }

    return (
        originalPrice -
        price
    );

};

const calculateDiscount = (
    price,
    originalPrice
) => {

    if (
        originalPrice <= price ||
        originalPrice <= 0
    ) {
        return 0;
    }

    return Math.round(
        (
            (originalPrice - price) /
            originalPrice
        ) * 100
    );

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const PriceComparison = memo(({

    price,

    originalPrice,

    currency = "₦",

    orientation = "vertical",

    size = "medium",

    showOriginalPrice = true,

    showSavings = true,

    showDiscountBadge = true,

    showCurrency = true,

    badgeVariant = "filled",

    style,

}) => {

    const {
        colors,
    } = theme;

    /* ---------------------------------------------------------------------- */
    /* Derived Values                                                         */
    /* ---------------------------------------------------------------------- */

    const savings =
        useMemo(
            () =>
                calculateSavings(
                    price,
                    originalPrice
                ),
            [
                price,
                originalPrice,
            ]
        );

    const discount =
        useMemo(
            () =>
                calculateDiscount(
                    price,
                    originalPrice
                ),
            [
                price,
                originalPrice,
            ]
        );

    const hasDiscount =
        discount > 0;

    const isHorizontal =
        orientation ===
        "horizontal";
            /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (

        <View
            style={[
                styles.container,

                isHorizontal
                    ? styles.horizontal
                    : styles.vertical,

                style,
            ]}
        >

            {/* -------------------------------------------------------------- */}
            {/* Current Price                                                  */}
            {/* -------------------------------------------------------------- */}

            <View
                style={styles.currentRow}
            >

                <Price
                    value={price}
                    currency={currency}
                    size={size}
                    showCurrency={
                        showCurrency
                    }
                />

                {showDiscountBadge &&
                    hasDiscount && (

                    <DiscountBadge
                        value={discount}
                        variant={
                            badgeVariant
                        }
                        size="small"
                    />

                )}

            </View>

            {/* -------------------------------------------------------------- */}
            {/* Original Price                                                 */}
            {/* -------------------------------------------------------------- */}

            {showOriginalPrice &&
                hasDiscount && (

                <Price
                    value={
                        originalPrice
                    }
                    currency={currency}
                    size="small"
                    showCurrency={
                        showCurrency
                    }
                    strikeThrough
                    color={
                        colors.textSecondary
                    }
                    style={
                        styles.originalPrice
                    }
                />

            )}

            {/* -------------------------------------------------------------- */}
            {/* Savings                                                        */}
            {/* -------------------------------------------------------------- */}

            {showSavings &&
                hasDiscount && (

                <View
                    style={
                        styles.savingsRow
                    }
                >

                    <Money
                        value={savings}
                        currency={currency}
                        showCurrency={
                            showCurrency
                        }
                        prefix="Save "
                        size="small"
                        color={
                            colors.success
                        }
                    />

                </View>

            )}

        </View>

    );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

PriceComparison.displayName =
    "PriceComparison";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

PriceComparison.propTypes = {

    price:
        PropTypes.number
            .isRequired,

    originalPrice:
        PropTypes.number,

    currency:
        PropTypes.string,

    orientation:
        PropTypes.oneOf([
            "vertical",
            "horizontal",
        ]),

    size:
        PropTypes.oneOf([
            "small",
            "medium",
            "large",
        ]),

    showOriginalPrice:
        PropTypes.bool,

    showSavings:
        PropTypes.bool,

    showDiscountBadge:
        PropTypes.bool,

    showCurrency:
        PropTypes.bool,

    badgeVariant:
        PropTypes.oneOf([
            "filled",
            "outline",
            "soft",
        ]),

    style:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
    StyleSheet.create({

        container: {

            justifyContent:
                "center",

        },

        vertical: {

            flexDirection:
                "column",

            alignItems:
                "flex-start",

        },

        horizontal: {

            flexDirection:
                "row",

            alignItems:
                "center",

            flexWrap:
                "wrap",

        },

        currentRow: {

            flexDirection:
                "row",

            alignItems:
                "center",

            flexWrap:
                "wrap",

        },

        originalPrice: {

            marginTop:
                4,

        },

        savingsRow: {

            marginTop:
                4,

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    PriceComparison;