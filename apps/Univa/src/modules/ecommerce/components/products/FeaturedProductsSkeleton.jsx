/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/products/FeaturedProductsSkeleton.jsx */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";

import {
  View,
  StyleSheet,
} from "react-native";

import { Skeleton } from "moti/skeleton";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */
/* Skeleton Card                                                              */
/* -------------------------------------------------------------------------- */

const SkeletonCard = ({
  horizontal = true,
}) => {
  const { colors, isDark } = theme;
    

  return (
    <View
      style={[
        styles.card,
        horizontal
          ? styles.horizontalCard
          : styles.gridCard,
        {
          backgroundColor:
            colors.card,
          borderColor:
            colors.border,
        },
      ]}
    >
      {/* Product Image */}

      <Skeleton
        colorMode={
          isDark
            ? "dark"
            : "light"
        }
        width="100%"
        height={180}
        radius={18}
      />

      <View style={styles.content}>
        {/* Category */}

        <Skeleton
          colorMode={
            isDark
              ? "dark"
              : "light"
          }
          width={70}
          height={12}
          radius={6}
        />

        {/* Product Name */}

        <View
          style={
            styles.spacingSmall
          }
        />

        <Skeleton
          colorMode={
            isDark
              ? "dark"
              : "light"
          }
          width="90%"
          height={18}
          radius={8}
        />

        <View
          style={
            styles.spacingTiny
          }
        />

        <Skeleton
          colorMode={
            isDark
              ? "dark"
              : "light"
          }
          width="65%"
          height={18}
          radius={8}
        />

        {/* Seller */}

        <View
          style={
            styles.spacingMedium
          }
        />

        <Skeleton
          colorMode={
            isDark
              ? "dark"
              : "light"
          }
          width={110}
          height={14}
          radius={7}
        />

        {/* Rating */}

        <View
          style={
            styles.spacingMedium
          }
        />

        <Skeleton
          colorMode={
            isDark
              ? "dark"
              : "light"
          }
          width={80}
          height={14}
          radius={7}
        />

        {/* Price */}

        <View
          style={
            styles.spacingMedium
          }
        />

        <Skeleton
          colorMode={
            isDark
              ? "dark"
              : "light"
          }
          width={100}
          height={22}
          radius={10}
        />

        {/* Bottom Row */}

        <View
          style={
            styles.bottomRow
          }
        >
          <Skeleton
            colorMode={
              isDark
                ? "dark"
                : "light"
            }
            width={90}
            height={14}
            radius={7}
          />

          <Skeleton
            colorMode={
              isDark
                ? "dark"
                : "light"
            }
            width={42}
            height={42}
            radius={21}
          />
        </View>
      </View>
    </View>
  );
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const FeaturedProductsSkeleton =
  memo(
    ({
      horizontal = true,

      count = horizontal
        ? 5
        : 6,
    }) => {
      return (
        <View
          style={[
            styles.container,
            horizontal &&
              styles.horizontalContainer,
          ]}
        >
          {Array.from({
            length: count,
          }).map((_, index) => (
            <SkeletonCard
              key={index}
              horizontal={
                horizontal
              }
            />
          ))}
        </View>
      );
    }
  );

FeaturedProductsSkeleton.displayName =
  "FeaturedProductsSkeleton";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent:
      "space-between",
    paddingHorizontal: 16,
    paddingBottom: 16,
  },

  horizontalContainer: {
    flexWrap: "nowrap",
  },

  card: {
    borderRadius: 18,
    borderWidth: 1,
    overflow: "hidden",
  },

  horizontalCard: {
    width: 220,
    marginRight: 16,
  },

  gridCard: {
    width: "48%",
    marginBottom: 18,
  },

  content: {
    padding: 16,
  },

  spacingTiny: {
    height: 6,
  },

  spacingSmall: {
    height: 10,
  },

  spacingMedium: {
    height: 14,
  },

  bottomRow: {
    marginTop: 18,

    flexDirection: "row",

    justifyContent:
      "space-between",

    alignItems: "center",
  },
});

export default FeaturedProductsSkeleton;