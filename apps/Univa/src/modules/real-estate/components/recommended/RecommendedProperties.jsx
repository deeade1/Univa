import React, {
  memo,
  useCallback,
} from "react";

import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { useRouter } from "expo-router";

import { useTheme } from "@/theme";

import { useRealEstate } from "../../context/RealEstateProvider";

import RecommendedPropertyCard from "./RecommendedPropertyCard";
import RecommendedPropertiesSkeleton from "./RecommendedPropertiesSkeleton";
import RecommendedPropertiesEmpty from "./RecommendedPropertiesEmpty";

/* -------------------------------------------------------------------------- */
/* Recommended Properties */
/* -------------------------------------------------------------------------- */

function RecommendedProperties() {
  const router = useRouter();

  const { colors } = useTheme();

  const {
    recommendedProperties,
    loading,
    error,
    refresh,
  } = useRealEstate();

  /* ---------------------------------------------------------------------- */
  /* Actions */
  /* ---------------------------------------------------------------------- */

  const handleViewAll =
    useCallback(() => {
      router.push(
        "/real-estate?recommended=true"
      );
    }, [router]);

  const openProperty =
    useCallback(
      (property) => {
        router.push({
          pathname:
            "/real-estate/[slug]",

          params: {
            slug:
              property.slug ??
              property.id,
          },
        });
      },
      [router]
    );

  /* ---------------------------------------------------------------------- */
  /* Render Item */
  /* ---------------------------------------------------------------------- */

  const renderItem =
    useCallback(
      ({ item }) => (
        <RecommendedPropertyCard
          property={item}
          onPress={() =>
            openProperty(item)
          }
        />
      ),
      [openProperty]
    );

  const keyExtractor =
    useCallback(
      (item) =>
        String(item.id),
      []
    );
      /* ---------------------------------------------------------------------- */
  /* Loading */
  /* ---------------------------------------------------------------------- */

  if (
    loading &&
    recommendedProperties.length === 0
  ) {
    return (
      <RecommendedPropertiesSkeleton />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Error */
  /* ---------------------------------------------------------------------- */

  if (error) {
    return (
      <View
        style={
          styles.errorContainer
        }
      >
        <Ionicons
          name="sparkles-outline"
          size={56}
          color={colors.error}
        />

        <Text
          style={[
            styles.errorTitle,
            {
              color:
                colors.text,
            },
          ]}
        >
          Unable to load recommendations
        </Text>

        <Text
          style={[
            styles.errorDescription,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          We couldn't generate personalized
          property recommendations right now.
        </Text>

        <Pressable
          onPress={refresh}
          style={[
            styles.retryButton,
            {
              backgroundColor:
                colors.primary,
            },
          ]}
        >
          <Text
            style={
              styles.retryText
            }
          >
            Retry
          </Text>
        </Pressable>
      </View>
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Empty */
  /* ---------------------------------------------------------------------- */

  if (
    recommendedProperties.length === 0
  ) {
    return (
      <RecommendedPropertiesEmpty />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* UI */
  /* ---------------------------------------------------------------------- */

  return (
    <View
      style={styles.container}
    >
      <View
        style={styles.header}
      >
        <View
          style={styles.headerLeft}
        >
          <View
            style={styles.titleRow}
          >
            <Ionicons
              name="sparkles"
              size={20}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.title,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              Recommended For You
            </Text>
          </View>

          <Text
            style={[
              styles.subtitle,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Personalized picks based on
            your interests and activity.
          </Text>
        </View>

        <Pressable
          onPress={
            handleViewAll
          }
          style={
            styles.viewAllButton
          }
        >
          <Text
            style={[
              styles.viewAll,
              {
                color:
                  colors.primary,
              },
            ]}
          >
            View All
          </Text>

          <Ionicons
            name="chevron-forward"
            size={16}
            color={
              colors.primary
            }
          />
        </Pressable>
      </View>

      <FlatList
        horizontal
        data={
          recommendedProperties
        }
        renderItem={
          renderItem
        }
        keyExtractor={
          keyExtractor
        }
        showsHorizontalScrollIndicator={
          false
        }
        contentContainerStyle={
          styles.list
        }
        ItemSeparatorComponent={() => (
          <View
            style={{
              width: 16,
            }}
          />
        )}
              />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 30,
  },

  /* ---------------------------------------------------------------------- */
  /* Header */
  /* ---------------------------------------------------------------------- */

  header: {
    marginHorizontal: 16,

    marginBottom: 18,

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  headerLeft: {
    flex: 1,

    marginRight: 12,
  },

  titleRow: {
    flexDirection: "row",

    alignItems: "center",
  },

  title: {
    marginLeft: 8,

    fontSize: 22,

    fontWeight: "700",
  },

  subtitle: {
    marginTop: 6,

    fontSize: 13,

    lineHeight: 20,
  },

  viewAllButton: {
    flexDirection: "row",

    alignItems: "center",
  },

  viewAll: {
    marginRight: 2,

    fontSize: 14,

    fontWeight: "600",
  },

  /* ---------------------------------------------------------------------- */
  /* List */
  /* ---------------------------------------------------------------------- */

  list: {
    paddingHorizontal: 16,

    paddingBottom: 6,
  },

  /* ---------------------------------------------------------------------- */
  /* Error */
  /* ---------------------------------------------------------------------- */

  errorContainer: {
    paddingVertical: 48,

    paddingHorizontal: 24,

    alignItems: "center",

    justifyContent: "center",
  },

  errorTitle: {
    marginTop: 18,

    fontSize: 18,

    fontWeight: "700",

    textAlign: "center",
  },

  errorDescription: {
    marginTop: 10,

    fontSize: 15,

    lineHeight: 22,

    textAlign: "center",
  },

  retryButton: {
    marginTop: 24,

    paddingHorizontal: 24,

    paddingVertical: 12,

    borderRadius: 12,
  },

  retryText: {
    color: "#FFFFFF",

    fontSize: 15,

    fontWeight: "700",
  },
});

export default memo(
  RecommendedProperties
);