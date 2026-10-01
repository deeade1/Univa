/* -------------------------------------------------------------------------- */
/* apps/Univa/src/components/ui/Button.jsx                                    */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    forwardRef,
    useMemo,
    useCallback,
} from "react";

import {
    ActivityIndicator,
    Pressable,
    StyleSheet,
    Text,
    View,
    Platform,
} from "react-native";

import PropTypes from "prop-types";

// ✅ Support both plain theme and useTheme hook
import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

export const VARIANTS = {

    primary: "primary",

    secondary: "secondary",

    outline: "outline",

    ghost: "ghost",

    text: "text",

    danger: "danger",

    success: "success",

};

export const SIZES = {

    small: "small",

    medium: "medium",

    large: "large",

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const Button = memo(

    forwardRef(({

        /* ------------------------------------------------------------------ */
        /* Content                                                            */
        /* ------------------------------------------------------------------ */

        title,

        children,

        /* ------------------------------------------------------------------ */
        /* Behaviour                                                          */
        /* ------------------------------------------------------------------ */

        onPress,

        disabled = false,

        loading = false,

        /* ------------------------------------------------------------------ */
        /* Appearance                                                         */
        /* ------------------------------------------------------------------ */

        variant = VARIANTS.primary,

        size = SIZES.medium,

        fullWidth = false,

        rounded = false,

        /* ------------------------------------------------------------------ */
        /* Icons                                                              */
        /* ------------------------------------------------------------------ */

        leftIcon,

        rightIcon,

        /* ------------------------------------------------------------------ */
        /* Accessibility                                                      */
        /* ------------------------------------------------------------------ */

        accessibilityLabel,

        accessibilityHint,

        /* ------------------------------------------------------------------ */
        /* Styling                                                            */
        /* ------------------------------------------------------------------ */

        style,

        textStyle,

        contentStyle,

        /* ------------------------------------------------------------------ */
        /* Test ID                                                            */
        /* ------------------------------------------------------------------ */

        testID,

        ...rest

    }, ref) => {

        // ✅ Support both plain theme and useTheme pattern
        let colors;
        try {
            // If theme is a plain object with colors property
            if (theme && typeof theme === 'object' && theme.colors) {
                colors = theme.colors;
            } 
            // If theme is a hook result or has a different structure
            else if (theme && typeof theme === 'object' && theme.primary) {
                colors = theme;
            }
            // Fallback
            else {
                colors = {
                    primary: "#2563EB",
                    secondary: "#6B7280",
                    error: "#DC2626",
                    success: "#16A34A",
                    text: "#1F2937",
                    onSecondary: "#FFFFFF",
                    surfaceVariant: "#F5F5F5",
                    ripple: "rgba(255,255,255,0.18)",
                };
            }
        } catch (e) {
            // Fallback if theme is not available
            colors = {
                primary: "#2563EB",
                secondary: "#6B7280",
                error: "#DC2626",
                success: "#16A34A",
                text: "#1F2937",
                onSecondary: "#FFFFFF",
                surfaceVariant: "#F5F5F5",
                ripple: "rgba(255,255,255,0.18)",
            };
        }

        /* ------------------------------------------------------------------ */
        /* State                                                              */
        /* ------------------------------------------------------------------ */

        const isDisabled =
            disabled || loading;

        /* ------------------------------------------------------------------ */
        /* Size Configuration                                                 */
        /* ------------------------------------------------------------------ */

        const sizeStyle =
            useMemo(() => {

                switch (size) {

                    case SIZES.small:

                        return {

                            height: 36,

                            paddingHorizontal: 14,

                            fontSize: 13,

                        };

                    case SIZES.large:

                        return {

                            height: 54,

                            paddingHorizontal: 24,

                            fontSize: 17,

                        };

                    case SIZES.medium:

                    default:

                        return {

                            height: 46,

                            paddingHorizontal: 18,

                            fontSize: 15,

                        };

                }

            }, [size]);

        /* ------------------------------------------------------------------ */
        /* Variant Configuration                                              */
        /* ------------------------------------------------------------------ */

        const variantStyle =
            useMemo(() => {

                switch (variant) {

                    case VARIANTS.secondary:

                        return {

                            backgroundColor:
                                colors.secondary,

                            borderColor:
                                colors.secondary,

                            textColor:
                                colors.onSecondary ??
                                "#FFFFFF",

                        };

                    case VARIANTS.outline:

                        return {

                            backgroundColor:
                                "transparent",

                            borderColor:
                                colors.primary,

                            textColor:
                                colors.primary,

                        };

                    case VARIANTS.text:

                        return {

                            backgroundColor:
                                "transparent",

                            borderColor:
                                "transparent",

                            textColor:
                                colors.primary,

                        };

                    case VARIANTS.ghost:

                        return {

                            backgroundColor:
                                colors.surfaceVariant ??
                                "#F5F5F5",

                            borderColor:
                                "transparent",

                            textColor:
                                colors.text,

                        };

                    case VARIANTS.danger:

                        return {

                            backgroundColor:
                                colors.error,

                            borderColor:
                                colors.error,

                            textColor:
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

                    case VARIANTS.primary:

                    default:

                        return {

                            backgroundColor:
                                colors.primary,

                            borderColor:
                                colors.primary,

                            textColor:
                                "#FFFFFF",

                        };

                }

            }, [

                colors,

                variant,

            ]);

        /* ------------------------------------------------------------------ */
        /* Elevation                                                          */
        /* ------------------------------------------------------------------ */

        // ✅ Only elevated variants get shadows
        const hasElevation =
            useMemo(

                () =>

                    !["text", "ghost", "outline"].includes(

                        variant

                    ),

                [

                    variant,

                ]

            );

        /* ------------------------------------------------------------------ */
        /* Press Handler                                                      */
        /* ------------------------------------------------------------------ */

        const handlePress =
            useCallback(

                () => {

                    if (isDisabled) {

                        return;

                    }

                    onPress?.();

                },

                [

                    isDisabled,

                    onPress,

                ]

            );

        /* ------------------------------------------------------------------ */
        /* Render                                                             */
        /* ------------------------------------------------------------------ */

        return (

            <Pressable

                ref={ref}

                onPress={handlePress}

                disabled={isDisabled}

                accessibilityRole="button"

                accessibilityLabel={
                    accessibilityLabel ??
                    title
                }

                accessibilityHint={
                    accessibilityHint
                }

                accessibilityState={{

                    disabled: isDisabled,

                    busy: loading,

                }}

                android_ripple={{

                    color:
                        colors.ripple ??
                        "rgba(255,255,255,0.18)",

                    borderless: false,

                }}

                style={({ pressed }) => [

                    styles.button,

                    {

                        backgroundColor:
                            variantStyle.backgroundColor,

                        borderColor:
                            variantStyle.borderColor,

                        height:
                            sizeStyle.height,

                        paddingHorizontal:
                            sizeStyle.paddingHorizontal,

                        opacity:

                            isDisabled

                                ? 0.55

                                : pressed

                                ? 0.85

                                : 1,

                        borderRadius:

                            rounded

                                ? 999

                                : 12,

                        // ✅ Conditional elevation
                        ...(hasElevation && {

                            elevation: Platform.OS === 'android' ? 2 : 0,

                            shadowColor: "#000",

                            shadowOffset: {

                                width: 0,

                                height: 2,

                            },

                            shadowOpacity: 0.12,

                            shadowRadius: 4,

                        }),

                    },

                    fullWidth &&

                        styles.fullWidth,

                    style,

                ]}

                testID={testID}

                {...rest}

            >

                <View

                    style={[

                        styles.content,

                        contentStyle,

                    ]}

                >

                    {/* ------------------------------------------------------ */}
                    {/* Left Icon                                              */}
                    {/* ------------------------------------------------------ */}

                    {!!leftIcon && (

                        <View

                            style={styles.leftIcon}

                        >

                            {leftIcon}

                        </View>

                    )}

                    {/* ------------------------------------------------------ */}
                    {/* Loading                                                */}
                    {/* ------------------------------------------------------ */}

                    {loading ? (

                        <ActivityIndicator

                            size="small"

                            color={
                                variantStyle.textColor
                            }

                        />

                    ) : children ? (

                        children

                    ) : (

                        <Text

                            numberOfLines={1}

                            ellipsizeMode="tail"

                            style={[

                                styles.text,

                                {

                                    color:
                                        variantStyle.textColor,

                                    fontSize:
                                        sizeStyle.fontSize,

                                },

                                textStyle,

                            ]}

                        >

                            {title}

                        </Text>

                    )}

                    {/* ------------------------------------------------------ */}
                    {/* Right Icon                                             */}
                    {/* ------------------------------------------------------ */}

                    {!!rightIcon &&
                        !loading && (

                        <View

                            style={styles.rightIcon}

                        >

                            {rightIcon}

                        </View>

                    )}

                </View>

            </Pressable>

        );

    })

);

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({

    /* ---------------------------------------------------------------------- */
    /* Button                                                                 */
    /* ---------------------------------------------------------------------- */

    button: {

        flexDirection: "row",

        alignItems: "center",

        justifyContent: "center",

        borderWidth: 1,

        overflow: "hidden",

        minWidth: 64,

    },

    fullWidth: {

        width: "100%",

    },

    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    content: {

        flexDirection: "row",

        alignItems: "center",

        justifyContent: "center",

        flexShrink: 1,

        paddingHorizontal: 4,

        gap: 4,

    },

    /* ---------------------------------------------------------------------- */
    /* Text                                                                   */
    /* ---------------------------------------------------------------------- */

    text: {

        fontWeight: "600",

        textAlign: "center",

        includeFontPadding: false,

    },

    /* ---------------------------------------------------------------------- */
    /* Icons                                                                  */
    /* ---------------------------------------------------------------------- */

    leftIcon: {

        alignItems: "center",

        justifyContent: "center",

    },

    rightIcon: {

        alignItems: "center",

        justifyContent: "center",

    },

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

Button.displayName = "Button";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

Button.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    title: PropTypes.string,

    children: PropTypes.node,

    /* ---------------------------------------------------------------------- */
    /* Behaviour                                                              */
    /* ---------------------------------------------------------------------- */

    onPress: PropTypes.func,

    disabled: PropTypes.bool,

    loading: PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* Appearance                                                             */
    /* ---------------------------------------------------------------------- */

    variant: PropTypes.oneOf(

        Object.values(VARIANTS)

    ),

    size: PropTypes.oneOf(

        Object.values(SIZES)

    ),

    fullWidth: PropTypes.bool,

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

    accessibilityHint: PropTypes.string,

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

    contentStyle: PropTypes.oneOfType([

        PropTypes.object,

        PropTypes.array,

    ]),

    /* ---------------------------------------------------------------------- */
    /* Test ID                                                                */
    /* ---------------------------------------------------------------------- */

    testID: PropTypes.string,

};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

Button.defaultProps = {

    title: null,

    children: null,

    onPress: null,

    disabled: false,

    loading: false,

    variant: VARIANTS.primary,

    size: SIZES.medium,

    fullWidth: false,

    rounded: false,

    leftIcon: null,

    rightIcon: null,

    accessibilityLabel: null,

    accessibilityHint: null,

    style: null,

    textStyle: null,

    contentStyle: null,

    testID: null,

};

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default Button;