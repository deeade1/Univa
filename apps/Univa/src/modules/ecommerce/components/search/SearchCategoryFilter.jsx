/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchCategoryFilter.jsx */
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
  FlatList,
  Pressable,
  StyleSheet,
} from "react-native";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Default Categories                                                         */
/* -------------------------------------------------------------------------- */

export const DEFAULT_CATEGORIES = [
  {
    id: "all",
    label: "All",
  },
  {
    id: "phones",
    label: "Phones",
  },
  {
    id: "fashion",
    label: "Fashion",
  },
  {
    id: "electronics",
    label: "Electronics",
  },
  {
    id: "beauty",
    label: "Beauty",
  },
  {
    id: "groceries",
    label: "Groceries",
  },
  {
    id: "furniture",
    label: "Furniture",
  },
];

/* -------------------------------------------------------------------------- */
/* Category Chip                                                              */
/* -------------------------------------------------------------------------- */

const CategoryChip = memo(
  ({
    item,
    selected,
    onPress,
  }) => {
    const { colors } = theme;

    const handlePress =
      useCallback(() => {
        onPress?.(item);
      }, [
        item,
        onPress,
      ]);

    return (
      <Pressable
        accessibilityRole="button"
        accessibilityState={{
          selected,
        }}
        accessibilityLabel={
          item.label
        }
        onPress={
          handlePress
        }
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
        <Text
          style={[
            styles.chipText,
            {
              color:
                selected
                  ? colors.white
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

CategoryChip.displayName =
  "CategoryChip";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SearchCategoryFilter =
  memo(
    ({
      categories =
        DEFAULT_CATEGORIES,

      selectedCategory =
        "all",

      contentContainerStyle,

      style,

      onSelect,
    }) => {
      const data =
        useMemo(
          () =>
            categories ??
            DEFAULT_CATEGORIES,
          [categories]
        );

      const renderItem =
        useCallback(
          ({ item }) => (
            <CategoryChip
              item={item}
              selected={
                item.id ===
                selectedCategory
              }
              onPress={
                onSelect
              }
            />
          ),
          [
            selectedCategory,
            onSelect,
          ]
        );

      const keyExtractor =
        useCallback(
          (item) =>
            item.id.toString(),
          []
        );

      return (
        <View
          style={[
            styles.container,
            style,
          ]}
        >
          <FlatList
            horizontal
            data={data}
            renderItem={
              renderItem
            }
            keyExtractor={
              keyExtractor
            }
            showsHorizontalScrollIndicator={
              false
            }
            contentContainerStyle={[
              styles.content,
              contentContainerStyle,
            ]}
          />
        </View>
      );
    }
  );

SearchCategoryFilter.displayName =
  "SearchCategoryFilter";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SearchCategoryFilter.propTypes =
  {
    /**
     * Category list.
     */
    categories:
      PropTypes.arrayOf(
        PropTypes.shape({
          id:
            PropTypes.oneOfType(
              [
                PropTypes.string,
                PropTypes.number,
              ]
            )
              .isRequired,

          label:
            PropTypes.string
              .isRequired,
        })
      ),

    /**
     * Active category id.
     */
    selectedCategory:
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
      ]),

    /**
     * Called when
     * category changes.
     */
    onSelect:
      PropTypes.func,

    /**
     * Style overrides.
     */
    style:
      PropTypes.oneOfType([
        PropTypes.object,
        PropTypes.array,
      ]),

    contentContainerStyle:
      PropTypes.oneOfType([
        PropTypes.object,
        PropTypes.array,
      ]),
  };

SearchCategoryFilter.defaultProps =
  {
    categories:
      DEFAULT_CATEGORIES,

    selectedCategory:
      "all",

    onSelect: null,

    style: null,

    contentContainerStyle:
      null,
  };

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      marginTop: 12,
    },

    content: {
      paddingHorizontal: 16,
      paddingVertical: 4,
    },

    chip: {
      minHeight: 40,

      paddingHorizontal: 18,

      borderRadius: 999,

      borderWidth: 1,

      justifyContent:
        "center",

      alignItems:
        "center",

      marginRight: 12,
    },

    chipText: {
      fontSize: 14,

      fontWeight: "600",
    },
  });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default SearchCategoryFilter;