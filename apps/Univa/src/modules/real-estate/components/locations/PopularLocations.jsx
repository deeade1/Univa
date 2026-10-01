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

import LocationCard from "./LocationCard";
import PopularLocationsSkeleton from "./PopularLocationsSkeleton";
import PopularLocationsEmpty from "./PopularLocationsEmpty";

/* -------------------------------------------------------------------------- */
/* Popular Locations */
/* -------------------------------------------------------------------------- */

function PopularLocations() {
  const router = useRouter();

  const { colors } = useTheme();

  const {
    popularLocations,
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

  const openLocation =
    useCallback(
      (location) => {
        router.push({
          pathname:
            "/real-estate/map",

          params: {
            location:
              location.slug ??
              location.id,
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
        <LocationCard
          location={item}
          onPress={() =>
            openLocation(item)
          }
        />
      ),
      [openLocation]
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
    popularLocations.length === 0
  ) {
    return (
      <PopularLocationsSkeleton />
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
          Unable to load locations
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
          Something went wrong while
          loading popular locations.
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
    popularLocations.length === 0
  ) {
    return (
      <PopularLocationsEmpty />
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
              name="location"
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
              Popular Locations
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
            Discover trending cities
            and neighborhoods with
            the highest property
            demand.
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
            Browse Map
          </Text>

          <Ionicons
            name="map-outline"
            size={18}
            color={
              colors.primary
            }
          />
        </Pressable>
      </View>

      <FlatList
        horizontal
        data={
          popularLocations
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
    marginRight: 4,

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
    paddingHorizontal: 24,

    paddingVertical: 48,

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

    fontSize: 14,

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
  PopularLocations
);