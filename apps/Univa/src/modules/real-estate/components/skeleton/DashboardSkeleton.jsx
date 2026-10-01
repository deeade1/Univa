import React, { memo } from "react";
import {
  ScrollView,
  StyleSheet,
  View,
} from "react-native";

import Header from "../header/Header";
import CategoriesSkeleton from "../categories/CategoriesSkeleton";
import FeaturedPropertiesSkeleton from "../featured/FeaturedPropertiesSkeleton";
import RecommendedSkeleton from "../recommended/RecommendedPropertiesSkeleton";
import NearbyPropertiesSkeleton from "../nearby/NearbyPropertiesSkeleton";
import PopularLocationsSkeleton from "../locations/PopularLocationsSkeleton";
import RecentPropertiesSkeleton from "../recent/RecentPropertiesSkeleton";
import FeaturedAgentsSkeleton from "../agent/FeaturedAgentsSkeleton";

/* -------------------------------------------------------------------------- */
/* Search Skeleton */
/* -------------------------------------------------------------------------- */

const SearchSkeleton = memo(() => {
  return (
    <View style={styles.searchContainer}>
      <View style={styles.searchBar} />
      <View style={styles.filterButton} />
    </View>
  );
});

SearchSkeleton.displayName = "SearchSkeleton";

/* -------------------------------------------------------------------------- */
/* Dashboard Skeleton */
/* -------------------------------------------------------------------------- */

const DashboardSkeleton = memo(() => {
  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* Header */}
      <Header />

      {/* Search */}
      <SearchSkeleton />

      {/* Categories */}
      <CategoriesSkeleton />

      {/* Featured */}
      <FeaturedPropertiesSkeleton />

      {/* Recommended */}
      <RecommendedSkeleton />

      {/* Nearby */}
      <NearbyPropertiesSkeleton />

      {/* Popular Locations */}
      <PopularLocationsSkeleton />

      {/* Recent Properties */}
      <RecentPropertiesSkeleton />

      {/* Featured Agents */}
      <FeaturedAgentsSkeleton />

      <View style={styles.bottomSpacing} />
    </ScrollView>
  );
});

DashboardSkeleton.displayName = "DashboardSkeleton";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  content: {
    paddingBottom: 40,
  },

  searchContainer: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    marginTop: 20,
    marginBottom: 12,
  },

  searchBar: {
    flex: 1,
    height: 54,
    borderRadius: 16,
    backgroundColor: "#E5E7EB",
  },

  filterButton: {
    width: 54,
    height: 54,
    borderRadius: 16,
    backgroundColor: "#E5E7EB",
    marginLeft: 12,
  },

  bottomSpacing: {
    height: 32,
  },
});

export default DashboardSkeleton;





