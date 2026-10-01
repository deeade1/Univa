/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/ProductInfo.jsx        */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useMemo,
} from "react";

import {
    StyleSheet,
    Text,
    View,
} from "react-native";

import PropTypes
    from "prop-types";

import theme
    from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import Divider
    from "../common/Divider";

import IconLabel
    from "../common/IconLabel";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductInfo = memo(({

    /* ---------------------------------------------------------------------- */
    /* Basic Information                                                      */
    /* ---------------------------------------------------------------------- */

    name,

    brand,

    sku,

    /* ---------------------------------------------------------------------- */
    /* Pricing                                                                */
    /* ---------------------------------------------------------------------- */

    price,

    originalPrice,

    discount,

    currency = "₦",

    /* ---------------------------------------------------------------------- */
    /* Rating                                                                 */
    /* ---------------------------------------------------------------------- */

    rating,

    reviewCount = 0,

    /* ---------------------------------------------------------------------- */
    /* Availability                                                           */
    /* ---------------------------------------------------------------------- */

    inStock = true,

    stockLabel,

    /* ---------------------------------------------------------------------- */
    /* Product Badges                                                        */
    /* ---------------------------------------------------------------------- */

    badges = [],

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,

}) => {

    const {
        colors,
        typography,
    } = theme;

    /* ---------------------------------------------------------------------- */
    /* Computed Values                                                        */
    /* ---------------------------------------------------------------------- */

    const hasDiscount =
        useMemo(

            () =>

                Number(discount) > 0 &&
                Number(originalPrice) > Number(price),

            [

                discount,

                originalPrice,

                price,

            ]

        );

    const availabilityText =
        useMemo(

            () =>

                stockLabel ??

                (

                    inStock

                        ? "In Stock"

                        : "Out of Stock"

                ),

            [

                inStock,

                stockLabel,

            ]

        );
            /* ---------------------------------------------------------------------- */
    /* Badges                                                                 */
    /* ---------------------------------------------------------------------- */

    const productBadges =
        useMemo(

            () => badges.filter(Boolean),

            [badges]

        );

    /* ---------------------------------------------------------------------- */
    /* Component                                                              */
    /* ---------------------------------------------------------------------- */

    return (

        <View
            style={[

                styles.container,

                style,

            ]}
        >

            {/* ------------------------------------------------------------------ */}
            {/* Product Title                                                     */}
            {/* ------------------------------------------------------------------ */}

            {!!name && (

                <Text
                    style={[

                        styles.title,

                        {

                            color:
                                colors.text,

                        },

                    ]}
                >

                    {name}

                </Text>

            )}

            {/* ------------------------------------------------------------------ */}
            {/* Brand                                                             */}
            {/* ------------------------------------------------------------------ */}

            {!!brand && (

                <View
                    style={
                        styles.brandContainer
                    }
                >

                    <IconLabel

                        icon="storefront-outline"

                        label={brand}

                        iconColor={
                            colors.primary
                        }

                        textStyle={[

                            styles.brandText,

                            {

                                color:
                                    colors.primary,

                            },

                        ]}

                    />

                </View>

            )}

            {/* ------------------------------------------------------------------ */}
            {/* Rating                                                            */}
            {/* ------------------------------------------------------------------ */}

            {rating != null && (

                <View
                    style={
                        styles.ratingContainer
                    }
                >

                    <IconLabel

                        icon="star"

                        label={
                            `${rating}`
                        }

                        iconColor="#F5B301"

                        textStyle={[

                            styles.ratingText,

                            {

                                color:
                                    colors.text,

                            },

                        ]}

                    />

                    <Text
                        style={[

                            styles.reviewText,

                            {

                                color:
                                    colors.textSecondary,

                            },

                        ]}
                    >

                        {"("}
                        {reviewCount.toLocaleString()}
                        {" Reviews)"}

                    </Text>

                </View>

            )}

            {/* ------------------------------------------------------------------ */}
            {/* Divider                                                           */}
            {/* ------------------------------------------------------------------ */}

            <Divider
                spacing={16}
            />
                        {/* ------------------------------------------------------------------ */}
            {/* Pricing                                                           */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.priceSection
                }
            >

                <View
                    style={
                        styles.priceRow
                    }
                >

                    {/* ---------------------------------------------------------- */}
                    {/* Current Price                                              */}
                    {/* ---------------------------------------------------------- */}

                    <Text
                        style={[

                            styles.currentPrice,

                            {

                                color:
                                    colors.primary,

                            },

                        ]}
                    >

                        {currency}
                        {Number(price ?? 0).toLocaleString()}

                    </Text>

                    {/* ---------------------------------------------------------- */}
                    {/* Original Price                                             */}
                    {/* ---------------------------------------------------------- */}

                    {hasDiscount && (

                        <Text
                            style={[

                                styles.originalPrice,

                                {

                                    color:
                                        colors.textSecondary,

                                },

                            ]}
                        >

                            {currency}
                            {Number(originalPrice).toLocaleString()}

                        </Text>

                    )}

                    {/* ---------------------------------------------------------- */}
                    {/* Discount Badge                                             */}
                    {/* ---------------------------------------------------------- */}

                    {hasDiscount && (

                        <View
                            style={[

                                styles.discountBadge,

                                {

                                    backgroundColor:
                                        colors.error,

                                },

                            ]}
                        >

                            <Text
                                style={[
                                    styles.discountText,
                                    {
                                        color:
                                            colors.onError ??
                                            "#FFFFFF",
                                    },
                                ]}
                            >

                                {discount}% OFF

                            </Text>

                        </View>

                    )}

                </View>

                {/* -------------------------------------------------------------- */}
                {/* Savings                                                       */}
                {/* -------------------------------------------------------------- */}

                {hasDiscount && (

                    <Text
                        style={[

                            styles.savingsText,

                            {

                                color:
                                    colors.success,

                            },

                        ]}
                    >

                        You save {currency}
                        {(
                            Number(originalPrice) -
                            Number(price)
                        ).toLocaleString()}

                    </Text>

                )}

            </View>

            <Divider
                spacing={16}
            />
                        {/* ------------------------------------------------------------------ */}
            {/* Availability                                                      */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.stockContainer
                }
            >

                <IconLabel

                    icon={
                        inStock
                            ? "check-circle"
                            : "close-circle"
                    }

                    label={
                        availabilityText
                    }

                    iconColor={
                        inStock
                            ? colors.success
                            : colors.error
                    }

                    textStyle={[

                        styles.stockText,

                        {

                            color:
                                inStock
                                    ? colors.success
                                    : colors.error,

                        },

                    ]}

                />

            </View>

            {/* ------------------------------------------------------------------ */}
            {/* SKU                                                               */}
            {/* ------------------------------------------------------------------ */}

            {!!sku && (

                <View
                    style={
                        styles.skuContainer
                    }
                >

                    <Text
                        style={[

                            styles.skuLabel,

                            {

                                color:
                                    colors.textSecondary,

                            },

                        ]}
                    >

                        SKU:

                    </Text>

                    <Text
                        style={[

                            styles.skuValue,

                            {

                                color:
                                    colors.text,

                            },

                        ]}
                    >

                        {sku}

                    </Text>

                </View>

            )}

            {/* ------------------------------------------------------------------ */}
            {/* Product Badges                                                    */}
            {/* ------------------------------------------------------------------ */}

            {!!productBadges.length && (

                <View
                    style={
                        styles.badgesContainer
                    }
                >

                    {productBadges.map(

                        (badge, index) => (

                            <View

                                key={
                                    `${badge}-${index}`
                                }

                                style={[

                                    styles.badge,

                                    {

                                        backgroundColor:
                                            colors.primaryContainer ??
                                            colors.surfaceVariant ??
                                            colors.surface,

                                    },

                                ]}

                            >

                                <Text
                                    style={[

                                        styles.badgeText,

                                        {

                                            color:
                                                colors.primary,

                                        },

                                    ]}
                                >

                                    {badge}

                                </Text>

                            </View>

                        )

                    )}

                </View>

            )}

        </View>

    );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ProductInfo.displayName =
    "ProductInfo";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductInfo.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Basic Information                                                      */
    /* ---------------------------------------------------------------------- */

    name:
        PropTypes.string,

    brand:
        PropTypes.string,

    sku:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Pricing                                                                */
    /* ---------------------------------------------------------------------- */

    price:
        PropTypes.oneOfType([

            PropTypes.number,

            PropTypes.string,

        ]),

    originalPrice:
        PropTypes.oneOfType([

            PropTypes.number,

            PropTypes.string,

        ]),

    discount:
        PropTypes.oneOfType([

            PropTypes.number,

            PropTypes.string,

        ]),

    currency:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Rating                                                                 */
    /* ---------------------------------------------------------------------- */

    rating:
        PropTypes.oneOfType([

            PropTypes.number,

            PropTypes.string,

        ]),

    reviewCount:
        PropTypes.number,

    /* ---------------------------------------------------------------------- */
    /* Availability                                                           */
    /* ---------------------------------------------------------------------- */

    inStock:
        PropTypes.bool,

    stockLabel:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Badges                                                                 */
    /* ---------------------------------------------------------------------- */

    badges:
        PropTypes.arrayOf(
            PropTypes.string
        ),

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

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

            paddingHorizontal:
                16,

            paddingVertical:
                16,

        },

        /* ------------------------------------------------------------------ */
        /* Title                                                              */
        /* ------------------------------------------------------------------ */

        title: {

            fontSize:
                22,

            fontWeight:
                "700",

            lineHeight:
                30,

        },

        /* ------------------------------------------------------------------ */
        /* Brand                                                              */
        /* ------------------------------------------------------------------ */

        brandContainer: {

            marginTop:
                8,

        },

        brandText: {

            fontSize:
                15,

            fontWeight:
                "600",

        },

        /* ------------------------------------------------------------------ */
        /* Rating                                                             */
        /* ------------------------------------------------------------------ */

        ratingContainer: {

            flexDirection:
                "row",

            alignItems:
                "center",

            marginTop:
                12,

        },

        ratingText: {

            fontSize:
                15,

            fontWeight:
                "600",

        },

        reviewText: {

            marginLeft:
                8,

            fontSize:
                14,

        },

        /* ------------------------------------------------------------------ */
        /* Pricing                                                            */
        /* ------------------------------------------------------------------ */

        priceSection: {

            gap:
                8,

        },

        priceRow: {

            flexDirection:
                "row",

            alignItems:
                "center",

            flexWrap:
                "wrap",

        },

        currentPrice: {

            fontSize:
                28,

            fontWeight:
                "700",

        },

        originalPrice: {

            marginLeft:
                12,

            fontSize:
                18,

            textDecorationLine:
                "line-through",

        },

        discountBadge: {

            marginLeft:
                12,

            paddingHorizontal:
                10,

            paddingVertical:
                4,

            borderRadius:
                8,

        },

        discountText: {

            fontSize:
                12,

            fontWeight:
                "700",

        },

        savingsText: {

            fontSize:
                14,

            fontWeight:
                "600",

        },

        /* ------------------------------------------------------------------ */
        /* Stock                                                              */
        /* ------------------------------------------------------------------ */

        stockContainer: {

            marginBottom:
                12,

        },

        stockText: {

            fontSize:
                15,

            fontWeight:
                "600",

        },

        /* ------------------------------------------------------------------ */
        /* SKU                                                                */
        /* ------------------------------------------------------------------ */

        skuContainer: {

            flexDirection:
                "row",

            alignItems:
                "center",

            marginBottom:
                16,

        },

        skuLabel: {

            fontSize:
                14,

            fontWeight:
                "600",

        },

        skuValue: {

            marginLeft:
                6,

            fontSize:
                14,

        },

        /* ------------------------------------------------------------------ */
        /* Badges                                                             */
        /* ------------------------------------------------------------------ */

        badgesContainer: {

            flexDirection:
                "row",

            flexWrap:
                "wrap",

            marginHorizontal:
                -4,

        },

        badge: {

            margin:
                4,

            paddingHorizontal:
                10,

            paddingVertical:
                6,

            borderRadius:
                16,

        },

        badgeText: {

            fontSize:
                12,

            fontWeight:
                "600",

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    ProductInfo;