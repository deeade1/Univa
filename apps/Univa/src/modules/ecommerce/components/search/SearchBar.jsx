/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/search/SearchBar.jsx           */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useRef,
  useEffect,
  useState,
} from "react";

import {
  View,
  TextInput,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme";
/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SearchBar = memo(
  ({
    value = "",

    placeholder = "Search products...",

    autoFocus = false,

    editable = true,

    loading = false,

    showBackButton = false,

    showFilterButton = true,

    showClearButton = true,

    showVoiceButton = false,

    returnKeyType = "search",

    onChangeText,

    onSubmit,

    onFocus,

    onBlur,

    onBack,

    onFilter,

    onVoice,

    onClear,

    style,

    inputStyle,
  }) => {
    const { colors } = theme;


    const inputRef =
      useRef(null);

    const [focused, setFocused] =
      useState(false);

    useEffect(() => {
      if (
        autoFocus &&
        inputRef.current
      ) {
        inputRef.current.focus();
      }
    }, [autoFocus]);

    const handleFocus = (
      event
    ) => {
      setFocused(true);
      onFocus?.(event);
    };

    const handleBlur = (
      event
    ) => {
      setFocused(false);
      onBlur?.(event);
    };

    const handleSubmit = (
      event
    ) => {
      onSubmit?.(
        event.nativeEvent.text
      );
    };

    return (
      <View
        style={[
          styles.container,
          {
            borderColor: focused
              ? colors.primary
              : colors.border,

            backgroundColor:
              colors.card,
          },
          style,
        ]}
      >
        {/* ---------------------------------------------------------- */}
        {/* Back Button */}
        {/* ---------------------------------------------------------- */}

        {showBackButton && (
          <Pressable
            onPress={onBack}
            style={
              styles.iconButton
            }
          >
            <MaterialCommunityIcons
              name="arrow-left"
              size={22}
              color={colors.text}
            />
          </Pressable>
        )}

        {/* ---------------------------------------------------------- */}
        {/* Search Icon */}
        {/* ---------------------------------------------------------- */}

        <MaterialCommunityIcons
          name="magnify"
          size={22}
          color={
            focused
              ? colors.primary
              : colors.textSecondary
          }
        />

        {/* ---------------------------------------------------------- */}
        {/* Input */}
        {/* ---------------------------------------------------------- */}

        <TextInput
          ref={inputRef}
          value={value}
          editable={
            editable &&
            !loading
          }
          placeholder={
            placeholder
          }
          placeholderTextColor={
            colors.textSecondary
          }
          returnKeyType={
            returnKeyType
          }
          autoCorrect={false}
          autoCapitalize="none"
          selectionColor={
            colors.primary
          }
          onFocus={
            handleFocus
          }
          onBlur={
            handleBlur
          }
          onChangeText={
            onChangeText
          }
          onSubmitEditing={
            handleSubmit
          }
          style={[
            styles.input,
            {
              color:
                colors.text,
            },
            inputStyle,
          ]}
        />

        {/* ---------------------------------------------------------- */}
        {/* Clear */}
        {/* ---------------------------------------------------------- */}

        {showClearButton &&
          value.length > 0 && (
            <Pressable
              onPress={() => {
                onChangeText?.("");
                onClear?.();
              }}
              style={
                styles.iconButton
              }
            >
              <MaterialCommunityIcons
                name="close-circle"
                size={20}
                color={
                  colors.textSecondary
                }
              />
            </Pressable>
          )}

        {/* ---------------------------------------------------------- */}
        {/* Voice */}
        {/* ---------------------------------------------------------- */}

        {showVoiceButton && (
          <Pressable
            onPress={onVoice}
            style={
              styles.iconButton
            }
          >
            <MaterialCommunityIcons
              name="microphone-outline"
              size={21}
              color={
                colors.primary
              }
            />
          </Pressable>
        )}

        {/* ---------------------------------------------------------- */}
        {/* Filter */}
        {/* ---------------------------------------------------------- */}

        {showFilterButton && (
          <Pressable
            onPress={onFilter}
            style={
              styles.iconButton
            }
          >
            <MaterialCommunityIcons
              name="tune-variant"
              size={22}
              color={
                colors.primary
              }
            />
          </Pressable>
        )}
      </View>
    );
  }
);

SearchBar.displayName =
  "SearchBar";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flexDirection: "row",

      alignItems: "center",

      borderWidth: 1.5,

      borderRadius: 16,

      paddingHorizontal: 14,

      height: 56,
    },

    input: {
      flex: 1,

      marginLeft: 10,

      fontSize: 16,

      paddingVertical: 0,
    },

    iconButton: {
      width: 36,

      height: 36,

      justifyContent:
        "center",

      alignItems: "center",
    },
  });

export default SearchBar;