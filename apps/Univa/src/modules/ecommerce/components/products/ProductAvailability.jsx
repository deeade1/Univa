/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/products/ProductAvailability.jsx */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useMemo,
} from "react";

import {
    Text,
    View,
    StyleSheet,
} from "react-native";

import PropTypes from "prop-types";

import Badge, {
    VARIANTS,
} from "../common/Badge";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Availability Status                                                        */
/* -------------------------------------------------------------------------- */

export const PRODUCT_STATUS = {

    IN_STOCK: "in_stock",

    LOW_STOCK: "low_stock",

    OUT_OF_STOCK: "out_of_stock",

    BACKORDER: "backorder",

    PREORDER: "preorder",

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductAvailability = memo(({

    quantity = 0,

    status,

    showQuantity = false,

    compact = false,

    badge = false,

    icon,

    style,

    textStyle,

}) => {

    const {

        colors,

    } = theme;

    /* ---------------------------------------------------------------------- */
    /* Determine Availability                                                 */
    /* ---------------------------------------------------------------------- */

    const availability = useMemo(() => {

        /* Explicit status overrides quantity */

        if (status === PRODUCT_STATUS.BACKORDER) {

            return {

                label: "Backorder",

                variant: VARIANTS.warning,

                color: colors.warning ?? "#F59E0B",

            };

        }

        if (status === PRODUCT_STATUS.PREORDER) {

            return {

                label: "Pre-order",

                variant: VARIANTS.info,

                color: colors.info ?? "#2563EB",

            };

        }

        if (quantity <= 0) {

            return {

                label: "Out of Stock",

                variant: VARIANTS.danger,

                color: colors.error,

            };

        }

        if (quantity <= 10) {

            return {

                label: "Low Stock",

                variant: VARIANTS.warning,

                color: colors.warning ?? "#F59E0B",

            };

        }

        return {

            label: "In Stock",

            variant: VARIANTS.success,

            color: colors.success ?? "#16A34A",

        };

    }, [

        colors,

        quantity,

        status,

    ]);

    /* ---------------------------------------------------------------------- */
    /* Display Text                                                           */
    /* ---------------------------------------------------------------------- */

    const displayText = useMemo(() => {

        if (

            showQuantity &&

            quantity > 0 &&

            availability.label !== "In Stock"

        ) {

            return `${availability.label} (${quantity} left)`;

        }

        return availability.label;

    }, [

        availability,

        quantity,

        showQuantity,

    ]);
        /* ---------------------------------------------------------------------- */
    /* Badge Mode                                                             */
    /* ---------------------------------------------------------------------- */

    if (badge) {

        return (

            <Badge

                label={displayText}

                variant={availability.variant}

                leftIcon={icon}

                rounded

                style={style}

                textStyle={textStyle}

            />

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (

        <View

            accessible

            accessibilityRole="text"

            accessibilityLabel={displayText}

            style={[

                styles.container,

                compact && styles.compactContainer,

                style,

            ]}

        >

            {/* -------------------------------------------------------------- */}
            {/* Optional Icon                                                 */}
            {/* -------------------------------------------------------------- */}

            {!!icon && (

                <View style={styles.iconContainer}>

                    {icon}

                </View>

            )}

            {/* -------------------------------------------------------------- */}
            {/* Availability Text                                             */}
            {/* -------------------------------------------------------------- */}

            <Text

                numberOfLines={1}

                style={[

                    styles.text,

                    {

                        color: availability.color,

                    },

                    compact && styles.compactText,

                    textStyle,

                ]}

            >

                {displayText}

            </Text>

        </View>

    );

});
/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({

    /* ---------------------------------------------------------------------- */
    /* Container                                                              */
    /* ---------------------------------------------------------------------- */

    container: {

        flexDirection: "row",

        alignItems: "center",

        alignSelf: "flex-start",

    },

    /* ---------------------------------------------------------------------- */
    /* Compact Container                                                      */
    /* ---------------------------------------------------------------------- */

    compactContainer: {

        minHeight: 18,

    },

    /* ---------------------------------------------------------------------- */
    /* Icon                                                                   */
    /* ---------------------------------------------------------------------- */

    iconContainer: {

        justifyContent: "center",

        alignItems: "center",

        marginRight: 6,

    },

    /* ---------------------------------------------------------------------- */
    /* Text                                                                   */
    /* ---------------------------------------------------------------------- */

    text: {

        fontSize: 13,

        fontWeight: "600",

        lineHeight: 18,

        includeFontPadding: false,

        flexShrink: 1,

    },

    /* ---------------------------------------------------------------------- */
    /* Compact Text                                                           */
    /* ---------------------------------------------------------------------- */

    compactText: {

        fontSize: 11,

        lineHeight: 14,

    },

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ProductAvailability.displayName = "ProductAvailability";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductAvailability.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Availability                                                           */
    /* ---------------------------------------------------------------------- */

    quantity: PropTypes.number,

    status: PropTypes.oneOf(

        Object.values(PRODUCT_STATUS)

    ),

    showQuantity: PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    compact: PropTypes.bool,

    badge: PropTypes.bool,

    icon: PropTypes.node,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style: PropTypes.oneOfType([

        PropTypes.object,

        PropTypes.array,

    ]),

    textStyle: PropTypes.oneOfType([

        PropTypes.object,

        PropTypes.array,

    ]),

};

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */


export default ProductAvailability;