/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchSuggestions.jsx   */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
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

/* -------------------------------------------------------------------------- */

const SearchSuggestions = memo(
  ({
    query = "",

    products = [],

    categories = [],

    brands = [],

    sellers = [],

    maxItems = 20,

    showProducts = true,

    showCategories = true,

    showBrands = true,

    showSellers = true,

    onSelect,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */
    /* Build Suggestions                                                      */
    /* ---------------------------------------------------------------------- */

    const suggestions =
      useMemo(() => {
        const data = [];

        if (showProducts) {
          products.forEach(
            (item) =>
              data.push({
                ...item,
                type: "product",
              })
          );
        }

        if (
          showCategories
        ) {
          categories.forEach(
            (item) =>
              data.push({
                ...item,
                type: "category",
              })
          );
        }

        if (showBrands) {
          brands.forEach(
            (item) =>
              data.push({
                ...item,
                type: "brand",
              })
          );
        }

        if (showSellers) {
          sellers.forEach(
            (item) =>
              data.push({
                ...item,
                type: "seller",
              })
          );
        }

        return data.slice(
          0,
          maxItems
        );
      }, [
        products,
        categories,
        brands,
        sellers,
        maxItems,
        showProducts,
        showCategories,
        showBrands,
        showSellers,
      ]);

    /* ---------------------------------------------------------------------- */

    const getTitle =
      useCallback(
        (item) =>
          item.name ??
          item.businessName ??
          item.title ??
          "",
        []
      );

    /* ---------------------------------------------------------------------- */

    const getSubtitle =
      useCallback(
        (type) => {
          switch (
            type
          ) {
            case "product":
              return "Product";

            case "category":
              return "Category";

            case "brand":
              return "Brand";

            case "seller":
              return "Seller";

            default:
              return "";
          }
        },
        []
      );

    /* ---------------------------------------------------------------------- */

    const getIcon =
      useCallback(
        (type) => {
          switch (
            type
          ) {
            case "product":
              return "package-variant";

            case "category":
              return "shape-outline";

            case "brand":
              return "tag-outline";

            case "seller":
              return "storefront-outline";

            default:
              return "magnify";
          }
        },
        []
      );

    /* ---------------------------------------------------------------------- */

    const highlight =
      useCallback(
        (text = "") => {
          if (
            !query
          ) {
            return (
              <Text
                style={{
                  color:
                    colors.text,
                  fontSize: 15,
                  fontWeight:
                    "500",
                }}
              >
                {text}
              </Text>
            );
          }

          const lower =
            text.toLowerCase();

          const search =
            query.toLowerCase();

          const index =
            lower.indexOf(
              search
            );

          if (
            index ===
            -1
          ) {
            return (
              <Text
                style={{
                  color:
                    colors.text,
                  fontSize: 15,
                  fontWeight:
                    "500",
                }}
              >
                {text}
              </Text>
            );
          }

          return (
            <Text
              style={{
                color:
                  colors.text,
                fontSize: 15,
              }}
            >
              {text.substring(
                0,
                index
              )}

              <Text
                style={{
                  color:
                    colors.primary,
                  fontWeight:
                    "700",
                }}
              >
                {text.substring(
                  index,
                  index +
                    query.length
                )}
              </Text>

              {text.substring(
                index +
                  query.length
              )}
            </Text>
          );
        },
        [
          query,
          colors,
        ]
      );

    /* ---------------------------------------------------------------------- */

    const renderItem =
      useCallback(
        ({ item }) => (
          <Pressable
            android_ripple={{
              color:
                colors.border,
            }}
            onPress={() =>
              onSelect?.(
                item
              )
            }
            style={({
              pressed,
            }) => [
              styles.item,
              {
                borderBottomColor:
                  colors.border,

                opacity:
                  pressed
                    ? 0.85
                    : 1,
              },
            ]}
          >
            <MaterialCommunityIcons
              name={getIcon(
                item.type
              )}
              size={22}
              color={
                colors.primary
              }
            />

            <View
              style={
                styles.content
              }
            >
              {highlight(
                getTitle(
                  item
                )
              )}

              <Text
                style={[
                  styles.subtitle,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                {getSubtitle(
                  item.type
                )}
              </Text>
            </View>

            <MaterialCommunityIcons
              name="arrow-top-left"
              size={18}
              color={
                colors.textSecondary
              }
            />
          </Pressable>
        ),
        [
          colors,
          onSelect,
          getIcon,
          getTitle,
          getSubtitle,
          highlight,
        ]
      );

    /* ---------------------------------------------------------------------- */

    if (
      suggestions.length ===
      0
    ) {
      return null;
    }

    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,
          {
            backgroundColor:
              colors.card,

            borderColor:
              colors.border,
          },
          style,
        ]}
      >
        <FlatList
          keyboardShouldPersistTaps="handled"
          data={
            suggestions
          }
          renderItem={
            renderItem
          }
          keyExtractor={(
            item,
            index
          ) =>
            `${item.type}-${item.id ?? index}`
          }
          showsVerticalScrollIndicator={
            false
          }
        />
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */

SearchSuggestions.displayName =
  "SearchSuggestions";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      borderWidth: 1,

      borderRadius: 14,

      overflow:
        "hidden",

      maxHeight: 420,
    },

    item: {
      flexDirection:
        "row",

      alignItems:
        "center",

      paddingHorizontal: 16,

      paddingVertical: 14,

      borderBottomWidth:
        StyleSheet.hairlineWidth,
    },

    content: {
      flex: 1,

      marginLeft: 14,
    },

    subtitle: {
      marginTop: 2,

      fontSize: 12,
    },
  });

/* -------------------------------------------------------------------------- */

export default SearchSuggestions;