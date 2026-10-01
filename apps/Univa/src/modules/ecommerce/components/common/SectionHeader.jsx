/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/SectionHeader.jsx        */
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

const SectionHeader = memo(({

    title,

    subtitle,

    icon,

    iconSize = 20,

    actionLabel,

    actionIcon =

        "chevron-right",

    onPress,

    badge,

    count,

    notification = false,

    disabled = false,

    style,

    titleStyle,

    subtitleStyle,

    actionStyle,

}) => {

    const {
        colors,
        typography,
    } = theme;

    const hasAction =

        Boolean(
            actionLabel ||
            onPress
        );

    return (

        <View
            style={[
                styles.container,
                style,
            ]}
        >

            {/* ---------------------------------------------------------- */}
            {/* Left Section                                               */}
            {/* ---------------------------------------------------------- */}

            <View
                style={
                    styles.left
                }
            >

                {!!icon && (

                    <MaterialCommunityIcons
                        name={icon}
                        size={
                            iconSize
                        }
                        color={
                            colors.primary
                        }
                        style={
                            styles.icon
                        }
                    />

                )}

                <View
                    style={
                        styles.textContainer
                    }
                >

                    {/* ---------------------------------------------- */}
                    {/* Title Row                                      */}
                    {/* ---------------------------------------------- */}

                    <View
                        style={
                            styles.titleRow
                        }
                    >

                        <Text
                            numberOfLines={1}
                            style={[
                                styles.title,
                                {
                                    color:
                                        colors.text,

                                    fontSize:
                                        typography?.titleMedium
                                            ?.fontSize ??
                                        18,
                                },
                                titleStyle,
                            ]}
                        >
                            {title}
                        </Text>

                        {!!count && (

                            <View
                                style={[
                                    styles.countBadge,
                                    {
                                        backgroundColor:
                                            colors.primary +
                                            "15",
                                    },
                                ]}
                            >

                                <Text
                                    style={[
                                        styles.countText,
                                        {
                                            color:
                                                colors.primary,
                                        },
                                    ]}
                                >
                                    {count}
                                </Text>

                            </View>

                        )}

                        {!!badge && (

                            <View
                                style={[
                                    styles.badge,
                                    {
                                        backgroundColor:
                                            colors.error,
                                    },
                                ]}
                            >

                                <Text
                                    style={
                                        styles.badgeText
                                    }
                                >
                                    {badge}
                                </Text>

                            </View>

                        )}

                        {notification && (

                            <View
                                style={[
                                    styles.dot,
                                    {
                                        backgroundColor:
                                            colors.error,
                                    },
                                ]}
                            />

                        )}

                    </View>

                    {!!subtitle && (

                        <Text
                            numberOfLines={2}
                            style={[
                                styles.subtitle,
                                {
                                    color:
                                        colors.textSecondary,
                                },
                                subtitleStyle,
                            ]}
                        >
                            {subtitle}
                        </Text>

                    )}

                </View>

            </View>

            {/* ---------------------------------------------------------- */}
            {/* Right Action                                               */}
            {/* ---------------------------------------------------------- */}

            {hasAction && (

                <Pressable

                    disabled={
                        disabled
                    }

                    onPress={
                        onPress
                    }

                    style={({ pressed }) => [

                        styles.action,

                        pressed &&

                            styles.pressed,

                        actionStyle,

                    ]}

                >

                    {!!actionLabel && (

                        <Text
                            style={[
                                styles.actionText,
                                {
                                    color:
                                        colors.primary,
                                },
                            ]}
                        >
                            {actionLabel}
                        </Text>

                    )}

                    <MaterialCommunityIcons
                        name={
                            actionIcon
                        }
                        size={18}
                        color={
                            colors.primary
                        }
                    />

                </Pressable>

            )}

        </View>

    );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

SectionHeader.displayName =
    "SectionHeader";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SectionHeader.propTypes = {

    title:
        PropTypes.string
            .isRequired,

    subtitle:
        PropTypes.string,

    icon:
        PropTypes.string,

    iconSize:
        PropTypes.number,

    actionLabel:
        PropTypes.string,

    actionIcon:
        PropTypes.string,

    onPress:
        PropTypes.func,

    badge:
        PropTypes.oneOfType([
            PropTypes.string,
            PropTypes.number,
        ]),

    count:
        PropTypes.oneOfType([
            PropTypes.string,
            PropTypes.number,
        ]),

    notification:
        PropTypes.bool,

    disabled:
        PropTypes.bool,

    style:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

    titleStyle:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

    subtitleStyle:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

    actionStyle:
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

            flexDirection:
                "row",

            alignItems:
                "center",

            justifyContent:
                "space-between",

            paddingVertical:
                12,

        },

        left: {

            flex: 1,

            flexDirection:
                "row",

            alignItems:
                "flex-start",

            marginRight:
                12,

        },

        icon: {

            marginRight:
                10,

            marginTop:
                2,

        },

        textContainer: {

            flex: 1,

        },

        titleRow: {

            flexDirection:
                "row",

            alignItems:
                "center",

            flexWrap:
                "wrap",

        },

        title: {

            fontWeight:
                "700",

        },

        subtitle: {

            marginTop:
                4,

            fontSize:
                13,

            lineHeight:
                18,

        },

        /* -------------------------------------------------------------- */
        /* Count Badge                                                    */
        /* -------------------------------------------------------------- */

        countBadge: {

            marginLeft:
                8,

            paddingHorizontal:
                8,

            paddingVertical:
                2,

            borderRadius:
                999,

            alignItems:
                "center",

            justifyContent:
                "center",

        },

        countText: {

            fontSize:
                11,

            fontWeight:
                "700",

        },

        /* -------------------------------------------------------------- */
        /* Badge                                                         */
        /* -------------------------------------------------------------- */

        badge: {

            marginLeft:
                8,

            paddingHorizontal:
                8,

            paddingVertical:
                2,

            borderRadius:
                999,

        },

        badgeText: {

            color:
                "#FFFFFF",

            fontSize:
                10,

            fontWeight:
                "700",

            textTransform:
                "uppercase",

        },

        /* -------------------------------------------------------------- */
        /* Notification Dot                                              */
        /* -------------------------------------------------------------- */

        dot: {

            width:
                8,

            height:
                8,

            borderRadius:
                4,

            marginLeft:
                8,

            alignSelf:
                "center",

        },

        /* -------------------------------------------------------------- */
        /* Action                                                        */
        /* -------------------------------------------------------------- */

        action: {

            flexDirection:
                "row",

            alignItems:
                "center",

        },

        actionText: {

            fontSize:
                14,

            fontWeight:
                "600",

            marginRight:
                4,

        },

        pressed: {

            opacity:
                0.65,

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    SectionHeader;