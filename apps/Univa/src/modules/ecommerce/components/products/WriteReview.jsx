/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/WriteReview.jsx        */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useState,
    useMemo,
    useCallback,
} from "react";

import {
    Image,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
    ScrollView,
} from "react-native";

import PropTypes
    from "prop-types";

import theme
    from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import Rating
    from "../common/Rating";

import Button
    from "../common/Button";

import TextField
    from "../common/TextField";

import TextArea
    from "../common/TextArea";

import LoadingOverlay
    from "../common/LoadingOverlay";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const WriteReview = memo(({

    /* ---------------------------------------------------------------------- */
    /* Initial Values                                                         */
    /* ---------------------------------------------------------------------- */

    initialRating = 0,

    initialTitle = "",

    initialComment = "",

    initialImages = [],

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    title = "Write a Review",

    titlePlaceholder = "Review title",

    commentPlaceholder = "Share your experience with this product...",

    maxCommentLength = 500,

    showPhotos = true,

    showCancel = true,

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    loading = false,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onSubmit,

    onCancel,

    onAddPhoto,

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
    /* Form State                                                             */
    /* ---------------------------------------------------------------------- */

    const [

        rating,

        setRating,

    ] = useState(

        initialRating

    );

    const [

        reviewTitle,

        setReviewTitle,

    ] = useState(

        initialTitle

    );

    const [

        comment,

        setComment,

    ] = useState(

        initialComment

    );

    const [

        images,

        setImages,

    ] = useState(

        initialImages

    );

    /* ---------------------------------------------------------------------- */
    /* Validation                                                             */
    /* ---------------------------------------------------------------------- */

    const commentLength =
        useMemo(

            () =>

                comment.length,

            [

                comment,

            ]

        );

    const errors =
        useMemo(

            () => {

                const validationErrors = {};

                if (rating === 0) {
                    validationErrors.rating = "Please select a rating.";
                }

                if (reviewTitle.trim().length === 0) {
                    validationErrors.title = "Review title is required.";
                }

                if (comment.trim().length === 0) {
                    validationErrors.comment = "Review comment is required.";
                }

                return validationErrors;

            },

            [

                rating,
                reviewTitle,
                comment,

            ]

        );

    const isValid =
        useMemo(

            () =>

                Object.keys(errors).length === 0,

            [

                errors,

            ]

        );

    const hasErrors =
        useMemo(

            () =>

                Object.keys(errors).length > 0,

            [

                errors,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleRatingChange =
        useCallback(

            value => {

                setRating(

                    value

                );

            },

            []

        );

    const handleSubmit =
        useCallback(

            () => {

                if (!isValid) {

                    return;

                }

                onSubmit?.({

                    rating,

                    title:
                        reviewTitle.trim(),

                    comment:
                        comment.trim(),

                    images,

                });

            },

            [

                isValid,

                rating,

                reviewTitle,

                comment,

                images,

                onSubmit,

            ]

        );

    const handleCancel =
        useCallback(

            () => {

                onCancel?.();

            },

            [

                onCancel,

            ]

        );

    const handleAddPhoto =
        useCallback(

            async () => {

                const result =
                    await onAddPhoto?.();

                if (!result) {

                    return;

                }

                // Support both single image and array results
                const newImages =
                    Array.isArray(result)
                        ? result
                        : [result];

                setImages(

                    previous => [

                        ...previous,

                        ...newImages,

                    ]

                );

            },

            [

                onAddPhoto,

            ]

        );

    const handleRemoveImage =
        useCallback(

            (indexToRemove) => {

                setImages(

                    previous =>

                        previous.filter(

                            (_, index) =>

                                index !== indexToRemove

                        )

                );

            },

            []

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

                    message="Submitting your review..."

                />

            </View>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Component                                                              */
    /* ---------------------------------------------------------------------- */

    return (

        <ScrollView

            style={[

                styles.container,

                style,

            ]}

            showsVerticalScrollIndicator={
                false
            }

        >

            {/* ------------------------------------------------------------------ */}
            {/* Header                                                             */}
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
            {/* Rating                                                             */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.ratingContainer
                }
            >

                <Rating

                    rating={
                        rating
                    }

                    size={
                        32
                    }

                    readonly={
                        false
                    }

                    onChange={
                        handleRatingChange
                    }

                />

                {errors.rating && (

                    <Text
                        style={[

                            styles.errorText,

                            {

                                color:
                                    colors.error,

                            },

                        ]}
                    >

                        {errors.rating}

                    </Text>

                )}

            </View>

            {/* ------------------------------------------------------------------ */}
            {/* Review Title                                                       */}
            {/* ------------------------------------------------------------------ */}

            <TextField

                label="Title"

                placeholder={
                    titlePlaceholder
                }

                value={
                    reviewTitle
                }

                onChangeText={
                    setReviewTitle
                }

                maxLength={
                    100
                }

                returnKeyType="next"

                error={
                    errors.title
                }

            />

            {/* ------------------------------------------------------------------ */}
            {/* Review Comment                                                     */}
            {/* ------------------------------------------------------------------ */}

            <TextArea

                label="Review"

                placeholder={
                    commentPlaceholder
                }

                value={
                    comment
                }

                onChangeText={
                    setComment
                }

                maxLength={
                    maxCommentLength
                }

                numberOfLines={
                    6
                }

                error={
                    errors.comment
                }

            />

            {/* ------------------------------------------------------------------ */}
            {/* Character Counter                                                  */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.counterContainer
                }
            >

                <Text
                    style={[

                        styles.counter,

                        {

                            color:
                                commentLength >=
                                maxCommentLength
                                    ? colors.error
                                    : colors.textSecondary,

                        },

                    ]}
                >

                    {commentLength}

                    /

                    {maxCommentLength}

                </Text>

            </View>

            {/* ------------------------------------------------------------------ */}
            {/* Photo Upload                                                      */}
            {/* ------------------------------------------------------------------ */}

            {showPhotos && (

                <View
                    style={
                        styles.photosSection
                    }
                >

                    <Button

                        title="Add Photos"
                        variant="outline"
                        onPress={handleAddPhoto}

                    />

                    {images.length > 0 && (

                        <ScrollView

                            horizontal

                            showsHorizontalScrollIndicator={
                                false
                            }

                            style={
                                styles.imageList
                            }

                            contentContainerStyle={
                                styles.imageListContent
                            }

                        >

                            {images.map(

                                (image, index) => (

                                    <View

                                        key={
                                            image?.id ??
                                            image?.uri ??
                                            index
                                        }

                                        style={
                                            styles.imageItem
                                        }

                                    >

                                        <Image

                                            source={{
                                                uri:
                                                    image?.uri ??
                                                    image,
                                            }}

                                            style={
                                                styles.thumbnail
                                            }

                                            resizeMode="cover"

                                        />

                                        <TouchableOpacity

                                            style={[
                                                styles.removeButton,
                                                {
                                                    backgroundColor:
                                                        colors.error ??
                                                        "#DC2626",
                                                },
                                            ]}

                                            onPress={() =>
                                                handleRemoveImage(index)
                                            }

                                            activeOpacity={0.7}

                                            accessibilityRole="button"

                                            accessibilityLabel="Remove photo"

                                        >

                                            <Text
                                                style={
                                                    styles.removeButtonText
                                                }
                                            >

                                                ✕

                                            </Text>

                                        </TouchableOpacity>

                                    </View>

                                )

                            )}

                        </ScrollView>

                    )}

                </View>

            )}

            {/* ------------------------------------------------------------------ */}
            {/* Actions                                                           */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.actions
                }
            >

                {showCancel && (

                    <Button

                        title="Cancel"

                        variant="outline"

                        onPress={
                            handleCancel
                        }

                        style={
                            styles.cancelButton
                        }

                    />

                )}

                <Button

                    title="Submit Review"

                    onPress={
                        handleSubmit
                    }

                    disabled={
                        !isValid
                    }

                    loading={
                        loading
                    }

                    style={
                        styles.submitButton
                    }

                />

            </View>

            {/* ------------------------------------------------------------------ */}
            {/* Validation Summary                                                 */}
            {/* ------------------------------------------------------------------ */}

            {hasErrors && (

                <View
                    style={
                        styles.errorSummary
                    }
                >

                    <Text
                        style={[

                            styles.errorSummaryText,

                            {

                                color:
                                    colors.error,

                            },

                        ]}
                    >

                        Please fix the following:

                    </Text>

                    {Object.values(errors).map(

                        (error, index) => (

                            <Text
                                key={index}
                                style={[

                                    styles.errorSummaryItem,

                                    {

                                        color:
                                            colors.error,

                                    },

                                ]}
                            >

                                • {error}

                            </Text>

                        )

                    )}

                </View>

            )}

        </ScrollView>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

WriteReview.displayName =
    "WriteReview";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

WriteReview.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Initial Values                                                         */
    /* ---------------------------------------------------------------------- */

    initialRating:
        PropTypes.number,

    initialTitle:
        PropTypes.string,

    initialComment:
        PropTypes.string,

    initialImages:
        PropTypes.arrayOf(
            PropTypes.oneOfType([

                PropTypes.string,

                PropTypes.shape({

                    id:
                        PropTypes.oneOfType([

                            PropTypes.string,

                            PropTypes.number,

                        ]),

                    uri:
                        PropTypes.string,

                    name:
                        PropTypes.string,

                }),

            ])
        ),

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    title:
        PropTypes.string,

    titlePlaceholder:
        PropTypes.string,

    commentPlaceholder:
        PropTypes.string,

    maxCommentLength:
        PropTypes.number,

    showPhotos:
        PropTypes.bool,

    showCancel:
        PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    loading:
        PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onSubmit:
        PropTypes.func,

    onCancel:
        PropTypes.func,

    onAddPhoto:
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

            padding:
                theme.spacing.md,

        },

        /* ------------------------------------------------------------------ */
        /* Header                                                             */
        /* ------------------------------------------------------------------ */

        title: {

            fontSize:
                20,

            fontWeight:
                "700",

            marginBottom:
                theme.spacing.lg,

        },

        /* ------------------------------------------------------------------ */
        /* Rating                                                             */
        /* ------------------------------------------------------------------ */

        ratingContainer: {

            alignItems:
                "center",

            marginBottom:
                theme.spacing.lg,

        },

        /* ------------------------------------------------------------------ */
        /* Error Text                                                         */
        /* ------------------------------------------------------------------ */

        errorText: {

            marginTop:
                theme.spacing.xs,

            fontSize:
                13,

            fontWeight:
                "500",

        },

        /* ------------------------------------------------------------------ */
        /* Counter                                                            */
        /* ------------------------------------------------------------------ */

        counterContainer: {

            alignItems:
                "flex-end",

            marginTop:
                theme.spacing.xs,

            marginBottom:
                theme.spacing.lg,

        },

        counter: {

            fontSize:
                13,

            fontWeight:
                "500",

        },

        /* ------------------------------------------------------------------ */
        /* Photos                                                             */
        /* ------------------------------------------------------------------ */

        photosSection: {

            marginBottom:
                theme.spacing.lg,

        },

        imageList: {

            marginTop:
                theme.spacing.sm,

        },

        imageListContent: {

            paddingVertical:
                theme.spacing.xs,

        },

        imageItem: {

            position:
                "relative",

            marginRight:
                theme.spacing.sm,

            borderRadius:
                8,

            overflow:
                "hidden",

        },

        thumbnail: {

            width:
                80,

            height:
                80,

            backgroundColor:
                theme.colors.surface,

        },

        removeButton: {

            position:
                "absolute",

            top:
                4,

            right:
                4,

            width:
                22,

            height:
                22,

            borderRadius:
                11,

            justifyContent:
                "center",

            alignItems:
                "center",

        },

        removeButtonText: {

            color:
                "#FFFFFF",

            fontSize:
                10,

            fontWeight:
                "700",

        },

        /* ------------------------------------------------------------------ */
        /* Actions                                                            */
        /* ------------------------------------------------------------------ */

        actions: {

            flexDirection:
                "row",

            justifyContent:
                "space-between",

            alignItems:
                "center",

            marginTop:
                theme.spacing.sm,

            marginBottom:
                theme.spacing.md,

        },

        cancelButton: {

            flex:
                1,

            marginRight:
                theme.spacing.xs,

        },

        submitButton: {

            flex:
                1,

            marginLeft:
                theme.spacing.xs,

        },

        /* ------------------------------------------------------------------ */
        /* Error Summary                                                      */
        /* ------------------------------------------------------------------ */

        errorSummary: {

            padding:
                theme.spacing.sm,

            marginBottom:
                theme.spacing.md,

            borderRadius:
                8,

            backgroundColor:
                theme.colors.errorContainer ??
                "#FEE2E2",

        },

        errorSummaryText: {

            fontSize:
                14,

            fontWeight:
                "700",

            marginBottom:
                4,

        },

        errorSummaryItem: {

            fontSize:
                13,

            fontWeight:
                "500",

            marginTop:
                2,

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    WriteReview;