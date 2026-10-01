/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/seller/SellerPolicies.jsx      */
/* -------------------------------------------------------------------------- */

import React, { memo, useCallback, useMemo } from "react";
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
/* Default Policies                                                           */
/* -------------------------------------------------------------------------- */

const DEFAULT_POLICIES = [
  {
    key: "shipping",
    title: "Shipping",
    icon: "truck-fast-outline",
  },
  {
    key: "returns",
    title: "Returns",
    icon: "backup-restore",
  },
  {
    key: "refund",
    title: "Refund Policy",
    icon: "cash-refund",
  },
  {
    key: "warranty",
    title: "Warranty",
    icon: "shield-check-outline",
  },
  {
    key: "support",
    title: "Customer Support",
    icon: "headset",
  },
];

/* -------------------------------------------------------------------------- */
/* Policy Item                                                                */
/* -------------------------------------------------------------------------- */

const PolicyItem = memo(({
  icon,
  title,
  value,
  colors,
  onPress,
  isLast = false,
  hideEmpty = false,
}) => {
  // If hideEmpty is true and value is empty, don't render
  if (hideEmpty && !value) {
    return null;
  }

  const handlePress = useCallback(() => {
    onPress?.();
  }, [onPress]);

  const displayValue = value || "Not specified";

  return (
    <Pressable
      accessible
      accessibilityRole={onPress ? "button" : "text"}
      accessibilityLabel={`${title}: ${displayValue}`}
      disabled={!onPress}
      onPress={handlePress}
      style={[
        styles.policyItem,
        !isLast && {
          borderBottomWidth: StyleSheet.hairlineWidth,
          borderBottomColor: colors.border,
        },
        onPress && styles.clickable,
      ]}
    >
      <View style={styles.left}>
        {/* ✅ Icon is now rendered! */}
        <MaterialCommunityIcons
          name={icon}
          size={22}
          color={colors.primary}
        />

        <View style={styles.content}>
          <Text
            style={[
              styles.title,
              { color: colors.text },
            ]}
          >
            {title}
          </Text>

          <Text
            style={[
              styles.value,
              { color: colors.textSecondary },
            ]}
          >
            {displayValue}
          </Text>
        </View>
      </View>

      {/* ✅ Chevron only shown when clickable */}
      {onPress && (
        <MaterialCommunityIcons
          name="chevron-right"
          size={22}
          color={colors.textSecondary}
        />
      )}
    </Pressable>
  );
});

PolicyItem.displayName = "PolicyItem";

PolicyItem.propTypes = {
  icon: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
  value: PropTypes.string,
  colors: PropTypes.object.isRequired,
  onPress: PropTypes.func,
  isLast: PropTypes.bool,
  hideEmpty: PropTypes.bool,
};

PolicyItem.defaultProps = {
  value: null,
  onPress: null,
  isLast: false,
  hideEmpty: false,
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SellerPolicies = memo(({
  seller = {},
  policies = DEFAULT_POLICIES,
  showHeader = true,
  headerIcon = "file-document-outline",
  headerTitle = "Seller Policies",
  onPolicyPress,
  hideEmptyPolicies = false,
  expandable = false,
  style,
}) => {
  const { colors } = theme;

  /* ---------------------------------------------------------------------- */
  /* Memoized Handlers                                                      */
  /* ---------------------------------------------------------------------- */

  const handlePolicyPress = useCallback((policy) => {
    onPolicyPress?.(policy, seller);
  }, [onPolicyPress, seller]);

  /* ---------------------------------------------------------------------- */
  /* Memoized Policies                                                      */
  /* ---------------------------------------------------------------------- */

  const displayPolicies = useMemo(() => {
    // If policies are provided as objects with value, use them directly
    if (policies.length > 0 && 'value' in policies[0]) {
      return policies;
    }

    // Otherwise build from seller data using DEFAULT_POLICIES config
    return DEFAULT_POLICIES.map((policy) => ({
      ...policy,
      value: seller?.[policy.key] || null,
    }));
  }, [policies, seller]);

  // Filter out empty policies if hideEmptyPolicies is true
  const filteredPolicies = useMemo(() => {
    if (!hideEmptyPolicies) return displayPolicies;
    return displayPolicies.filter((policy) => policy.value);
  }, [displayPolicies, hideEmptyPolicies]);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  if (filteredPolicies.length === 0) {
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
      {showHeader && (
        <View style={[
          styles.header,
          {
            borderBottomColor: colors.border,
          },
        ]}>
          <MaterialCommunityIcons
            name={headerIcon}
            size={22}
            color={colors.primary}
          />

          <Text
            style={[
              styles.headerTitle,
              { color: colors.text },
            ]}
          >
            {headerTitle}
          </Text>
        </View>
      )}

      {filteredPolicies.map((policy, index) => (
        <PolicyItem
          key={policy.key || index}
          icon={policy.icon}
          title={policy.title}
          value={policy.value}
          colors={colors}
          onPress={expandable ? () => handlePolicyPress(policy) : null}
          isLast={index === filteredPolicies.length - 1}
          hideEmpty={hideEmptyPolicies}
        />
      ))}
    </View>
  );
});

SellerPolicies.displayName = "SellerPolicies";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SellerPolicies.propTypes = {
  /**
   * Seller object containing policy values
   */
  seller: PropTypes.shape({
    shipping: PropTypes.string,
    returns: PropTypes.string,
    refund: PropTypes.string,
    warranty: PropTypes.string,
    support: PropTypes.string,
  }),

  /**
   * Custom policies array with full control
   */
  policies: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string,
      title: PropTypes.string.isRequired,
      icon: PropTypes.string.isRequired,
      value: PropTypes.string,
    })
  ),

  /**
   * Show the header section
   */
  showHeader: PropTypes.bool,

  /**
   * Custom header icon name
   */
  headerIcon: PropTypes.string,

  /**
   * Custom header title
   */
  headerTitle: PropTypes.string,

  /**
   * Called when a policy is pressed (requires expandable)
   */
  onPolicyPress: PropTypes.func,

  /**
   * Hide policies with empty values
   */
  hideEmptyPolicies: PropTypes.bool,

  /**
   * Enable expandable policies (shows chevron and makes clickable)
   */
  expandable: PropTypes.bool,

  /**
   * Optional style overrides
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

SellerPolicies.defaultProps = {
  seller: {},
  policies: DEFAULT_POLICIES,
  showHeader: true,
  headerIcon: "file-document-outline",
  headerTitle: "Seller Policies",
  onPolicyPress: null,
  hideEmptyPolicies: false,
  expandable: false,
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

  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 18,
    paddingVertical: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },

  headerTitle: {
    marginLeft: 10,
    fontSize: 18,
    fontWeight: "700",
  },

  policyItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 18,
    paddingVertical: 16,
  },

  clickable: {
    opacity: 0.9,
  },

  left: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
  },

  content: {
    marginLeft: 14,
    flex: 1,
  },

  title: {
    fontSize: 15,
    fontWeight: "600",
  },

  value: {
    marginTop: 4,
    fontSize: 13,
    lineHeight: 18,
  },
});

export default SellerPolicies;