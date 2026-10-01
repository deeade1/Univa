/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/IconLabel.jsx           */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
} from "react";

import {
    Pressable,
    StyleSheet,
    Text,
    View,
} from "react-native";

import PropTypes
    from "prop-types";

import {
    MaterialCommunityIcons,
} from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const IconLabel = memo(({

    icon,

    label,

    iconPosition = "left",

    size = 16,

    color,

    textColor,

    vertical = false,

    badge = false,

    disabled = false,

    numberOfLines = 1,

    onPress,

    style,

    textStyle,

    iconStyle,

}) => {

    const {
        colors,
        typography,
    } = theme;

    const iconColor =
        color ??
        colors.textSecondary;

    const labelColor =
        textColor ??
        colors.text;

    const content = (

        <View
            style={[

                vertical
                    ? styles.column
                    : styles.row,

                badge && [

                    styles.badge,

                    {
                        backgroundColor:
                            colors.surface ??
                            colors.background,

                        borderColor:
                            colors.border,
                    },

                ],

            ]}
        >

            {/* ---------------------------------------------------------- */}
            {/* Left Icon                                                  */}
            {/* ---------------------------------------------------------- */}

            {icon &&
                iconPosition ===
                    "left" && (

                <MaterialCommunityIcons
                    name={icon}
                    size={size}
                    color={iconColor}
                    style={[
                        styles.leftIcon,
                        iconStyle,
                    ]}
                />

            )}

            {/* ---------------------------------------------------------- */}
            {/* Label                                                      */}
            {/* ---------------------------------------------------------- */}

            <Text
                numberOfLines={
                    numberOfLines
                }
                style={[

                    styles.label,

                    {

                        color:
                            labelColor,

                        fontSize:
                            typography
                                ?.bodyMedium
                                ?.fontSize ??
                            14,

                    },

                    textStyle,

                ]}
            >
                {label}
            </Text>

            {/* ---------------------------------------------------------- */}
            {/* Right Icon                                                 */}
            {/* ---------------------------------------------------------- */}

            {icon &&
                iconPosition ===
                    "right" && (

                <MaterialCommunityIcons
                    name={icon}
                    size={size}
                    color={iconColor}
                    style={[
                        styles.rightIcon,
                        iconStyle,
                    ]}
                />

            )}

        </View>

    );

    /* ---------------------------------------------------------------------- */
    /* Render                                                                  */
    /* ---------------------------------------------------------------------- */

    if (!onPress) {
        return content;
    }

    return (

        <Pressable

            disabled={
                disabled
            }

            onPress={
                onPress
            }

            style={({ pressed }) => [

                pressed &&
                    styles.pressed,

                style,

            ]}

        >

            {content}

        </Pressable>

    );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

IconLabel.displayName =
    "IconLabel";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

IconLabel.propTypes = {

    icon:
        PropTypes.string,

    label:
        PropTypes.oneOfType([
            PropTypes.string,
            PropTypes.number,
        ]).isRequired,

    iconPosition:
        PropTypes.oneOf([
            "left",
            "right",
        ]),

    size:
        PropTypes.number,

    color:
        PropTypes.string,

    textColor:
        PropTypes.string,

    vertical:
        PropTypes.bool,

    badge:
        PropTypes.bool,

    disabled:
        PropTypes.bool,

    numberOfLines:
        PropTypes.number,

    onPress:
        PropTypes.func,

    style:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

    textStyle:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

    iconStyle:
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
        /* Layout                                                             */
        /* ------------------------------------------------------------------ */

        row: {

            flexDirection:
                "row",

            alignItems:
                "center",

            alignSelf:
                "flex-start",

        },

        column: {

            flexDirection:
                "column",

            alignItems:
                "center",

            justifyContent:
                "center",

        },

        /* ------------------------------------------------------------------ */
        /* Label                                                              */
        /* ------------------------------------------------------------------ */

        label: {

            fontWeight:
                "500",

            includeFontPadding:
                false,

        },

        /* ------------------------------------------------------------------ */
        /* Icons                                                              */
        /* ------------------------------------------------------------------ */

        leftIcon: {

            marginRight:
                6,

        },

        rightIcon: {

            marginLeft:
                6,

        },

        /* ------------------------------------------------------------------ */
        /* Badge                                                              */
        /* ------------------------------------------------------------------ */

        badge: {

            paddingHorizontal:
                10,

            paddingVertical:
                6,

            borderRadius:
                999,

            borderWidth:
                StyleSheet.hairlineWidth,

        },

        /* ------------------------------------------------------------------ */
        /* Pressed                                                            */
        /* ------------------------------------------------------------------ */

        pressed: {

            opacity:
                0.65,

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    IconLabel;