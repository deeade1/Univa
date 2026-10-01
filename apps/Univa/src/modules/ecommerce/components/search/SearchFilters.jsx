/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchFilters.jsx       */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
} from "react-native";

import {
  MaterialCommunityIcons,
} from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */

const DEFAULT_SORT_OPTIONS = [
  {
    label: "Relevance",
    value: "relevance",
  },
  {
    label: "Newest",
    value: "newest",
  },
  {
    label: "Price ↑",
    value: "price_asc",
  },
  {
    label: "Price ↓",
    value: "price_desc",
  },
  {
    label: "Rating",
    value: "rating",
  },
];

/* -------------------------------------------------------------------------- */

const RATINGS = [
  5,
  4,
  3,
  2,
  1,
];

/* -------------------------------------------------------------------------- */

const SearchFilters = memo(
  ({
    categories = [],

    brands = [],

    selectedCategory,

    selectedBrand,

    selectedRating,

    sortBy = "relevance",

    inStock = false,

    featuredOnly = false,

    onCategoryChange,

    onBrandChange,

    onRatingChange,

    onSortChange,

    onStockChange,

    onFeaturedChange,

    onReset,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const sortOptions =
      useMemo(
        () =>
          DEFAULT_SORT_OPTIONS,
        []
      );

    /* ---------------------------------------------------------------------- */

    const renderChip =
      useCallback(
        ({
          label,
          selected,
          onPress,
          icon,
        }) => (
          <Pressable
            key={label}
            onPress={onPress}
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
            {icon && (
              <MaterialCommunityIcons
                name={icon}
                size={16}
                color={
                  selected
                    ? "#FFF"
                    : colors.textSecondary
                }
                style={
                  styles.icon
                }
              />
            )}

            <Text
              style={{
                color:
                  selected
                    ? "#FFF"
                    : colors.text,

                fontWeight:
                  selected
                    ? "700"
                    : "500",
              }}
            >
              {label}
            </Text>
          </Pressable>
        ),
        [colors]
      );

    /* ---------------------------------------------------------------------- */

    return (
      <ScrollView
        style={[
          styles.container,
          style,
        ]}
        showsVerticalScrollIndicator={
          false
        }
      >
        {/* -------------------------------------------------------------- */}
        {/* Header */}
        {/* -------------------------------------------------------------- */}

        <View
          style={
            styles.header
          }
        >
          <Text
            style={[
              styles.title,
              {
                color:
                  colors.text,
              },
            ]}
          >
            Filters
          </Text>

          <Pressable
            onPress={onReset}
          >
            <Text
              style={{
                color:
                  colors.primary,

                fontWeight:
                  "700",
              }}
            >
              Reset
            </Text>
          </Pressable>
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Categories */}
        {/* -------------------------------------------------------------- */}

        <Text
          style={[
            styles.sectionTitle,
            {
              color:
                colors.text,
            },
          ]}
        >
          Categories
        </Text>

        <View
          style={
            styles.chips
          }
        >
          {categories.map(
            (
              category
            ) =>
              renderChip({
                label:
                  category.name,
                selected:
                  selectedCategory ===
                  category.id,
                onPress:
                  () =>
                    onCategoryChange?.(
                      category.id
                    ),
              })
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Brands */}
        {/* -------------------------------------------------------------- */}

        {!!brands.length && (
          <>
            <Text
              style={[
                styles.sectionTitle,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              Brands
            </Text>

            <View
              style={
                styles.chips
              }
            >
              {brands.map(
                (
                  brand
                ) =>
                  renderChip({
                    label:
                      brand.name,
                    selected:
                      selectedBrand ===
                      brand.id,
                    onPress:
                      () =>
                        onBrandChange?.(
                          brand.id
                        ),
                    icon:
                      "tag-outline",
                  })
              )}
            </View>
          </>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Rating */}
        {/* -------------------------------------------------------------- */}

        <Text
          style={[
            styles.sectionTitle,
            {
              color:
                colors.text,
            },
          ]}
        >
          Minimum Rating
        </Text>

        <View
          style={
            styles.chips
          }
        >
          {RATINGS.map(
            (
              rating
            ) =>
              renderChip({
                label: `${rating}★`,

                selected:
                  selectedRating ===
                  rating,

                onPress:
                  () =>
                    onRatingChange?.(
                      rating
                    ),

                icon:
                  "star",
              })
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Sort */}
        {/* -------------------------------------------------------------- */}

        <Text
          style={[
            styles.sectionTitle,
            {
              color:
                colors.text,
            },
          ]}
        >
          Sort By
        </Text>

        <View
          style={
            styles.chips
          }
        >
          {sortOptions.map(
            (
              option
            ) =>
              renderChip({
                label:
                  option.label,

                selected:
                  sortBy ===
                  option.value,

                onPress:
                  () =>
                    onSortChange?.(
                      option.value
                    ),

                icon:
                  "sort",
              })
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Toggles */}
        {/* -------------------------------------------------------------- */}

        <View
          style={[
            styles.row,
            {
              borderTopColor:
                colors.border,
            },
          ]}
        >
          <Text
            style={[
              styles.rowTitle,
              {
                color:
                  colors.text,
              },
            ]}
          >
            In Stock Only
          </Text>

          <Switch
            value={
              inStock
            }
            onValueChange={
              onStockChange
            }
            trackColor={{
              true: colors.primary,
            }}
          />
        </View>

        <View
          style={[
            styles.row,
            {
              borderTopColor:
                colors.border,
            },
          ]}
        >
          <Text
            style={[
              styles.rowTitle,
              {
                color:
                  colors.text,
              },
            ]}
          >
            Featured Products
          </Text>

          <Switch
            value={
              featuredOnly
            }
            onValueChange={
              onFeaturedChange
            }
            trackColor={{
              true: colors.primary,
            }}
          />
        </View>
      </ScrollView>
    );
  }
);

/* -------------------------------------------------------------------------- */

SearchFilters.displayName =
  "SearchFilters";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flex: 1,
    },

    header: {
      flexDirection:
        "row",

      justifyContent:
        "space-between",

      alignItems:
        "center",

      marginBottom: 24,
    },

    title: {
      fontSize: 22,

      fontWeight: "700",
    },

    sectionTitle: {
      fontSize: 16,

      fontWeight: "700",

      marginBottom: 12,

      marginTop: 20,
    },

    chips: {
      flexDirection:
        "row",

      flexWrap:
        "wrap",
    },

    chip: {
      flexDirection:
        "row",

      alignItems:
        "center",

      borderWidth: 1,

      borderRadius: 24,

      paddingHorizontal: 14,

      paddingVertical: 10,

      marginRight: 10,

      marginBottom: 10,
    },

    icon: {
      marginRight: 6,
    },

    row: {
      flexDirection:
        "row",

      justifyContent:
        "space-between",

      alignItems:
        "center",

      paddingVertical: 18,

      borderTopWidth:
        StyleSheet.hairlineWidth,
    },

    rowTitle: {
      fontSize: 15,

      fontWeight: "500",
    },
  });

/* -------------------------------------------------------------------------- */

export default SearchFilters;