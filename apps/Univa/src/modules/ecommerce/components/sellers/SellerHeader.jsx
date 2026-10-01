/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/seller/SellerHeader.jsx        */
/* -------------------------------------------------------------------------- */

import React, { memo, useCallback } from "react";
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

import SellerBadge, { SellerBadgeTypes } from "@/modules/ecommerce/components/common/SellerBadge";

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

/**
 * Formats large numbers into compact format (e.g., 12500 -> 12.5K)
 */
const formatCompactNumber = (num) => {
  if (num == null) return "0";
  
  const number = Number(num);
  if (isNaN(number)) return "0";
  
  if (number >= 1_000_000) {
    return (number / 1_000_000).toFixed(1) + "M";
  }
  if (number >= 1_000) {
    return (number / 1_000).toFixed(1) + "K";
  }
  return number.toString();
};

/**
 * Safely gets rating with fallback
 */
const getSafeRating = (rating) => {
  const num = Number(rating);
  return isNaN(num) ? 0 : num;
};

/* -------------------------------------------------------------------------- */
/* Sub-components                                                             */
/* -------------------------------------------------------------------------- */

const StatItem = memo(({ label, value }) => {
  const { colors } = theme;
  
  return (
    <View style={styles.stat}>
      <Text style={[styles.statValue, { color: colors.text }]}>
        {formatCompactNumber(value)}
      </Text>
      <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
        {label}
      </Text>
    </View>
  );
});

StatItem.displayName = "StatItem";

StatItem.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
};

StatItem.defaultProps = {
  value: 0,
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SellerHeader = memo(({
  seller,
  following = false,
  showBackButton = false,
  showMessageButton = true,
  showFollowButton = true,
  stats = null, // Custom stats array for future flexibility
  onBack,
  onMessage,
  onFollow,
  style,
}) => {
  const { colors } = theme;

  /* ---------------------------------------------------------------------- */
  /* Memoized Handlers                                                      */
  /* ---------------------------------------------------------------------- */

  const handleBack = useCallback(() => {
    onBack?.();
  }, [onBack]);

  const handleMessage = useCallback(() => {
    onMessage?.(seller);
  }, [onMessage, seller]);

  const handleFollow = useCallback(() => {
    onFollow?.(seller);
  }, [onFollow, seller]);

  /* ---------------------------------------------------------------------- */
  /* Derived Values                                                         */
  /* ---------------------------------------------------------------------- */

  // Use custom stats if provided, otherwise use default seller stats
  const displayStats = stats || [
    { label: "Products", value: seller?.products },
    { label: "Followers", value: seller?.followers },
    { label: "Sales", value: seller?.sales },
  ];

  const safeRating = getSafeRating(seller?.rating);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: colors.card,
          borderBottomColor: colors.border,
        },
        style,
      ]}
    >
      {/* -------------------------------------------------------------- */}
      {/* Top Row */}
      {/* -------------------------------------------------------------- */}

      <View style={styles.topRow}>
        {showBackButton ? (
          <Pressable
            accessible
            accessibilityRole="button"
            accessibilityLabel="Go back"
            onPress={handleBack}
            style={[
              styles.iconButton,
              { backgroundColor: colors.background },
            ]}
          >
            <MaterialCommunityIcons
              name="arrow-left"
              size={22}
              color={colors.text}
            />
          </Pressable>
        ) : (
          <View />
        )}

        <View style={styles.actionRow}>
          {showMessageButton && (
            <Pressable
              accessible
              accessibilityRole="button"
              accessibilityLabel={`Message ${seller?.name || "seller"}`}
              onPress={handleMessage}
              style={[
                styles.iconButton,
                { backgroundColor: colors.background },
              ]}
            >
              <MaterialCommunityIcons
                name="message-outline"
                size={22}
                color={colors.primary}
              />
            </Pressable>
          )}

          {showFollowButton && (
            <Pressable
              accessible
              accessibilityRole="button"
              accessibilityLabel={
                following 
                  ? `Unfollow ${seller?.name || "seller"}`
                  : `Follow ${seller?.name || "seller"}`
              }
              onPress={handleFollow}
              style={[
                styles.followButton,
                {
                  backgroundColor: following ? colors.background : colors.primary,
                  borderColor: colors.primary,
                },
              ]}
            >
              <MaterialCommunityIcons
                name={
                  following
                    ? "account-check-outline"
                    : "account-plus-outline"
                }
                size={18}
                color={following ? colors.primary : colors.white}
              />

              <Text
                style={[
                  styles.followText,
                  {
                    color: following ? colors.primary : colors.white,
                  },
                ]}
              >
                {following ? "Following" : "Follow"}
              </Text>
            </Pressable>
          )}
        </View>
      </View>

      {/* -------------------------------------------------------------- */}
      {/* Seller Profile */}
      {/* -------------------------------------------------------------- */}

      <Image
        source={
          seller?.avatar
            ? { uri: seller.avatar }
            : require("../../../assets/images/avatar-placeholder.png")
        }
        style={styles.avatar}
      />

      <View style={styles.nameRow}>
        <Text
          numberOfLines={1}
          style={[
            styles.name,
            { color: colors.text },
          ]}
        >
          {seller?.name ?? "Seller"}
        </Text>

        {/* ✅ Use SellerBadge component for consistency */}
        {seller?.verified && (
          <SellerBadge
            verified={seller.verified}
            size={20}
            style={{ marginLeft: 6 }}
          />
        )}
      </View>

      {seller?.tagline && (
        <Text
          style={[
            styles.tagline,
            { color: colors.textSecondary },
          ]}
        >
          {seller.tagline}
        </Text>
      )}

      <View style={styles.locationRow}>
        <MaterialCommunityIcons
          name="map-marker-outline"
          size={16}
          color={colors.textSecondary}
        />

        <Text
          style={[
            styles.location,
            { color: colors.textSecondary },
          ]}
        >
          {seller?.location ?? "Unknown location"}
        </Text>
      </View>

      {/* -------------------------------------------------------------- */}
      {/* Rating */}
      {/* -------------------------------------------------------------- */}

      <View style={styles.ratingRow}>
        <MaterialCommunityIcons
          name="star"
          size={18}
          color={colors.warning || "#FBBF24"}
        />

        <Text
          style={[
            styles.rating,
            { color: colors.text },
          ]}
        >
          {safeRating.toFixed(1)}
        </Text>

        <Text
          style={[
            styles.reviewCount,
            { color: colors.textSecondary },
          ]}
        >
          ({formatCompactNumber(seller?.reviewCount ?? 0)} reviews)
        </Text>
      </View>

      {/* -------------------------------------------------------------- */}
      {/* Statistics */}
      {/* -------------------------------------------------------------- */}

      <View
        style={[
          styles.stats,
          { borderTopColor: colors.border },
        ]}
      >
        {displayStats.map((stat, index) => (
          <StatItem
            key={index}
            label={stat.label}
            value={stat.value}
          />
        ))}
      </View>
    </View>
  );
});

SellerHeader.displayName = "SellerHeader";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SellerHeader.propTypes = {
  /**
   * Seller object containing profile information
   */
  seller: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    name: PropTypes.string,
    avatar: PropTypes.string,
    tagline: PropTypes.string,
    location: PropTypes.string,
    rating: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    reviewCount: PropTypes.number,
    products: PropTypes.number,
    followers: PropTypes.number,
    sales: PropTypes.number,
    verified: PropTypes.bool,
  }),

  /**
   * Whether the current user is following this seller
   */
  following: PropTypes.bool,

  /**
   * Show back button in header
   */
  showBackButton: PropTypes.bool,

  /**
   * Show message button
   */
  showMessageButton: PropTypes.bool,

  /**
   * Show follow button
   */
  showFollowButton: PropTypes.bool,

  /**
   * Custom stats configuration for flexibility
   */
  stats: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    })
  ),

  /**
   * Back button handler
   */
  onBack: PropTypes.func,

  /**
   * Message button handler
   */
  onMessage: PropTypes.func,

  /**
   * Follow button handler
   */
  onFollow: PropTypes.func,

  /**
   * Optional style overrides
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

SellerHeader.defaultProps = {
  seller: null,
  following: false,
  showBackButton: false,
  showMessageButton: true,
  showFollowButton: true,
  stats: null,
  onBack: () => {},
  onMessage: () => {},
  onFollow: () => {},
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 24,
    borderBottomWidth: 1,
  },

  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 24,
  },

  actionRow: {
    flexDirection: "row",
    alignItems: "center",
  },

  iconButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    justifyContent: "center",
    alignItems: "center",
  },

  followButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 12,
    paddingHorizontal: 18,
    height: 42,
    borderRadius: 21,
    borderWidth: 1.5,
  },

  followText: {
    marginLeft: 6,
    fontWeight: "700",
    fontSize: 14,
  },

  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    alignSelf: "center",
    backgroundColor: "#E5E7EB",
  },

  nameRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 18,
  },

  name: {
    fontSize: 24,
    fontWeight: "700",
  },

  tagline: {
    marginTop: 8,
    textAlign: "center",
    fontSize: 15,
    lineHeight: 22,
  },

  locationRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 10,
  },

  location: {
    marginLeft: 4,
    fontSize: 14,
  },

  ratingRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 16,
  },

  rating: {
    marginLeft: 6,
    fontSize: 17,
    fontWeight: "700",
  },

  reviewCount: {
    marginLeft: 8,
    fontSize: 14,
  },

  stats: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginTop: 24,
    paddingTop: 20,
    borderTopWidth: 1,
  },

  stat: {
    alignItems: "center",
  },

  statValue: {
    fontSize: 22,
    fontWeight: "700",
  },

  statLabel: {
    marginTop: 4,
    fontSize: 13,
  },
});

export default SellerHeader;