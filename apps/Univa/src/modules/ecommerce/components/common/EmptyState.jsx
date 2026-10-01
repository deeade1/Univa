/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/EmptyState.jsx          */
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

const EmptyState = memo(({

    icon = "package-variant",

    title = "Nothing here",

    description =

        "There is nothing to display at the moment.",

    actionLabel,

    onAction,

    iconSize = 72,

    iconColor,

    centered = true,

    children,

    style,

}) => {

    const {
        colors,
        typography,
    } = theme;

    const resolvedIconColor =
        iconColor ??
        colors.textSecondary;

    return (

        <View
            style={[

                styles.container,

                centered &&
                    styles.center,

                style,

            ]}
        >

            {!!icon && (

                <MaterialCommunityIcons
                    name={icon}
                    size={iconSize}
                    color={
                        resolvedIconColor
                    }
                />

            )}

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

            {!!actionLabel &&
                !!onAction && (

                <Pressable
                    onPress={
                        onAction
                    }
                    style={[

                        styles.button,

                        {
                            backgroundColor:
                                colors.primary,
                        },

                    ]}
                >

                    <Text
                        style={
                            styles.buttonText
                        }
                    >
                        {actionLabel}
                    </Text>

                </Pressable>

            )}

            {children}

        </View>

    );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

EmptyState.displayName =
    "EmptyState";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

EmptyState.propTypes = {

    icon:
        PropTypes.string,

    title:
        PropTypes.string,

    description:
        PropTypes.string,

    actionLabel:
        PropTypes.string,

    onAction:
        PropTypes.func,

    iconSize:
        PropTypes.number,

    iconColor:
        PropTypes.string,

    centered:
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

        textAlign:
            "center",

        lineHeight: 22,

        maxWidth: 320,

    },

    button: {

        marginTop: 24,

        paddingHorizontal: 20,

        paddingVertical: 12,

        borderRadius: 10,

    },

    buttonText: {

        color: "#FFFFFF",

        fontWeight: "700",

    },

});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    EmptyState;