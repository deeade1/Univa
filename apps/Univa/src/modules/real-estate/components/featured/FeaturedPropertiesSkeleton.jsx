import React, { memo } from "react";

import {
  ScrollView,
  StyleSheet,
  View,
} from "react-native";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Skeleton Card */
/* -------------------------------------------------------------------------- */

function SkeletonCard({ colors }) {
  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: colors.card,
        },
      ]}
    >
      {/* Image */}
      <View
        style={[
          styles.image,
          {
            backgroundColor:
              colors.border,
          },
        ]}
      />

      <View style={styles.content}>
        {/* Price */}
        <View
          style={[
            styles.price,
            {
              backgroundColor:
                colors.border,
            },
          ]}
        />

        {/* Title */}
        <View
          style={[
            styles.title,
            {
              backgroundColor:
                colors.border,
            },
          ]}
        />

        <View
          style={[
            styles.subtitle,
            {
              backgroundColor:
                colors.border,
            },
          ]}
        />

        {/* Location */}
        <View
          style={[
            styles.location,
            {
              backgroundColor:
                colors.border,
            },
          ]}
        />

        {/* Badges */}
        <View
          style={styles.badgesRow}
        >
          <View
            style={[
              styles.badge,
              {
                backgroundColor:
                  colors.border,
              },
            ]}
          />

          <View
            style={[
              styles.badge,
              {
                backgroundColor:
                  colors.border,
              },
            ]}
          />
        </View>

        {/* Stats */}
        <View
          style={styles.statsRow}
        >
          {[1, 2, 3, 4].map(
            (item) => (
              <View
                key={item}
                style={
                  styles.stat
                }
              >
                <View
                  style={[
                    styles.statIcon,
                    {
                      backgroundColor:
                        colors.border,
                    },
                  ]}
                />

                <View
                  style={[
                    styles.statText,
                    {
                      backgroundColor:
                        colors.border,
                    },
                  ]}
                />
              </View>
            )
          )}
        </View>
      </View>
    </View>
  );
}

/* -------------------------------------------------------------------------- */
/* Featured Properties Skeleton */
/* -------------------------------------------------------------------------- */

function FeaturedPropertiesSkeleton() {
  const { colors } = useTheme();

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={
        false
      }
      contentContainerStyle={
        styles.container
      }
    >
      {[1, 2, 3].map((item) => (
        <View
          key={item}
          style={styles.item}
        >
          <SkeletonCard
            colors={colors}
          />
        </View>
      ))}
    </ScrollView>
  );
}

const styles =
  StyleSheet.create({
    container: {
      paddingHorizontal: 16,
      paddingBottom: 8,
    },

    item: {
      marginRight: 16,
    },

    card: {
      width: 320,
      borderRadius: 22,
      overflow: "hidden",
    },

    image: {
      width: "100%",
      height: 220,
    },

    content: {
      padding: 18,
    },

    price: {
      width: 120,
      height: 26,
      borderRadius: 8,
    },

    title: {
      width: "85%",
      height: 18,
      marginTop: 16,
      borderRadius: 6,
    },

    subtitle: {
      width: "60%",
      height: 18,
      marginTop: 8,
      borderRadius: 6,
    },

    location: {
      width: "70%",
      height: 16,
      marginTop: 16,
      borderRadius: 6,
    },

    badgesRow: {
      flexDirection: "row",
      marginTop: 18,
    },

    badge: {
      width: 90,
      height: 30,
      borderRadius: 16,
      marginRight: 12,
    },

    statsRow: {
      flexDirection: "row",
      justifyContent:
        "space-between",
      marginTop: 24,
      paddingTop: 18,
    },

    stat: {
      alignItems: "center",
      flex: 1,
    },

    statIcon: {
      width: 22,
      height: 22,
      borderRadius: 11,
    },

    statText: {
      width: 40,
      height: 10,
      borderRadius: 4,
      marginTop: 10,
    },
  });

export default memo(
  FeaturedPropertiesSkeleton
);