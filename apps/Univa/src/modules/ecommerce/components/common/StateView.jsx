/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/StateView.jsx           */
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

const StateView = memo(({

    icon,

    iconSize = 72,

    iconColor,

    title,

    description,

    primaryLabel,

    secondaryLabel,

    onPrimaryPress,

    onSecondaryPress,

    primaryButton,

    secondaryButton,

    centered = true,

    children,

    footer,

    style,

}) => {

    const {
        colors,
        typography,
    } = theme;

    const resolvedIconColor =
        iconColor ??
        colors.primary;

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

                    color={resolvedIconColor}

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
                                22,

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
                                15,

                        },

                    ]}

                >

                    {description}

                </Text>

            )}

            {/* ---------------------------------------------------------- */}
            {/* Custom Content                                            */}
            {/* ---------------------------------------------------------- */}

            {children}

            {/* ---------------------------------------------------------- */}
            {/* Actions                                                   */}
            {/* ---------------------------------------------------------- */}

            {(primaryLabel ||
              secondaryLabel ||
              primaryButton ||
              secondaryButton) && (

                <View
                    style={
                        styles.actions
                    }
                >

                    {primaryButton ?? (

                        !!primaryLabel &&
                        !!onPrimaryPress && (

                            <Pressable

                                onPress={
                                    onPrimaryPress
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

                                    {primaryLabel}

                                </Text>

                            </Pressable>

                        )

                    )}

                    {secondaryButton ?? (

                        !!secondaryLabel &&
                        !!onSecondaryPress && (

                            <Pressable

                                onPress={
                                    onSecondaryPress
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

                        )

                    )}

                </View>

            )}

            {footer}

        </View>

    );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

StateView.displayName =
    "StateView";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

StateView.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Icon                                                                    */
    /* ---------------------------------------------------------------------- */

    icon:
        PropTypes.string,

    iconSize:
        PropTypes.number,

    iconColor:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Text                                                                    */
    /* ---------------------------------------------------------------------- */

    title:
        PropTypes.oneOfType([
            PropTypes.string,
            PropTypes.node,
        ]),

    description:
        PropTypes.oneOfType([
            PropTypes.string,
            PropTypes.node,
        ]),

    /* ---------------------------------------------------------------------- */
    /* Primary Action                                                          */
    /* ---------------------------------------------------------------------- */

    primaryLabel:
        PropTypes.string,

    onPrimaryPress:
        PropTypes.func,

    primaryButton:
        PropTypes.node,

    /* ---------------------------------------------------------------------- */
    /* Secondary Action                                                        */
    /* ---------------------------------------------------------------------- */

    secondaryLabel:
        PropTypes.string,

    onSecondaryPress:
        PropTypes.func,

    secondaryButton:
        PropTypes.node,

    /* ---------------------------------------------------------------------- */
    /* Layout                                                                  */
    /* ---------------------------------------------------------------------- */

    centered:
        PropTypes.bool,

    children:
        PropTypes.node,

    footer:
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

            paddingHorizontal:
                24,

            paddingVertical:
                32,

        },

        center: {

            flex: 1,

            justifyContent:
                "center",

            alignItems:
                "center",

        },

        title: {

            marginTop:
                20,

            textAlign:
                "center",

            fontWeight:
                "700",

        },

        description: {

            marginTop:
                12,

            textAlign:
                "center",

            lineHeight:
                22,

            maxWidth:
                360,

        },

        actions: {

            flexDirection:
                "row",

            flexWrap:
                "wrap",

            justifyContent:
                "center",

            alignItems:
                "center",

            marginTop:
                28,

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

            minWidth:
                120,

            alignItems:
                "center",

        },

        primaryText: {

            color:
                "#FFFFFF",

            fontWeight:
                "700",

            fontSize:
                15,

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

            minWidth:
                120,

            alignItems:
                "center",

        },

        secondaryText: {

            fontWeight:
                "600",

            fontSize:
                15,

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    StateView;