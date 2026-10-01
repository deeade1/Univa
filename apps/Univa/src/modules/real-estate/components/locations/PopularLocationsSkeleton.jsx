import React, { memo } from "react";
import {
  ScrollView,
  StyleSheet,
  View,
} from "react-native";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Skeleton Block */
/* -------------------------------------------------------------------------- */

function Skeleton({
  width,
  height,
  radius = 10,
  style,
}) {
  const { colors } = useTheme();

  return (
    <View
      style={[
        {
          width,
          height,
          borderRadius: radius,
          backgroundColor: colors.border,
        },
        style,
      ]}
    />
  );
}

/* -------------------------------------------------------------------------- */
/* Location Card Skeleton */
/* -------------------------------------------------------------------------- */

const LocationCardSkeleton = memo(() => {
  return (
    <View style={styles.card}>
      <Skeleton
        width="100%"
        height={120}
        radius={18}
      />

      <View style={styles.content}>
        <Skeleton
          width="70%"
          height={18}
          radius={8}
        />

        <Skeleton
          width="45%"
          height={14}
          radius={7}
          style={styles.spacing}
        />
      </View>
    </View>
  );
});

LocationCardSkeleton.displayName = "LocationCardSkeleton";

/* -------------------------------------------------------------------------- */
/* Popular Locations Skeleton */
/* -------------------------------------------------------------------------- */

const PopularLocationsSkeleton = memo(() => {
  return (
    <View style={styles.container}>
      <Skeleton
        width={180}
        height={24}
        radius={8}
        style={styles.title}
      />

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.list}
      >
        {[1, 2, 3, 4].map((item) => (
          <LocationCardSkeleton key={item} />
        ))}
      </ScrollView>
    </View>
  );
});

PopularLocationsSkeleton.displayName = "PopularLocationsSkeleton";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    marginTop: 28,
  },

  title: {
    marginHorizontal: 20,
    marginBottom: 16,
  },

  list: {
    paddingHorizontal: 20,
    gap: 16,
  },

  card: {
    width: 230,
  },

  content: {
    marginTop: 12,
    paddingHorizontal: 4,
  },

  spacing: {
    marginTop: 10,
  },
});

export default PopularLocationsSkeleton;