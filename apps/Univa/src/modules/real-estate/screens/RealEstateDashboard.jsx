import React, {
  memo,
  useCallback,
} from "react";

import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";

import { useRouter } from "expo-router";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Hooks */
/* -------------------------------------------------------------------------- */

import useDashboard from "../hooks/useDashboard";
import usePropertySearch from "../hooks/usePropertySearch";
import useSavedProperties from "../hooks/useSavedProperties";

/* -------------------------------------------------------------------------- */
/* Components */
/* -------------------------------------------------------------------------- */

import Header from "../components/header/Header";

import SearchBar from "../components/search/SearchBar";

// ✅ Fixed: Using CategoriesGrid instead of Categories
import CategoriesGrid from "../components/categories/CategoriesGrid";

import FeaturedProperties from "../components/featured/FeaturedProperties";

import RecommendedProperties from "../components/recommended/RecommendedProperties";

import NearbyProperties from "../components/nearby/NearbyProperties";

import PropertyMap from "../components/map/PropertyMap";

import MapLegend from "../components/map/MapLegend";

import PopularLocations from "../components/locations/PopularLocations";

import RecentProperties from "../components/recent/RecentProperties";

import FeaturedAgents from "../components/agent/FeaturedAgents";

import Footer from "../components/footer/Footer";

import DashboardSkeleton from "../components/skeleton/DashboardSkeleton";

import DashboardEmpty from "../components/empty/DashboardEmpty";

/* -------------------------------------------------------------------------- */
/* Dashboard */
/* -------------------------------------------------------------------------- */

const RealEstateDashboard = memo(() => {
  const router = useRouter();

  const { colors } = useTheme();

  /* ---------------------------------------------------------------------- */
  /* Dashboard Data */
  /* ---------------------------------------------------------------------- */

  const {
    featuredProperties,

    recommendedProperties,

    nearbyProperties,

    recentProperties,

    popularLocations,

    featuredAgents,

    propertyCategories,

    loading,

    refreshing,

    error,

    refreshDashboard,
  } = useDashboard();

  /* ---------------------------------------------------------------------- */
  /* Search */
  /* ---------------------------------------------------------------------- */

  const {
    keyword,

    setKeyword,

    search,

    clearKeyword,
  } = usePropertySearch();

  /* ---------------------------------------------------------------------- */
  /* Saved */
  /* ---------------------------------------------------------------------- */

  const {
    toggleSaved,

    isSaved,
  } = useSavedProperties();

  /* ---------------------------------------------------------------------- */
  /* Navigation */
  /* ---------------------------------------------------------------------- */

  const openProperty =
    useCallback(
      (property) => {
        router.push({
          pathname:
            "/real-estate/property/[id]",

          params: {
            id: property.id,
          },
        });
      },
      [router]
    );

  const openAgent =
    useCallback(
      (agent) => {
        router.push({
          pathname:
            "/real-estate/agent/[id]",

          params: {
            id: agent.id,
          },
        });
      },
      [router]
    );

  const openLocation =
    useCallback(
      (location) => {
        router.push({
          pathname:
            "/real-estate/location/[id]",

          params: {
            id: location.id,
          },
        });
      },
      [router]
    );

  const openCategory =
    useCallback(
      (category) => {
        router.push({
          pathname:
            "/real-estate/category/[slug]",

          params: {
            slug: category.slug,
          },
        });
      },
      [router]
    );

  /* ---------------------------------------------------------------------- */
  /* Search */
  /* ---------------------------------------------------------------------- */

  const handleSearch =
    useCallback(() => {
      search();
    }, [search]);

  /* ---------------------------------------------------------------------- */
  /* Refresh */
  /* ---------------------------------------------------------------------- */

  const handleRefresh =
    useCallback(async () => {
      await refreshDashboard();
    }, [refreshDashboard]);

  /* ---------------------------------------------------------------------- */
  /* Loading */
  /* ---------------------------------------------------------------------- */

  if (loading) {
    return <DashboardSkeleton />;
  }

  /* ---------------------------------------------------------------------- */
  /* Error / Empty */
  /* ---------------------------------------------------------------------- */

  if (
    error &&
    featuredProperties.length === 0
  ) {
    return (
      <DashboardEmpty
        title="Unable to load dashboard"
        description={
          error.message
        }
        onRetry={
          handleRefresh
        }
      />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Content */
  /* ---------------------------------------------------------------------- */

  return (
    <ScrollView
      style={[
        styles.container,
        {
          backgroundColor:
            colors.background,
        },
      ]}
      contentContainerStyle={
        styles.content
      }
      showsVerticalScrollIndicator={
        false
      }
      refreshControl={
        <RefreshControl
          refreshing={
            refreshing
          }
          onRefresh={
            handleRefresh
          }
          tintColor={
            colors.primary
          }
          colors={[
            colors.primary,
          ]}
        />
      }
    >
      {/* ------------------------------------------------------------------ */}
      {/* Header */}
      {/* ------------------------------------------------------------------ */}

      <Header
        onNotificationPress={() =>
          router.push("/notifications")
        }
        onProfilePress={() =>
          router.push("/profile")
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Search */}
      {/* ------------------------------------------------------------------ */}

      <SearchBar
        value={keyword}
        onChangeText={setKeyword}
        onSubmitEditing={handleSearch}
        onSearch={handleSearch}
        onClear={clearKeyword}
        placeholder="Search properties, cities or agents..."
        onFilterPress={() =>
          router.push(
            "/real-estate/search/filter"
          )
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Categories */}
      {/* ------------------------------------------------------------------ */}

      {/* ✅ Fixed: Using CategoriesGrid component */}
      <CategoriesGrid
        categories={propertyCategories}
        onCategoryPress={
          openCategory
        }
        onSeeAll={() =>
          router.push(
            "/real-estate/categories"
          )
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Featured Properties */}
      {/* ------------------------------------------------------------------ */}

      <FeaturedProperties
        properties={
          featuredProperties
        }
        onPropertyPress={
          openProperty
        }
        onFavoritePress={(
          property
        ) =>
          toggleSaved(
            property.id
          )
        }
        isSaved={isSaved}
        onSeeAll={() =>
          router.push(
            "/real-estate/properties/featured"
          )
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Recommended Properties */}
      {/* ------------------------------------------------------------------ */}

      <RecommendedProperties
        properties={
          recommendedProperties
        }
        onPropertyPress={
          openProperty
        }
        onFavoritePress={(
          property
        ) =>
          toggleSaved(
            property.id
          )
        }
        isSaved={isSaved}
        onSeeAll={() =>
          router.push(
            "/real-estate/properties/recommended"
          )
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Nearby Properties */}
      {/* ------------------------------------------------------------------ */}

      <NearbyProperties
        properties={nearbyProperties}
        onPropertyPress={openProperty}
        onFavoritePress={(property) =>
          toggleSaved(property.id)
        }
        isSaved={isSaved}
        onSeeAll={() =>
          router.push(
            "/real-estate/properties/nearby"
          )
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Property Map */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.mapSection}>
        <PropertyMap
          properties={nearbyProperties}
          onMarkerPress={openProperty}
          onCalloutPress={openProperty}
          showsUserLocation
          showsMyLocationButton
          followsUserLocation={false}
        />
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Map Legend */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.legendContainer}>
        <MapLegend />
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Popular Locations */}
      {/* ------------------------------------------------------------------ */}

      <PopularLocations
        locations={popularLocations}
        onLocationPress={openLocation}
        onSeeAll={() =>
          router.push(
            "/real-estate/locations"
          )
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Recent Properties */}
      {/* ------------------------------------------------------------------ */}

      <RecentProperties
        properties={recentProperties}
        onPropertyPress={openProperty}
        onFavoritePress={(property) =>
          toggleSaved(property.id)
        }
        isSaved={isSaved}
        onSeeAll={() =>
          router.push(
            "/real-estate/properties/recent"
          )
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Featured Agents */}
      {/* ------------------------------------------------------------------ */}

      <FeaturedAgents
        agents={featuredAgents}
        onAgentPress={openAgent}
        onSeeAll={() =>
          router.push(
            "/real-estate/agents"
          )
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Footer */}
      {/* ------------------------------------------------------------------ */}

      <Footer
        version="v1.0.0"
        onBrowseProperties={() =>
          router.push(
            "/real-estate/properties"
          )
        }
        onExploreMap={() =>
          router.push(
            "/real-estate/map"
          )
        }
        onBecomeAgent={() =>
          router.push(
            "/real-estate/agent/register"
          )
        }
        onSavedProperties={() =>
          router.push(
            "/real-estate/saved"
          )
        }
        onSupport={() =>
          router.push(
            "/support"
          )
        }
        onPrivacyPolicy={() =>
          router.push(
            "/privacy-policy"
          )
        }
        onTerms={() =>
          router.push(
            "/terms"
          )
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Bottom Spacing */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={styles.bottomSpacing}
      />
    </ScrollView>
  );
});

RealEstateDashboard.displayName =
  "RealEstateDashboard";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  content: {
    paddingBottom: 32,
  },

  mapSection: {
    marginTop: 24,
    marginHorizontal: 20,
  },

  legendContainer: {
    marginTop: 16,
    marginHorizontal: 20,
    marginBottom: 8,
  },

  bottomSpacing: {
    height: 40,
  },
});

/* -------------------------------------------------------------------------- */
/* Export */
/* -------------------------------------------------------------------------- */

export default RealEstateDashboard;