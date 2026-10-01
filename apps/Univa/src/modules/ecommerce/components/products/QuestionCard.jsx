/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/QuestionCard.jsx       */
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

const QuestionCard = memo(({

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    question,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showAnswer = true,

    showHelpful = true,

    helpfulLabel = "Helpful",

    sellerBadgeLabel = "Seller",

    answeredLabel = "Answered",

    pendingLabel = "Pending",

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onPress,

    onHelpful,

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

        question: questionText,

        askedBy,

        createdAt,

        helpfulCount = 0,

        answer,

    } = question ?? {};

    const hasAnswer =
        useMemo(

            () =>

                Boolean(

                    answer?.message

                ),

            [

                answer,

            ]

        );

    const responderLabel =
        useMemo(

            () =>

                answer?.responder ??

                sellerBadgeLabel,

            [

                answer,

                sellerBadgeLabel,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handlePress =
        useCallback(

            () => {

                onPress?.(

                    question

                );

            },

            [

                onPress,

                question,

            ]

        );

    const handleHelpful =
        useCallback(

            () => {

                onHelpful?.(

                    question

                );

            },

            [

                onHelpful,

                question,

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

            accessibilityLabel={`Question: ${questionText?.slice(0, 50)}${questionText?.length > 50 ? "..." : ""}`}

            accessibilityHint="Opens the question details"

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

                    <Text
                        style={[

                            styles.author,

                            {

                                color:
                                    colors.text,

                            },

                        ]}
                    >

                        {askedBy ??

                            "Anonymous"}

                    </Text>

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

                </View>

                <Badge

                    label={

                        hasAnswer

                            ? answeredLabel

                            : pendingLabel

                    }

                    variant={

                        hasAnswer

                            ? "success"

                            : "warning"

                    }

                />

            </View>

            {/* ------------------------------------------------------------------ */}
            {/* Question                                                           */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.questionContainer
                }
            >

                <View
                    style={[

                        styles.questionBadge,

                        {

                            backgroundColor:
                                colors.primary,

                        },

                    ]}
                >

                    <Text
                        style={
                            styles.questionBadgeText
                        }
                    >

                        Q

                    </Text>

                </View>

                <View
                    style={
                        styles.questionContent
                    }
                >

                    <Text
                        style={[

                            styles.questionText,

                            {

                                color:
                                    colors.text,

                            },

                        ]}
                    >

                        {questionText}

                    </Text>

                </View>

            </View>

            {/* ------------------------------------------------------------------ */}
            {/* Answer                                                            */}
            {/* ------------------------------------------------------------------ */}

            {showAnswer && hasAnswer && (

                <View
                    style={[
                        styles.answerContainer,
                        {
                            borderTopColor:
                                colors.outlineVariant ??
                                colors.border ??
                                "#E5E7EB",
                        },
                    ]}
                >

                    <View
                        style={
                            styles.answerHeader
                        }
                    >

                        <Badge

                            label={
                                responderLabel
                            }

                            variant="success"

                        />

                        {answer?.createdAt && (

                            <Text
                                style={[

                                    styles.answerDate,

                                    {

                                        color:
                                            colors.textSecondary,

                                    },

                                ]}
                            >

                                {answer.createdAt}

                            </Text>

                        )}

                    </View>

                    <Text
                        style={[

                            styles.answerText,

                            {

                                color:
                                    colors.text,

                            },

                        ]}
                    >

                        {answer.message}

                    </Text>

                </View>

            )}

            {/* ------------------------------------------------------------------ */}
            {/* Footer                                                            */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={

                    styles.footer

                }
            >

                {showHelpful && (

                    <Button

                        title={`${helpfulLabel} (${helpfulCount})`}

                        variant="text"

                        size="small"

                        onPress={
                            handleHelpful
                        }

                        accessibilityLabel={`Mark question as ${helpfulLabel.toLowerCase()}`}

                    />

                )}

            </View>

        </TouchableOpacity>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

QuestionCard.displayName =
    "QuestionCard";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

QuestionCard.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    question:
        PropTypes.shape({

            id:
                PropTypes.oneOfType([

                    PropTypes.string,

                    PropTypes.number,

                ]),

            question:
                PropTypes.string,

            askedBy:
                PropTypes.string,

            createdAt:
                PropTypes.string,

            helpfulCount:
                PropTypes.number,

            answer:
                PropTypes.shape({

                    responder:
                        PropTypes.string,

                    message:
                        PropTypes.string,

                    createdAt:
                        PropTypes.string,

                }),

        }),

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showAnswer:
        PropTypes.bool,

    showHelpful:
        PropTypes.bool,

    helpfulLabel:
        PropTypes.string,

    sellerBadgeLabel:
        PropTypes.string,

    answeredLabel:
        PropTypes.string,

    pendingLabel:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onPress:
        PropTypes.func,

    onHelpful:
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

            flex:
                1,

            marginRight:
                theme.spacing.sm,

        },

        author: {

            fontSize:
                15,

            fontWeight:
                "600",

        },

        date: {

            marginTop:
                2,

            fontSize:
                12,

        },

        /* ------------------------------------------------------------------ */
        /* Question                                                           */
        /* ------------------------------------------------------------------ */

        questionContainer: {

            flexDirection:
                "row",

            alignItems:
                "flex-start",

        },

        questionBadge: {

            width:
                28,

            height:
                28,

            borderRadius:
                14,

            justifyContent:
                "center",

            alignItems:
                "center",

            marginRight:
                theme.spacing.sm,

        },

        questionBadgeText: {

            color:
                "#FFFFFF",

            fontWeight:
                "700",

            fontSize:
                14,

        },

        questionContent: {

            flex:
                1,

        },

        questionText: {

            fontSize:
                15,

            lineHeight:
                22,

            fontWeight:
                "500",

        },

        /* ------------------------------------------------------------------ */
        /* Answer                                                             */
        /* ------------------------------------------------------------------ */

        answerContainer: {

            marginTop:
                theme.spacing.md,

            marginLeft:
                40,

            paddingTop:
                theme.spacing.md,

            borderTopWidth:
                StyleSheet.hairlineWidth,

        },

        answerHeader: {

            flexDirection:
                "row",

            justifyContent:
                "space-between",

            alignItems:
                "center",

            marginBottom:
                theme.spacing.xs,

        },

        answerDate: {

            fontSize:
                12,

        },

        answerText: {

            fontSize:
                14,

            lineHeight:
                21,

        },

        /* ------------------------------------------------------------------ */
        /* Footer                                                             */
        /* ------------------------------------------------------------------ */

        footer: {

            marginTop:
                theme.spacing.md,

            flexDirection:
                "row",

            justifyContent:
                "flex-end",

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    QuestionCard;