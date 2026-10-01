/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/reviews/RatingSummary.jsx      */
/* -------------------------------------------------------------------------- */

import React, { memo, useMemo } from "react";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const STAR_LEVELS = [5, 4, 3, 2, 1];

const RatingBar = ({
  star,
  count,
  percentage,
  colors,
}) => (
  <View style={styles.barRow}>
    <View style={styles.starContainer}>
      <Text
        style={[
          styles.starText,
          {
            color: colors.text,
          },
        ]}
      >
        {star}
      </Text>

      <MaterialCommunityIcons
        name="star"
        size={14}
        color="#FBBF24"
      />
    </View>

    <View
      style={[
        styles.track,
        {
          backgroundColor:
            colors.border,
        },
      ]}
    >
      <View
        style={[
          styles.progress,
          {
            width: `${percentage}%`,
            backgroundColor:
              "#FBBF24",
          },
        ]}
      />
    </View>

    <Text
      style={[
        styles.count,
        {
          color:
            colors.textSecondary,
        },
      ]}
    >
      {count}
    </Text>
  </View>
);

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const RatingSummary = memo(
  ({
    rating = 0,

    totalReviews = 0,

    distribution = {},

    recommendationRate,

    showRecommendation = true,

    style,
  }) => {
    const { colors } = theme;


    const stats = useMemo(() => {
      return STAR_LEVELS.map(
        (star) => {
          const count =
            distribution[
              star
            ] ?? 0;

          return {
            star,
            count,
            percentage:
              totalReviews >
              0
                ? (
                    (count /
                      totalReviews) *
                    100
                  ).toFixed(1)
                : 0,
          };
        }
      );
    }, [
      distribution,
      totalReviews,
    ]);

    return (
      <View
        style={[
          styles.container,
          {
            backgroundColor:
              colors.card,

            borderColor:
              colors.border,
          },
          style,
        ]}
      >
        {/* ------------------------------------------------------------ */}
        {/* Left */}
        {/* ------------------------------------------------------------ */}

        <View
          style={styles.left}
        >
          <Text
            style={[
              styles.rating,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {Number(
              rating
            ).toFixed(1)}
          </Text>

          <View
            style={
              styles.stars
            }
          >
            {Array.from({
              length: 5,
            }).map(
              (_, index) => (
                <MaterialCommunityIcons
                  key={
                    index
                  }
                  name={
                    index <
                    Math.round(
                      rating
                    )
                      ? "star"
                      : "star-outline"
                  }
                  size={20}
                  color="#FBBF24"
                />
              )
            )}
          </View>

          <Text
            style={[
              styles.reviewCount,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            {totalReviews.toLocaleString()}{" "}
            Review
            {totalReviews !==
            1
              ? "s"
              : ""}
          </Text>

          {showRecommendation &&
            recommendationRate !=
              null && (
              <View
                style={
                  styles.recommendation
                }
              >
                <MaterialCommunityIcons
                  name="thumb-up"
                  size={16}
                  color="#22C55E"
                />

                <Text
                  style={[
                    styles.recommendationText,
                  ]}
                >
                  {
                    recommendationRate
                  }
                  % recommend
                </Text>
              </View>
            )}
        </View>

        {/* ------------------------------------------------------------ */}
        {/* Right */}
        {/* ------------------------------------------------------------ */}

        <View
          style={
            styles.right
          }
        >
          {stats.map(
            (item) => (
              <RatingBar
                key={
                  item.star
                }
                star={
                  item.star
                }
                count={
                  item.count
                }
                percentage={
                  item.percentage
                }
                colors={
                  colors
                }
              />
            )
          )}
        </View>
      </View>
    );
  }
);

RatingSummary.displayName =
  "RatingSummary";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flexDirection: "row",

      borderWidth: 1,

      borderRadius: 20,

      padding: 20,

      marginBottom: 20,
    },

    left: {
      width: 120,

      alignItems: "center",

      marginRight: 20,
    },

    rating: {
      fontSize: 44,

      fontWeight: "700",
    },

    stars: {
      flexDirection: "row",

      marginTop: 8,
    },

    reviewCount: {
      marginTop: 10,

      fontSize: 13,

      textAlign: "center",
    },

    recommendation: {
      flexDirection: "row",

      alignItems: "center",

      marginTop: 12,
    },

    recommendationText: {
      marginLeft: 6,

      fontSize: 13,

      fontWeight: "600",

      color: "#22C55E",
    },

    right: {
      flex: 1,

      justifyContent:
        "center",
    },

    barRow: {
      flexDirection: "row",

      alignItems: "center",

      marginBottom: 10,
    },

    starContainer: {
      width: 36,

      flexDirection: "row",

      alignItems: "center",
    },

    starText: {
      fontWeight: "600",

      marginRight: 4,
    },

    track: {
      flex: 1,

      height: 8,

      borderRadius: 4,

      overflow: "hidden",
    },

    progress: {
      height: "100%",

      borderRadius: 4,
    },

    count: {
      width: 36,

      textAlign: "right",

      marginLeft: 10,

      fontSize: 12,
    },
  });

export default RatingSummary;