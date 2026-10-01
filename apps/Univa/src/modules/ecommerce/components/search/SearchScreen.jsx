/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchScreen.jsx        */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useState,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  SafeAreaView,
  StyleSheet,
} from "react-native";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Hooks                                                                      */
/* -------------------------------------------------------------------------- */

import useSearch from "../../hooks/useSearch";

/* -------------------------------------------------------------------------- */
/* Search Components                                                          */
/* -------------------------------------------------------------------------- */

import SearchHeader from "./SearchHeader";
import SearchCategoryFilter, {
  DEFAULT_CATEGORIES,
} from "./SearchCategoryFilter";

import SearchFilters from "./SearchFilters";
import SearchSortSheet from "./SearchSortSheet";
import SearchResultsGrid from "./SearchResultsGrid";
import SearchSuggestions from "./SearchSuggestions";
import RecentSearches from "./RecentSearches";
import SearchSkeleton from "./SearchSkeleton";
import SearchEmpty from "./SearchEmpty";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SearchScreen = memo(
  ({
    initialQuery = "",

    initialCategory = "all",

    initialSort = "relevance",

    autoFocus = false,

    showSuggestions = true,

    showRecentSearches = true,

    onProductPress,

    onBack,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Local State                                                            */
    /* ---------------------------------------------------------------------- */

    const [query, setQuery] =
      useState(initialQuery);

    const [
      selectedCategory,
      setSelectedCategory,
    ] = useState(
      initialCategory
    );

    const [
      selectedSort,
      setSelectedSort,
    ] = useState(initialSort);

    const [
      sortVisible,
      setSortVisible,
    ] = useState(false);

    /* ---------------------------------------------------------------------- */
    /* Search Hook                                                            */
    /* ---------------------------------------------------------------------- */

    const {
      products = [],

      loading = false,

      refreshing = false,

      suggestions = [],

      recentSearches = [],

      refresh,

      search,

      clearHistory,
    } = useSearch({
      query,

      category:
        selectedCategory,

      sort: selectedSort,
    });

    /* ---------------------------------------------------------------------- */
    /* Derived Values                                                         */
    /* ---------------------------------------------------------------------- */

    const hasQuery =
      useMemo(
        () =>
          query.trim()
            .length > 0,
        [query]
      );

    const hasResults =
      useMemo(
        () =>
          products.length > 0,
        [products]
      );

    const showEmptyState =
      useMemo(
        () =>
          hasQuery &&
          !loading &&
          !hasResults,
        [
          hasQuery,
          loading,
          hasResults,
        ]
      );

    /* ---------------------------------------------------------------------- */
    /* Event Handlers                                                         */
    /* ---------------------------------------------------------------------- */

    const handleQueryChange =
      useCallback(
        (text) => {
          setQuery(text);

          search?.(text);
        },
        [search]
      );

    const handleSubmit =
      useCallback(() => {
        search?.(query);
      }, [
        query,
        search,
      ]);

    const handleCategory =
      useCallback(
        (category) => {
          setSelectedCategory(
            category.id
          );
        },
        []
      );

    const handleSort =
      useCallback(
        (option) => {
          setSelectedSort(
            option.id
          );
        },
        []
      );

    const openSortSheet =
      useCallback(() => {
        setSortVisible(true);
      }, []);

    const closeSortSheet =
      useCallback(() => {
        setSortVisible(false);
      }, []);

    const handleSuggestion =
      useCallback(
        (value) => {
          setQuery(value);

          search?.(value);
        },
        [search]
      );

    const handleRecentSearch =
      useCallback(
        (value) => {
          setQuery(value);

          search?.(value);
        },
        [search]
      );

    const handleRefresh =
      useCallback(() => {
        refresh?.();
      }, [refresh]);

    const handleVoiceSearch =
      useCallback(() => {
        // Will be connected
        // to react-native-voice
        // or Expo Speech later.
      }, []);

    const handleFilterPress =
      useCallback(() => {
        openSortSheet();
      }, [openSortSheet]);

    const handleProductPress =
      useCallback(
        (product) => {
          onProductPress?.(
            product
          );
        },
        [onProductPress]
      );
          /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <SafeAreaView
        style={[
          styles.container,
          {
            backgroundColor:
              colors.background,
          },
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Header                                                         */}
        {/* -------------------------------------------------------------- */}

        <SearchHeader
          value={query}
          autoFocus={autoFocus}
          onBack={onBack}
          onChangeText={
            handleQueryChange
          }
          onSubmit={
            handleSubmit
          }
          onClear={() =>
            handleQueryChange("")
          }
          onVoicePress={
            handleVoiceSearch
          }
          onFilterPress={
            handleFilterPress
          }
        />

        {/* -------------------------------------------------------------- */}
        {/* Category Filter                                                */}
        {/* -------------------------------------------------------------- */}

        <SearchCategoryFilter
          categories={
            DEFAULT_CATEGORIES
          }
          selectedCategory={
            selectedCategory
          }
          onSelect={
            handleCategory
          }
        />

        {/* -------------------------------------------------------------- */}
        {/* Advanced Filters                                               */}
        {/* -------------------------------------------------------------- */}

        <SearchFilters
          category={
            selectedCategory
          }
          sortBy={
            selectedSort
          }
          onCategoryChange={
            handleCategory
          }
          onSortChange={
            handleSort
          }
        />

        {/* -------------------------------------------------------------- */}
        {/* Sort Bottom Sheet                                              */}
        {/* -------------------------------------------------------------- */}

        <SearchSortSheet
          visible={
            sortVisible
          }
          selectedSort={
            selectedSort
          }
          onSelect={
            handleSort
          }
          onClose={
            closeSortSheet
          }
        />

        {/* -------------------------------------------------------------- */}
        {/* Content starts in Part 3                                       */}
        {/* -------------------------------------------------------------- */}
                {/* -------------------------------------------------------------- */}
        {/* Content                                                        */}
        {/* -------------------------------------------------------------- */}

        {loading ? (
          <SearchSkeleton />
        ) : (
          <>
            {/* ---------------------------------------------------------- */}
            {/* Recent Searches                                           */}
            {/* ---------------------------------------------------------- */}

            {!hasQuery &&
              showRecentSearches &&
              recentSearches.length >
                0 && (
                <RecentSearches
                  searches={
                    recentSearches
                  }
                  onPress={
                    handleRecentSearch
                  }
                  onClear={
                    clearHistory
                  }
                />
              )}

            {/* ---------------------------------------------------------- */}
            {/* Search Suggestions                                        */}
            {/* ---------------------------------------------------------- */}

            {hasQuery &&
              showSuggestions &&
              suggestions.length >
                0 &&
              !hasResults && (
                <SearchSuggestions
                  suggestions={
                    suggestions
                  }
                  query={query}
                  onSuggestionPress={
                    handleSuggestion
                  }
                />
              )}

            {/* ---------------------------------------------------------- */}
            {/* Search Results                                            */}
            {/* ---------------------------------------------------------- */}

            {hasResults && (
              <SearchResultsGrid
                products={
                  products
                }
                loading={
                  loading
                }
                refreshing={
                  refreshing
                }
                onRefresh={
                  handleRefresh
                }
                onProductPress={
                  handleProductPress
                }
              />
            )}

            {/* ---------------------------------------------------------- */}
            {/* Empty State                                               */}
            {/* ---------------------------------------------------------- */}

            {showEmptyState && (
              <SearchEmpty
                query={query}
                onClear={() =>
                  handleQueryChange(
                    ""
                  )
                }
              />
            )}
          </>
        )}
      </SafeAreaView>
    );
  }
);

SearchScreen.displayName =
  "SearchScreen";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SearchScreen.propTypes = {
  /**
   * Initial search query.
   */
  initialQuery:
    PropTypes.string,

  /**
   * Initially selected category.
   */
  initialCategory:
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

  /**
   * Initial sort option.
   */
  initialSort:
    PropTypes.string,

  /**
   * Automatically focus
   * the search input.
   */
  autoFocus:
    PropTypes.bool,

  /**
   * Display search
   * suggestions.
   */
  showSuggestions:
    PropTypes.bool,

  /**
   * Display recent
   * searches.
   */
  showRecentSearches:
    PropTypes.bool,

  /**
   * Product selected.
   */
  onProductPress:
    PropTypes.func,

  /**
   * Back button callback.
   */
  onBack:
    PropTypes.func,
};

SearchScreen.defaultProps = {
  initialQuery: "",

  initialCategory: "all",

  initialSort: "relevance",

  autoFocus: false,

  showSuggestions: true,

  showRecentSearches: true,

  onProductPress: null,

  onBack: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flex: 1,
    },
  });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default SearchScreen;