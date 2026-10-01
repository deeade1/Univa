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
/* Recommended Properties Skeleton */
/* -------------------------------------------------------------------------- */

function RecommendedPropertiesSkeleton() {
  const { colors } = useTheme();

  return (
    <View style={styles.container}>
      {/* -------------------------------------------------- */}
      {/* Header */}
      {/* -------------------------------------------------- */}

      <View style={styles.header}>
        <View>
          <Skeleton
            width={190}
            height={24}
          />

          <Skeleton
            width={230}
            height={14}
            style={{
              marginTop: 10,
            }}
          />
        </View>

        <Skeleton
          width={90}
          height={34}
          radius={18}
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
            {/* Hero Image */}

            <Skeleton
              width="100%"
              height={220}
              radius={0}
            />

            <View
              style={
                styles.content
              }
            >
              {/* Price */}

              <View
                style={
                  styles.priceRow
                }
              >
                <Skeleton
                  width={130}
                  height={26}
                />

                <Skeleton
                  width={60}
                  height={18}
                />
              </View>

              {/* Title */}

              <Skeleton
                width={220}
                height={20}
                style={
                  styles.title
                }
              />

              <Skeleton
                width={180}
                height={20}
                style={{
                  marginTop: 8,
                }}
              />

              {/* Location */}

              <Skeleton
                width={210}
                height={14}
                style={
                  styles.location
                }
              />

              {/* AI Box */}

              <View
                style={[
                  styles.aiBox,
                  {
                    backgroundColor:
                      colors.border,
                  },
                ]}
              >
                <Skeleton
                  width={120}
                  height={16}
                />

                <Skeleton
                  width="100%"
                  height={14}
                  style={{
                    marginTop: 12,
                  }}
                />

                <Skeleton
                  width="85%"
                  height={14}
                  style={{
                    marginTop: 8,
                  }}
                />
              </View>

              {/* Features */}

              <View
                style={
                  styles.features
                }
              >
                <Skeleton
                  width={70}
                  height={14}
                />

                <Skeleton
                  width={70}
                  height={14}
                />

                <Skeleton
                  width={70}
                  height={14}
                />
              </View>

              {/* Footer */}

              <Skeleton
                width={120}
                height={16}
                style={
                  styles.footer
                }
              />
            </View>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles =
  StyleSheet.create({
    container: {
      marginTop: 30,
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
      width: 330,

      marginRight: 16,

      borderRadius: 24,

      overflow: "hidden",
    },

    content: {
      padding: 18,
    },

    priceRow: {
      flexDirection: "row",

      justifyContent:
        "space-between",

      alignItems: "center",
    },

    title: {
      marginTop: 16,
    },

    location: {
      marginTop: 14,
    },

    aiBox: {
      marginTop: 20,

      padding: 16,

      borderRadius: 14,
    },

    features: {
      marginTop: 22,

      flexDirection: "row",

      justifyContent:
        "space-between",
    },

    footer: {
      marginTop: 24,
    },
  });

export default memo(
  RecommendedPropertiesSkeleton
);