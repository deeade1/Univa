/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchSortSheet.jsx     */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  Modal,
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Default Sort Options                                                       */
/* -------------------------------------------------------------------------- */

export const SEARCH_SORT_OPTIONS = [
  {
    id: "relevance",
    label: "Most Relevant",
    icon: "star-circle-outline",
  },
  {
    id: "newest",
    label: "Newest",
    icon: "clock-outline",
  },
  {
    id: "price_low",
    label: "Price: Low → High",
    icon: "sort-ascending",
  },
  {
    id: "price_high",
    label: "Price: High → Low",
    icon: "sort-descending",
  },
  {
    id: "rating",
    label: "Highest Rated",
    icon: "star-outline",
  },
  {
    id: "popular",
    label: "Most Popular",
    icon: "fire",
  },
  {
    id: "discount",
    label: "Biggest Discount",
    icon: "sale",
  },
];

/* -------------------------------------------------------------------------- */
/* Sort Item                                                                  */
/* -------------------------------------------------------------------------- */

const SortItem = memo(
  ({
    option,
    selected,
    onPress,
  }) => {
    const { colors } = theme;

    const handlePress =
      useCallback(() => {
        onPress?.(option);
      }, [option, onPress]);

    return (
      <Pressable
        accessibilityRole="button"
        accessibilityState={{
          selected,
        }}
        onPress={handlePress}
        style={[
          styles.option,
          {
            backgroundColor:
              selected
                ? colors.primary + "12"
                : "transparent",
          },
        ]}
      >
        <MaterialCommunityIcons
          name={option.icon}
          size={22}
          color={
            selected
              ? colors.primary
              : colors.textSecondary
          }
        />

        <Text
          style={[
            styles.optionText,
            {
              color:
                selected
                  ? colors.primary
                  : colors.text,
            },
          ]}
        >
          {option.label}
        </Text>

        {selected && (
          <MaterialCommunityIcons
            name="check-circle"
            size={22}
            color={
              colors.primary
            }
          />
        )}
      </Pressable>
    );
  }
);

SortItem.displayName =
  "SortItem";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SearchSortSheet = memo(
  ({
    visible = false,

    selectedSort =
      "relevance",

    options =
      SEARCH_SORT_OPTIONS,

    title =
      "Sort Results",

    closeOnSelect = true,

    onSelect,

    onClose,
  }) => {
    const { colors } = theme;

    const data =
      useMemo(
        () =>
          options ??
          SEARCH_SORT_OPTIONS,
        [options]
      );

    const handleSelect =
      useCallback(
        (option) => {
          onSelect?.(option);

          if (
            closeOnSelect
          ) {
            onClose?.();
          }
        },
        [
          onSelect,
          onClose,
          closeOnSelect,
        ]
      );

    return (
      <Modal
        visible={visible}
        animationType="slide"
        transparent
        onRequestClose={
          onClose
        }
      >
        {/* Overlay */}

        <Pressable
          style={
            styles.overlay
          }
          onPress={
            onClose
          }
        />

        {/* Sheet */}

        <View
          style={[
            styles.sheet,
            {
              backgroundColor:
                colors.card,
            },
          ]}
        >
          {/* Handle */}

          <View
            style={[
              styles.handle,
              {
                backgroundColor:
                  colors.border,
              },
            ]}
          />

          {/* Header */}

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
              {title}
            </Text>

            <Pressable
              onPress={
                onClose
              }
            >
              <MaterialCommunityIcons
                name="close"
                size={24}
                color={
                  colors.text
                }
              />
            </Pressable>
          </View>

          {/* Options */}

          <ScrollView
            showsVerticalScrollIndicator={
              false
            }
          >
            {data.map(
              (option) => (
                <SortItem
                  key={
                    option.id
                  }
                  option={
                    option
                  }
                  selected={
                    option.id ===
                    selectedSort
                  }
                  onPress={
                    handleSelect
                  }
                />
              )
            )}
          </ScrollView>
        </View>
      </Modal>
    );
  }
);

SearchSortSheet.displayName =
  "SearchSortSheet";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SearchSortSheet.propTypes = {
  visible:
    PropTypes.bool,

  selectedSort:
    PropTypes.string,

  title:
    PropTypes.string,

  closeOnSelect:
    PropTypes.bool,

  options:
    PropTypes.arrayOf(
      PropTypes.shape({
        id:
          PropTypes.string
            .isRequired,

        label:
          PropTypes.string
            .isRequired,

        icon:
          PropTypes.string,
      })
    ),

  onSelect:
    PropTypes.func,

  onClose:
    PropTypes.func,
};

SearchSortSheet.defaultProps =
  {
    visible: false,

    selectedSort:
      "relevance",

    title:
      "Sort Results",

    closeOnSelect: true,

    options:
      SEARCH_SORT_OPTIONS,

    onSelect: null,

    onClose: null,
  };

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    overlay: {
      flex: 1,

      backgroundColor:
        "rgba(0,0,0,0.35)",
    },

    sheet: {
      maxHeight: "70%",

      borderTopLeftRadius: 24,

      borderTopRightRadius: 24,

      paddingHorizontal: 20,

      paddingTop: 14,

      paddingBottom: 32,
    },

    handle: {
      width: 54,

      height: 5,

      borderRadius: 3,

      alignSelf: "center",

      marginBottom: 18,
    },

    header: {
      flexDirection: "row",

      alignItems: "center",

      justifyContent:
        "space-between",

      marginBottom: 16,
    },

    title: {
      fontSize: 20,

      fontWeight: "700",
    },

    option: {
      flexDirection: "row",

      alignItems: "center",

      paddingVertical: 16,

      paddingHorizontal: 14,

      borderRadius: 14,

      marginBottom: 8,
    },

    optionText: {
      flex: 1,

      marginLeft: 14,

      fontSize: 16,

      fontWeight: "600",
    },
  });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default SearchSortSheet;