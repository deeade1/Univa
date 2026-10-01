/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/Rating.jsx              */
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
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const Rating = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Value                                                                   */
    /* ---------------------------------------------------------------------- */

    rating = 0,
    maxRating = 5,
    reviewCount = 0,

    /* ---------------------------------------------------------------------- */
    /* Behaviour                                                               */
    /* ---------------------------------------------------------------------- */

    readonly = true,
    allowHalf = true,
    interactive = false,
    onChange,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showValue = true,
    showReviewCount = true,
    showStar = true,
    size = "md", // xs | sm | md | lg | xl
    spacing = 4,

    /* ---------------------------------------------------------------------- */
    /* Colors                                                                 */
    /* ---------------------------------------------------------------------- */

    activeColor,
    inactiveColor,
    textColor,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,
    starStyle,
    textStyle,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Metrics                                                                */
    /* ---------------------------------------------------------------------- */

    const metrics = useMemo(() => {
      switch (size) {
        case "xs":
          return { icon: 12, text: 10, spacing: 2 };
        case "sm":
          return { icon: 14, text: 12, spacing: 3 };
        case "lg":
          return { icon: 20, text: 16, spacing: 6 };
        case "xl":
          return { icon: 24, text: 18, spacing: 8 };
        default:
          return { icon: 16, text: 14, spacing: 4 };
      }
    }, [size]);

    /* ---------------------------------------------------------------------- */
    /* Colors                                                                 */
    /* ---------------------------------------------------------------------- */

    const filledColor = activeColor ?? "#FBBF24";
    const emptyColor = inactiveColor ?? colors.border;
    const valueColor = textColor ?? colors.text;

    /* ---------------------------------------------------------------------- */
    /* Safe Rating                                                            */
    /* ---------------------------------------------------------------------- */

    const safeRating = useMemo(() => {
      const value = Number(rating);
      if (Number.isNaN(value)) return 0;
      return Math.max(0, Math.min(value, maxRating));
    }, [rating, maxRating]);

    /* ---------------------------------------------------------------------- */
    /* Stars Array                                                            */
    /* ---------------------------------------------------------------------- */

    const stars = useMemo(
      () => Array.from({ length: maxRating }, (_, index) => index + 1),
      [maxRating]
    );

    /* ---------------------------------------------------------------------- */
    /* Get Icon Name                                                          */
    /* ---------------------------------------------------------------------- */

    const getIconName = useCallback(
      (star) => {
        if (safeRating >= star) return "star";
        if (allowHalf && safeRating >= star - 0.5) return "star-half-full";
        return "star-outline";
      },
      [safeRating, allowHalf]
    );

    /* ---------------------------------------------------------------------- */
    /* Handle Press                                                           */
    /* ---------------------------------------------------------------------- */

    const handlePress = useCallback(
      (star) => {
        if (readonly || !interactive) return;
        onChange?.(star === safeRating ? star - 0.5 : star);
      },
      [readonly, interactive, onChange, safeRating]
    );

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <View style={[styles.container, style]}>
        {/* Stars */}
        {showStar && (
          <View style={[styles.starsContainer, starStyle]}>
            {stars.map((star) => {
              const iconName = getIconName(star);
              const isActive = iconName === "star" || iconName === "star-half-full";

              return (
                <Pressable
                  key={star}
                  disabled={readonly || !interactive}
                  hitSlop={8}
                  onPress={() => handlePress(star)}
                  style={{
                    marginRight: star === maxRating ? 0 : (spacing || metrics.spacing),
                  }}
                >
                  <MaterialCommunityIcons
                    name={iconName}
                    size={metrics.icon}
                    color={isActive ? filledColor : emptyColor}
                  />
                </Pressable>
              );
            })}
          </View>
        )}

        {/* Rating Value */}
        {showValue && (
          <Text
            style={[
              styles.rating,
              {
                fontSize: metrics.text,
                color: valueColor,
                marginLeft: showStar ? (spacing || metrics.spacing) : 0,
              },
              textStyle,
            ]}
          >
            {safeRating.toFixed(1)}
          </Text>
        )}

        {/* Review Count */}
        {showReviewCount && reviewCount > 0 && (
          <Text
            style={[
              styles.reviews,
              {
                fontSize: metrics.text - 1,
                color: colors.textSecondary,
                marginLeft: spacing || metrics.spacing,
              },
              textStyle,
            ]}
          >
            ({reviewCount})
          </Text>
        )}
      </View>
    );
  }
);

Rating.displayName = "Rating";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

Rating.propTypes = {
  // Value
  rating: PropTypes.number,
  maxRating: PropTypes.number,
  reviewCount: PropTypes.number,

  // Behaviour
  readonly: PropTypes.bool,
  allowHalf: PropTypes.bool,
  interactive: PropTypes.bool,
  onChange: PropTypes.func,

  // Display
  showValue: PropTypes.bool,
  showReviewCount: PropTypes.bool,
  showStar: PropTypes.bool,
  size: PropTypes.oneOf(["xs", "sm", "md", "lg", "xl"]),
  spacing: PropTypes.number,

  // Colors
  activeColor: PropTypes.string,
  inactiveColor: PropTypes.string,
  textColor: PropTypes.string,

  // Styling
  style: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
  starStyle: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
  textStyle: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
};

Rating.defaultProps = {
  rating: 0,
  maxRating: 5,
  reviewCount: 0,
  readonly: true,
  allowHalf: true,
  interactive: false,
  onChange: null,
  showValue: true,
  showReviewCount: true,
  showStar: true,
  size: "md",
  spacing: 4,
  activeColor: null,
  inactiveColor: null,
  textColor: null,
  style: null,
  starStyle: null,
  textStyle: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
  },
  starsContainer: {
    flexDirection: "row",
    alignItems: "center",
  },
  rating: {
    fontWeight: "600",
  },
  reviews: {
    fontWeight: "500",
  },
});

export default Rating;