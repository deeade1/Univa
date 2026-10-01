import React, {
  memo,
} from "react";

import {
  ScrollView,
  StyleSheet,
  View,
} from "react-native";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Skeleton Card */
/* -------------------------------------------------------------------------- */

function SkeletonCard() {
  const { colors } = useTheme();

  const skeletonColor =
    colors.border ??
    "#E5E7EB";

  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor:
            colors.card,
        },
      ]}
    >
      <View
        style={[
          styles.image,
          {
            backgroundColor:
              skeletonColor,
          },
        ]}
      />

      <View
        style={[
          styles.price,
          {
            backgroundColor:
              skeletonColor,
          },
        ]}
      />

      <View
        style={[
          styles.title,
          {
            backgroundColor:
              skeletonColor,
          },
        ]}
      />

      <View
        style={[
          styles.subtitle,
          {
            backgroundColor:
              skeletonColor,
          },
        ]}
      />

      <View
        style={styles.infoRow}
      >
        <View
          style={[
            styles.info,
            {
              backgroundColor:
                skeletonColor,
            },
          ]}
        />

        <View
          style={[
            styles.info,
            {
              backgroundColor:
                skeletonColor,
            },
          ]}
        />

        <View
          style={[
            styles.info,
            {
              backgroundColor:
                skeletonColor,
            },
          ]}
        />
      </View>

      <View
        style={[
          styles.footer,
          {
            backgroundColor:
              skeletonColor,
          },
        ]}
      />
    </View>
  );
}

/* -------------------------------------------------------------------------- */
/* Recent Properties Skeleton */
/* -------------------------------------------------------------------------- */

function RecentPropertiesSkeleton() {
  return (
    <View
      style={styles.container}
    >
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={
          false
        }
        contentContainerStyle={
          styles.list
        }
      >
        {Array.from({
          length: 4,
        }).map((_, index) => (
          <SkeletonCard
            key={index}
          />
        ))}
      </ScrollView>
    </View>
  );
}

const styles =
  StyleSheet.create({
    container: {
      marginTop: 28,
    },

    list: {
      paddingHorizontal: 16,
    },

    card: {
      width: 290,

      borderRadius: 20,

      marginRight: 16,

      overflow: "hidden",

      paddingBottom: 18,
    },

    image: {
      width: "100%",

      height: 180,
    },

    price: {
      height: 24,

      width: 140,

      borderRadius: 6,

      marginTop: 18,

      marginHorizontal: 16,
    },

    title: {
      height: 18,

      borderRadius: 6,

      marginTop: 14,

      marginHorizontal: 16,
    },

    subtitle: {
      height: 14,

      width: "65%",

      borderRadius: 6,

      marginTop: 10,

      marginHorizontal: 16,
    },

    infoRow: {
      flexDirection: "row",

      justifyContent:
        "space-between",

      marginTop: 22,

      marginHorizontal: 16,
    },

    info: {
      width: 60,

      height: 14,

      borderRadius: 5,
    },

    footer: {
      height: 14,

      width: "45%",

      borderRadius: 5,

      marginTop: 24,

      marginHorizontal: 16,
    },
  });

export default memo(
  RecentPropertiesSkeleton
);