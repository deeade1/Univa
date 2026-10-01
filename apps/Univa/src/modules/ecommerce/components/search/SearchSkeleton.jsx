/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchSkeleton.jsx      */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import {
  View,
  StyleSheet,
} from "react-native";

import ContentLoader, {
  Rect,
} from "react-content-loader/native";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */

const SearchSkeleton = memo(
  ({
    count = 8,

    columns = 2,

    mode = "grid", // "grid" | "list"

    spacing = 16,

    style,
  }) => {
    const { colors } = theme;


    /* ---------------------------------------------------------------------- */

    const placeholders =
      useMemo(
        () =>
          Array.from(
            {
              length: count,
            },
            (_, i) => i
          ),
        [count]
      );

    /* ---------------------------------------------------------------------- */

    if (mode === "list") {
      return (
        <View
          style={[
            styles.listContainer,
            style,
          ]}
        >
          {placeholders.map(
            (item) => (
              <View
                key={item}
                style={
                  styles.listItem
                }
              >
                <ContentLoader
                  speed={1.4}
                  width="100%"
                  height={96}
                  backgroundColor={
                    colors.border
                  }
                  foregroundColor={
                    colors.card
                  }
                >
                  {/* Image */}

                  <Rect
                    x="0"
                    y="0"
                    rx="12"
                    ry="12"
                    width="88"
                    height="88"
                  />

                  {/* Title */}

                  <Rect
                    x="102"
                    y="8"
                    rx="4"
                    ry="4"
                    width="180"
                    height="14"
                  />

                  {/* Subtitle */}

                  <Rect
                    x="102"
                    y="34"
                    rx="4"
                    ry="4"
                    width="140"
                    height="12"
                  />

                  {/* Price */}

                  <Rect
                    x="102"
                    y="62"
                    rx="4"
                    ry="4"
                    width="90"
                    height="16"
                  />
                </ContentLoader>
              </View>
            )
          )}
        </View>
      );
    }

    /* ---------------------------------------------------------------------- */
    /* Grid Skeleton                                                           */
    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.grid,

          {
            marginHorizontal:
              -spacing / 2,
          },

          style,
        ]}
      >
        {placeholders.map(
          (item) => (
            <View
              key={item}
              style={[
                styles.card,

                {
                  width: `${100 / columns}%`,

                  padding:
                    spacing / 2,
                },
              ]}
            >
              <ContentLoader
                speed={1.4}
                width="100%"
                height={260}
                backgroundColor={
                  colors.border
                }
                foregroundColor={
                  colors.card
                }
              >
                {/* Image */}

                <Rect
                  x="0"
                  y="0"
                  rx="16"
                  ry="16"
                  width="100%"
                  height="150"
                />

                {/* Brand */}

                <Rect
                  x="0"
                  y="166"
                  rx="4"
                  ry="4"
                  width="55%"
                  height="10"
                />

                {/* Product */}

                <Rect
                  x="0"
                  y="186"
                  rx="4"
                  ry="4"
                  width="90%"
                  height="14"
                />

                <Rect
                  x="0"
                  y="208"
                  rx="4"
                  ry="4"
                  width="65%"
                  height="14"
                />

                {/* Price */}

                <Rect
                  x="0"
                  y="236"
                  rx="4"
                  ry="4"
                  width="40%"
                  height="16"
                />
              </ContentLoader>
            </View>
          )
        )}
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */

SearchSkeleton.displayName =
  "SearchSkeleton";

/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    grid: {
      flexDirection:
        "row",

      flexWrap:
        "wrap",
    },

    card: {
      marginBottom: 12,
    },

    listContainer: {
      width: "100%",
    },

    listItem: {
      marginBottom: 16,
    },
  });

/* -------------------------------------------------------------------------- */

export default SearchSkeleton;