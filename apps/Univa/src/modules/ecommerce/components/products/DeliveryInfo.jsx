/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/DeliveryInfo.jsx       */
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

const DeliveryInfo = memo(({

    /* ---------------------------------------------------------------------- */
    /* Delivery                                                               */
    /* ---------------------------------------------------------------------- */

    estimatedDelivery,

    shippingFee = 0,

    currency = "₦",

    freeShipping = false,

    /* ---------------------------------------------------------------------- */
    /* Options                                                                */
    /* ---------------------------------------------------------------------- */

    expressDelivery = false,

    pickupAvailable = false,

    nationwideDelivery = true,

    cashOnDelivery = false,

    returnPolicy,

    /* ---------------------------------------------------------------------- */
    /* Visibility                                                             */
    /* ---------------------------------------------------------------------- */

    showShippingFee = true,

    showReturnPolicy = true,

    showOptions = true,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,

}) => {

    const {
        colors,
        spacing,
    } = theme;

    /* ---------------------------------------------------------------------- */
    /* Computed Values                                                        */
    /* ---------------------------------------------------------------------- */

    const shippingText =
        useMemo(

            () =>

                freeShipping

                    ? "Free Shipping"

                    : `${currency}${Number(
                        shippingFee
                    ).toLocaleString()}`,

            [

                freeShipping,

                shippingFee,

                currency,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Format Estimated Delivery                                              */
    /* ---------------------------------------------------------------------- */

    const formattedDelivery =
        useMemo(

            () => {

                if (!estimatedDelivery) {
                    return null;
                }

                // Handle Date objects
                if (estimatedDelivery instanceof Date) {
                    return estimatedDelivery.toLocaleDateString(
                        "en-US",
                        {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                        }
                    );
                }

                // Handle string
                return estimatedDelivery;

            },

            [estimatedDelivery]

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
            {/* Section Title                                                     */}
            {/* ------------------------------------------------------------------ */}

            <Text
                style={[

                    styles.title,

                    {

                        color:
                            colors.text,

                    },

                ]}
            >

                Delivery Information

            </Text>

            {/* ------------------------------------------------------------------ */}
            {/* Estimated Delivery                                                */}
            {/* ------------------------------------------------------------------ */}

            {!!formattedDelivery && (

                <IconLabel

                    icon="truck-delivery-outline"

                    label={`Estimated Delivery: ${formattedDelivery}`}

                    iconColor={
                        colors.primary
                    }

                    textStyle={[

                        styles.infoText,

                        {

                            color:
                                colors.text,

                        },

                    ]}

                    style={
                        styles.infoRow
                    }

                />

            )}

            {/* ------------------------------------------------------------------ */}
            {/* Shipping Fee                                                      */}
            {/* ------------------------------------------------------------------ */}

            {showShippingFee && (

                <IconLabel

                    icon={
                        freeShipping
                            ? "gift-outline"
                            : "cash-multiple"
                    }

                    label={`Shipping Fee: ${shippingText}`}

                    iconColor={
                        freeShipping
                            ? colors.success ?? "#16A34A"
                            : colors.primary
                    }

                    textStyle={[

                        styles.infoText,

                        {

                            color:
                                freeShipping
                                    ? colors.success ?? "#16A34A"
                                    : colors.text,

                        },

                    ]}

                    style={
                        styles.infoRow
                    }

                />

            )}

            <Divider
                spacing={theme.spacing.md}
            />

            {/* ------------------------------------------------------------------ */}
            {/* Delivery Features                                                 */}
            {/* ------------------------------------------------------------------ */}

            {showOptions && (

                <View
                    style={
                        styles.featuresContainer
                    }
                >

                    {expressDelivery && (

                        <IconLabel

                            icon="rocket-launch-outline"

                            label="Express Delivery Available"

                            iconColor={
                                colors.success ?? "#16A34A"
                            }

                            textStyle={[

                                styles.featureText,

                                {

                                    color:
                                        colors.text,

                                },

                            ]}

                            style={
                                styles.featureItem
                            }

                        />

                    )}

                    {pickupAvailable && (

                        <IconLabel

                            icon="store-outline"

                            label="Store Pickup Available"

                            iconColor={
                                colors.primary
                            }

                            textStyle={[

                                styles.featureText,

                                {

                                    color:
                                        colors.text,

                                },

                            ]}

                            style={
                                styles.featureItem
                            }

                        />

                    )}

                    {nationwideDelivery && (

                        <IconLabel

                            icon="map-marker-radius-outline"

                            label="Nationwide Delivery"

                            iconColor={
                                colors.primary
                            }

                            textStyle={[

                                styles.featureText,

                                {

                                    color:
                                        colors.text,

                                },

                            ]}

                            style={
                                styles.featureItem
                            }

                        />

                    )}

                    {cashOnDelivery && (

                        <IconLabel

                            icon="cash-check"

                            label="Cash on Delivery"

                            iconColor={
                                colors.success ?? "#16A34A"
                            }

                            textStyle={[

                                styles.featureText,

                                {

                                    color:
                                        colors.text,

                                },

                            ]}

                            style={
                                styles.featureItem
                            }

                        />

                    )}

                </View>

            )}

            {/* ------------------------------------------------------------------ */}
            {/* Return Policy                                                     */}
            {/* ------------------------------------------------------------------ */}

            {showReturnPolicy &&
                !!returnPolicy && (

                <>

                    <Divider
                        spacing={theme.spacing.md}
                    />

                    <View
                        style={
                            styles.returnPolicyContainer
                        }
                    >

                        <Text
                            style={[

                                styles.returnPolicyTitle,

                                {

                                    color:
                                        colors.text,

                                },

                            ]}
                        >

                            Return Policy

                        </Text>

                        <Text
                            style={[

                                styles.returnPolicyText,

                                {

                                    color:
                                        colors.textSecondary,

                                },

                            ]}
                        >

                            {returnPolicy}

                        </Text>

                    </View>

                </>

            )}

        </View>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

DeliveryInfo.displayName =
    "DeliveryInfo";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

DeliveryInfo.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Delivery                                                               */
    /* ---------------------------------------------------------------------- */

    estimatedDelivery:
        PropTypes.oneOfType([

            PropTypes.string,

            PropTypes.instanceOf(Date),

        ]),

    shippingFee:
        PropTypes.oneOfType([

            PropTypes.number,

            PropTypes.string,

        ]),

    currency:
        PropTypes.string,

    freeShipping:
        PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* Delivery Options                                                       */
    /* ---------------------------------------------------------------------- */

    expressDelivery:
        PropTypes.bool,

    pickupAvailable:
        PropTypes.bool,

    nationwideDelivery:
        PropTypes.bool,

    cashOnDelivery:
        PropTypes.bool,

    returnPolicy:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Visibility                                                             */
    /* ---------------------------------------------------------------------- */

    showShippingFee:
        PropTypes.bool,

    showReturnPolicy:
        PropTypes.bool,

    showOptions:
        PropTypes.bool,

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

        /* ------------------------------------------------------------------ */
        /* Container                                                          */
        /* ------------------------------------------------------------------ */

        container: {

            paddingHorizontal:
                theme.spacing.md,

            paddingVertical:
                theme.spacing.md,

        },

        /* ------------------------------------------------------------------ */
        /* Header                                                             */
        /* ------------------------------------------------------------------ */

        title: {

            fontSize:
                18,

            fontWeight:
                "700",

            marginBottom:
                theme.spacing.md,

        },

        /* ------------------------------------------------------------------ */
        /* Information Rows                                                   */
        /* ------------------------------------------------------------------ */

        infoRow: {

            marginBottom:
                theme.spacing.sm,

        },

        infoText: {

            fontSize:
                15,

            fontWeight:
                "500",

            lineHeight:
                22,

        },

        /* ------------------------------------------------------------------ */
        /* Delivery Features                                                  */
        /* ------------------------------------------------------------------ */

        featuresContainer: {

            marginTop:
                4,

        },

        featureItem: {

            marginBottom:
                theme.spacing.sm,

        },

        featureText: {

            fontSize:
                14,

            fontWeight:
                "500",

            lineHeight:
                20,

        },

        /* ------------------------------------------------------------------ */
        /* Return Policy                                                      */
        /* ------------------------------------------------------------------ */

        returnPolicyContainer: {

            marginTop:
                4,

        },

        returnPolicyTitle: {

            fontSize:
                16,

            fontWeight:
                "700",

            marginBottom:
                theme.spacing.sm,

        },

        returnPolicyText: {

            fontSize:
                14,

            lineHeight:
                22,

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    DeliveryInfo;