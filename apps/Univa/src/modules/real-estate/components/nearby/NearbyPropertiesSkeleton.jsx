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
          backgroundColor:
            colors.border,
        },
        style,
      ]}
    />
  );
}

/* -------------------------------------------------------------------------- */
/* Nearby Properties Skeleton */
/* -------------------------------------------------------------------------- */

function NearbyPropertiesSkeleton() {
  const { colors } = useTheme();

  return (
    <View
      style={styles.container}
    >
      {/* -------------------------------------------------- */}
      {/* Header */}
      {/* -------------------------------------------------- */}

      <View
        style={styles.header}
      >
        <View>
          <Skeleton
            width={180}
            height={24}
          />

          <Skeleton
            width={140}
            height={14}
            style={{
              marginTop: 10,
            }}
          />
        </View>

        <Skeleton
          width={90}
          height={34}
          radius={20}
        />
      </View>

      {/* -------------------------------------------------- */}
      {/* Cards */}
      {/* -------------------------------------------------- */}

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={
          false
        }
        contentContainerStyle={
          styles.list
        }
      >
        {[1, 2].map((item) => (
          <View
            key={item}
            style={[
              styles.card,
              {
                backgroundColor:
                  colors.card,
              },
            ]}
          >
            <Skeleton
              width="100%"
              height={190}
              radius={0}
            />

            <Skeleton
              width={140}
              height={24}
              style={
                styles.price
              }
            />

            <Skeleton
              width={210}
              height={18}
              style={
                styles.title
              }
            />

            <Skeleton
              width={170}
              height={14}
              style={
                styles.location
              }
            />

            <View
              style={
                styles.row
              }
            >
              <Skeleton
                width={60}
                height={14}
              />

              <Skeleton
                width={70}
                height={14}
              />

              <Skeleton
                width={45}
                height={14}
              />
            </View>

            <View
              style={
                styles.row
              }
            >
              <Skeleton
                width={55}
                height={14}
              />

              <Skeleton
                width={55}
                height={14}
              />

              <Skeleton
                width={70}
                height={14}
              />
            </View>

            <Skeleton
              width={120}
              height={16}
              style={
                styles.footer
              }
            />
          </View>
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

    header: {
      marginHorizontal: 16,

      marginBottom: 18,

      flexDirection: "row",

      justifyContent:
        "space-between",

      alignItems: "center",
    },

    list: {
      paddingHorizontal: 16,
    },

    card: {
      width: 300,

      marginRight: 16,

      borderRadius: 22,

      overflow: "hidden",

      paddingBottom: 20,
    },

    price: {
      marginTop: 16,

      marginHorizontal: 16,
    },

    title: {
      marginTop: 12,

      marginHorizontal: 16,
    },

    location: {
      marginTop: 12,

      marginHorizontal: 16,
    },

    row: {
      marginTop: 18,

      marginHorizontal: 16,

      flexDirection: "row",

      justifyContent:
        "space-between",
    },

    footer: {
      marginTop: 22,

      marginHorizontal: 16,
    },
  });

export default memo(
  NearbyPropertiesSkeleton
);