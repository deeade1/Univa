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

import RecentPropertyCard from "./RecentPropertyCard";
import RecentPropertiesSkeleton from "./RecentPropertiesSkeleton";
import RecentPropertiesEmpty from "./RecentPropertiesEmpty";

/* -------------------------------------------------------------------------- */
/* Recent Properties */
/* -------------------------------------------------------------------------- */

function RecentProperties() {
  const router = useRouter();

  const { colors } = useTheme();

  const {
    recentProperties,
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
        "/real-estate/properties?sort=newest"
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
        <RecentPropertyCard
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
    recentProperties.length === 0
  ) {
    return (
      <RecentPropertiesSkeleton />
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
          name="alert-circle-outline"
          size={54}
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
          Unable to load recent properties
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
          Please check your internet
          connection and try again.
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
          <Ionicons
            name="refresh-outline"
            size={18}
            color="#FFFFFF"
          />

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
    recentProperties.length === 0
  ) {
    return (
      <RecentPropertiesEmpty
        onRefresh={refresh}
      />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* UI */
  /* ---------------------------------------------------------------------- */

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text
          style={[
            styles.title,
            {
              color:
                colors.text,
            },
          ]}
        >
          Recently Added
        </Text>

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
          recentProperties
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
    marginTop: 28,
  },

  /* ---------------------------------------------------------------------- */
  /* Header */
  /* ---------------------------------------------------------------------- */

  header: {
    marginHorizontal: 16,

    marginBottom: 18,

    flexDirection: "row",

    justifyContent:
      "space-between",

    alignItems: "center",
  },

  title: {
    fontSize: 22,

    fontWeight: "700",
  },

  viewAllButton: {
    flexDirection: "row",

    alignItems: "center",
  },

  viewAll: {
    fontSize: 14,

    fontWeight: "600",

    marginRight: 2,
  },

  /* ---------------------------------------------------------------------- */
  /* List */
  /* ---------------------------------------------------------------------- */

  list: {
    paddingHorizontal: 16,

    paddingBottom: 8,
  },

  /* ---------------------------------------------------------------------- */
  /* Error */
  /* ---------------------------------------------------------------------- */

  errorContainer: {
    marginTop: 28,

    paddingHorizontal: 24,

    paddingVertical: 40,

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

    maxWidth: 300,
  },

  retryButton: {
    marginTop: 24,

    flexDirection: "row",

    alignItems: "center",

    justifyContent: "center",

    paddingHorizontal: 24,

    paddingVertical: 12,

    borderRadius: 12,
  },

  retryText: {
    color: "#FFFFFF",

    fontSize: 15,

    fontWeight: "700",

    marginLeft: 8,
  },
});

export default memo(
  RecentProperties
);
