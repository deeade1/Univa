/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/index.js                */
/* -------------------------------------------------------------------------- */

/* -------------------------------------------------------------------------- */
/* Core Search Components                                                     */
/* -------------------------------------------------------------------------- */

export { default as SearchScreen } from "./SearchScreen";
export { default as SearchHeader } from "./SearchHeader";
export { default as SearchBar } from "./SearchBar";
export { default as SearchVoiceButton } from "./SearchVoiceButton";

/* -------------------------------------------------------------------------- */
/* Search Results                                                             */
/* -------------------------------------------------------------------------- */

export { default as SearchResultsGrid } from "./SearchResultsGrid";
export { default as SearchSuggestions } from "./SearchSuggestions";
export { default as RecentSearches } from "./RecentSearches";
export { default as SearchHistoryItem } from "./SearchHistoryItem";

/* -------------------------------------------------------------------------- */
/* Search Filters                                                             */
/* -------------------------------------------------------------------------- */

export {
  default as SearchCategoryFilter,
  DEFAULT_CATEGORIES,
} from "./SearchCategoryFilter";

export { default as SearchFilters } from "./SearchFilters";

export {
  default as SearchSortSheet,
  SEARCH_SORT_OPTIONS,
} from "./SearchSortSheet";

/* -------------------------------------------------------------------------- */
/* Search States                                                              */
/* -------------------------------------------------------------------------- */

export { default as SearchEmpty } from "./SearchEmpty";
export { default as SearchSkeleton } from "./SearchSkeleton";