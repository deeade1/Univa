// ✅ Only ONE import statement for React at the top
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

// ✅ Fixed import path - going up one level from components/featured/
import { useRealEstate } from "../../context/RealEstateProvider";

import FeaturedPropertyCard from "./FeaturedPropertyCard";
import FeaturedPropertiesSkeleton from "./FeaturedPropertiesSkeleton";
import FeaturedPropertiesEmpty from "./FeaturedPropertiesEmpty";

/* -------------------------------------------------------------------------- */
/* Featured Properties */
/* -------------------------------------------------------------------------- */

function FeaturedProperties() {
  const router = useRouter();

  const { colors } = useTheme();

  const {
    featuredProperties = [],
    loading,
    error,
    refresh,
  } = useRealEstate();

  /* -------------------------------------------------------------------------- */
  /* Actions */
  /* -------------------------------------------------------------------------- */

  const handleViewAll = useCallback(() => {
    router.push("/real-estate/properties?featured=true");
  }, [router]);

  const openProperty = useCallback((property) => {
    router.push({
      pathname: "/real-estate/[slug]",
      params: {
        slug: property.slug ?? property.id,
      },
    });
  }, [router]);

  const handleFavorite = useCallback((property) => {
    console.log("Favorite:", property.id);
    // TODO: add/remove favorite mutation
  }, []);

  /* -------------------------------------------------------------------------- */
  /* Render */
  /* -------------------------------------------------------------------------- */

  const renderItem = useCallback(({ item }) => (
    <FeaturedPropertyCard
      property={item}
      onPress={() => openProperty(item)}
      onFavoritePress={() => handleFavorite(item)}
    />
  ), [openProperty, handleFavorite]);

  const keyExtractor = useCallback((item) => String(item.id), []);

  /* -------------------------------------------------------------------------- */
  /* Loading */
  /* -------------------------------------------------------------------------- */

  if (loading && featuredProperties.length === 0) {
    return <FeaturedPropertiesSkeleton />;
  }

  /* -------------------------------------------------------------------------- */
  /* Error */
  /* -------------------------------------------------------------------------- */

  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Ionicons
          name="cloud-offline-outline"
          size={44}
          color={colors.error}
        />

        <Text
          style={[
            styles.errorTitle,
            {
              color: colors.text,
            },
          ]}
        >
          Unable to load featured properties
        </Text>

        <Pressable
          onPress={refresh}
          style={[
            styles.retryButton,
            {
              backgroundColor: colors.primary,
            },
          ]}
        >
          <Text style={styles.retryText}>Retry</Text>
        </Pressable>
      </View>
    );
  }

  /* -------------------------------------------------------------------------- */
  /* Empty */
  /* -------------------------------------------------------------------------- */

  if (featuredProperties.length === 0) {
    return <FeaturedPropertiesEmpty />;
  }

  /* -------------------------------------------------------------------------- */
  /* UI */
  /* -------------------------------------------------------------------------- */

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text
          style={[
            styles.title,
            {
              color: colors.text,
            },
          ]}
        >
          Featured Properties
        </Text>

        <Pressable onPress={handleViewAll} style={styles.viewAllButton}>
          <Text
            style={[
              styles.viewAll,
              {
                color: colors.primary,
              },
            ]}
          >
            View All
          </Text>

          <Ionicons
            name="chevron-forward"
            size={16}
            color={colors.primary}
          />
        </Pressable>
      </View>

      <FlatList
        horizontal
        data={featuredProperties}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={{ width: 16 }} />}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 28,
  },

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

  viewAllButton: {
    flexDirection: "row",
    alignItems: "center",
  },

  viewAll: {
    fontSize: 14,
    fontWeight: "600",
    marginRight: 2,
  },

  list: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },

  errorContainer: {
    paddingVertical: 40,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
  },

  errorTitle: {
    marginTop: 14,
    fontSize: 16,
    fontWeight: "600",
    textAlign: "center",
  },

  retryButton: {
    marginTop: 20,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 10,
  },

  retryText: {
    color: "#FFFFFF",
    fontWeight: "700",
  },
});

// ✅ Correct export - single line
export default memo(FeaturedProperties);