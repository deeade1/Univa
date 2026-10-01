import React, {
  memo,
  useCallback,
  useMemo,
  useState,
} from "react";

import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
  Text,
  Pressable,
} from "react-native";

import { useRouter } from "expo-router";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Hooks */
/* -------------------------------------------------------------------------- */

import useSavedProperties from "../hooks/useSavedProperties";

/* -------------------------------------------------------------------------- */
/* Components */
/* -------------------------------------------------------------------------- */

import SearchBar from "../components/search/SearchBar";
import PropertyCard from "../components/property/PropertyCard";

import DashboardSkeleton from "../components/skeleton/DashboardSkeleton";
import DashboardEmpty from "../components/empty/DashboardEmpty";

/* -------------------------------------------------------------------------- */
/* Saved Properties */
/* -------------------------------------------------------------------------- */

const SavedProperties = memo(() => {
  const router = useRouter();

  const { colors } = useTheme();

  const {
    savedProperties,

    loading,

    refreshing,

    error,

    refresh,

    removeProperty,
  } = useSavedProperties();

  /* ---------------------------------------------------------------------- */
  /* State */
  /* ---------------------------------------------------------------------- */

  const [keyword, setKeyword] =
    useState("");

  const [viewMode, setViewMode] =
    useState("list");

  const [sortBy, setSortBy] =
    useState("recent");

  /* ---------------------------------------------------------------------- */
  /* Filtered Properties */
  /* ---------------------------------------------------------------------- */

  const filteredProperties =
    useMemo(() => {
      let items = [
        ...savedProperties,
      ];

      if (keyword.trim()) {
        const query =
          keyword.toLowerCase();

        items = items.filter(
          (property) =>
            property.title
              ?.toLowerCase()
              .includes(query) ||
            property.address
              ?.toLowerCase()
              .includes(query) ||
            property.city
              ?.toLowerCase()
              .includes(query)
        );
      }

      switch (sortBy) {
        case "price_low":
          items.sort(
            (a, b) =>
              a.price - b.price
          );
          break;

        case "price_high":
          items.sort(
            (a, b) =>
              b.price - a.price
          );
          break;

        case "name":
          items.sort((a, b) =>
            a.title.localeCompare(
              b.title
            )
          );
          break;

        default:
          break;
      }

      return items;
    }, [
      savedProperties,
      keyword,
      sortBy,
    ]);

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

  /* ---------------------------------------------------------------------- */
  /* Actions */
  /* ---------------------------------------------------------------------- */

  const handleRefresh =
    useCallback(async () => {
      await refresh();
    }, [refresh]);

  const handleRemove =
    useCallback(
      async (property) => {
        await removeProperty(
          property.id
        );
      },
      [removeProperty]
    );

  const clearSearch =
    useCallback(() => {
      setKeyword("");
    }, []);

  /* ---------------------------------------------------------------------- */
  /* Loading */
  /* ---------------------------------------------------------------------- */

  if (loading) {
    return <DashboardSkeleton />;
  }

  /* ---------------------------------------------------------------------- */
  /* Error */
  /* ---------------------------------------------------------------------- */

  if (error) {
    return (
      <DashboardEmpty
        title="Unable to load saved properties"
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
      showsVerticalScrollIndicator={
        false
      }
      keyboardShouldPersistTaps="handled"
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

      <View style={styles.header}>
        <View style={styles.headerContent}>
          <Text
            style={[
              styles.title,
              {
                color: colors.text,
              },
            ]}
          >
            Saved Properties
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
            {filteredProperties.length} saved
            {filteredProperties.length === 1
              ? " property"
              : " properties"}
          </Text>
        </View>

        <Pressable
          style={({ pressed }) => [
            styles.backButton,
            {
              backgroundColor:
                colors.card,
              opacity: pressed ? 0.8 : 1,
            },
          ]}
          onPress={() => router.back()}
        >
          <MaterialCommunityIcons
            name="arrow-left"
            size={22}
            color={colors.text}
          />
        </Pressable>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Search */}
      {/* ------------------------------------------------------------------ */}

      <SearchBar
        value={keyword}
        onChangeText={setKeyword}
        onClear={clearSearch}
        placeholder="Search saved properties..."
      />

      {/* ------------------------------------------------------------------ */}
      {/* Toolbar */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.toolbar,
          {
            backgroundColor:
              colors.card,
            borderColor:
              colors.border,
          },
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Results */}
        {/* -------------------------------------------------------------- */}

        <Text
          style={[
            styles.resultText,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          {filteredProperties.length} Result
          {filteredProperties.length === 1
            ? ""
            : "s"}
        </Text>

        <View style={styles.toolbarActions}>
          {/* ------------------------------------------------------------ */}
          {/* View Toggle */}
          {/* ------------------------------------------------------------ */}

          <Pressable
            style={[
              styles.iconButton,
              viewMode ===
                "list" && {
                backgroundColor:
                  colors.primary,
              },
            ]}
            onPress={() =>
              setViewMode("list")
            }
          >
            <MaterialCommunityIcons
              name="view-list"
              size={20}
              color={
                viewMode ===
                "list"
                  ? "#FFFFFF"
                  : colors.text
              }
            />
          </Pressable>

          <Pressable
            style={[
              styles.iconButton,
              viewMode ===
                "grid" && {
                backgroundColor:
                  colors.primary,
              },
            ]}
            onPress={() =>
              setViewMode("grid")
            }
          >
            <MaterialCommunityIcons
              name="view-grid"
              size={20}
              color={
                viewMode ===
                "grid"
                  ? "#FFFFFF"
                  : colors.text
              }
            />
          </Pressable>

          {/* ------------------------------------------------------------ */}
          {/* Sort */}
          {/* ------------------------------------------------------------ */}

          <Pressable
            style={[
              styles.sortButton,
              {
                borderColor:
                  colors.border,
              },
            ]}
            onPress={() => {
              const next =
                sortBy ===
                "recent"
                  ? "price_low"
                  : sortBy ===
                    "price_low"
                  ? "price_high"
                  : sortBy ===
                    "price_high"
                  ? "name"
                  : "recent";

              setSortBy(next);
            }}
          >
            <MaterialCommunityIcons
              name="sort"
              size={18}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.sortText,
                {
                  color:
                    colors.primary,
                },
              ]}
            >
              {sortBy ===
                "recent" &&
                "Recent"}

              {sortBy ===
                "price_low" &&
                "Price ↑"}

              {sortBy ===
                "price_high" &&
                "Price ↓"}

              {sortBy ===
                "name" &&
                "A-Z"}
            </Text>
          </Pressable>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Bulk Actions */}
      {/* ------------------------------------------------------------------ */}

      {savedProperties.length >
        0 && (
        <View
          style={
            styles.bulkActions
          }
        >
          <Pressable
            onPress={
              clearSearch
            }
          >
            <Text
              style={[
                styles.bulkText,
                {
                  color:
                    colors.primary,
                },
              ]}
            >
              Clear Search
            </Text>
          </Pressable>

          <Pressable
            onPress={() => {
              // Future:
              // remove all saved
            }}
          >
            <Text
              style={[
                styles.bulkText,
                {
                  color: "#EF4444",
                },
              ]}
            >
              Remove All
            </Text>
          </Pressable>
        </View>
      )}
            {/* ------------------------------------------------------------------ */}
      {/* Saved Properties */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.resultsContainer}>
        {filteredProperties.length > 0 ? (
          viewMode === "grid" ? (
            /* ------------------------------------------------------------ */
            /* Grid View */
            /* ------------------------------------------------------------ */

            <View style={styles.gridContainer}>
              {filteredProperties.map(
                (property) => (
                  <View
                    key={property.id}
                    style={
                      styles.gridItem
                    }
                  >
                    <PropertyCard
                      property={property}
                      compact
                      saved
                      onPress={() =>
                        openProperty(
                          property
                        )
                      }
                      onFavoritePress={() =>
                        handleRemove(
                          property
                        )
                      }
                    />
                  </View>
                )
              )}
            </View>
          ) : (
            /* ------------------------------------------------------------ */
            /* List View */
            /* ------------------------------------------------------------ */

            filteredProperties.map(
              (property) => (
                <PropertyCard
                  key={property.id}
                  property={property}
                  saved
                  style={
                    styles.propertyCard
                  }
                  onPress={() =>
                    openProperty(
                      property
                    )
                  }
                  onFavoritePress={() =>
                    handleRemove(
                      property
                    )
                  }
                />
              )
            )
          )
        ) : (
          /* -------------------------------------------------------------- */
          /* Empty Saved Properties */
          /* -------------------------------------------------------------- */

          <DashboardEmpty
            title="No Saved Properties"
            description={
              keyword
                ? `No saved properties match "${keyword}".`
                : "You haven't saved any properties yet. Browse properties and tap the heart icon to save your favorites."
            }
            actionLabel="Browse Properties"
            onAction={() =>
              router.push(
                "/real-estate/properties"
              )
            }
          />
        )}
      </View>
            {/* ------------------------------------------------------------------ */}
      {/* Collection Statistics */}
      {/* ------------------------------------------------------------------ */}

      {filteredProperties.length > 0 && (
        <View
          style={[
            styles.statisticsCard,
            {
              backgroundColor: colors.card,
              borderColor: colors.border,
            },
          ]}
        >
          <View style={styles.statisticsItem}>
            <MaterialCommunityIcons
              name="heart"
              size={26}
              color="#EF4444"
            />

            <Text
              style={[
                styles.statisticsValue,
                {
                  color: colors.text,
                },
              ]}
            >
              {savedProperties.length}
            </Text>

            <Text
              style={[
                styles.statisticsLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Saved
            </Text>
          </View>

          <View style={styles.statisticsDivider} />

          <View style={styles.statisticsItem}>
            <MaterialCommunityIcons
              name="magnify"
              size={26}
              color={colors.primary}
            />

            <Text
              style={[
                styles.statisticsValue,
                {
                  color: colors.text,
                },
              ]}
            >
              {filteredProperties.length}
            </Text>

            <Text
              style={[
                styles.statisticsLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Showing
            </Text>
          </View>

          <View style={styles.statisticsDivider} />

          <View style={styles.statisticsItem}>
            <MaterialCommunityIcons
              name="home-city"
              size={26}
              color="#22C55E"
            />

            <Text
              style={[
                styles.statisticsValue,
                {
                  color: colors.text,
                },
              ]}
            >
              {
                new Set(
                  filteredProperties.map(
                    (item) =>
                      item.city
                  )
                ).size
              }
            </Text>

            <Text
              style={[
                styles.statisticsLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Cities
            </Text>
          </View>
        </View>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Load More */}
      {/* ------------------------------------------------------------------ */}

      {filteredProperties.length > 0 && (
        <View style={styles.paginationContainer}>
          <Pressable
            style={({ pressed }) => [
              styles.loadMoreButton,
              {
                backgroundColor:
                  colors.primary,
                opacity: pressed
                  ? 0.85
                  : 1,
              },
            ]}
            onPress={() => {
              // Future pagination
            }}
          >
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
              Load More
            </Text>
          </Pressable>
        </View>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Collection Summary */}
      {/* ------------------------------------------------------------------ */}

      {filteredProperties.length > 0 && (
        <View
          style={[
            styles.summaryCard,
            {
              backgroundColor:
                colors.card,
              borderColor:
                colors.border,
            },
          ]}
        >
          <MaterialCommunityIcons
            name="information-outline"
            size={22}
            color={colors.primary}
          />

          <View
            style={
              styles.summaryContent
            }
          >
            <Text
              style={[
                styles.summaryTitle,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              Your Saved Collection
            </Text>

            <Text
              style={[
                styles.summaryText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Your saved properties are synced
              with your account. You can remove,
              compare, or revisit them anytime.
            </Text>
          </View>
        </View>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* End of Collection */}
      {/* ------------------------------------------------------------------ */}

      {filteredProperties.length > 0 && (
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
            End of Saved Properties
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
            You've reached the end of your saved
            collection. Continue browsing to add
            more favourite properties.
          </Text>
        </View>
      )}
    {/* ------------------------------------------------------------------ */}
      {/* Tips */}
      {/* ------------------------------------------------------------------ */}

      {savedProperties.length > 0 && (
        <View
          style={[
            styles.tipsCard,
            {
              backgroundColor: colors.card,
              borderColor: colors.border,
            },
          ]}
        >
          <MaterialCommunityIcons
            name="lightbulb-outline"
            size={24}
            color={colors.primary}
          />

          <View style={styles.tipsContent}>
            <Text
              style={[
                styles.tipsTitle,
                {
                  color: colors.text,
                },
              ]}
            >
              Pro Tip
            </Text>

            <Text
              style={[
                styles.tipsText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Save properties you're interested in
              so you can easily compare prices,
              monitor availability, and contact
              agents later without searching again.
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

SavedProperties.displayName =
  "SavedProperties";

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
  /* Header */
  /* ---------------------------------------------------------------------- */

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },

  headerContent: {
    flex: 1,
    marginRight: 16,
  },

  title: {
    fontSize: 30,
    fontWeight: "700",
  },

  subtitle: {
    marginTop: 6,
    fontSize: 15,
  },

  backButton: {
    width: 46,
    height: 46,
    borderRadius: 23,
    alignItems: "center",
    justifyContent: "center",
  },

  /* ---------------------------------------------------------------------- */
  /* Toolbar */
  /* ---------------------------------------------------------------------- */

  toolbar: {
    marginTop: 20,
    marginBottom: 20,
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  toolbarActions: {
    flexDirection: "row",
    alignItems: "center",
  },

  resultText: {
    fontSize: 14,
    fontWeight: "600",
  },

  iconButton: {
    width: 42,
    height: 42,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
    marginLeft: 10,
  },

  sortButton: {
    flexDirection: "row",
    alignItems: "center",
    marginLeft: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
  },

  sortText: {
    marginLeft: 6,
    fontSize: 14,
    fontWeight: "600",
  },

  /* ---------------------------------------------------------------------- */
  /* Bulk Actions */
  /* ---------------------------------------------------------------------- */

  bulkActions: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 24,
  },

  bulkText: {
    fontSize: 15,
    fontWeight: "600",
  },

  /* ---------------------------------------------------------------------- */
  /* Results */
  /* ---------------------------------------------------------------------- */

  resultsContainer: {
    flex: 1,
  },

  propertyCard: {
    marginBottom: 18,
  },

  /* ---------------------------------------------------------------------- */
  /* Grid */
  /* ---------------------------------------------------------------------- */

  gridContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
  },

  gridItem: {
    width: "48%",
    marginBottom: 18,
  },

  /* ---------------------------------------------------------------------- */
  /* Statistics */
  /* ---------------------------------------------------------------------- */

  statisticsCard: {
    flexDirection: "row",
    marginTop: 24,
    paddingVertical: 20,
    borderRadius: 18,
    borderWidth: 1,
  },

  statisticsItem: {
    flex: 1,
    alignItems: "center",
  },

  statisticsDivider: {
    width: StyleSheet.hairlineWidth,
    backgroundColor: "#D1D5DB",
  },

  statisticsValue: {
    marginTop: 10,
    fontSize: 22,
    fontWeight: "700",
  },

  statisticsLabel: {
    marginTop: 6,
    fontSize: 13,
  },

  /* ---------------------------------------------------------------------- */
  /* Pagination */
  /* ---------------------------------------------------------------------- */

  paginationContainer: {
    alignItems: "center",
    marginTop: 28,
  },

  loadMoreButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 26,
    paddingVertical: 14,
    borderRadius: 14,
    minWidth: 220,
  },

  loadMoreText: {
    marginLeft: 8,
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
  },

  /* ---------------------------------------------------------------------- */
  /* Summary */
  /* ---------------------------------------------------------------------- */

  summaryCard: {
    flexDirection: "row",
    marginTop: 28,
    padding: 18,
    borderRadius: 18,
    borderWidth: 1,
  },

  summaryContent: {
    flex: 1,
    marginLeft: 14,
  },

  summaryTitle: {
    fontSize: 17,
    fontWeight: "700",
    marginBottom: 6,
  },

  summaryText: {
    fontSize: 14,
    lineHeight: 22,
  },

  /* ---------------------------------------------------------------------- */
  /* End */
  /* ---------------------------------------------------------------------- */

  endContainer: {
    alignItems: "center",
    marginTop: 30,
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
  /* Tips */
  /* ---------------------------------------------------------------------- */

  tipsCard: {
    flexDirection: "row",
    marginTop: 30,
    padding: 18,
    borderRadius: 18,
    borderWidth: 1,
  },

  tipsContent: {
    flex: 1,
    marginLeft: 14,
  },

  tipsTitle: {
    fontSize: 17,
    fontWeight: "700",
    marginBottom: 6,
  },

  tipsText: {
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

export default SavedProperties;