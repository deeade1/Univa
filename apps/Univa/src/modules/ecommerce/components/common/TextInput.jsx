/* -------------------------------------------------------------------------- */
/* apps/Univa/src/components/ui/TextInput.jsx                                 */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    forwardRef,
    useCallback,
    useState,
    useMemo,
} from "react";

import {
    Pressable,
    StyleSheet,
    Text,
    TextInput as RNTextInput,
    View,
    Platform,
} from "react-native";

import PropTypes from "prop-types";

import theme from "@/theme";

// Optional: Import icons if available
// import { Ionicons } from '@expo/vector-icons';

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const KEYBOARD_TYPES = [
    "default",
    "email-address",
    "numeric",
    "phone-pad",
    "number-pad",
    "decimal-pad",
    "url",
    "ascii-capable",
    "numbers-and-punctuation",
    "twitter",
    "web-search",
    "visible-password",
];

const RETURN_KEY_TYPES = [
    "done",
    "go",
    "next",
    "search",
    "send",
    "default",
    "emergency-call",
    "join",
    "route",
    "yahoo",
    "google",
    "continue",
    "previous",
];

const AUTO_CAPITALIZE_TYPES = [
    "none",
    "sentences",
    "words",
    "characters",
];

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const TextInput = memo(

    forwardRef(({

        /* ------------------------------------------------------------------ */
        /* Content                                                            */
        /* ------------------------------------------------------------------ */

        label,

        placeholder,

        value,

        helperText,

        error,

        /* ------------------------------------------------------------------ */
        /* Behaviour                                                          */
        /* ------------------------------------------------------------------ */

        onChangeText,

        onBlur,

        onFocus,

        onSubmitEditing,

        onEndEditing,

        editable = true,

        required = false,

        multiline = false,

        secureTextEntry = false,

        autoCapitalize = "none",

        autoCorrect = false,

        autoComplete = "off",

        textContentType = "none",

        autoFocus = false,

        blurOnSubmit = false,

        selectTextOnFocus = false,

        keyboardType = "default",

        returnKeyType = "done",

        maxLength,

        numberOfLines,

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

        inputStyle,

        labelStyle,

        /* ------------------------------------------------------------------ */
        /* Test ID                                                            */
        /* ------------------------------------------------------------------ */

        testID,

        ...rest

    }, ref) => {

        // ✅ Support both plain theme and useTheme pattern
        let colors;
        try {
            if (theme && typeof theme === 'object' && theme.colors) {
                colors = theme.colors;
            } else if (theme && typeof theme === 'object' && theme.primary) {
                colors = theme;
            } else {
                colors = {
                    primary: "#2563EB",
                    error: "#DC2626",
                    text: "#1F2937",
                    textSecondary: "#6B7280",
                    border: "#E5E7EB",
                    surface: "#FFFFFF",
                    disabled: "#F3F4F6",
                    placeholder: "#9CA3AF",
                };
            }
        } catch (e) {
            colors = {
                primary: "#2563EB",
                error: "#DC2626",
                text: "#1F2937",
                textSecondary: "#6B7280",
                border: "#E5E7EB",
                surface: "#FFFFFF",
                disabled: "#F3F4F6",
                placeholder: "#9CA3AF",
            };
        }

        /* ------------------------------------------------------------------ */
        /* State                                                              */
        /* ------------------------------------------------------------------ */

        const [focused, setFocused] = useState(false);
        const [passwordVisible, setPasswordVisible] = useState(false);

        /* ------------------------------------------------------------------ */
        /* Derived State                                                      */
        /* ------------------------------------------------------------------ */

        const hasError = Boolean(error);
        const isPassword = secureTextEntry;
        const shouldHidePassword = isPassword && !passwordVisible;
        const hasValue = Boolean(value && value.length > 0);

        /* ------------------------------------------------------------------ */
        /* Handlers                                                           */
        /* ------------------------------------------------------------------ */

        const handleFocus =
            useCallback(

                (event) => {
                    setFocused(true);
                    onFocus?.(event);
                },

                [onFocus]

            );

        const handleBlur =
            useCallback(

                (event) => {
                    setFocused(false);
                    onBlur?.(event);
                },

                [onBlur]

            );

        const togglePasswordVisibility =
            useCallback(

                () => {
                    setPasswordVisible(
                        (visible) => !visible
                    );
                },

                []

            );

        /* ------------------------------------------------------------------ */
        /* Render Helper: Character Counter                                   */
        /* ------------------------------------------------------------------ */

        const renderCounter =
            useCallback(

                () => {

                    if (typeof maxLength !== "number") {

                        return null;

                    }

                    const currentLength =
                        value?.length ?? 0;

                    const isNearLimit =
                        currentLength > maxLength * 0.8;

                    const isAtLimit =
                        currentLength >= maxLength;

                    return (

                        <Text

                            style={[

                                styles.counter,

                                {

                                    color:

                                        isAtLimit

                                            ? colors.error

                                            : isNearLimit

                                            ? colors.textSecondary

                                            : colors.textSecondary,

                                    marginTop:

                                        multiline ? 4 : 0,

                                },

                            ]}

                        >

                            {currentLength}

                            {" / "}

                            {maxLength}

                        </Text>

                    );

                },

                [

                    maxLength,

                    value,

                    colors,

                    multiline,

                ]

            );

        /* ------------------------------------------------------------------ */
        /* Render Helper: Password Toggle Icon                                */
        /* ------------------------------------------------------------------ */

        const renderPasswordToggle =
            useCallback(

                () => {

                    // If custom rightIcon is provided, use it
                    if (rightIcon) {

                        return (

                            <View style={styles.rightIcon}>

                                {rightIcon}

                            </View>

                        );

                    }

                    // Use icon if available
                    const EyeIcon = () => {

                        // If you have vector icons installed, use them
                        // return <Ionicons 
                        //     name={passwordVisible ? "eye-off" : "eye"} 
                        //     size={20} 
                        //     color={colors.textSecondary} 
                        // />;

                        // Fallback to text
                        return (

                            <Text

                                style={[

                                    styles.toggleText,

                                    {

                                        color:
                                            colors.textSecondary,

                                    },

                                ]}

                            >

                                {passwordVisible
                                    ? "Hide"
                                    : "Show"}

                            </Text>

                        );

                    };

                    return (

                        <Pressable

                            onPress={
                                togglePasswordVisibility
                            }

                            style={styles.rightIcon}

                            accessibilityRole="button"

                            accessibilityLabel={
                                passwordVisible
                                    ? "Hide password"
                                    : "Show password"
                            }

                            accessibilityHint="Toggle password visibility"

                            hitSlop={{
                                top: 8,
                                bottom: 8,
                                left: 8,
                                right: 8,
                            }}

                        >

                            <EyeIcon />

                        </Pressable>

                    );

                },

                [

                    rightIcon,
                    passwordVisible,
                    togglePasswordVisibility,
                    colors,

                ]

            );

        /* ------------------------------------------------------------------ */
        /* Render                                                             */
        /* ------------------------------------------------------------------ */

        return (

            <View

                style={[

                    styles.container,

                    {

                        marginBottom: 16,

                    },

                    style,

                ]}

                testID={testID}

            >

                {/* ---------------------------------------------------------- */}
                {/* Label                                                     */}
                {/* ---------------------------------------------------------- */}

                {!!label && (

                    <Text

                        style={[

                            styles.label,

                            {

                                color:
                                    hasError
                                        ? colors.error
                                        : colors.text,

                                fontSize: 14,

                                fontWeight: "600",

                                marginBottom: 8,

                            },

                            labelStyle,

                        ]}

                    >

                        {label}

                        {required && (

                            <Text

                                style={{

                                    color: colors.error,

                                }}

                            >

                                {" *"}

                            </Text>

                        )}

                    </Text>

                )}

                {/* ---------------------------------------------------------- */}
                {/* Input Container                                           */}
                {/* ---------------------------------------------------------- */}

                <View

                    style={[

                        styles.inputContainer,

                        {

                            borderColor:

                                hasError
                                    ? colors.error
                                    : focused
                                    ? colors.primary
                                    : colors.border,

                            backgroundColor:

                                editable
                                    ? colors.surface
                                    : colors.disabled,

                            minHeight: 48,

                            borderWidth: 1,

                            borderRadius: 12,

                            paddingHorizontal: 14,

                            flexDirection: "row",

                            alignItems: "center",

                        },

                        // Multiline adjustment
                        multiline && {

                            alignItems: "flex-start",

                            paddingTop: 12,

                            paddingBottom: 12,

                        },

                    ]}

                >

                    {/* Left Icon */}
                    {!!leftIcon && (

                        <View

                            style={[

                                styles.leftIcon,

                                {

                                    justifyContent: "center",

                                    alignItems: "center",

                                    marginRight: 12,

                                },

                            ]}

                        >

                            {leftIcon}

                        </View>

                    )}

                    {/* Input */}
                    <RNTextInput

                        ref={ref}

                        value={value}

                        placeholder={placeholder}

                        placeholderTextColor={
                            colors.placeholder ??
                            "#9CA3AF"
                        }

                        editable={editable}

                        multiline={multiline}

                        secureTextEntry={
                            shouldHidePassword
                        }

                        autoCapitalize={
                            autoCapitalize
                        }

                        autoCorrect={
                            autoCorrect
                        }

                        autoComplete={
                            autoComplete
                        }

                        textContentType={
                            textContentType
                        }

                        autoFocus={
                            autoFocus
                        }

                        blurOnSubmit={
                            blurOnSubmit
                        }

                        selectTextOnFocus={
                            selectTextOnFocus
                        }

                        keyboardType={
                            keyboardType
                        }

                        returnKeyType={
                            returnKeyType
                        }

                        maxLength={
                            maxLength
                        }

                        numberOfLines={
                            numberOfLines
                        }

                        onChangeText={
                            onChangeText
                        }

                        onFocus={
                            handleFocus
                        }

                        onBlur={
                            handleBlur
                        }

                        onSubmitEditing={
                            onSubmitEditing
                        }

                        onEndEditing={
                            onEndEditing
                        }

                        accessibilityLabel={
                            accessibilityLabel ??
                            label ??
                            placeholder
                        }

                        accessibilityHint={
                            accessibilityHint
                        }

                        accessibilityState={{

                            disabled: !editable,

                            busy: false,

                            selected: focused,

                        }}

                        style={[

                            styles.input,

                            {

                                flex: 1,

                                fontSize: 16,

                                paddingVertical:
                                    multiline ? 0 : 12,

                                includeFontPadding:
                                    false,

                                textAlignVertical:
                                    multiline ? "top" : "center",

                                color:
                                    colors.text,

                            },

                            // ✅ Multiline conditional
                            multiline && {

                                minHeight: 100,

                                paddingTop: 0,

                            },

                            inputStyle,

                        ]}

                        {...rest}

                    />

                    {/* Right Icon / Password Toggle */}
                    {isPassword ? (
                        renderPasswordToggle()
                    ) : (
                        !!rightIcon && (
                            <View
                                style={[

                                    styles.rightIcon,

                                    {

                                        justifyContent:
                                            "center",

                                        alignItems:
                                            "center",

                                        marginLeft: 12,

                                    },

                                ]}
                            >

                                {rightIcon}

                            </View>
                        )
                    )}

                </View>

                {/* ---------------------------------------------------------- */}
                {/* Helper / Error                                            */}
                {/* ---------------------------------------------------------- */}

                {!!error ? (

                    <Text

                        accessibilityRole="alert"

                        style={[

                            styles.errorText,

                            {

                                color: colors.error,

                                marginTop: 6,

                                fontSize: 12,

                                fontWeight: "500",

                                lineHeight: 18,

                            },

                        ]}

                    >

                        {error}

                    </Text>

                ) : !!helperText ? (

                    <Text

                        style={[

                            styles.helperText,

                            {

                                color:
                                    colors.textSecondary,

                                marginTop: 6,

                                fontSize: 12,

                                lineHeight: 18,

                            },

                        ]}

                    >

                        {helperText}

                    </Text>

                ) : null}

                {/* ---------------------------------------------------------- */}
                {/* Character Counter                                         */}
                {/* ---------------------------------------------------------- */}

                {renderCounter()}

            </View>

        );

    })

);

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({

    /* ---------------------------------------------------------------------- */
    /* Container                                                              */
    /* ---------------------------------------------------------------------- */

    container: {

        width: "100%",

    },

    /* ---------------------------------------------------------------------- */
    /* Label                                                                  */
    /* ---------------------------------------------------------------------- */

    label: {

        // Styles applied inline

    },

    /* ---------------------------------------------------------------------- */
    /* Input Container                                                        */
    /* ---------------------------------------------------------------------- */

    inputContainer: {

        // Styles applied inline

    },

    /* ---------------------------------------------------------------------- */
    /* Input                                                                  */
    /* ---------------------------------------------------------------------- */

    input: {

        // Styles applied inline

    },

    /* ---------------------------------------------------------------------- */
    /* Icons                                                                  */
    /* ---------------------------------------------------------------------- */

    leftIcon: {

        // Styles applied inline

    },

    rightIcon: {

        // Styles applied inline

    },

    /* ---------------------------------------------------------------------- */
    /* Password Toggle                                                        */
    /* ---------------------------------------------------------------------- */

    toggleText: {

        fontSize: 13,

        fontWeight: "600",

    },

    /* ---------------------------------------------------------------------- */
    /* Helper / Error                                                         */
    /* ---------------------------------------------------------------------- */

    helperText: {

        // Styles applied inline

    },

    errorText: {

        // Styles applied inline

    },

    /* ---------------------------------------------------------------------- */
    /* Character Counter                                                      */
    /* ---------------------------------------------------------------------- */

    counter: {

        fontSize: 11,

        alignSelf: "flex-end",

    },

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

TextInput.displayName = "TextInput";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

TextInput.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    label: PropTypes.string,

    placeholder: PropTypes.string,

    value: PropTypes.string,

    helperText: PropTypes.string,

    error: PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Behaviour                                                              */
    /* ---------------------------------------------------------------------- */

    onChangeText: PropTypes.func,

    onBlur: PropTypes.func,

    onFocus: PropTypes.func,

    onSubmitEditing: PropTypes.func,

    onEndEditing: PropTypes.func,

    editable: PropTypes.bool,

    required: PropTypes.bool,

    multiline: PropTypes.bool,

    secureTextEntry: PropTypes.bool,

    autoCapitalize: PropTypes.oneOf(AUTO_CAPITALIZE_TYPES),

    autoCorrect: PropTypes.bool,

    autoComplete: PropTypes.string,

    textContentType: PropTypes.string,

    autoFocus: PropTypes.bool,

    blurOnSubmit: PropTypes.bool,

    selectTextOnFocus: PropTypes.bool,

    keyboardType: PropTypes.oneOf(KEYBOARD_TYPES),

    returnKeyType: PropTypes.oneOf(RETURN_KEY_TYPES),

    maxLength: PropTypes.number,

    numberOfLines: PropTypes.number,

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

    inputStyle: PropTypes.oneOfType([

        PropTypes.object,

        PropTypes.array,

    ]),

    labelStyle: PropTypes.oneOfType([

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

TextInput.defaultProps = {

    label: null,

    placeholder: null,

    value: "",

    helperText: null,

    error: null,

    onChangeText: null,

    onBlur: null,

    onFocus: null,

    onSubmitEditing: null,

    onEndEditing: null,

    editable: true,

    required: false,

    multiline: false,

    secureTextEntry: false,

    autoCapitalize: "none",

    autoCorrect: false,

    autoComplete: "off",

    textContentType: "none",

    autoFocus: false,

    blurOnSubmit: false,

    selectTextOnFocus: false,

    keyboardType: "default",

    returnKeyType: "done",

    maxLength: null,

    numberOfLines: null,

    leftIcon: null,

    rightIcon: null,

    accessibilityLabel: null,

    accessibilityHint: null,

    style: null,

    inputStyle: null,

    labelStyle: null,

    testID: null,

};

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

// ✅ Remove duplicate exports - only export once
export default TextInput;