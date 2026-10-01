/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/WishlistHeader.jsx    */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
  useMemo,
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

const WishlistHeader = memo(
  ({
    title = "My Wishlist",
    subtitle = null,

    itemCount = 0,

    showBack = false,
    showSearch = true,
    showShare = true,
    showFilter = true,

    onBack,
    onSearch,
    onShare,
    onFilter,

    rightComponent = null,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Memoized Values                                                        */
    /* ---------------------------------------------------------------------- */

    const countLabel = useMemo(() => {
      return `${itemCount} ${
        itemCount === 1 ? "item" : "items"
      }`;
    }, [itemCount]);

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleBack = useCallback(() => {
      onBack?.();
    }, [onBack]);

    const handleSearch = useCallback(() => {
      onSearch?.();
    }, [onSearch]);

    const handleShare = useCallback(() => {
      onShare?.();
    }, [onShare]);

    const handleFilter = useCallback(() => {
      onFilter?.();
    }, [onFilter]);

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,
          style,
        ]}
      >
        {/* ---------------------------------------------------------------- */}
        {/* Top Row                                                          */}
        {/* ---------------------------------------------------------------- */}

        <View style={styles.topRow}>
          <View style={styles.leftSection}>
            {showBack && (
              <Pressable
                accessible
                accessibilityRole="button"
                accessibilityLabel="Go back"
                onPress={handleBack}
                style={[
                  styles.iconButton,
                  {
                    backgroundColor:
                      colors.card,
                    borderColor:
                      colors.border,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name="arrow-left"
                  size={22}
                  color={colors.text}
                />
              </Pressable>
            )}

            <View style={styles.titleContainer}>
              <Text
                numberOfLines={1}
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

              <Text
                style={[
                  styles.count,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                {countLabel}
              </Text>
            </View>
          </View>

          {/* -------------------------------------------------------------- */}
          {/* Right Actions                                                  */}
          {/* -------------------------------------------------------------- */}

          {rightComponent || (
            <View style={styles.actions}>
              {showSearch && (
                <Pressable
                  accessible
                  accessibilityRole="button"
                  accessibilityLabel="Search wishlist"
                  onPress={
                    handleSearch
                  }
                  style={[
                    styles.iconButton,
                    {
                      backgroundColor:
                        colors.card,
                      borderColor:
                        colors.border,
                    },
                  ]}
                >
                  <MaterialCommunityIcons
                    name="magnify"
                    size={22}
                    color={colors.text}
                  />
                </Pressable>
              )}

              {showFilter && (
                <Pressable
                  accessible
                  accessibilityRole="button"
                  accessibilityLabel="Filter wishlist"
                  onPress={
                    handleFilter
                  }
                  style={[
                    styles.iconButton,
                    {
                      backgroundColor:
                        colors.card,
                      borderColor:
                        colors.border,
                    },
                  ]}
                >
                  <MaterialCommunityIcons
                    name="tune-variant"
                    size={22}
                    color={colors.text}
                  />
                </Pressable>
              )}

              {showShare && (
                <Pressable
                  accessible
                  accessibilityRole="button"
                  accessibilityLabel="Share wishlist"
                  onPress={
                    handleShare
                  }
                  style={[
                    styles.iconButton,
                    {
                      backgroundColor:
                        colors.card,
                      borderColor:
                        colors.border,
                    },
                  ]}
                >
                  <MaterialCommunityIcons
                    name="share-variant"
                    size={22}
                    color={colors.text}
                  />
                </Pressable>
              )}
            </View>
          )}
        </View>

        {/* ---------------------------------------------------------------- */}
        {/* Subtitle                                                         */}
        {/* ---------------------------------------------------------------- */}

        {!!subtitle && (
          <Text
            style={[
              styles.subtitle,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            {subtitle}
          </Text>
        )}
      </View>
    );
  }
);

WishlistHeader.displayName =
  "WishlistHeader";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

WishlistHeader.propTypes = {
  title: PropTypes.string,

  subtitle: PropTypes.string,

  itemCount: PropTypes.number,

  showBack: PropTypes.bool,

  showSearch: PropTypes.bool,

  showShare: PropTypes.bool,

  showFilter: PropTypes.bool,

  onBack: PropTypes.func,

  onSearch: PropTypes.func,

  onShare: PropTypes.func,

  onFilter: PropTypes.func,

  rightComponent: PropTypes.node,

  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

WishlistHeader.defaultProps = {
  title: "My Wishlist",

  subtitle: null,

  itemCount: 0,

  showBack: false,

  showSearch: true,

  showShare: true,

  showFilter: true,

  onBack: null,

  onSearch: null,

  onShare: null,

  onFilter: null,

  rightComponent: null,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    marginBottom: 20,
  },

  topRow: {
    flexDirection: "row",

    justifyContent:
      "space-between",

    alignItems: "center",
  },

  leftSection: {
    flex: 1,

    flexDirection: "row",

    alignItems: "center",
  },

  titleContainer: {
    flex: 1,

    marginLeft: 12,
  },

  title: {
    fontSize: 28,

    fontWeight: "700",
  },

  count: {
    marginTop: 4,

    fontSize: 14,

    fontWeight: "500",
  },

  subtitle: {
    marginTop: 12,

    fontSize: 15,

    lineHeight: 22,
  },

  actions: {
    flexDirection: "row",

    alignItems: "center",
  },

  iconButton: {
    width: 42,

    height: 42,

    borderRadius: 21,

    borderWidth: 1,

    justifyContent:
      "center",

    alignItems: "center",

    marginLeft: 10,
  },
});

export default WishlistHeader;