/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchVoiceButton.jsx   */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  Pressable,
  ActivityIndicator,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SearchVoiceButton = memo(
  ({
    listening = false,

    disabled = false,

    loading = false,

    size = 46,

    iconSize = 22,

    accessibilityLabel = "Voice search",

    onPress,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handlePress =
      useCallback(() => {
        if (
          disabled ||
          loading
        ) {
          return;
        }

        onPress?.();
      }, [
        disabled,
        loading,
        onPress,
      ]);

    /* ---------------------------------------------------------------------- */
    /* Computed Values                                                        */
    /* ---------------------------------------------------------------------- */

    const backgroundColor =
      listening
        ? colors.error ||
          "#EF4444"
        : colors.card;

    const iconColor =
      listening
        ? colors.white
        : colors.primary;

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <Pressable
        accessible
        accessibilityRole="button"
        accessibilityLabel={
          accessibilityLabel
        }
        accessibilityState={{
          disabled,
          busy: loading,
        }}
        disabled={
          disabled ||
          loading
        }
        onPress={
          handlePress
        }
        style={[
          styles.button,
          {
            width: size,
            height: size,
            borderRadius:
              size / 2,
            backgroundColor,
            borderColor:
              colors.border,
            opacity:
              disabled
                ? 0.5
                : 1,
          },
          style,
        ]}
      >
        {loading ? (
          <ActivityIndicator
            size="small"
            color={iconColor}
          />
        ) : (
          <MaterialCommunityIcons
            name={
              listening
                ? "microphone"
                : "microphone-outline"
            }
            size={iconSize}
            color={iconColor}
          />
        )}
      </Pressable>
    );
  }
);

SearchVoiceButton.displayName =
  "SearchVoiceButton";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SearchVoiceButton.propTypes = {
  /**
   * Whether voice recognition
   * is currently active.
   */
  listening:
    PropTypes.bool,

  /**
   * Disable interaction.
   */
  disabled:
    PropTypes.bool,

  /**
   * Show loading spinner.
   */
  loading:
    PropTypes.bool,

  /**
   * Button diameter.
   */
  size:
    PropTypes.number,

  /**
   * Icon size.
   */
  iconSize:
    PropTypes.number,

  /**
   * Accessibility label.
   */
  accessibilityLabel:
    PropTypes.string,

  /**
   * Press callback.
   */
  onPress:
    PropTypes.func,

  /**
   * Style overrides.
   */
  style:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),
};

SearchVoiceButton.defaultProps = {
  listening: false,

  disabled: false,

  loading: false,

  size: 46,

  iconSize: 22,

  accessibilityLabel:
    "Voice search",

  onPress: null,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    button: {
      justifyContent:
        "center",

      alignItems:
        "center",

      borderWidth: 1,

      elevation: 2,
    },
  });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default SearchVoiceButton;