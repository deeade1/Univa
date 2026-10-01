/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ErrorState.jsx          */
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

const ErrorState = memo(({

    icon = "alert-circle-outline",

    title = "Something went wrong",

    description =
        "An unexpected error occurred. Please try again.",

    retryLabel = "Try Again",

    onRetry,

    secondaryLabel,

    onSecondaryAction,

    iconSize = 72,

    iconColor,

    centered = true,

    showRetry = true,

    children,

    style,

}) => {

    const {
        colors,
        typography,
    } = theme;

    const resolvedIconColor =
        iconColor ??
        colors.error;

    return (

        <View
            style={[

                styles.container,

                centered &&
                    styles.center,

                style,

            ]}
        >

            {/* ---------------------------------------------------------- */}
            {/* Icon                                                      */}
            {/* ---------------------------------------------------------- */}

            {!!icon && (

                <MaterialCommunityIcons
                    name={icon}
                    size={iconSize}
                    color={
                        resolvedIconColor
                    }
                />

            )}

            {/* ---------------------------------------------------------- */}
            {/* Title                                                     */}
            {/* ---------------------------------------------------------- */}

            {!!title && (

                <Text
                    style={[

                        styles.title,

                        {

                            color:
                                colors.text,

                            fontSize:
                                typography
                                    ?.titleMedium
                                    ?.fontSize ??
                                20,

                        },

                    ]}
                >
                    {title}
                </Text>

            )}

            {/* ---------------------------------------------------------- */}
            {/* Description                                               */}
            {/* ---------------------------------------------------------- */}

            {!!description && (

                <Text
                    style={[

                        styles.description,

                        {

                            color:
                                colors.textSecondary,

                            fontSize:
                                typography
                                    ?.bodyMedium
                                    ?.fontSize ??
                                14,

                        },

                    ]}
                >
                    {description}
                </Text>

            )}

            {/* ---------------------------------------------------------- */}
            {/* Actions                                                   */}
            {/* ---------------------------------------------------------- */}

            <View
                style={
                    styles.actions
                }
            >

                {showRetry &&
                    !!onRetry && (

                    <Pressable
                        onPress={
                            onRetry
                        }
                        style={[

                            styles.primaryButton,

                            {
                                backgroundColor:
                                    colors.primary,
                            },

                        ]}
                    >

                        <Text
                            style={
                                styles.primaryText
                            }
                        >
                            {retryLabel}
                        </Text>

                    </Pressable>

                )}

                {!!secondaryLabel &&
                    !!onSecondaryAction && (

                    <Pressable
                        onPress={
                            onSecondaryAction
                        }
                        style={[

                            styles.secondaryButton,

                            {
                                borderColor:
                                    colors.border,
                            },

                        ]}
                    >

                        <Text
                            style={[
                                styles.secondaryText,

                                {
                                    color:
                                        colors.text,
                                },

                            ]}
                        >
                            {secondaryLabel}
                        </Text>

                    </Pressable>

                )}

            </View>

            {children}

        </View>

    );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ErrorState.displayName =
    "ErrorState";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ErrorState.propTypes = {

    icon:
        PropTypes.string,

    title:
        PropTypes.string,

    description:
        PropTypes.string,

    retryLabel:
        PropTypes.string,

    onRetry:
        PropTypes.func,

    secondaryLabel:
        PropTypes.string,

    onSecondaryAction:
        PropTypes.func,

    iconSize:
        PropTypes.number,

    iconColor:
        PropTypes.string,

    centered:
        PropTypes.bool,

    showRetry:
        PropTypes.bool,

    children:
        PropTypes.node,

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

        padding: 24,

    },

    center: {

        flex: 1,

        justifyContent:
            "center",

        alignItems:
            "center",

    },

    title: {

        marginTop: 20,

        fontWeight:
            "700",

        textAlign:
            "center",

    },

    description: {

        marginTop: 10,

        maxWidth: 340,

        textAlign:
            "center",

        lineHeight: 22,

    },

    actions: {

        flexDirection:
            "row",

        alignItems:
            "center",

        justifyContent:
            "center",

        flexWrap:
            "wrap",

        marginTop: 24,

    },

    primaryButton: {

        paddingHorizontal:
            20,

        paddingVertical:
            12,

        borderRadius:
            10,

        marginHorizontal:
            6,

        marginBottom:
            8,

    },

    primaryText: {

        color:
            "#FFFFFF",

        fontWeight:
            "700",

    },

    secondaryButton: {

        paddingHorizontal:
            20,

        paddingVertical:
            12,

        borderRadius:
            10,

        borderWidth:
            StyleSheet.hairlineWidth,

        marginHorizontal:
            6,

        marginBottom:
            8,

    },

    secondaryText: {

        fontWeight:
            "600",

    },

});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    ErrorState;