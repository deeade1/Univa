/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/Divider.jsx             */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
} from "react";

import {
    StyleSheet,
    Text,
    View,
} from "react-native";

import PropTypes
    from "prop-types";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const Divider = memo(({

    vertical = false,

    dashed = false,

    inset = 0,

    thickness = StyleSheet.hairlineWidth,

    color,

    label,

    margin = 16,

    flex = 1,

    style,

    labelStyle,

}) => {

    const {
        colors,
    } = theme;

    const dividerColor =
        color ??
        colors.border;

    /* ---------------------------------------------------------------------- */
    /* Vertical Divider                                                       */
    /* ---------------------------------------------------------------------- */

    if (vertical) {

        return (

            <View
                style={[
                    styles.vertical,

                    {

                        width:
                            thickness,

                        backgroundColor:
                            dividerColor,

                        marginHorizontal:
                            margin,

                    },

                    dashed && {

                        borderStyle:
                            "dashed",

                        borderLeftWidth:
                            thickness,

                        borderLeftColor:
                            dividerColor,

                        backgroundColor:
                            "transparent",

                        width: 0,

                    },

                    style,

                ]}
            />

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Horizontal Divider                                                     */
    /* ---------------------------------------------------------------------- */

    if (!label) {

        return (

            <View
                style={[
                    styles.horizontal,

                    {

                        marginVertical:
                            margin,

                        marginLeft:
                            inset,

                        height:
                            thickness,

                        backgroundColor:
                            dividerColor,

                    },

                    dashed && {

                        borderStyle:
                            "dashed",

                        borderTopWidth:
                            thickness,

                        borderTopColor:
                            dividerColor,

                        backgroundColor:
                            "transparent",

                        height: 0,

                    },

                    style,

                ]}
            />

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Label Divider                                                          */
    /* ---------------------------------------------------------------------- */

    return (

        <View
            style={[
                styles.labelContainer,
                {
                    marginVertical:
                        margin,
                },
                style,
            ]}
        >

            <View
                style={[
                    styles.line,

                    {

                        flex,

                        marginLeft:
                            inset,

                        height:
                            thickness,

                        backgroundColor:
                            dashed
                                ? "transparent"
                                : dividerColor,

                        borderTopWidth:
                            dashed
                                ? thickness
                                : 0,

                        borderStyle:
                            dashed
                                ? "dashed"
                                : "solid",

                        borderTopColor:
                            dividerColor,

                    },

                ]}
            />

            <Text
                style={[

                    styles.label,

                    {

                        color:
                            colors.textSecondary,

                    },

                    labelStyle,

                ]}
            >
                {label}
            </Text>

            <View
                style={[
                    styles.line,

                    {

                        flex,

                        height:
                            thickness,

                        backgroundColor:
                            dashed
                                ? "transparent"
                                : dividerColor,

                        borderTopWidth:
                            dashed
                                ? thickness
                                : 0,

                        borderTopColor:
                            dividerColor,

                        borderStyle:
                            dashed
                                ? "dashed"
                                : "solid",

                    },

                ]}
            />

        </View>

    );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

Divider.displayName =
    "Divider";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

Divider.propTypes = {

    vertical:
        PropTypes.bool,

    dashed:
        PropTypes.bool,

    inset:
        PropTypes.number,

    thickness:
        PropTypes.number,

    color:
        PropTypes.string,

    label:
        PropTypes.string,

    margin:
        PropTypes.number,

    flex:
        PropTypes.number,

    style:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

    labelStyle:
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
        /* Horizontal Divider                                                 */
        /* ------------------------------------------------------------------ */

        horizontal: {

            width:
                "100%",

            flexShrink:
                1,

        },

        /* ------------------------------------------------------------------ */
        /* Vertical Divider                                                   */
        /* ------------------------------------------------------------------ */

        vertical: {

            alignSelf:
                "stretch",

            minHeight:
                16,

        },

        /* ------------------------------------------------------------------ */
        /* Label Divider                                                      */
        /* ------------------------------------------------------------------ */

        labelContainer: {

            flexDirection:
                "row",

            alignItems:
                "center",

            width:
                "100%",

        },

        line: {

            flex:
                1,

        },

        label: {

            marginHorizontal:
                12,

            fontSize:
                13,

            fontWeight:
                "600",

            textAlign:
                "center",

            includeFontPadding:
                false,

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    Divider;