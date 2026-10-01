/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/SellerInfo.jsx         */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useMemo,
    useCallback,
} from "react";

import {
    Image,
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

import LoadingOverlay
    from "../common/LoadingOverlay";

import EmptyState
    from "../common/EmptyState";

import ErrorState
    from "../common/ErrorState";

import Rating
    from "../common/Rating";

/* -------------------------------------------------------------------------- */
/* Utility - Format Number                                                    */
/* -------------------------------------------------------------------------- */

const formatNumber =
    (num) => {

        if (!num) return "0";

        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + "M";
        }

        if (num >= 1000) {
            return (num / 1000).toFixed(1) + "K";
        }

        return num.toString();

    };

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SellerInfo = memo(({

    /* ---------------------------------------------------------------------- */
    /* Seller                                                                 */
    /* ---------------------------------------------------------------------- */

    seller = null,

    loading = false,

    error = null,

    /* ---------------------------------------------------------------------- */
    /* Visibility                                                             */
    /* ---------------------------------------------------------------------- */

    showRating = true,

    showFollowers = true,

    showResponseRate = true,

    showLocation = true,

    showMemberSince = true,

    showVisitButton = true,

    showContactButton = true,

    showFollowButton = false,

    /* ---------------------------------------------------------------------- */
    /* Labels                                                                 */
    /* ---------------------------------------------------------------------- */

    visitLabel = "Visit Store",

    contactLabel = "Contact Seller",

    followLabel = "Follow",

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onVisitStore,

    onContactSeller,

    onFollow,

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
    /* Seller Data                                                            */
    /* ---------------------------------------------------------------------- */

    const sellerData =
        useMemo(

            () => seller ?? {},

            [seller]

        );

    const {

        avatar,

        name,

        verified,

        rating,

        reviewCount,

        followers,

        responseRate,

        responseTime,

        location,

        memberSince,

    } = sellerData;

    /* ---------------------------------------------------------------------- */
    /* Computed Values                                                        */
    /* ---------------------------------------------------------------------- */

    const formattedFollowers =
        useMemo(

            () => formatNumber(followers),

            [followers]

        );

    const initial =
        useMemo(

            () => name?.charAt(0)?.toUpperCase() ?? "S",

            [name]

        );

    const avatarSource =
        useMemo(

            () => {

                if (avatar) {
                    return { uri: avatar };
                }

                // Return placeholder - you can use a local image or null
                // and let the fallback render the initials
                return null;

            },

            [avatar]

        );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleVisitStore =
        useCallback(

            () => {

                onVisitStore?.(

                    sellerData

                );

            },

            [

                sellerData,

                onVisitStore,

            ]

        );

    const handleContactSeller =
        useCallback(

            () => {

                onContactSeller?.(

                    sellerData

                );

            },

            [

                sellerData,

                onContactSeller,

            ]

        );

    const handleFollow =
        useCallback(

            () => {

                onFollow?.(

                    sellerData

                );

            },

            [

                sellerData,

                onFollow,

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

                    message="Loading seller information..."

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

                    title="Unable to load seller"

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

    if (!sellerData?.id) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                <EmptyState

                    icon="store-off"

                    title="Seller unavailable"

                    description="Seller information is currently unavailable."

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
            {/* Seller Header                                                     */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.header
                }
            >

                <View
                    style={styles.avatarContainer}
                >

                    {avatarSource ? (

                        <Image

                            source={
                                avatarSource
                            }

                            style={
                                styles.avatar
                            }

                            resizeMode="cover"

                        />

                    ) : (

                        <View
                            style={[

                                styles.avatarPlaceholder,

                                {

                                    backgroundColor:
                                        colors.primaryContainer ??
                                        "#E0E7FF",

                                },

                            ]}
                        >

                            <Text
                                style={[

                                    styles.avatarInitial,

                                    {

                                        color:
                                            colors.primary,

                                    },

                                ]}
                            >

                                {initial}

                            </Text>

                        </View>

                    )}

                </View>

                <View
                    style={
                        styles.headerContent
                    }
                >

                    <View
                        style={
                            styles.nameRow
                        }
                    >

                        <Text
                            style={[

                                styles.name,

                                {

                                    color:
                                        colors.text,

                                },

                            ]}

                            numberOfLines={1}

                        >

                            {name}

                        </Text>

                        {verified && (

                            <View
                                style={[

                                    styles.verifiedBadge,

                                    {

                                        backgroundColor:
                                            colors.success ??
                                            "#16A34A",

                                    },

                                ]}
                            >

                                <Text
                                    style={
                                        styles.verifiedText
                                    }
                                >

                                    VERIFIED

                                </Text>

                            </View>

                        )}

                    </View>

                    {showRating &&
                        typeof rating === "number" && (

                        <View
                            style={
                                styles.ratingRow
                            }
                        >

                            <Rating

                                rating={
                                    rating
                                }

                                size={
                                    16
                                }

                                readonly

                            />

                            <Text
                                style={[

                                    styles.reviewText,

                                    {

                                        color:
                                            colors.textSecondary,

                                    },

                                ]}
                            >

                                {rating.toFixed(1)}

                                {"  "}

                                ({reviewCount ?? 0} Reviews)

                            </Text>

                        </View>

                    )}

                </View>

            </View>

            <Divider
                spacing={theme.spacing.md}
            />

            {/* ------------------------------------------------------------------ */}
            {/* Seller Statistics                                                  */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.statisticsContainer
                }
            >

                {showFollowers && (

                    <View
                        style={
                            styles.statRow
                        }
                    >

                        <Text
                            style={[
                                styles.statLabel,
                                {
                                    color:
                                        colors.textSecondary,
                                },
                            ]}
                        >

                            Followers

                        </Text>

                        <Text
                            style={[
                                styles.statValue,
                                {
                                    color:
                                        colors.text,
                                },
                            ]}
                        >

                            {formattedFollowers}

                        </Text>

                    </View>

                )}

                {showResponseRate && (

                    <>

                        <View
                            style={
                                styles.statRow
                            }
                        >

                            <Text
                                style={[
                                    styles.statLabel,
                                    {
                                        color:
                                            colors.textSecondary,
                                    },
                                ]}
                            >

                                Response Rate

                            </Text>

                            <Text
                                style={[
                                    styles.statValue,
                                    {
                                        color:
                                            colors.success ??
                                            "#16A34A",
                                    },
                                ]}
                            >

                                {responseRate ?? 0}%

                            </Text>

                        </View>

                        {!!responseTime && (

                            <View
                                style={
                                    styles.statRow
                                }
                            >

                                <Text
                                    style={[
                                        styles.statLabel,
                                        {
                                            color:
                                                colors.textSecondary,
                                        },
                                    ]}
                                >

                                    Response Time

                                </Text>

                                <Text
                                    style={[
                                        styles.statValue,
                                        {
                                            color:
                                                colors.text,
                                        },
                                    ]}
                                >

                                    {responseTime}

                                </Text>

                            </View>

                        )}

                    </>

                )}

                {showLocation &&
                    !!location && (

                    <View
                        style={
                            styles.statRow
                        }
                    >

                        <Text
                            style={[
                                styles.statLabel,
                                {
                                    color:
                                        colors.textSecondary,
                                },
                            ]}
                        >

                            Location

                        </Text>

                        <Text
                            style={[
                                styles.statValue,
                                {
                                    color:
                                        colors.text,
                                },
                            ]}
                        >

                            {location}

                        </Text>

                    </View>

                )}

                {showMemberSince &&
                    !!memberSince && (

                    <View
                        style={
                            styles.statRow
                        }
                    >

                        <Text
                            style={[
                                styles.statLabel,
                                {
                                    color:
                                        colors.textSecondary,
                                },
                            ]}
                        >

                            Member Since

                        </Text>

                        <Text
                            style={[
                                styles.statValue,
                                {
                                    color:
                                        colors.text,
                                },
                            ]}
                        >

                            {memberSince}

                        </Text>

                    </View>

                )}

            </View>

            <Divider
                spacing={theme.spacing.lg}
            />

            {/* ------------------------------------------------------------------ */}
            {/* Action Buttons                                                    */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={
                    styles.actionsContainer
                }
            >

                {showVisitButton && (

                    <TouchableOpacity

                        style={[
                            styles.primaryButton,
                            {
                                backgroundColor:
                                    colors.primary,
                            },
                        ]}

                        activeOpacity={0.8}

                        onPress={
                            handleVisitStore
                        }

                        accessibilityRole="button"

                        accessibilityLabel={
                            visitLabel
                        }

                    >

                        <Text
                            style={[
                                styles.primaryButtonText,
                                {
                                    color:
                                        colors.onPrimary ??
                                        "#FFFFFF",
                                },
                            ]}
                        >

                            {visitLabel}

                        </Text>

                    </TouchableOpacity>

                )}

                {showContactButton && (

                    <TouchableOpacity

                        style={[
                            styles.secondaryButton,
                            {
                                borderColor:
                                    colors.primary,
                            },
                        ]}

                        activeOpacity={0.8}

                        onPress={
                            handleContactSeller
                        }

                        accessibilityRole="button"

                        accessibilityLabel={
                            contactLabel
                        }

                    >

                        <Text
                            style={[
                                styles.secondaryButtonText,
                                {
                                    color:
                                        colors.primary,
                                },
                            ]}
                        >

                            {contactLabel}

                        </Text>

                    </TouchableOpacity>

                )}

                {showFollowButton && (

                    <TouchableOpacity

                        style={[
                            styles.secondaryButton,
                            {
                                borderColor:
                                    colors.primary,
                            },
                        ]}

                        activeOpacity={0.8}

                        onPress={
                            handleFollow
                        }

                        accessibilityRole="button"

                        accessibilityLabel={
                            followLabel
                        }

                    >

                        <Text
                            style={[
                                styles.secondaryButtonText,
                                {
                                    color:
                                        colors.primary,
                                },
                            ]}
                        >

                            {followLabel}

                        </Text>

                    </TouchableOpacity>

                )}

            </View>

        </View>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

SellerInfo.displayName =
    "SellerInfo";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SellerInfo.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Seller                                                                 */
    /* ---------------------------------------------------------------------- */

    seller:
        PropTypes.shape({

            id:
                PropTypes.oneOfType([

                    PropTypes.string,

                    PropTypes.number,

                ]),

            name:
                PropTypes.string,

            avatar:
                PropTypes.string,

            verified:
                PropTypes.bool,

            rating:
                PropTypes.number,

            reviewCount:
                PropTypes.number,

            followers:
                PropTypes.number,

            responseRate:
                PropTypes.number,

            responseTime:
                PropTypes.string,

            location:
                PropTypes.string,

            memberSince:
                PropTypes.oneOfType([

                    PropTypes.string,

                    PropTypes.number,

                ]),

        }),

    /* ---------------------------------------------------------------------- */
    /* States                                                                 */
    /* ---------------------------------------------------------------------- */

    loading:
        PropTypes.bool,

    error:
        PropTypes.object,

    /* ---------------------------------------------------------------------- */
    /* Visibility                                                             */
    /* ---------------------------------------------------------------------- */

    showRating:
        PropTypes.bool,

    showFollowers:
        PropTypes.bool,

    showResponseRate:
        PropTypes.bool,

    showLocation:
        PropTypes.bool,

    showMemberSince:
        PropTypes.bool,

    showVisitButton:
        PropTypes.bool,

    showContactButton:
        PropTypes.bool,

    showFollowButton:
        PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* Labels                                                                 */
    /* ---------------------------------------------------------------------- */

    visitLabel:
        PropTypes.string,

    contactLabel:
        PropTypes.string,

    followLabel:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onVisitStore:
        PropTypes.func,

    onContactSeller:
        PropTypes.func,

    onFollow:
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
        /* Header                                                             */
        /* ------------------------------------------------------------------ */

        header: {

            flexDirection:
                "row",

            alignItems:
                "center",

        },

        avatarContainer: {

            width:
                72,

            height:
                72,

            borderRadius:
                36,

            overflow:
                "hidden",

        },

        avatar: {

            width:
                "100%",

            height:
                "100%",

            backgroundColor:
                theme.colors.surface,

        },

        avatarPlaceholder: {

            width:
                "100%",

            height:
                "100%",

            justifyContent:
                "center",

            alignItems:
                "center",

        },

        avatarInitial: {

            fontSize:
                28,

            fontWeight:
                "700",

        },

        headerContent: {

            flex:
                1,

            marginLeft:
                theme.spacing.md,

        },

        nameRow: {

            flexDirection:
                "row",

            alignItems:
                "center",

            flexWrap:
                "wrap",

        },

        name: {

            flex:
                1,

            fontSize:
                20,

            fontWeight:
                "700",

        },

        verifiedBadge: {

            marginLeft:
                theme.spacing.xs,

            paddingHorizontal:
                theme.spacing.xs,

            paddingVertical:
                4,

            borderRadius:
                12,

        },

        verifiedText: {

            color:
                "#FFFFFF",

            fontSize:
                10,

            fontWeight:
                "700",

        },

        ratingRow: {

            flexDirection:
                "row",

            alignItems:
                "center",

            marginTop:
                theme.spacing.xs,

        },

        reviewText: {

            marginLeft:
                theme.spacing.xs,

            fontSize:
                13,

        },

        /* ------------------------------------------------------------------ */
        /* Statistics                                                         */
        /* ------------------------------------------------------------------ */

        statisticsContainer: {

            marginTop:
                4,

        },

        statRow: {

            flexDirection:
                "row",

            justifyContent:
                "space-between",

            alignItems:
                "center",

            marginBottom:
                theme.spacing.sm,

        },

        statLabel: {

            fontSize:
                14,

            fontWeight:
                "500",

        },

        statValue: {

            fontSize:
                14,

            fontWeight:
                "600",

        },

        /* ------------------------------------------------------------------ */
        /* Actions                                                            */
        /* ------------------------------------------------------------------ */

        actionsContainer: {

            marginTop:
                4,

        },

        primaryButton: {

            height:
                48,

            borderRadius:
                12,

            justifyContent:
                "center",

            alignItems:
                "center",

            marginBottom:
                theme.spacing.sm,

        },

        primaryButtonText: {

            fontSize:
                16,

            fontWeight:
                "700",

        },

        secondaryButton: {

            height:
                48,

            borderRadius:
                12,

            borderWidth:
                1,

            justifyContent:
                "center",

            alignItems:
                "center",

            marginBottom:
                theme.spacing.sm,

        },

        secondaryButtonText: {

            fontSize:
                16,

            fontWeight:
                "600",

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    SellerInfo;