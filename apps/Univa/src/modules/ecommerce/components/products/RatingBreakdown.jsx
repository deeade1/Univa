/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/RatingBreakdown.jsx     */
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
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import Rating from "./Rating";
import ProgressBar from "./ProgressBar";
import LoadingOverlay from "./LoadingOverlay";
import EmptyState from "./EmptyState";
import ErrorState from "./ErrorState";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const RatingBreakdown = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Header                                                                 */
    /* ---------------------------------------------------------------------- */

    title = "Customer Ratings",

    /* ---------------------------------------------------------------------- */
    /* Rating                                                                 */
    /* ---------------------------------------------------------------------- */

    averageRating = 0,
    totalReviews = 0,
    breakdown = {},

    /* ---------------------------------------------------------------------- */
    /* Interactive Features                                                   */
    /* ---------------------------------------------------------------------- */

    interactive = false,
    selectedRating = null,
    showClearFilter = true,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showAverage = true,
    showProgressBars = true,
    compact = false,

    /* ---------------------------------------------------------------------- */
    /* States                                                                 */
    /* ---------------------------------------------------------------------- */

    loading = false,
    error = null,

    /* ---------------------------------------------------------------------- */
    /* Labels                                                                 */
    /* ---------------------------------------------------------------------- */

    emptyTitle = "No Ratings Yet",
    emptyDescription = "Ratings will appear once customers start reviewing this product.",
    clearFilterLabel = "Clear Filter",

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onSelectRating,
    onRetry,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,
  }) => {
    const { colors, spacing } = theme;

    /* ---------------------------------------------------------------------- */
    /* Rating Distribution                                                    */
    /* ---------------------------------------------------------------------- */

    const ratingRows = useMemo(
      () =>
        [5, 4, 3, 2, 1].map((star) => {
          const count = breakdown?.[star] ?? 0;
          const percentage = totalReviews > 0 ? (count / totalReviews) * 100 : 0;
          return { star, count, percentage };
        }),
      [breakdown, totalReviews]
    );

    const hasRatings = useMemo(() => totalReviews > 0, [totalReviews]);

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleSelectRating = useCallback(
      (star) => {
        if (!interactive) return;
        const newRating = selectedRating === star ? null : star;
        onSelectRating?.(newRating);
      },
      [interactive, selectedRating, onSelectRating]
    );

    const handleClearFilter = useCallback(() => {
      onSelectRating?.(null);
    }, [onSelectRating]);

    /* ---------------------------------------------------------------------- */
    /* Loading State                                                          */
    /* ---------------------------------------------------------------------- */

    if (loading) {
      return (
        <View style={[styles.container, style]}>
          <LoadingOverlay
            visible
            fullscreen={false}
            transparent
            message="Loading rating breakdown..."
          />
        </View>
      );
    }

    /* ---------------------------------------------------------------------- */
    /* Error State                                                            */
    /* ---------------------------------------------------------------------- */

    if (error) {
      return (
        <View style={[styles.container, style]}>
          <ErrorState
            title="Unable to load ratings"
            description={error?.message ?? "Please try again."}
            onRetry={onRetry}
          />
        </View>
      );
    }

    /* ---------------------------------------------------------------------- */
    /* Empty State                                                            */
    /* ---------------------------------------------------------------------- */

    if (!hasRatings) {
      return (
        <View style={[styles.container, style]}>
          <EmptyState
            icon="star-outline"
            title={emptyTitle}
            description={emptyDescription}
          />
        </View>
      );
    }

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <View style={[styles.container, style]}>
        {/* Title */}
        <Text
          style={[
            styles.title,
            {
              color: colors.text,
            },
          ]}
        >
          {title}
        </Text>

        {/* Average Rating Summary */}
        {showAverage && (
          <View style={styles.summaryContainer}>
            <Text
              style={[
                styles.averageRating,
                {
                  color: colors.text,
                },
              ]}
            >
              {Number(averageRating).toFixed(1)}
            </Text>

            <Rating
              rating={averageRating}
              readonly
              size="lg"
              showReviewCount={false}
            />

            <Text
              style={[
                styles.reviewCount,
                {
                  color: colors.textSecondary,
                },
              ]}
            >
              {totalReviews.toLocaleString()} {totalReviews === 1 ? "Review" : "Reviews"}
            </Text>
          </View>
        )}

        {/* Rating Distribution */}
        {showProgressBars && (
          <View style={styles.breakdownContainer}>
            {ratingRows.map(({ star, count, percentage }) => {
              const isSelected = interactive && selectedRating === star;
              const hasCount = count > 0;

              return (
                <Pressable
                  key={star}
                  style={[
                    styles.breakdownRow,
                    interactive && {
                      opacity: isSelected ? 1 : 0.7,
                    },
                    interactive && hasCount && {
                      paddingVertical: spacing?.xs ?? 4,
                    },
                  ]}
                  onPress={() => handleSelectRating(star)}
                  disabled={!interactive || !hasCount}
                  activeOpacity={0.7}
                  accessibilityRole="button"
                  accessibilityLabel={`Filter by ${star} star reviews`}
                  accessibilityState={{
                    selected: isSelected,
                    disabled: !hasCount,
                  }}
                >
                  {/* Star Label */}
                  <View style={styles.starContainer}>
                    <Text
                      style={[
                        styles.starText,
                        {
                          color: isSelected ? colors.primary : colors.text,
                        },
                      ]}
                    >
                      {star}★
                    </Text>
                  </View>

                  {/* Progress Bar */}
                  <View style={styles.progressContainer}>
                    <ProgressBar
                      progress={percentage / 100}
                      color={isSelected ? colors.primary : colors.primary}
                      height={compact ? 6 : 8}
                      animated
                    />
                  </View>

                  {/* Review Count */}
                  <Text
                    style={[
                      styles.countText,
                      {
                        color: isSelected ? colors.primary : colors.textSecondary,
                      },
                    ]}
                  >
                    {count.toLocaleString()}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        )}

        {/* Clear Filter Button */}
        {interactive && selectedRating !== null && showClearFilter && (
          <Pressable
            onPress={handleClearFilter}
            activeOpacity={0.7}
            style={styles.clearFilterButton}
            accessibilityRole="button"
            accessibilityLabel={clearFilterLabel}
          >
            <Text
              style={[
                styles.clearFilterText,
                {
                  color: colors.primary,
                },
              ]}
            >
              {clearFilterLabel}
            </Text>
          </Pressable>
        )}
      </View>
    );
  }
);

RatingBreakdown.displayName = "RatingBreakdown";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

RatingBreakdown.propTypes = {
  // Header
  title: PropTypes.string,

  // Rating
  averageRating: PropTypes.number,
  totalReviews: PropTypes.number,
  breakdown: PropTypes.shape({
    1: PropTypes.number,
    2: PropTypes.number,
    3: PropTypes.number,
    4: PropTypes.number,
    5: PropTypes.number,
  }),

  // Interactive Features
  interactive: PropTypes.bool,
  selectedRating: PropTypes.number,
  showClearFilter: PropTypes.bool,

  // Display
  showAverage: PropTypes.bool,
  showProgressBars: PropTypes.bool,
  compact: PropTypes.bool,

  // States
  loading: PropTypes.bool,
  error: PropTypes.object,

  // Labels
  emptyTitle: PropTypes.string,
  emptyDescription: PropTypes.string,
  clearFilterLabel: PropTypes.string,

  // Events
  onSelectRating: PropTypes.func,
  onRetry: PropTypes.func,

  // Styling
  style: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
};

RatingBreakdown.defaultProps = {
  title: "Customer Ratings",
  averageRating: 0,
  totalReviews: 0,
  breakdown: {},
  interactive: false,
  selectedRating: null,
  showClearFilter: true,
  showAverage: true,
  showProgressBars: true,
  compact: false,
  loading: false,
  error: null,
  emptyTitle: "No Ratings Yet",
  emptyDescription: "Ratings will appear once customers start reviewing this product.",
  clearFilterLabel: "Clear Filter",
  onSelectRating: null,
  onRetry: null,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 16,
    paddingVertical: 16,
  },

  /* ------------------------------------------------------------------ */
  /* Header                                                             */
  /* ------------------------------------------------------------------ */

  title: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 16,
  },

  /* ------------------------------------------------------------------ */
  /* Summary                                                            */
  /* ------------------------------------------------------------------ */

  summaryContainer: {
    alignItems: "center",
    marginBottom: 16,
  },

  averageRating: {
    fontSize: 40,
    fontWeight: "700",
    marginBottom: 4,
  },

  reviewCount: {
    marginTop: 4,
    fontSize: 14,
  },

  /* ------------------------------------------------------------------ */
  /* Breakdown                                                          */
  /* ------------------------------------------------------------------ */

  breakdownContainer: {
    width: "100%",
  },

  breakdownRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },

  starContainer: {
    width: 40,
  },

  starText: {
    fontSize: 14,
    fontWeight: "600",
  },

  progressContainer: {
    flex: 1,
    marginHorizontal: 8,
  },

  countText: {
    width: 50,
    textAlign: "right",
    fontSize: 13,
    fontWeight: "500",
  },

  /* ------------------------------------------------------------------ */
  /* Clear Filter                                                       */
  /* ------------------------------------------------------------------ */

  clearFilterButton: {
    alignSelf: "center",
    marginTop: 12,
    paddingVertical: 6,
    paddingHorizontal: 16,
  },

  clearFilterText: {
    fontSize: 14,
    fontWeight: "600",
  },
});

export default RatingBreakdown;