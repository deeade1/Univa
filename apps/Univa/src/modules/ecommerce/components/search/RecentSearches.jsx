/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/RecentSearches.jsx      */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
} from "react";

import {
  View,
  Text,
  FlatList,
  Pressable,
  StyleSheet,
} from "react-native";

import {
  MaterialCommunityIcons,
} from "@expo/vector-icons";

import theme from "@/theme";

import SearchHistoryItem from "./SearchHistoryItem";

/* -------------------------------------------------------------------------- */

const RecentSearches = memo(
  ({
    searches = [],

    title = "Recent Searches",

    maxItems,

    horizontal = false,

    showHeader = true,

    showClearAll = true,

    emptyText = "No recent searches.",

    keyExtractor,

    onPress,

    onRemove,

    onClearAll,

    contentContainerStyle,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const data =
      maxItems
        ? searches.slice(
            0,
            maxItems
          )
        : searches;

    /* ---------------------------------------------------------------------- */

    const renderItem =
      useCallback(
        ({ item }) => (
          <SearchHistoryItem
            item={item}
            onPress={
              onPress
            }
            onRemove={
              onRemove
            }
            showTime
          />
        ),
        [
          onPress,
          onRemove,
        ]
      );

    /* ---------------------------------------------------------------------- */

    const extractKey =
      useCallback(
        (
          item,
          index
        ) =>
          keyExtractor
            ? keyExtractor(
                item,
                index
              )
            : String(
                item?.id ??
                  item?.query ??
                  item?.text ??
                  index
              ),
        [keyExtractor]
      );

    /* ---------------------------------------------------------------------- */

    const renderEmpty =
      useCallback(
        () => (
          <View
            style={
              styles.emptyContainer
            }
          >
            <MaterialCommunityIcons
              name="history"
              size={40}
              color={
                colors.textSecondary
              }
            />

            <Text
              style={[
                styles.emptyText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {emptyText}
            </Text>
          </View>
        ),
        [
          colors,
          emptyText,
        ]
      );

    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Header */}
        {/* -------------------------------------------------------------- */}

        {showHeader && (
          <View
            style={
              styles.header
            }
          >
            <View
              style={
                styles.headerLeft
              }
            >
              <MaterialCommunityIcons
                name="history"
                size={20}
                color={
                  colors.primary
                }
              />

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
            </View>

            {showClearAll &&
              data.length >
                0 && (
                <Pressable
                  onPress={
                    onClearAll
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
                    Clear All
                  </Text>
                </Pressable>
              )}
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* List */}
        {/* -------------------------------------------------------------- */}

        <FlatList
          data={data}
          horizontal={
            horizontal
          }
          renderItem={
            renderItem
          }
          keyExtractor={
            extractKey
          }
          ListEmptyComponent={
            renderEmpty
          }
          keyboardShouldPersistTaps="handled"
          showsHorizontalScrollIndicator={
            false
          }
          showsVerticalScrollIndicator={
            false
          }
          contentContainerStyle={[
            data.length ===
              0 &&
              styles.emptyList,
            contentContainerStyle,
          ]}
        />
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */

RecentSearches.displayName =
  "RecentSearches";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      width: "100%",
    },

    header: {
      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "space-between",

      marginBottom: 12,
    },

    headerLeft: {
      flexDirection:
        "row",

      alignItems:
        "center",
    },

    title: {
      fontSize: 17,

      fontWeight: "700",

      marginLeft: 8,
    },

    clearText: {
      fontSize: 14,

      fontWeight: "600",
    },

    emptyList: {
      flexGrow: 1,
    },

    emptyContainer: {
      alignItems:
        "center",

      justifyContent:
        "center",

      paddingVertical: 40,
    },

    emptyText: {
      marginTop: 12,

      fontSize: 15,

      textAlign:
        "center",
    },
  });

/* -------------------------------------------------------------------------- */

export default RecentSearches;