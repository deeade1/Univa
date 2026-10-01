import React, {
  memo,
} from "react";

import {
  StyleSheet,
  View,
} from "react-native";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Categories Skeleton */
/* -------------------------------------------------------------------------- */

function CategoriesSkeleton() {
  const { colors } = useTheme();

  return (
    <View style={styles.container}>
      {/* ------------------------------------------------------ */}
      {/* Header */}
      {/* ------------------------------------------------------ */}

      <View style={styles.header}>
        <View
          style={[
            styles.titleSkeleton,
            {
              backgroundColor:
                colors.border,
            },
          ]}
        />

        <View
          style={[
            styles.viewAllSkeleton,
            {
              backgroundColor:
                colors.border,
            },
          ]}
        />
      </View>

      {/* ------------------------------------------------------ */}
      {/* Grid */}
      {/* ------------------------------------------------------ */}

      <View style={styles.grid}>
        {[...Array(6)].map(
          (_, index) => (
            <View
              key={index}
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
                  styles.icon,
                  {
                    backgroundColor:
                      colors.border,
                  },
                ]}
              />

              <View
                style={[
                  styles.lineLarge,
                  {
                    backgroundColor:
                      colors.border,
                  },
                ]}
              />

              <View
                style={[
                  styles.lineSmall,
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

    titleSkeleton: {
      width: 170,

      height: 24,

      borderRadius: 8,
    },

    viewAllSkeleton: {
      width: 70,

      height: 18,

      borderRadius: 6,
    },

    grid: {
      flexDirection: "row",

      flexWrap: "wrap",

      justifyContent:
        "space-between",

      paddingHorizontal: 16,
    },

    card: {
      width: "48%",

      height: 120,

      borderRadius: 18,

      padding: 18,

      marginBottom: 16,
    },

    icon: {
      width: 52,

      height: 52,

      borderRadius: 16,
    },

    lineLarge: {
      width: "80%",

      height: 16,

      borderRadius: 6,

      marginTop: 18,
    },

    lineSmall: {
      width: "55%",

      height: 12,

      borderRadius: 6,

      marginTop: 10,
    },
  });

export default memo(
  CategoriesSkeleton
);