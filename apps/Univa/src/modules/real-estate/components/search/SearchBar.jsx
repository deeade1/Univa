import React, {
  memo,
  useState,
  useCallback,
} from "react";

import {
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { useRouter } from "expo-router";

import { useTheme } from "@/theme";

function SearchBar({
  value,
  onChangeText,
  placeholder = "Search properties...",
  editable = true,
}) {
  const router = useRouter();

  const { colors } = useTheme();

  const [focused, setFocused] =
    useState(false);
      const openSearch =
    useCallback(() => {
      router.push(
        "/real-estate/search"
      );
    }, [router]);

  const openFilters =
    useCallback(() => {
      router.push(
        "/real-estate/filter"
      );
    }, [router]);
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
      ]}
    >
      <Ionicons
        name="search-outline"
        size={22}
        color={colors.textSecondary}
      />

      <TextInput
        value={value}
        editable={editable}
        placeholder={placeholder}
        placeholderTextColor={
          colors.textSecondary
        }
        style={[
          styles.input,
          {
            color: colors.text,
          },
        ]}
        onFocus={() =>
          setFocused(true)
        }
        onBlur={() =>
          setFocused(false)
        }
        onChangeText={onChangeText}
        onPressIn={openSearch}
      />

      <Pressable
        onPress={openFilters}
        style={styles.filterButton}
      >
        <Ionicons
          name="options-outline"
          size={22}
          color={colors.primary}
        />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 16,

    marginTop: 12,

    flexDirection: "row",

    alignItems: "center",

    borderWidth: 1,

    borderRadius: 16,

    paddingHorizontal: 14,

    height: 56,
  },

  input: {
    flex: 1,

    fontSize: 16,

    marginLeft: 10,
  },

  filterButton: {
    marginLeft: 10,

    width: 42,

    height: 42,

    borderRadius: 21,

    justifyContent: "center",

    alignItems: "center",
  },
});

export default memo(SearchBar);