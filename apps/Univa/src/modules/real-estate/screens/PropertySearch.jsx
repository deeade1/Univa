import React, {
  memo,
  useCallback,
  useMemo,
} from "react";

import {
  RefreshControl,
  ScrollView,
  StyleSheet,
} from "react-native";

import { useRouter } from "expo-router";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Hooks */
/* -------------------------------------------------------------------------- */

import usePropertySearch from "../hooks/usePropertySearch";
import useSavedProperties from "../hooks/useSavedProperties";

/* -------------------------------------------------------------------------- */
/* Components */
/* -------------------------------------------------------------------------- */

import SearchBar from "../components/search/SearchBar";
import PropertyCard from "../components/property/PropertyCard";

import DashboardSkeleton from "../components/skeleton/DashboardSkeleton";
import DashboardEmpty from "../components/empty/DashboardEmpty";

/* -------------------------------------------------------------------------- */
/* Property Search */
/* -------------------------------------------------------------------------- */

const PropertySearch = memo(() => {
  const router = useRouter();

  const { colors } = useTheme();

  /* ---------------------------------------------------------------------- */
  /* Search Hook */
  /* ---------------------------------------------------------------------- */

  const {
    keyword,

    setKeyword,

    clearKeyword,

    search,

    refresh,

    refreshing,

    loading,

    error,

    properties,

    history,

    addHistory,

    clearHistory,

    filters,

    hasFilters,

    loadMore,
  } = usePropertySearch();

  /* ---------------------------------------------------------------------- */
  /* Saved Properties */
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

  const openFilters =
    useCallback(() => {
      router.push(
        "/real-estate/search/filter"
      );
    }, [router]);

  /* ---------------------------------------------------------------------- */
  /* Search */
  /* ---------------------------------------------------------------------- */

  const handleSearch =
    useCallback(() => {
      addHistory(keyword);

      search();
    }, [
      keyword,
      addHistory,
      search,
    ]);

  /* ---------------------------------------------------------------------- */
  /* Refresh */
  /* ---------------------------------------------------------------------- */

  const handleRefresh =
    useCallback(async () => {
      await refresh();
    }, [refresh]);

  /* ---------------------------------------------------------------------- */
  /* Load More */
  /* ---------------------------------------------------------------------- */

  const handleLoadMore =
    useCallback(() => {
      loadMore();
    }, [loadMore]);

  /* ---------------------------------------------------------------------- */
  /* Result Count */
  /* ---------------------------------------------------------------------- */

  const resultCount =
    useMemo(
      () =>
        properties.length,
      [properties]
    );

  /* ---------------------------------------------------------------------- */
  /* Loading */
  /* ---------------------------------------------------------------------- */

  if (loading && resultCount === 0) {
    return <DashboardSkeleton />;
  }

  /* ---------------------------------------------------------------------- */
  /* Error */
  /* ---------------------------------------------------------------------- */

  if (error) {
    return (
      <DashboardEmpty
        title="Search Failed"
        description={
          error.message
        }
        onRetry={handleRefresh}
      />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Screen */
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
      keyboardShouldPersistTaps="handled"
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
      {/* Search Header */}
      {/* ------------------------------------------------------------------ */}

      <SearchBar
        value={keyword}
        onChangeText={setKeyword}
        onSearch={handleSearch}
        onSubmitEditing={handleSearch}
        onClear={clearKeyword}
        placeholder="Search properties, locations, or agents..."
        autoFocus
        showFilter
        hasActiveFilters={hasFilters}
        onFilterPress={openFilters}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Search Statistics */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.statsCard,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <Text
          style={[
            styles.resultCount,
            {
              color: colors.text,
            },
          ]}
        >
          {resultCount} Result
          {resultCount === 1 ? "" : "s"}
        </Text>

        {hasFilters && (
          <View
            style={[
              styles.filterBadge,
              {
                backgroundColor:
                  colors.primary,
              },
            ]}
          >
            <Text
              style={
                styles.filterBadgeText
              }
            >
              Filters Applied
            </Text>
          </View>
        )}
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Active Filters */}
      {/* ------------------------------------------------------------------ */}

      {hasFilters && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={
            false
          }
          contentContainerStyle={
            styles.filterContainer
          }
        >
          {Object.entries(filters)
            .filter(
              ([, value]) =>
                value !== null &&
                value !== "" &&
                value !== false
            )
            .map(([key, value]) => (
              <View
                key={key}
                style={[
                  styles.filterChip,
                  {
                    backgroundColor:
                      colors.primary +
                      "15",
                    borderColor:
                      colors.primary,
                  },
                ]}
              >
                <Text
                  style={[
                    styles.filterChipText,
                    {
                      color:
                        colors.primary,
                    },
                  ]}
                >
                  {key}:{" "}
                  {String(value)}
                </Text>
              </View>
            ))}
        </ScrollView>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Recent Searches */}
      {/* ------------------------------------------------------------------ */}

      {history.length > 0 && (
        <>
          <View
            style={
              styles.sectionHeader
            }
          >
            <Text
              style={[
                styles.sectionTitle,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              Recent Searches
            </Text>

            <Text
              onPress={
                clearHistory
              }
              style={[
                styles.clearText,
                {
                  color:
                    colors.primary,
                },
              ]}
            >
              Clear
            </Text>
          </View>

          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={
              false
            }
            contentContainerStyle={
              styles.historyContainer
            }
          >
            {history.map(
              (
                item,
                index
              ) => (
                <Text
                  key={`${item}-${index}`}
                  style={[
                    styles.historyChip,
                    {
                      backgroundColor:
                        colors.card,
                      borderColor:
                        colors.border,
                      color:
                        colors.text,
                    },
                  ]}
                  onPress={() => {
                    setKeyword(
                      item
                    );

                    search();
                  }}
                >
                  {item}
                </Text>
              )
            )}
          </ScrollView>
        </>
      )}
            {/* ------------------------------------------------------------------ */}
      {/* Search Results */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.resultsContainer}>
        {resultCount > 0 ? (
          <>
            <View style={styles.sectionHeader}>
              <Text
                style={[
                  styles.sectionTitle,
                  {
                    color: colors.text,
                  },
                ]}
              >
                Properties
              </Text>

              <Text
                style={[
                  styles.resultSummary,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                {resultCount} found
              </Text>
            </View>

            {properties.map(
              (property) => (
                <PropertyCard
                  key={property.id}
                  property={property}
                  saved={isSaved(
                    property.id
                  )}
                  onPress={() =>
                    openProperty(
                      property
                    )
                  }
                  onFavoritePress={() =>
                    toggleSaved(
                      property.id
                    )
                  }
                  style={
                    styles.propertyCard
                  }
                />
              )
            )}
          </>
        ) : (
          /* -------------------------------------------------------------- */
          /* Empty Search Results */
          /* -------------------------------------------------------------- */

          <DashboardEmpty
            title="No Properties Found"
            description={
              keyword
                ? `No properties matched "${keyword}". Try another search or adjust your filters.`
                : "Start typing to search for properties."
            }
            actionLabel={
              hasFilters
                ? "Clear Filters"
                : undefined
            }
            onAction={
              hasFilters
                ? clearKeyword
                : undefined
            }
          />
        )}
      </View>
            {/* ------------------------------------------------------------------ */}
      {/* Load More */}
      {/* ------------------------------------------------------------------ */}

      {resultCount > 0 && (
        <View style={styles.paginationContainer}>
          <Pressable
            style={({ pressed }) => [
              styles.loadMoreButton,
              {
                backgroundColor:
                  colors.primary,
                opacity: pressed ? 0.8 : 1,
              },
            ]}
            onPress={handleLoadMore}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator
                color="#FFFFFF"
              />
            ) : (
              <>
                <MaterialCommunityIcons
                  name="refresh"
                  size={20}
                  color="#FFFFFF"
                />

                <Text
                  style={
                    styles.loadMoreText
                  }
                >
                  Load More Properties
                </Text>
              </>
            )}
          </Pressable>
        </View>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Pagination Footer */}
      {/* ------------------------------------------------------------------ */}

      {resultCount > 0 && (
        <View
          style={[
            styles.paginationFooter,
            {
              borderTopColor:
                colors.border,
            },
          ]}
        >
          <MaterialCommunityIcons
            name="home-search"
            size={20}
            color={
              colors.primary
            }
          />

          <Text
            style={[
              styles.paginationText,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Showing {resultCount}{" "}
            {resultCount === 1
              ? "property"
              : "properties"}
          </Text>
        </View>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* End of Results */}
      {/* ------------------------------------------------------------------ */}

      {resultCount > 0 && !loading && (
        <View style={styles.endContainer}>
          <MaterialCommunityIcons
            name="check-circle-outline"
            size={24}
            color="#22C55E"
          />

          <Text
            style={[
              styles.endTitle,
              {
                color: colors.text,
              },
            ]}
          >
            You've reached the end
          </Text>

          <Text
            style={[
              styles.endSubtitle,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Try refining your search or
            adjusting the filters to discover
            more properties.
          </Text>
        </View>
      )}
            {/* ------------------------------------------------------------------ */}
      {/* Search Tips */}
      {/* ------------------------------------------------------------------ */}

      {resultCount > 0 && (
        <View
          style={[
            styles.searchTipsCard,
            {
              backgroundColor: colors.card,
              borderColor: colors.border,
            },
          ]}
        >
          <MaterialCommunityIcons
            name="lightbulb-outline"
            size={22}
            color={colors.primary}
          />

          <View style={styles.searchTipsContent}>
            <Text
              style={[
                styles.searchTipsTitle,
                {
                  color: colors.text,
                },
              ]}
            >
              Search Tips
            </Text>

            <Text
              style={[
                styles.searchTipsText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Refine your search using filters
              such as price range, location,
              bedrooms, bathrooms, amenities,
              and property type to find your
              ideal property faster.
            </Text>
          </View>
        </View>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Bottom Spacer */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.bottomSpacing} />
    </ScrollView>
  );
});

PropertySearch.displayName =
  "PropertySearch";

  /* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  content: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 40,
  },

  /* ---------------------------------------------------------------------- */
  /* Statistics */
  /* ---------------------------------------------------------------------- */

  statsCard: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 20,
    marginBottom: 16,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 16,
    borderWidth: 1,
  },

  resultCount: {
    fontSize: 16,
    fontWeight: "700",
  },

  resultSummary: {
    fontSize: 14,
  },

  filterBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
  },

  filterBadgeText: {
    color: "#FFFFFF",
    fontWeight: "600",
    fontSize: 12,
  },

  /* ---------------------------------------------------------------------- */
  /* Filters */
  /* ---------------------------------------------------------------------- */

  filterContainer: {
    paddingBottom: 16,
    gap: 10,
  },

  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    marginRight: 10,
  },

  filterChipText: {
    fontSize: 13,
    fontWeight: "600",
  },

  /* ---------------------------------------------------------------------- */
  /* Section */
  /* ---------------------------------------------------------------------- */

  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 20,
    marginBottom: 16,
  },

  sectionTitle: {
    fontSize: 20,
    fontWeight: "700",
  },

  clearText: {
    fontSize: 14,
    fontWeight: "600",
  },

  /* ---------------------------------------------------------------------- */
  /* History */
  /* ---------------------------------------------------------------------- */

  historyContainer: {
    paddingBottom: 12,
  },

  historyChip: {
    marginRight: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 999,
    borderWidth: 1,
    overflow: "hidden",
    fontSize: 14,
  },

  /* ---------------------------------------------------------------------- */
  /* Results */
  /* ---------------------------------------------------------------------- */

  resultsContainer: {
    marginTop: 12,
  },

  propertyCard: {
    marginBottom: 18,
  },

  /* ---------------------------------------------------------------------- */
  /* Pagination */
  /* ---------------------------------------------------------------------- */

  paginationContainer: {
    marginTop: 28,
    alignItems: "center",
  },

  loadMoreButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    minWidth: 220,
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 14,
  },

  loadMoreText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 15,
    marginLeft: 8,
  },

  paginationFooter: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 24,
    paddingTop: 20,
    borderTopWidth: StyleSheet.hairlineWidth,
  },

  paginationText: {
    marginLeft: 8,
    fontSize: 14,
  },

  /* ---------------------------------------------------------------------- */
  /* End */
  /* ---------------------------------------------------------------------- */

  endContainer: {
    alignItems: "center",
    marginTop: 32,
    paddingHorizontal: 20,
  },

  endTitle: {
    marginTop: 12,
    fontSize: 18,
    fontWeight: "700",
    textAlign: "center",
  },

  endSubtitle: {
    marginTop: 8,
    fontSize: 14,
    lineHeight: 22,
    textAlign: "center",
  },

  /* ---------------------------------------------------------------------- */
  /* Search Tips */
  /* ---------------------------------------------------------------------- */

  searchTipsCard: {
    flexDirection: "row",
    marginTop: 32,
    padding: 18,
    borderRadius: 18,
    borderWidth: 1,
  },

  searchTipsContent: {
    flex: 1,
    marginLeft: 14,
  },

  searchTipsTitle: {
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 6,
  },

  searchTipsText: {
    fontSize: 14,
    lineHeight: 22,
  },

  /* ---------------------------------------------------------------------- */
  /* Bottom */
  /* ---------------------------------------------------------------------- */

  bottomSpacing: {
    height: 40,
  },
});

/* -------------------------------------------------------------------------- */
/* Export */
/* -------------------------------------------------------------------------- */

export default PropertySearch;