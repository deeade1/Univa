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

import NearbyPropertyCard from "./NearbyPropertyCard";
import NearbyPropertiesSkeleton from "./NearbyPropertiesSkeleton";
import NearbyPropertiesEmpty from "./NearbyPropertiesEmpty";

/* -------------------------------------------------------------------------- */
/* Nearby Properties */
/* -------------------------------------------------------------------------- */

function NearbyProperties() {
  const router = useRouter();

  const { colors } = useTheme();

  const {
    nearbyProperties,
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
        "/real-estate/map"
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
        <NearbyPropertyCard
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
    nearbyProperties.length === 0
  ) {
    return (
      <NearbyPropertiesSkeleton />
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
          name="location-outline"
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
          Unable to load nearby properties
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
          Check your internet connection
          and try again.
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
    nearbyProperties.length === 0
  ) {
    return (
      <NearbyPropertiesEmpty />
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
        <View>
          <Text
            style={[
              styles.title,
              {
                color:
                  colors.text,
              },
            ]}
          >
            Nearby You
          </Text>

          <Text
            style={[
              styles.subtitle,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Properties close to your
            current location
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
          <Ionicons
            name="map-outline"
            size={18}
            color={
              colors.primary
            }
          />

          <Text
            style={[
              styles.viewAll,
              {
                color:
                  colors.primary,
              },
            ]}
          >
            Open Map
          </Text>
        </Pressable>
      </View>

      <FlatList
        horizontal
        data={nearbyProperties}
        renderItem={renderItem}
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

  title: {
    fontSize: 22,

    fontWeight: "700",
  },

  subtitle: {
    marginTop: 4,

    fontSize: 13,
  },

  viewAllButton: {
       flexDirection: "row",

    alignItems: "center",

    paddingHorizontal: 14,

    paddingVertical: 8,

    borderRadius: 20,
  },

  viewAll: {
    marginLeft: 6,

    fontSize: 14,

    fontWeight: "600",
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
    marginTop: 8,

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
  NearbyProperties
);