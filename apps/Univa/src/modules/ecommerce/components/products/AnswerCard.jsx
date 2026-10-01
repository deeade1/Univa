/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/AnswerCard.jsx         */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useMemo,
    useCallback,
} from "react";

import {
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from "react-native";

import PropTypes
    from "prop-types";

import theme
    from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import Badge
    from "../common/Badge";

import Button
    from "../common/Button";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const AnswerCard = memo(({

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    answer,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showHelpful = true,

    showReport = false,

    helpfulLabel = "Helpful",

    reportLabel = "Report",

    verifiedSellerLabel = "Verified Seller",

    customerLabel = "Customer",

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onPress,

    onHelpful,

    onReport,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,

}) => {

    const {
        colors,
        spacing,
    } = theme;

    /* ---------------------------------------------------------------------- */
    /* Derived Data                                                           */
    /* ---------------------------------------------------------------------- */

    const {

        id,

        responder,

        responderName,

        message,

        createdAt,

        helpfulCount = 0,

        verified = false,

    } = answer ?? {};

    const responderLabel =
        useMemo(

            () =>

                responder ??

                customerLabel,

            [

                responder,

                customerLabel,

            ]

        );

    const isVerified =
        useMemo(

            () =>

                Boolean(

                    verified

                ),

            [

                verified,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handlePress =
        useCallback(

            () => {

                onPress?.(

                    answer

                );

            },

            [

                answer,

                onPress,

            ]

        );

    const handleHelpful =
        useCallback(

            () => {

                onHelpful?.(

                    answer

                );

            },

            [

                answer,

                onHelpful,

            ]

        );

    const handleReport =
        useCallback(

            () => {

                onReport?.(

                    answer

                );

            },

            [

                answer,

                onReport,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Component                                                              */
    /* ---------------------------------------------------------------------- */

    return (

        <TouchableOpacity

            activeOpacity={0.8}

            onPress={handlePress}

            accessible

            accessibilityRole="button"

            accessibilityLabel="View answer"

            accessibilityHint="Opens the answer details"

            style={[

                styles.container,

                {

                    backgroundColor:
                        colors.surface,

                    shadowColor:
                        colors.shadow ??
                        "#000",

                },

                style,

            ]}

        >

            {/* ------------------------------------------------------------------ */}
            {/* Header                                                             */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.header
                }
            >

                <View
                    style={
                        styles.headerLeft
                    }
                >

                    <Badge

                        label={
                            responderLabel
                        }

                        variant={
                            isVerified
                                ? "success"
                                : "default"
                        }

                    />

                    {isVerified && (

                        <Badge

                            label={
                                verifiedSellerLabel
                            }

                            variant="success"

                            style={
                                styles.verifiedBadge
                            }

                        />

                    )}

                </View>

                {!!createdAt && (

                    <Text
                        style={[

                            styles.date,

                            {

                                color:
                                    colors.textSecondary,

                            },

                        ]}
                    >

                        {createdAt}

                    </Text>

                )}

            </View>

            {/* ------------------------------------------------------------------ */}
            {/* Responder                                                         */}
            {/* ------------------------------------------------------------------ */}

            {!!responderName && (

                <Text
                    style={[

                        styles.responderName,

                        {

                            color:
                                colors.text,

                        },

                    ]}
                >

                    {responderName}

                </Text>

            )}

            {/* ------------------------------------------------------------------ */}
            {/* Answer                                                            */}
            {/* ------------------------------------------------------------------ */}

            <Text
                style={[

                    styles.answerText,

                    {

                        color:
                            colors.text,

                    },

                ]}
            >

                {message}

            </Text>

            {/* ------------------------------------------------------------------ */}
            {/* Footer                                                            */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.footer
                }
            >

                <View
                    style={
                        styles.footerLeft
                    }
                >

                    {showHelpful && (

                        <Button

                            title={`${helpfulLabel} (${helpfulCount.toLocaleString()})`}

                            variant="text"

                            size="small"

                            onPress={
                                handleHelpful
                            }

                            accessibilityLabel={`Mark answer as ${helpfulLabel.toLowerCase()}`}

                        />

                    )}

                </View>

                <View
                    style={
                        styles.footerRight
                    }
                >

                    {showReport && (

                        <Button

                            title={
                                reportLabel
                            }

                            variant="text"

                            size="small"

                            onPress={
                                handleReport
                            }

                            accessibilityLabel={reportLabel}

                        />

                    )}

                </View>

            </View>

        </TouchableOpacity>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

AnswerCard.displayName =
    "AnswerCard";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

AnswerCard.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    answer:
        PropTypes.shape({

            id:
                PropTypes.oneOfType([

                    PropTypes.string,

                    PropTypes.number,

                ]),

            responder:
                PropTypes.string,

            responderName:
                PropTypes.string,

            message:
                PropTypes.string,

            createdAt:
                PropTypes.string,

            helpfulCount:
                PropTypes.number,

            verified:
                PropTypes.bool,

            // Future-ready fields
            likedByUser:
                PropTypes.bool,

            edited:
                PropTypes.bool,

            attachments:
                PropTypes.array,

            status:
                PropTypes.oneOf([

                    "published",

                    "pending",

                    "hidden",

                ]),

        }),

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showHelpful:
        PropTypes.bool,

    showReport:
        PropTypes.bool,

    helpfulLabel:
        PropTypes.string,

    reportLabel:
        PropTypes.string,

    verifiedSellerLabel:
        PropTypes.string,

    customerLabel:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onPress:
        PropTypes.func,

    onHelpful:
        PropTypes.func,

    onReport:
        PropTypes.func,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

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

        /* ------------------------------------------------------------------ */
        /* Card                                                               */
        /* ------------------------------------------------------------------ */

        container: {

            marginHorizontal:
                theme.spacing.md,

            marginBottom:
                theme.spacing.md,

            padding:
                theme.spacing.md,

            borderRadius:
                12,

            elevation:
                2,

            shadowOpacity:
                0.08,

            shadowRadius:
                6,

            shadowOffset: {

                width:
                    0,

                height:
                    2,

            },

        },

        /* ------------------------------------------------------------------ */
        /* Header                                                             */
        /* ------------------------------------------------------------------ */

        header: {

            flexDirection:
                "row",

            justifyContent:
                "space-between",

            alignItems:
                "center",

            marginBottom:
                theme.spacing.sm,

        },

        headerLeft: {

            flexDirection:
                "row",

            alignItems:
                "center",

            flexWrap:
                "wrap",

            flex:
                1,

        },

        verifiedBadge: {

            marginLeft:
                theme.spacing.xs,

        },

        date: {

            fontSize:
                12,

        },

        /* ------------------------------------------------------------------ */
        /* Content                                                            */
        /* ------------------------------------------------------------------ */

        responderName: {

            fontSize:
                15,

            fontWeight:
                "600",

            marginBottom:
                theme.spacing.xs,

        },

        answerText: {

            fontSize:
                15,

            lineHeight:
                22,

        },

        /* ------------------------------------------------------------------ */
        /* Footer                                                             */
        /* ------------------------------------------------------------------ */

        footer: {

            flexDirection:
                "row",

            justifyContent:
                "space-between",

            alignItems:
                "center",

            marginTop:
                theme.spacing.lg,

        },

        footerLeft: {

            flex:
                1,

        },

        footerRight: {

            alignItems:
                "flex-end",

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    AnswerCard;