import React, { memo } from "react";
import {
  ScrollView,
  StyleSheet,
  View,
} from "react-native";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Skeleton */
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
/* Agent Skeleton Card */
/* -------------------------------------------------------------------------- */

const AgentSkeletonCard = memo(() => {
  return (
    <View style={styles.card}>
      <Skeleton
        width={72}
        height={72}
        radius={36}
      />

      <View style={styles.content}>
        <Skeleton
          width="70%"
          height={18}
        />

        <Skeleton
          width="50%"
          height={14}
          style={styles.spacing}
        />

        <Skeleton
          width="40%"
          height={14}
          style={styles.spacing}
        />

        <View style={styles.stats}>
          <Skeleton
            width={50}
            height={12}
          />

          <Skeleton
            width={50}
            height={12}
          />

          <Skeleton
            width={50}
            height={12}
          />
        </View>
      </View>

      <View style={styles.actions}>
        <Skeleton
          width={42}
          height={42}
          radius={21}
        />

        <Skeleton
          width={42}
          height={42}
          radius={21}
        />
      </View>
    </View>
  );
});

AgentSkeletonCard.displayName = "AgentSkeletonCard";

/* -------------------------------------------------------------------------- */
/* Featured Agents Skeleton */
/* -------------------------------------------------------------------------- */

const FeaturedAgentsSkeleton = memo(() => {
  return (
    <View style={styles.container}>
      <Skeleton
        width={190}
        height={24}
        style={styles.title}
      />

      <Skeleton
        width={150}
        height={14}
        style={styles.subtitle}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        scrollEnabled={false}
        contentContainerStyle={styles.list}
      >
        {[1, 2, 3].map((item) => (
          <AgentSkeletonCard key={item} />
        ))}
      </ScrollView>
    </View>
  );
});

FeaturedAgentsSkeleton.displayName = "FeaturedAgentsSkeleton";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    marginTop: 28,
  },

  title: {
    marginHorizontal: 20,
    marginBottom: 10,
  },

  subtitle: {
    marginHorizontal: 20,
    marginBottom: 20,
  },

  list: {
    paddingHorizontal: 20,
  },

  card: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 18,
  },

  content: {
    flex: 1,
    marginLeft: 16,
  },

  spacing: {
    marginTop: 8,
  },

  stats: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 14,
    width: 170,
  },

  actions: {
    marginLeft: 16,
    justifyContent: "space-between",
    height: 72,
  },
});

export default FeaturedAgentsSkeleton;