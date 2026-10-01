/* -------------------------------------------------------------------------- */
/* apps/Univa/src/components/ui/Badge.jsx                                     */
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

import PropTypes from "prop-types";

// ✅ Support both plain theme and useTheme pattern
import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

export const VARIANTS = {

    primary: "primary",

    secondary: "secondary",

    success: "success",

    warning: "warning",

    danger: "danger",

    info: "info",

    outline: "outline",

    neutral: "neutral",

};

export const SIZES = {

    small: "small",

    medium: "medium",

    large: "large",

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const Badge = memo(({

    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    label,

    children,

    /* ---------------------------------------------------------------------- */
    /* Appearance                                                             */
    /* ---------------------------------------------------------------------- */

    variant = VARIANTS.primary,

    size = SIZES.medium,

    rounded = false,

    /* ---------------------------------------------------------------------- */
    /* Icons                                                                  */
    /* ---------------------------------------------------------------------- */

    leftIcon,

    rightIcon,

    /* ---------------------------------------------------------------------- */
    /* Accessibility                                                          */
    /* ---------------------------------------------------------------------- */

    accessibilityLabel,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,

    textStyle,

}) => {

    // ✅ Support both plain theme and useTheme pattern
    let colors;
    try {
        if (theme && typeof theme === 'object' && theme.colors) {
            colors = theme.colors;
        } else if (theme && typeof theme === 'object' && theme.primary) {
            colors = theme;
        } else {
            // Fallback colors
            colors = {
                primary: "#2563EB",
                secondary: "#6B7280",
                success: "#16A34A",
                warning: "#F59E0B",
                error: "#DC2626",
                info: "#0EA5E9",
                text: "#1F2937",
                surfaceVariant: "#F3F4F6",
                onSecondary: "#FFFFFF",
            };
        }
    } catch (e) {
        colors = {
            primary: "#2563EB",
            secondary: "#6B7280",
            success: "#16A34A",
            warning: "#F59E0B",
            error: "#DC2626",
            info: "#0EA5E9",
            text: "#1F2937",
            surfaceVariant: "#F3F4F6",
            onSecondary: "#FFFFFF",
        };
    }

    /* ---------------------------------------------------------------------- */
    /* Size Configuration                                                     */
    /* ---------------------------------------------------------------------- */

    const sizeStyle =
        useMemo(() => {

            switch (size) {

                case SIZES.small:

                    return {

                        paddingHorizontal: 8,

                        paddingVertical: 3,

                        fontSize: 11,

                        minHeight: 20,

                    };

                case SIZES.large:

                    return {

                        paddingHorizontal: 14,

                        paddingVertical: 7,

                        fontSize: 15,

                        minHeight: 32,

                    };

                case SIZES.medium:

                default:

                    return {

                        paddingHorizontal: 10,

                        paddingVertical: 5,

                        fontSize: 13,

                        minHeight: 26,

                    };

            }

        }, [size]);

    /* ---------------------------------------------------------------------- */
    /* Variant Configuration                                                  */
    /* ---------------------------------------------------------------------- */

    const variantStyle =
        useMemo(() => {

            switch (variant) {

                case VARIANTS.secondary:

                    return {

                        backgroundColor:
                            colors.secondary ??
                            "#6B7280",

                        borderColor:
                            colors.secondary ??
                            "#6B7280",

                        textColor:
                            colors.onSecondary ??
                            "#FFFFFF",

                    };

                case VARIANTS.success:

                    return {

                        backgroundColor:
                            colors.success ??
                            "#16A34A",

                        borderColor:
                            colors.success ??
                            "#16A34A",

                        textColor:
                            "#FFFFFF",

                    };

                case VARIANTS.warning:

                    return {

                        backgroundColor:
                            colors.warning ??
                            "#F59E0B",

                        borderColor:
                            colors.warning ??
                            "#F59E0B",

                        textColor:
                            "#FFFFFF",

                    };

                case VARIANTS.danger:

                    return {

                        backgroundColor:
                            colors.error ??
                            "#DC2626",

                        borderColor:
                            colors.error ??
                            "#DC2626",

                        textColor:
                            "#FFFFFF",

                    };

                case VARIANTS.info:

                    return {

                        backgroundColor:
                            colors.info ??
                            "#0EA5E9",

                        borderColor:
                            colors.info ??
                            "#0EA5E9",

                        textColor:
                            "#FFFFFF",

                    };

                case VARIANTS.outline:

                    return {

                        backgroundColor:
                            "transparent",

                        borderColor:
                            colors.primary ??
                            "#2563EB",

                        textColor:
                            colors.primary ??
                            "#2563EB",

                    };

                case VARIANTS.neutral:

                    return {

                        backgroundColor:
                            colors.surfaceVariant ??
                            "#F3F4F6",

                        borderColor:
                            "transparent",

                        textColor:
                            colors.text ??
                            "#1F2937",

                    };

                case VARIANTS.primary:

                default:

                    return {

                        backgroundColor:
                            colors.primary ??
                            "#2563EB",

                        borderColor:
                            colors.primary ??
                            "#2563EB",

                        textColor:
                            "#FFFFFF",

                    };

            }

        }, [

            colors,

            variant,

        ]);

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    const content =
        children || label;

    if (!content) {

        return null;

    }

    return (

        <View

            accessible

            accessibilityRole="text"

            accessibilityLabel={
                accessibilityLabel ||
                (typeof label === "string"
                    ? label
                    : undefined)
            }

            style={[

                styles.container,

                {

                    backgroundColor:
                        variantStyle.backgroundColor,

                    borderColor:
                        variantStyle.borderColor,

                    paddingHorizontal:
                        sizeStyle.paddingHorizontal,

                    paddingVertical:
                        sizeStyle.paddingVertical,

                    minHeight:
                        sizeStyle.minHeight,

                    borderRadius:

                        rounded

                            ? 999

                            : 8, // TODO: Use theme.radius.sm

                },

                style,

            ]}

        >

            {/* -------------------------------------------------------------- */}
            {/* Left Icon                                                     */}
            {/* -------------------------------------------------------------- */}

            {!!leftIcon && (

                <View

                    style={styles.leftIcon}

                    accessible={false}

                >

                    {leftIcon}

                </View>

            )}

            {/* -------------------------------------------------------------- */}
            {/* Content                                                       */}
            {/* -------------------------------------------------------------- */}

            {typeof content === "string" ? (

                <Text

                    numberOfLines={1}

                    ellipsizeMode="tail"

                    style={[

                        styles.label,

                        {

                            color:
                                variantStyle.textColor,

                            fontSize:
                                sizeStyle.fontSize,

                            fontWeight: "600",

                            textAlign: "center",

                            includeFontPadding: false,

                            flexShrink: 1,

                        },

                        textStyle,

                    ]}

                >

                    {content}

                </Text>

            ) : (

                content

            )}

            {/* -------------------------------------------------------------- */}
            {/* Right Icon                                                    */}
            {/* -------------------------------------------------------------- */}

            {!!rightIcon && (

                <View

                    style={styles.rightIcon}

                    accessible={false}

                >

                    {rightIcon}

                </View>

            )}

        </View>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

Badge.displayName = "Badge";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({

    /* ---------------------------------------------------------------------- */
    /* Badge Container                                                        */
    /* ---------------------------------------------------------------------- */

    container: {

        flexDirection: "row",

        alignItems: "center",

        justifyContent: "center",

        alignSelf: "flex-start",

        borderWidth: 1,

        maxWidth: "100%",

        overflow: "hidden",

    },

    /* ---------------------------------------------------------------------- */
    /* Label                                                                  */
    /* ---------------------------------------------------------------------- */

    label: {

        // Styles applied inline

    },

    /* ---------------------------------------------------------------------- */
    /* Left Icon                                                              */
    /* ---------------------------------------------------------------------- */

    leftIcon: {

        justifyContent: "center",

        alignItems: "center",

        marginRight: 6,

    },

    /* ---------------------------------------------------------------------- */
    /* Right Icon                                                             */
    /* ---------------------------------------------------------------------- */

    rightIcon: {

        justifyContent: "center",

        alignItems: "center",

        marginLeft: 6,

    },

});

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

Badge.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    label: PropTypes.oneOfType([

        PropTypes.string,

        PropTypes.number,

    ]),

    children: PropTypes.node,

    /* ---------------------------------------------------------------------- */
    /* Appearance                                                             */
    /* ---------------------------------------------------------------------- */

    variant: PropTypes.oneOf(

        Object.values(VARIANTS)

    ),

    size: PropTypes.oneOf(

        Object.values(SIZES)

    ),

    rounded: PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* Icons                                                                  */
    /* ---------------------------------------------------------------------- */

    leftIcon: PropTypes.node,

    rightIcon: PropTypes.node,

    /* ---------------------------------------------------------------------- */
    /* Accessibility                                                          */
    /* ---------------------------------------------------------------------- */

    accessibilityLabel: PropTypes.string,

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
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

Badge.defaultProps = {

    label: null,

    children: null,

    variant: VARIANTS.primary,

    size: SIZES.medium,

    rounded: false,

    leftIcon: null,

    rightIcon: null,

    accessibilityLabel: null,

    style: null,

    textStyle: null,

};

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default Badge;

