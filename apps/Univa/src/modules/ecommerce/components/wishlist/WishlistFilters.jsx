/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/WishlistFilters.jsx   */
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
  ScrollView,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Default Filters                                                            */
/* -------------------------------------------------------------------------- */

export const DEFAULT_FILTERS = [
  {
    key: "all",
    label: "All",
    icon: "view-grid-outline",
  },
  {
    key: "in-stock",
    label: "In Stock",
    icon: "check-circle-outline",
  },
  {
    key: "sale",
    label: "On Sale",
    icon: "sale",
  },
  {
    key: "new",
    label: "New",
    icon: "star-outline",
  },
  {
    key: "free-shipping",
    label: "Free Shipping",
    icon: "truck-fast-outline",
  },
];

/* -------------------------------------------------------------------------- */
/* Filter Chip                                                                */
/* -------------------------------------------------------------------------- */

const FilterChip = memo(
  ({
    item,
    selected,
    onPress,
  }) => {
    const { colors } = theme;

    const handlePress =
      useCallback(() => {
        onPress?.(item);
      }, [item, onPress]);

    return (
      <Pressable
        accessible
        accessibilityRole="button"
        accessibilityState={{
          selected,
        }}
        accessibilityLabel={
          item.label
        }
        onPress={handlePress}
        style={[
          styles.chip,
          {
            backgroundColor:
              selected
                ? colors.primary
                : colors.card,

            borderColor:
              selected
                ? colors.primary
                : colors.border,
          },
        ]}
      >
        {!!item.icon && (
          <MaterialCommunityIcons
            name={item.icon}
            size={16}
            color={
              selected
                ? colors.white ||
                  "#FFFFFF"
                : colors.textSecondary
            }
          />
        )}

        <Text
          style={[
            styles.chipText,
            {
              color: selected
                ? colors.white ||
                  "#FFFFFF"
                : colors.text,
            },
          ]}
        >
          {item.label}
        </Text>
      </Pressable>
    );
  }
);

FilterChip.displayName =
  "FilterChip";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const WishlistFilters = memo(
  ({
    filters =
      DEFAULT_FILTERS,

    selected = "all",

    showTitle = false,

    title = "Filters",

    showClear = false,

    clearLabel = "Clear",

    onChange,

    onClear,

    style,
  }) => {
    const { colors } = theme;

    const data = useMemo(
      () => filters ?? [],
      [filters]
    );

    const handleSelect =
      useCallback(
        (item) => {
          onChange?.(item);
        },
        [onChange]
      );

    const handleClear =
      useCallback(() => {
        onClear?.();
      }, [onClear]);

    return (
      <View
        style={[
          styles.container,
          style,
        ]}
      >
        {(showTitle ||
          showClear) && (
          <View
            style={
              styles.header
            }
          >
            {showTitle && (
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
            )}

            {showClear && (
              <Pressable
                onPress={
                  handleClear
                }
              >
                <Text
                  style={[
                    styles.clearText,
                    {
                      color:
                        colors.primary,
                    },
                  ]}
                >
                  {clearLabel}
                </Text>
              </Pressable>
            )}
          </View>
        )}

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={
            false
          }
          contentContainerStyle={
            styles.scrollContent
          }
        >
          {data.map(
            (item) => (
              <FilterChip
                key={
                  item.key
                }
                item={item}
                selected={
                  selected ===
                  item.key
                }
                onPress={
                  handleSelect
                }
              />
            )
          )}
        </ScrollView>
      </View>
    );
  }
);

WishlistFilters.displayName =
  "WishlistFilters";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

WishlistFilters.propTypes =
  {
    filters:
      PropTypes.arrayOf(
        PropTypes.shape({
          key:
            PropTypes.string
              .isRequired,

          label:
            PropTypes.string
              .isRequired,

          icon:
            PropTypes.string,
        })
      ),

    selected:
      PropTypes.string,

    showTitle:
      PropTypes.bool,

    title:
      PropTypes.string,

    showClear:
      PropTypes.bool,

    clearLabel:
      PropTypes.string,

    onChange:
      PropTypes.func,

    onClear:
      PropTypes.func,

    style:
      PropTypes.oneOfType(
        [
          PropTypes.object,
          PropTypes.array,
        ]
      ),
  };

WishlistFilters.defaultProps =
  {
    filters:
      DEFAULT_FILTERS,

    selected: "all",

    showTitle: false,

    title: "Filters",

    showClear: false,

    clearLabel:
      "Clear",

    onChange: null,

    onClear: null,

    style: null,
  };

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      marginBottom: 20,
    },

    header: {
      flexDirection:
        "row",

      justifyContent:
        "space-between",

      alignItems:
        "center",

      marginBottom: 12,
    },

    title: {
      fontSize: 18,

      fontWeight: "700",
    },

    clearText: {
      fontSize: 14,

      fontWeight: "600",
    },

    scrollContent: {
      paddingRight: 16,
    },

    chip: {
      flexDirection:
        "row",

      alignItems:
        "center",

      borderWidth: 1,

      borderRadius: 999,

      paddingHorizontal: 16,

      height: 42,

      marginRight: 10,
    },

    chipText: {
      marginLeft: 8,

      fontSize: 14,

      fontWeight: "600",
    },
  });

export default WishlistFilters;






