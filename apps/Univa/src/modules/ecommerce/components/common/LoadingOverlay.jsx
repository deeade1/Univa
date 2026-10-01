/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/LoadingOverlay.jsx      */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
} from "react";

import {
    ActivityIndicator,
    Modal,
    Pressable,
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

const LoadingOverlay = memo(({

    visible = false,

    message = "Loading...",

    transparent = true,

    dismissible = false,

    fullscreen = true,

    size = "large",

    color,

    backgroundColor,

    indicator,

    children,

    onRequestClose,

    style,

}) => {

    const {
        colors,
        typography,
    } = theme;

    if (!visible) {
        return null;
    }

    const spinnerColor =
        color ??
        colors.primary;

    const overlayColor =

        backgroundColor ??

        (
            transparent
                ? "rgba(0,0,0,0.45)"
                : colors.background
        );

    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    const content = (

        <Pressable

            disabled={
                !dismissible
            }

            onPress={
                onRequestClose
            }

            style={[

                fullscreen
                    ? styles.overlay
                    : styles.inline,

                {
                    backgroundColor:
                        overlayColor,
                },

            ]}

        >

            <View
                style={[

                    styles.card,

                    {
                        backgroundColor:
                            colors.surface ??
                            colors.card ??
                            colors.background,
                    },

                    style,

                ]}
            >

                {indicator ?? (

                    <ActivityIndicator
                        size={size}
                        color={
                            spinnerColor
                        }
                    />

                )}

                {!!message && (

                    <Text
                        style={[

                            styles.message,

                            {

                                color:
                                    colors.text,

                                fontSize:
                                    typography
                                        ?.bodyMedium
                                        ?.fontSize ??
                                    15,

                            },

                        ]}
                    >
                        {message}
                    </Text>

                )}

                {children}

            </View>

        </Pressable>

    );

    /* ---------------------------------------------------------------------- */
    /* Fullscreen                                                             */
    /* ---------------------------------------------------------------------- */

    if (fullscreen) {

        return (

            <Modal

                visible={visible}

                transparent

                animationType="fade"

                statusBarTranslucent

                onRequestClose={
                    onRequestClose
                }

            >

                {content}

            </Modal>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Inline Overlay                                                         */
    /* ---------------------------------------------------------------------- */

    return content;

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

LoadingOverlay.displayName =
    "LoadingOverlay";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

LoadingOverlay.propTypes = {

    visible:
        PropTypes.bool,

    message:
        PropTypes.string,

    transparent:
        PropTypes.bool,

    dismissible:
        PropTypes.bool,

    fullscreen:
        PropTypes.bool,

    size:
        PropTypes.oneOf([
            "small",
            "large",
        ]),

    color:
        PropTypes.string,

    backgroundColor:
        PropTypes.string,

    indicator:
        PropTypes.node,

    children:
        PropTypes.node,

    onRequestClose:
        PropTypes.func,

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

    overlay: {

        flex: 1,

        justifyContent:
            "center",

        alignItems:
            "center",

        padding: 24,

    },

    inline: {

        ...StyleSheet.absoluteFillObject,

        justifyContent:
            "center",

        alignItems:
            "center",

        zIndex: 999,

    },

    card: {

        minWidth: 180,

        maxWidth: 320,

        borderRadius: 16,

        paddingHorizontal: 24,

        paddingVertical: 20,

        alignItems:
            "center",

        justifyContent:
            "center",

        elevation: 6,

        shadowColor:
            "#000",

        shadowOpacity:
            0.15,

        shadowRadius:
            10,

        shadowOffset: {
            width: 0,
            height: 4,
        },

    },

    message: {

        marginTop: 14,

        textAlign:
            "center",

        fontWeight:
            "500",

    },

});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    LoadingOverlay;