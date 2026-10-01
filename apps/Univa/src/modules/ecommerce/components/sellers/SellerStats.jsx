/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/seller/SellerStats.jsx         */
/* -------------------------------------------------------------------------- */

import React, { memo, useMemo } from "react";
import PropTypes from "prop-types";

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

const StatItem = memo(({
  icon,
  color,
  value,
  label,
  showDivider = false,
  dividerColor,
  accessibilityLabel,
}) => {
  const { colors } = theme;

  return (
    <View
      accessible
      accessibilityRole="text"
      accessibilityLabel={accessibilityLabel || `${label}: ${value}`}
      style={[
        styles.item,
        showDivider && {
          borderRightWidth: 1,
          borderRightColor: dividerColor || colors.border,
        },
      ]}
    >
      <MaterialCommunityIcons
        name={icon}
        size={22}
        color={color}
      />

      <Text
        style={[
          styles.value,
          { color: colors.text },
        ]}
      >
        {value}
      </Text>

      <Text
        style={[
          styles.label,
          { color: colors.textSecondary },
        ]}
      >
        {label}
      </Text>
    </View>
  );
});

StatItem.displayName = "StatItem";

StatItem.propTypes = {
  icon: PropTypes.string.isRequired,
  color: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  label: PropTypes.string.isRequired,
  showDivider: PropTypes.bool,
  dividerColor: PropTypes.string,
  accessibilityLabel: PropTypes.string,
};

StatItem.defaultProps = {
  showDivider: false,
  dividerColor: null,
  accessibilityLabel: null,
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SellerStats = memo(({
  seller = {},
  stats = null, // Custom stats for flexibility
  columns = 3, // Number of columns per row
  showRating = true,
  showProducts = true,
  showFollowers = true,
  showSales = true,
  showResponseRate = true,
  showResponseTime = true,
  showDividers = true,
  compact = false,
  style,
}) => {
  const { colors } = theme;

  /* ---------------------------------------------------------------------- */
  /* Build Stats with useMemo                                               */
  /* ---------------------------------------------------------------------- */

  const displayStats = useMemo(() => {
    // If custom stats are provided, use them
    if (stats) {
      return stats.map((stat) => ({
        key: stat.key || stat.label.toLowerCase().replace(/\s+/g, '_'),
        ...stat,
      }));
    }

    // Otherwise build from seller data
    const builtStats = [];

    if (showRating) {
      builtStats.push({
        key: "rating",
        icon: "star",
        color: colors.warning || "#FBBF24",
        value: getSafeRating(seller?.rating).toFixed(1),
        label: "Rating",
        accessibilityLabel: `Rating ${getSafeRating(seller?.rating).toFixed(1)} out of 5`,
      });
    }

    if (showProducts) {
      builtStats.push({
        key: "products",
        icon: "package-variant",
        color: colors.info || "#3B82F6",
        value: compact 
          ? formatCompactNumber(seller?.products)
          : seller?.products ?? 0,
        label: "Products",
        accessibilityLabel: `${seller?.products ?? 0} products`,
      });
    }

    if (showFollowers) {
      builtStats.push({
        key: "followers",
        icon: "account-group-outline",
        color: colors.purple || "#8B5CF6",
        value: compact 
          ? formatCompactNumber(seller?.followers)
          : seller?.followers ?? 0,
        label: "Followers",
        accessibilityLabel: `${seller?.followers ?? 0} followers`,
      });
    }

    if (showSales) {
      builtStats.push({
        key: "sales",
        icon: "cart-check",
        color: colors.success || "#10B981",
        value: compact 
          ? formatCompactNumber(seller?.sales)
          : seller?.sales ?? 0,
        label: "Sales",
        accessibilityLabel: `${seller?.sales ?? 0} sales`,
      });
    }

    if (showResponseRate) {
      builtStats.push({
        key: "responseRate",
        icon: "chat-processing",
        color: colors.warning || "#F97316",
        value: `${seller?.responseRate ?? 0}%`,
        label: "Response",
        accessibilityLabel: `${seller?.responseRate ?? 0}% response rate`,
      });
    }

    if (showResponseTime) {
      builtStats.push({
        key: "responseTime",
        icon: "clock-outline",
        color: colors.cyan || "#06B6D4",
        value: seller?.responseTime ?? "--",
        label: "Avg Reply",
        accessibilityLabel: `Average reply time ${seller?.responseTime ?? '--'}`,
      });
    }

    return builtStats;
  }, [
    stats,
    seller,
    showRating,
    showProducts,
    showFollowers,
    showSales,
    showResponseRate,
    showResponseTime,
    compact,
    colors,
  ]);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  if (displayStats.length === 0) {
    return null;
  }

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: colors.card,
          borderColor: colors.border,
        },
        style,
      ]}
    >
      <View style={[
        styles.grid,
        { flexWrap: columns > 1 ? 'wrap' : 'nowrap' }
      ]}>
        {displayStats.map((item, index) => (
          <StatItem
            key={item.key}
            icon={item.icon}
            color={item.color}
            value={item.value}
            label={item.label}
            showDivider={showDividers && index < displayStats.length - 1}
            dividerColor={colors.border}
            accessibilityLabel={item.accessibilityLabel}
          />
        ))}
      </View>
    </View>
  );
});

SellerStats.displayName = "SellerStats";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SellerStats.propTypes = {
  /**
   * Seller object containing statistics
   */
  seller: PropTypes.shape({
    rating: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    products: PropTypes.number,
    followers: PropTypes.number,
    sales: PropTypes.number,
    responseRate: PropTypes.number,
    responseTime: PropTypes.string,
  }),

  /**
   * Custom stats array for flexibility
   */
  stats: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string,
      icon: PropTypes.string.isRequired,
      color: PropTypes.string.isRequired,
      value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      label: PropTypes.string.isRequired,
      accessibilityLabel: PropTypes.string,
    })
  ),

  /**
   * Number of columns per row
   */
  columns: PropTypes.number,

  /**
   * Show rating stat
   */
  showRating: PropTypes.bool,

  /**
   * Show products stat
   */
  showProducts: PropTypes.bool,

  /**
   * Show followers stat
   */
  showFollowers: PropTypes.bool,

  /**
   * Show sales stat
   */
  showSales: PropTypes.bool,

  /**
   * Show response rate stat
   */
  showResponseRate: PropTypes.bool,

  /**
   * Show response time stat
   */
  showResponseTime: PropTypes.bool,

  /**
   * Show dividers between stats
   */
  showDividers: PropTypes.bool,

  /**
   * Compact mode (formats numbers with K/M)
   */
  compact: PropTypes.bool,

  /**
   * Optional style overrides
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

SellerStats.defaultProps = {
  seller: {},
  stats: null,
  columns: 3,
  showRating: true,
  showProducts: true,
  showFollowers: true,
  showSales: true,
  showResponseRate: true,
  showResponseTime: true,
  showDividers: true,
  compact: false,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderRadius: 18,
    overflow: "hidden",
    marginVertical: 16,
  },

  grid: {
    flexDirection: "row",
  },

  item: {
    flex: 1,
    paddingVertical: 18,
    paddingHorizontal: 8,
    alignItems: "center",
    justifyContent: "center",
    minWidth: 60, // Ensures items don't get too small
  },

  value: {
    marginTop: 10,
    fontSize: 18,
    fontWeight: "700",
    textAlign: "center",
  },

  label: {
    marginTop: 4,
    fontSize: 12,
    textAlign: "center",
  },
});

export default SellerStats;