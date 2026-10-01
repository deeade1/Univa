/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/ReviewsPreview.jsx     */
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

import Divider
    from "../common/Divider";

import Rating
    from "../common/Rating";

import LoadingOverlay
    from "../common/LoadingOverlay";

import EmptyState
    from "../common/EmptyState";

import ErrorState
    from "../common/ErrorState";

/* -------------------------------------------------------------------------- */
/* Product Components                                                         */
/* -------------------------------------------------------------------------- */

import ReviewCard
    from "./ReviewCard";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ReviewsPreview = memo(({

    /* ---------------------------------------------------------------------- */
    /* Header                                                                 */
    /* ---------------------------------------------------------------------- */

    title = "Customer Reviews",

    /* ---------------------------------------------------------------------- */
    /* Rating Summary                                                         */
    /* ---------------------------------------------------------------------- */

    averageRating = 0,

    totalReviews = 0,

    /* ---------------------------------------------------------------------- */
    /* Reviews                                                                */
    /* ---------------------------------------------------------------------- */

    reviews = [],

    previewCount = 2,

    /* ---------------------------------------------------------------------- */
    /* View All                                                               */
    /* ---------------------------------------------------------------------- */

    showViewAll = true,

    viewAllLabel = "View All Reviews",

    /* ---------------------------------------------------------------------- */
    /* States                                                                 */
    /* ---------------------------------------------------------------------- */

    loading = false,

    error = null,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onViewAll,

    onReviewPress,

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
    /* Preview Reviews                                                        */
    /* ---------------------------------------------------------------------- */

    const previewReviews =
        useMemo(

            () =>

                reviews.slice(

                    0,

                    previewCount

                ),

            [

                reviews,

                previewCount,

            ]

        );

    const hasReviews =
        useMemo(

            () =>

                reviews.length > 0,

            [

                reviews,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleViewAll =
        useCallback(

            () => {

                onViewAll?.();

            },

            [

                onViewAll,

            ]

        );

    const handleReviewPress =
        useCallback(

            (review, index) => {

                onReviewPress?.(

                    review,

                    index

                );

            },

            [

                onReviewPress,

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

                    message="Loading reviews..."

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

                <ErrorState

                    title="Unable to load reviews"

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

    if (!hasReviews) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                <EmptyState

                    icon="star-outline"

                    title="No Reviews Yet"

                    description="Be the first to review this product."

                />

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

            {/* ------------------------------------------------------------------ */}
            {/* Section Title                                                     */}
            {/* ------------------------------------------------------------------ */}

            <Text
                style={[

                    styles.title,

                    {

                        color:
                            colors.text,

                    },

                ]}
            >

                {title}

            </Text>

            {/* ------------------------------------------------------------------ */}
            {/* Rating Summary                                                    */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.summaryContainer
                }
            >

                <Text
                    style={[

                        styles.averageRating,

                        {

                            color:
                                colors.text,

                        },

                    ]}
                >

                    {Number(
                        averageRating
                    ).toFixed(1)}

                </Text>

                <Rating

                    rating={
                        averageRating
                    }

                    size={
                        18
                    }

                    readonly

                />

                <Text
                    style={[

                        styles.reviewCount,

                        {

                            color:
                                colors.textSecondary,

                        },

                    ]}
                >

                    {totalReviews.toLocaleString()}

                    {" "}

                    {totalReviews === 1

                        ? "Review"

                        : "Reviews"}

                </Text>

            </View>

            <Divider
                spacing={theme.spacing.lg}
            />

            {/* ------------------------------------------------------------------ */}
            {/* Review Preview List                                                */}
            {/* ------------------------------------------------------------------ */}

            {previewReviews.map(

                (review, index) => (

                    <View
                        key={
                            review?.id?.toString?.() ??
                            index.toString()
                        }
                    >

                        <ReviewCard

                            review={
                                review
                            }

                            onPress={
                                onReviewPress
                                    ? () => handleReviewPress(review, index)
                                    : undefined
                            }

                        />

                        {index <
                            previewReviews.length - 1 && (

                            <Divider
                                spacing={theme.spacing.md}
                            />

                        )}

                    </View>

                )

            )}

            {/* ------------------------------------------------------------------ */}
            {/* View All Reviews                                                   */}
            {/* ------------------------------------------------------------------ */}

            {showViewAll &&
                typeof onViewAll === "function" && (

                <>

                    <Divider
                        spacing={theme.spacing.lg}
                    />

                    <TouchableOpacity

                        onPress={
                            handleViewAll
                        }

                        activeOpacity={0.7}

                        accessibilityRole="button"

                        accessibilityLabel={
                            viewAllLabel
                        }

                        accessibilityHint="Opens the complete list of customer reviews"

                        style={
                            styles.viewAllButton
                        }

                    >

                        <Text
                            style={[

                                styles.viewAllText,

                                {

                                    color:
                                        colors.primary,

                                },

                            ]}
                        >

                            {viewAllLabel}

                        </Text>

                    </TouchableOpacity>

                </>

            )}

        </View>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ReviewsPreview.displayName =
    "ReviewsPreview";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ReviewsPreview.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Header                                                                 */
    /* ---------------------------------------------------------------------- */

    title:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Rating Summary                                                         */
    /* ---------------------------------------------------------------------- */

    averageRating:
        PropTypes.number,

    totalReviews:
        PropTypes.number,

    /* ---------------------------------------------------------------------- */
    /* Reviews                                                                */
    /* ---------------------------------------------------------------------- */

    reviews:
        PropTypes.arrayOf(

            PropTypes.shape({

                id:
                    PropTypes.oneOfType([

                        PropTypes.string,

                        PropTypes.number,

                    ]),

                rating:
                    PropTypes.number,

                title:
                    PropTypes.string,

                comment:
                    PropTypes.string,

                reviewer:
                    PropTypes.string,

                avatar:
                    PropTypes.string,

                createdAt:
                    PropTypes.string,

                helpfulCount:
                    PropTypes.number,

                verifiedPurchase:
                    PropTypes.bool,

                sellerResponse:
                    PropTypes.string,

            })

        ),

    previewCount:
        PropTypes.number,

    /* ---------------------------------------------------------------------- */
    /* View All                                                               */
    /* ---------------------------------------------------------------------- */

    showViewAll:
        PropTypes.bool,

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

    onViewAll:
        PropTypes.func,

    onReviewPress:
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

            paddingHorizontal:
                theme.spacing.md,

            paddingVertical:
                theme.spacing.md,

        },

        /* ------------------------------------------------------------------ */
        /* Title                                                              */
        /* ------------------------------------------------------------------ */

        title: {

            fontSize:
                18,

            fontWeight:
                "700",

            marginBottom:
                theme.spacing.md,

        },

        /* ------------------------------------------------------------------ */
        /* Rating Summary                                                     */
        /* ------------------------------------------------------------------ */

        summaryContainer: {

            alignItems:
                "center",

        },

        averageRating: {

            fontSize:
                36,

            fontWeight:
                "700",

            marginBottom:
                theme.spacing.xs,

        },

        reviewCount: {

            fontSize:
                14,

            marginTop:
                theme.spacing.xs,

        },

        /* ------------------------------------------------------------------ */
        /* View All Button                                                    */
        /* ------------------------------------------------------------------ */

        viewAllButton: {

            alignSelf:
                "center",

            paddingVertical:
                10,

        },

        viewAllText: {

            fontSize:
                15,

            fontWeight:
                "600",

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    ReviewsPreview;