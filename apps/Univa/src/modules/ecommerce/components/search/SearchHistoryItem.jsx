/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchHistoryItem.jsx   */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
} from "react";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from "react-native";

import {
  MaterialCommunityIcons,
} from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */

const SearchHistoryItem = memo(
  ({
    item,

    text,

    timestamp,

    pinned = false,

    showTime = false,

    showPin = true,

    showRemove = true,

    onPress,

    onRemove,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const searchText =
      text ??
      item?.text ??
      item?.query ??
      "";

    const time =
      timestamp ??
      item?.timestamp ??
      item?.createdAt ??
      item?.date;

    /* ---------------------------------------------------------------------- */

    const handlePress =
      useCallback(() => {
        onPress?.(
          item ??
            searchText
        );
      }, [
        item,
        searchText,
        onPress,
      ]);

    /* ---------------------------------------------------------------------- */

    const handleRemove =
      useCallback(() => {
        onRemove?.(
          item ??
            searchText
        );
      }, [
        item,
        searchText,
        onRemove,
      ]);

    /* ---------------------------------------------------------------------- */

    return (
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Search ${searchText}`}
        android_ripple={{
          color:
            colors.border,
        }}
        onPress={
          handlePress
        }
        style={({ pressed }) => [
          styles.container,

          {
            backgroundColor:
              colors.card,

            borderBottomColor:
              colors.border,

            opacity:
              pressed
                ? 0.8
                : 1,
          },

          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Left */}
        {/* -------------------------------------------------------------- */}

        <View
          style={
            styles.left
          }
        >
          <MaterialCommunityIcons
            name="history"
            size={20}
            color={
              colors.textSecondary
            }
          />

          <View
            style={
              styles.textContainer
            }
          >
            <Text
              numberOfLines={
                1
              }
              style={[
                styles.title,

                {
                  color:
                    colors.text,
                },
              ]}
            >
              {searchText}
            </Text>

            {showTime &&
              !!time && (
                <Text
                  style={[
                    styles.subtitle,
                    {
                      color:
                        colors.textSecondary,
                    },
                  ]}
                >
                  {time}
                </Text>
              )}
          </View>
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Right */}
        {/* -------------------------------------------------------------- */}

        <View
          style={
            styles.right
          }
        >
          {pinned &&
            showPin && (
              <MaterialCommunityIcons
                name="pin"
                size={18}
                color={
                  colors.primary
                }
                style={
                  styles.iconSpacing
                }
              />
            )}

          {showRemove && (
            <Pressable
              hitSlop={8}
              onPress={
                handleRemove
              }
            >
              <MaterialCommunityIcons
                name="close"
                size={20}
                color={
                  colors.textSecondary
                }
              />
            </Pressable>
          )}
        </View>
      </Pressable>
    );
  }
);

/* -------------------------------------------------------------------------- */

SearchHistoryItem.displayName =
  "SearchHistoryItem";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "space-between",

      paddingHorizontal: 16,

      paddingVertical: 14,

      borderBottomWidth:
        StyleSheet.hairlineWidth,
    },

    left: {
      flex: 1,

      flexDirection:
        "row",

      alignItems:
        "center",
    },

    textContainer: {
      flex: 1,

      marginLeft: 12,
    },

    title: {
      fontSize: 15,

      fontWeight: "500",
    },

    subtitle: {
      marginTop: 2,

      fontSize: 12,
    },

    right: {
      flexDirection:
        "row",

      alignItems:
        "center",

      marginLeft: 12,
    },

    iconSpacing: {
      marginRight: 10,
    },
  });

/* -------------------------------------------------------------------------- */

export default SearchHistoryItem;