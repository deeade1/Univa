/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/QuestionsAndAnswers.jsx */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useMemo,
    useCallback,
} from "react";

import {
    FlatList,
    StyleSheet,
    View,
} from "react-native";

import PropTypes
    from "prop-types";

import theme
    from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import SectionHeader
    from "../common/SectionHeader";

import LoadingOverlay
    from "../common/LoadingOverlay";

import EmptyState
    from "../common/EmptyState";

import ErrorState
    from "../common/ErrorState";

import Button
    from "../common/Button";

/* -------------------------------------------------------------------------- */
/* Product Components                                                         */
/* -------------------------------------------------------------------------- */

import QuestionCard
    from "./QuestionCard";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const questionPropType =
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

        answer:
            PropTypes.shape({

                responder:
                    PropTypes.string,

                message:
                    PropTypes.string,

                createdAt:
                    PropTypes.string,

            }),

    });

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const QuestionsAndAnswers = memo(({

    /* ---------------------------------------------------------------------- */
    /* Header                                                                 */
    /* ---------------------------------------------------------------------- */

    title = "Questions & Answers",

    subtitle,

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    questions = [],

    previewCount = 3,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showAskQuestion = true,

    showViewAll = true,

    askQuestionLabel = "Ask a Question",

    viewAllLabel = "View All Questions",

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    loading = false,

    error = null,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onAskQuestion,

    onViewAll,

    onQuestionPress,

    onRetry,

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
    /* Preview Questions                                                      */
    /* ---------------------------------------------------------------------- */

    const previewQuestions =
        useMemo(

            () =>

                questions.slice(

                    0,

                    previewCount

                ),

            [

                questions,

                previewCount,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Statistics                                                             */
    /* ---------------------------------------------------------------------- */

    const totalQuestions =
        useMemo(

            () =>

                questions.length,

            [

                questions,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleAskQuestion =
        useCallback(

            () => {

                onAskQuestion?.();

            },

            [

                onAskQuestion,

            ]

        );

    const handleViewAll =
        useCallback(

            () => {

                onViewAll?.();

            },

            [

                onViewAll,

            ]

        );

    const handleQuestionPress =
        useCallback(

            (question) => {

                onQuestionPress?.(

                    question

                );

            },

            [

                onQuestionPress,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Render Question                                                        */
    /* ---------------------------------------------------------------------- */

    const renderQuestion =
        useCallback(

            ({ item }) => (

                <QuestionCard

                    question={
                        item
                    }

                    onPress={
                        handleQuestionPress
                    }

                />

            ),

            [

                handleQuestionPress,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Key Extractor                                                          */
    /* ---------------------------------------------------------------------- */

    const keyExtractor =
        useCallback(

            (item) =>

                item?.id?.toString?.() ??
                item?.question?.slice(0, 10) ??
                Math.random().toString(),

            []

        );

    /* ---------------------------------------------------------------------- */
    /* List Header Component                                                  */
    /* ---------------------------------------------------------------------- */

    const ListHeaderComponent =
        useMemo(

            () => (

                <SectionHeader

                    title={
                        title
                    }

                    subtitle={

                        subtitle ??

                        `${totalQuestions} ${

                            totalQuestions === 1

                                ? "Question"

                                : "Questions"

                        }`

                    }

                />

            ),

            [

                title,

                subtitle,

                totalQuestions,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* List Footer Component                                                  */
    /* ---------------------------------------------------------------------- */

    const ListFooterComponent =
        useMemo(

            () => {

                const showFooterActions =
                    showAskQuestion ||
                    (showViewAll &&
                        totalQuestions > previewCount);

                if (!showFooterActions) {

                    return null;

                }

                return (

                    <View
                        style={
                            styles.actionsContainer
                        }
                    >

                        {showAskQuestion && (

                            <Button

                                title={
                                    askQuestionLabel
                                }

                                onPress={
                                    handleAskQuestion
                                }

                                style={
                                    styles.askButton
                                }

                            />

                        )}

                        {showViewAll &&
                            totalQuestions > previewCount && (

                            <Button

                                title={
                                    viewAllLabel
                                }

                                variant="text"

                                onPress={
                                    handleViewAll
                                }

                                style={
                                    styles.viewAllButton
                                }

                            />

                        )}

                    </View>

                );

            },

            [

                showAskQuestion,
                showViewAll,
                totalQuestions,
                previewCount,
                askQuestionLabel,
                viewAllLabel,
                handleAskQuestion,
                handleViewAll,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Loading State                                                          */
    /* ---------------------------------------------------------------------- */

    if (loading) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                <LoadingOverlay

                    visible

                    fullscreen={false}

                    transparent

                    message="Loading questions..."

                />

            </View>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Error State                                                            */
    /* ---------------------------------------------------------------------- */

    if (error) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                <SectionHeader

                    title={
                        title
                    }

                    subtitle={
                        subtitle ??
                        `${totalQuestions} Questions`
                    }

                />

                <ErrorState

                    title="Unable to load questions"

                    description={
                        error?.message ??
                        "Please try again."
                    }

                    onRetry={
                        onRetry
                    }

                />

            </View>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Empty State                                                            */
    /* ---------------------------------------------------------------------- */

    if (!totalQuestions) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                <SectionHeader

                    title={
                        title
                    }

                    subtitle="0 Questions"

                />

                <EmptyState

                    icon="help-circle-outline"

                    title="No Questions Yet"

                    description={
                        "Be the first to ask a question about this product."
                    }

                />

                {showAskQuestion && (

                    <Button

                        title={
                            askQuestionLabel
                        }

                        onPress={
                            handleAskQuestion
                        }

                        style={
                            styles.askButton
                        }

                    />

                )}

            </View>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Component                                                              */
    /* ---------------------------------------------------------------------- */

    return (

        <View
            style={[

                styles.container,

                style,

            ]}
        >

            <FlatList

                data={
                    previewQuestions
                }

                renderItem={
                    renderQuestion
                }

                keyExtractor={
                    keyExtractor
                }

                scrollEnabled={
                    false
                }

                ListHeaderComponent={
                    ListHeaderComponent
                }

                ListFooterComponent={
                    ListFooterComponent
                }

                ItemSeparatorComponent={() => (

                    <View
                        style={styles.separator}
                    />

                )}

            />

        </View>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

QuestionsAndAnswers.displayName =
    "QuestionsAndAnswers";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

QuestionsAndAnswers.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Header                                                                 */
    /* ---------------------------------------------------------------------- */

    title:
        PropTypes.string,

    subtitle:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    questions:
        PropTypes.arrayOf(
            questionPropType
        ),

    previewCount:
        PropTypes.number,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showAskQuestion:
        PropTypes.bool,

    showViewAll:
        PropTypes.bool,

    askQuestionLabel:
        PropTypes.string,

    viewAllLabel:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* States                                                                 */
    /* ---------------------------------------------------------------------- */

    loading:
        PropTypes.bool,

    error:
        PropTypes.object,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onAskQuestion:
        PropTypes.func,

    onViewAll:
        PropTypes.func,

    onQuestionPress:
        PropTypes.func,

    onRetry:
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
        /* Container                                                          */
        /* ------------------------------------------------------------------ */

        container: {

            marginBottom:
                theme.spacing.lg,

        },

        /* ------------------------------------------------------------------ */
        /* Questions List                                                     */
        /* ------------------------------------------------------------------ */

        separator: {

            height:
                theme.spacing.xs,

        },

        /* ------------------------------------------------------------------ */
        /* Footer Actions                                                     */
        /* ------------------------------------------------------------------ */

        actionsContainer: {

            marginTop:
                theme.spacing.lg,

            paddingHorizontal:
                theme.spacing.md,

        },

        askButton: {

            marginBottom:
                theme.spacing.sm,

        },

        viewAllButton: {

            alignSelf:
                "center",

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    QuestionsAndAnswers;