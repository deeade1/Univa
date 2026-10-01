import React, {
  memo,
  useCallback,
  useMemo,
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

import theme  from "@/theme";

import { useRealEstate } from "../../context/RealEstateProvider";

import CategoryCard from "./CategoryCard";
import CategoriesSkeleton from "./CategoriesSkeleton";
import CategoriesEmpty from "./CategoriesEmpty";

/* -------------------------------------------------------------------------- */
/* Categories Grid */
/* -------------------------------------------------------------------------- */

function CategoriesGrid() {
  const router = useRouter();

  const { colors } = useTheme();

  const {
    categories = [],
    loading,
    error,
    refresh,
  } = useRealEstate();

  /* -------------------------------------------------------------------------- */
  /* Category Data */
  /* -------------------------------------------------------------------------- */

  const categoryData =
    useMemo(() => {
      return categories.map(
        (category) => ({
          id: category.id,

          name:
            category.name ??
            "Category",

          slug:
            category.slug ??
            String(category.id),

          icon:
            category.icon ??
            "home-outline",

          color:
            category.color ??
            colors.primary,

          count:
            category.propertyCount ??
            category.count ??
            0,
        })
      );
    }, [categories, colors.primary]);

  /* -------------------------------------------------------------------------- */
  /* Navigation */
  /* -------------------------------------------------------------------------- */

  const openCategory =
    useCallback(
      (category) => {
        router.push({
          pathname:
            "/real-estate/properties",

          params: {
            category:
              category.slug,
          },
        });
      },
      [router]
    );

  const handleViewAll =
    useCallback(() => {
      router.push(
        "/real-estate/properties"
      );
    }, [router]);
      /* -------------------------------------------------------------------------- */
  /* Render Item */
  /* -------------------------------------------------------------------------- */

  const renderItem =
    useCallback(
      ({ item }) => (
        <CategoryCard
          category={item}
          onPress={() =>
            openCategory(item)
          }
        />
      ),
      [openCategory]
    );

  const keyExtractor =
    useCallback(
      (item) => String(item.id),
      []
    );

  /* -------------------------------------------------------------------------- */
  /* Loading */
  /* -------------------------------------------------------------------------- */

  if (
    loading &&
    categoryData.length === 0
  ) {
    return (
      <CategoriesSkeleton />
    );
  }

  /* -------------------------------------------------------------------------- */
  /* Error */
  /* -------------------------------------------------------------------------- */

  if (error) {
    return (
      <View
        style={
          styles.errorContainer
        }
      >
        <Ionicons
          name="cloud-offline-outline"
          size={44}
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
          Unable to load
          categories
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

  /* -------------------------------------------------------------------------- */
  /* Empty */
  /* -------------------------------------------------------------------------- */

  if (
    categoryData.length === 0
  ) {
    return (
      <CategoriesEmpty />
    );
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
          Browse Categories
        </Text>

        <Pressable
          onPress={handleViewAll}
          style={styles.viewAllButton}
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
            color={colors.primary}
          />
        </Pressable>
      </View>

      <FlatList
        data={categoryData}
        renderItem={renderItem}
        keyExtractor={
          keyExtractor
        }
        numColumns={2}
        scrollEnabled={false}
        columnWrapperStyle={
          styles.row
        }
        contentContainerStyle={
          styles.list
        }
        showsVerticalScrollIndicator={
          false
        }
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

  list: {
    paddingHorizontal: 16,

    paddingBottom: 6,
  },

  row: {
    justifyContent:
      "space-between",

    marginBottom: 16,
  },

  errorContainer: {
    paddingVertical: 40,

    paddingHorizontal: 24,

    justifyContent: "center",

    alignItems: "center",
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

    fontSize: 15,
  },
});

export default memo(
  CategoriesGrid
);