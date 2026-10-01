/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ReviewCard.jsx          */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  Image,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import Rating from "./Rating";
import Avatar from "./Avatar";
import Badge from "./Badge";

/* -------------------------------------------------------------------------- */
/* Utility - Format Date                                                      */
/* -------------------------------------------------------------------------- */

const formatDate = (dateString) => {
  if (!dateString) return null;

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;

    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateString;
  }
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ReviewCard = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Review                                                                 */
    /* ---------------------------------------------------------------------- */

    review,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showProduct = false,
    showImages = true,
    showVerified = true,
    showHelpful = true,
    showReport = false,
    showReply = true,
    compact = false,

    /* ---------------------------------------------------------------------- */
    /* Labels                                                                 */
    /* ---------------------------------------------------------------------- */

    helpfulLabel = "Helpful",
    reportLabel = "Report",
    sellerReplyTitle = "Seller Response",

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
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Review Data                                                            */
    /* ---------------------------------------------------------------------- */

    const {
      id,
      avatar,
      reviewer,
      name,
      user,
      verified,
      rating = 0,
      title,
      comment,
      helpfulCount = 0,
      createdAt,
      images: reviewImages = [],
      reply,
      sellerReply,
      product: reviewProduct,
    } = review ?? {};

    /* ---------------------------------------------------------------------- */
    /* Computed Values                                                        */
    /* ---------------------------------------------------------------------- */

    const reviewerName = useMemo(
      () => reviewer ?? user?.name ?? name ?? "Anonymous",
      [reviewer, user, name]
    );

    const reviewerAvatar = useMemo(
      () => avatar ?? user?.avatar ?? null,
      [avatar, user]
    );

    const isVerified = useMemo(
      () => verified ?? user?.verified ?? false,
      [verified, user]
    );

    const formattedDate = useMemo(
      () => formatDate(createdAt),
      [createdAt]
    );

    const hasSellerReply = useMemo(
      () => Boolean(reply ?? sellerReply?.message),
      [reply, sellerReply]
    );

    const sellerReplyMessage = useMemo(
      () => reply ?? sellerReply?.message ?? null,
      [reply, sellerReply]
    );

    const sellerReplyDate = useMemo(
      () => formatDate(sellerReply?.createdAt),
      [sellerReply]
    );

    const productName = useMemo(
      () => reviewProduct?.name ?? reviewProduct ?? null,
      [reviewProduct]
    );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handlePress = useCallback(() => {
      onPress?.(review);
    }, [onPress, review]);

    const handleHelpful = useCallback(() => {
      onHelpful?.(review);
    }, [onHelpful, review]);

    const handleReport = useCallback(() => {
      onReport?.(review);
    }, [onReport, review]);

    /* ---------------------------------------------------------------------- */
    /* Render Helper - Stars                                                  */
    /* ---------------------------------------------------------------------- */

    const renderStars = useCallback(() => {
      return Array.from({ length: 5 }).map((_, index) => (
        <MaterialCommunityIcons
          key={index}
          name={index < rating ? "star" : "star-outline"}
          size={compact ? 14 : 16}
          color="#FBBF24"
          style={styles.star}
        />
      ));
    }, [rating, compact]);

    /* ---------------------------------------------------------------------- */
    /* Render Helper - Images                                                 */
    /* ---------------------------------------------------------------------- */

    const renderReviewImages = useCallback(() => {
      if (!showImages || !reviewImages?.length) return null;

      const imagesToShow = reviewImages.slice(0, 4);

      return (
        <View style={styles.imagesRow}>
          {imagesToShow.map((image, index) => (
            <Image
              key={index}
              source={{ uri: typeof image === "string" ? image : image?.url }}
              style={styles.image}
            />
          ))}
          {reviewImages.length > 4 && (
            <View style={[styles.image, styles.moreImages]}>
              <Text style={styles.moreImagesText}>
                +{reviewImages.length - 4}
              </Text>
            </View>
          )}
        </View>
      );
    }, [reviewImages, showImages]);

    /* ---------------------------------------------------------------------- */
    /* Render Helper - Seller Reply                                           */
    /* ---------------------------------------------------------------------- */

    const renderSellerReply = useCallback(() => {
      if (!showReply || !hasSellerReply) return null;

      return (
        <View
          style={[
            styles.reply,
            {
              backgroundColor: colors.background ?? colors.surfaceVariant,
            },
          ]}
        >
          <Text
            style={[
              styles.replyTitle,
              {
                color: colors.primary,
              },
            ]}
          >
            {sellerReplyTitle}
          </Text>

          <Text
            style={[
              styles.replyText,
              {
                color: colors.textSecondary,
              },
            ]}
          >
            {sellerReplyMessage}
          </Text>

          {sellerReplyDate && (
            <Text
              style={[
                styles.replyDate,
                {
                  color: colors.textSecondary,
                },
              ]}
            >
              {sellerReplyDate}
            </Text>
          )}
        </View>
      );
    }, [
      showReply,
      hasSellerReply,
      sellerReplyMessage,
      sellerReplyDate,
      sellerReplyTitle,
      colors,
    ]);

    /* ---------------------------------------------------------------------- */
    /* Render Helper - Actions                                                */
    /* ---------------------------------------------------------------------- */

    const renderActions = useCallback(() => {
      if (!showHelpful && !showReport) return null;

      return (
        <View style={styles.actions}>
          {showHelpful && (
            <Pressable
              onPress={handleHelpful}
              style={styles.actionButton}
              accessibilityRole="button"
              accessibilityLabel={`Mark review as ${helpfulLabel.toLowerCase()}`}
            >
              <MaterialCommunityIcons
                name="thumb-up-outline"
                size={18}
                color={colors.primary}
              />
              <Text
                style={[
                  styles.actionText,
                  {
                    color: colors.primary,
                  },
                ]}
              >
                {helpfulLabel} ({helpfulCount})
              </Text>
            </Pressable>
          )}

          {showReport && (
            <Pressable
              onPress={handleReport}
              style={styles.actionButton}
              accessibilityRole="button"
              accessibilityLabel={`${reportLabel} this review`}
            >
              <MaterialCommunityIcons
                name="flag-outline"
                size={18}
                color={colors.error}
              />
              <Text
                style={[
                  styles.actionText,
                  {
                    color: colors.error,
                  },
                ]}
              >
                {reportLabel}
              </Text>
            </Pressable>
          )}
        </View>
      );
    }, [
      showHelpful,
      showReport,
      helpfulCount,
      helpfulLabel,
      reportLabel,
      colors,
      handleHelpful,
      handleReport,
    ]);

    /* ---------------------------------------------------------------------- */
    /* Main Render                                                            */
    /* ---------------------------------------------------------------------- */

    return (
      <Pressable
        disabled={!onPress}
        onPress={handlePress}
        style={[
          styles.container,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
          compact && styles.compactContainer,
          style,
        ]}
        accessibilityRole="button"
        accessibilityLabel={`Review by ${reviewerName}`}
      >
        {/* -------------------------------------------------------------- */}
        {/* Header                                                         */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.header}>
          <View style={styles.userSection}>
            <Avatar
              source={reviewerAvatar ? { uri: reviewerAvatar } : undefined}
              name={reviewerName}
              size={compact ? 40 : 50}
            />

            <View style={styles.userInfo}>
              <View style={styles.nameRow}>
                <Text
                  style={[
                    styles.name,
                    {
                      color: colors.text,
                    },
                    compact && styles.compactName,
                  ]}
                  numberOfLines={1}
                >
                  {reviewerName}
                </Text>

                {showVerified && isVerified && (
                  <Badge
                    label="Verified"
                    variant="success"
                    size="small"
                    style={styles.verifiedBadge}
                  />
                )}
              </View>

              <View style={styles.ratingRow}>
                {renderStars()}
                {formattedDate && (
                  <Text
                    style={[
                      styles.date,
                      {
                        color: colors.textSecondary,
                      },
                    ]}
                  >
                    {formattedDate}
                  </Text>
                )}
              </View>
            </View>
          </View>
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Product                                                        */}
        {/* -------------------------------------------------------------- */}

        {showProduct && productName && (
          <Text
            style={[
              styles.product,
              {
                color: colors.primary,
              },
            ]}
          >
            {productName}
          </Text>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Title                                                          */}
        {/* -------------------------------------------------------------- */}

        {!!title && (
          <Text
            style={[
              styles.title,
              {
                color: colors.text,
              },
              compact && styles.compactTitle,
            ]}
          >
            {title}
          </Text>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Comment                                                        */}
        {/* -------------------------------------------------------------- */}

        <Text
          style={[
            styles.comment,
            {
              color: colors.textSecondary,
            },
            compact && styles.compactComment,
          ]}
          numberOfLines={compact ? 3 : undefined}
        >
          {comment}
        </Text>

        {/* -------------------------------------------------------------- */}
        {/* Images                                                         */}
        {/* -------------------------------------------------------------- */}

        {renderReviewImages()}

        {/* -------------------------------------------------------------- */}
        {/* Seller Reply                                                   */}
        {/* -------------------------------------------------------------- */}

        {renderSellerReply()}

        {/* -------------------------------------------------------------- */}
        {/* Footer / Actions                                               */}
        {/* -------------------------------------------------------------- */}

        {renderActions()}
      </Pressable>
    );
  }
);

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ReviewCard.displayName = "ReviewCard";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const reviewPropType = PropTypes.shape({
  id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  avatar: PropTypes.string,
  reviewer: PropTypes.string,
  name: PropTypes.string,
  user: PropTypes.shape({
    name: PropTypes.string,
    avatar: PropTypes.string,
    verified: PropTypes.bool,
  }),
  verified: PropTypes.bool,
  rating: PropTypes.number,
  title: PropTypes.string,
  comment: PropTypes.string,
  helpfulCount: PropTypes.number,
  createdAt: PropTypes.string,
  images: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.shape({
        url: PropTypes.string,
      }),
    ])
  ),
  reply: PropTypes.string,
  sellerReply: PropTypes.shape({
    message: PropTypes.string,
    createdAt: PropTypes.string,
  }),
  product: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.shape({
      name: PropTypes.string,
    }),
  ]),
});

ReviewCard.propTypes = {
  review: reviewPropType.isRequired,

  // Display
  showProduct: PropTypes.bool,
  showImages: PropTypes.bool,
  showVerified: PropTypes.bool,
  showHelpful: PropTypes.bool,
  showReport: PropTypes.bool,
  showReply: PropTypes.bool,
  compact: PropTypes.bool,

  // Labels
  helpfulLabel: PropTypes.string,
  reportLabel: PropTypes.string,
  sellerReplyTitle: PropTypes.string,

  // Events
  onPress: PropTypes.func,
  onHelpful: PropTypes.func,
  onReport: PropTypes.func,

  // Styling
  style: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ReviewCard.defaultProps = {
  showProduct: false,
  showImages: true,
  showVerified: true,
  showHelpful: true,
  showReport: false,
  showReply: true,
  compact: false,
  helpfulLabel: "Helpful",
  reportLabel: "Report",
  sellerReplyTitle: "Seller Response",
  onPress: null,
  onHelpful: null,
  onReport: null,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  /* ------------------------------------------------------------------ */
  /* Container                                                          */
  /* ------------------------------------------------------------------ */

  container: {
    borderWidth: 1,
    borderRadius: 20,
    padding: 18,
    marginBottom: 16,
  },

  compactContainer: {
    padding: 14,
  },

  /* ------------------------------------------------------------------ */
  /* Header                                                             */
  /* ------------------------------------------------------------------ */

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },

  userSection: {
    flexDirection: "row",
    flex: 1,
  },

  userInfo: {
    flex: 1,
    marginLeft: 12,
  },

  nameRow: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 8,
  },

  name: {
    fontSize: 16,
    fontWeight: "700",
  },

  compactName: {
    fontSize: 14,
  },

  verifiedBadge: {
    marginLeft: 4,
  },

  ratingRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 4,
  },

  star: {
    marginRight: 2,
  },

  date: {
    marginLeft: 8,
    fontSize: 12,
  },

  /* ------------------------------------------------------------------ */
  /* Product                                                            */
  /* ------------------------------------------------------------------ */

  product: {
    marginTop: 16,
    fontWeight: "700",
    fontSize: 14,
  },

  /* ------------------------------------------------------------------ */
  /* Review Content                                                     */
  /* ------------------------------------------------------------------ */

  title: {
    marginTop: 10,
    fontSize: 17,
    fontWeight: "700",
  },

  compactTitle: {
    fontSize: 15,
  },

  comment: {
    marginTop: 10,
    fontSize: 15,
    lineHeight: 24,
  },

  compactComment: {
    fontSize: 14,
    lineHeight: 22,
  },

  /* ------------------------------------------------------------------ */
  /* Images                                                             */
  /* ------------------------------------------------------------------ */

  imagesRow: {
    flexDirection: "row",
    marginTop: 16,
  },

  image: {
    width: 74,
    height: 74,
    borderRadius: 12,
    marginRight: 10,
    backgroundColor: "#F3F4F6",
  },

  moreImages: {
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,0.5)",
  },

  moreImagesText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },

  /* ------------------------------------------------------------------ */
  /* Seller Reply                                                       */
  /* ------------------------------------------------------------------ */

  reply: {
    marginTop: 18,
    padding: 14,
    borderRadius: 14,
  },

  replyTitle: {
    fontWeight: "700",
    marginBottom: 6,
    fontSize: 14,
  },

  replyText: {
    lineHeight: 22,
    fontSize: 14,
  },

  replyDate: {
    marginTop: 6,
    fontSize: 12,
  },

  /* ------------------------------------------------------------------ */
  /* Actions                                                            */
  /* ------------------------------------------------------------------ */

  actions: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 18,
  },

  actionButton: {
    flexDirection: "row",
    alignItems: "center",
    marginRight: 20,
  },

  actionText: {
    marginLeft: 6,
    fontWeight: "600",
    fontSize: 14,
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default ReviewCard;