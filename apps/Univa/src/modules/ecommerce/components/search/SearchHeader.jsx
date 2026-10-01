/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchHeader.jsx        */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Search Components                                                          */
/* -------------------------------------------------------------------------- */

import SearchBar from "./SearchBar";
import SearchVoiceButton from "./SearchVoiceButton";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SearchHeader = memo(
  ({
    value = "",

    placeholder = "Search products...",

    showBackButton = true,

    showVoiceButton = true,

    showFilterButton = true,

    autoFocus = false,

    editable = true,

    loading = false,

    onBack,

    onChangeText,

    onSubmit,

    onClear,

    onVoicePress,

    onFilterPress,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleBack =
      useCallback(() => {
        onBack?.();
      }, [onBack]);

    const handleVoice =
      useCallback(() => {
        onVoicePress?.();
      }, [onVoicePress]);

    const handleFilter =
      useCallback(() => {
        onFilterPress?.();
      }, [onFilterPress]);

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,
          {
            backgroundColor:
              colors.background,
            borderBottomColor:
              colors.border,
          },
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Back Button                                                    */}
        {/* -------------------------------------------------------------- */}

        {showBackButton && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Go back"
            onPress={handleBack}
            style={[
              styles.iconButton,
              {
                backgroundColor:
                  colors.card,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="arrow-left"
              size={22}
              color={colors.text}
            />
          </Pressable>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Search Bar                                                     */}
        {/* -------------------------------------------------------------- */}

        <View
          style={styles.searchWrapper}
        >
          <SearchBar
            value={value}
            placeholder={
              placeholder
            }
            editable={editable}
            loading={loading}
            autoFocus={autoFocus}
            onChangeText={
              onChangeText
            }
            onSubmitEditing={
              onSubmit
            }
            onClear={onClear}
          />
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Voice Button                                                   */}
        {/* -------------------------------------------------------------- */}

        {showVoiceButton && (
          <SearchVoiceButton
            onPress={
              handleVoice
            }
            style={
              styles.voiceButton
            }
          />
        )}

        {/* -------------------------------------------------------------- */}
        {/* Filter Button                                                  */}
        {/* -------------------------------------------------------------- */}

        {showFilterButton && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Open filters"
            onPress={
              handleFilter
            }
            style={[
              styles.iconButton,
              {
                backgroundColor:
                  colors.primary,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="tune-vertical"
              size={22}
              color={colors.white}
            />
          </Pressable>
        )}
      </View>
    );
  }
);

SearchHeader.displayName =
  "SearchHeader";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SearchHeader.propTypes = {
  value: PropTypes.string,

  placeholder:
    PropTypes.string,

  showBackButton:
    PropTypes.bool,

  showVoiceButton:
    PropTypes.bool,

  showFilterButton:
    PropTypes.bool,

  autoFocus:
    PropTypes.bool,

  editable:
    PropTypes.bool,

  loading:
    PropTypes.bool,

  onBack:
    PropTypes.func,

  onChangeText:
    PropTypes.func,

  onSubmit:
    PropTypes.func,

  onClear:
    PropTypes.func,

  onVoicePress:
    PropTypes.func,

  onFilterPress:
    PropTypes.func,

  style:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),
};

SearchHeader.defaultProps = {
  value: "",

  placeholder:
    "Search products...",

  showBackButton: true,

  showVoiceButton: true,

  showFilterButton: true,

  autoFocus: false,

  editable: true,

  loading: false,

  onBack: null,

  onChangeText: null,

  onSubmit: null,

  onClear: null,

  onVoicePress: null,

  onFilterPress: null,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flexDirection: "row",

      alignItems: "center",

      paddingHorizontal: 16,

      paddingVertical: 12,

      borderBottomWidth: 1,
    },

    searchWrapper: {
      flex: 1,

      marginHorizontal: 12,
    },

    iconButton: {
      width: 44,

      height: 44,

      borderRadius: 22,

      justifyContent:
        "center",

      alignItems:
        "center",

      elevation: 2,
    },

    voiceButton: {
      marginRight: 10,
    },
  });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default SearchHeader;