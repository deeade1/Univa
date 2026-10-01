/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/SearchBar.jsx           */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import {
  View,
  TextInput,
  Pressable,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

import {
  colors,
  spacing,
  radius,
  typography,
} from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SearchBar = memo(({
  onPress,
  onChangeText,
  value = "",
  placeholder = "Search products...",
  disabled = false,
  loading = false,
  style,
  inputStyle,
}) => {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || !onPress}
      style={[styles.container, style]}
    >
      <Ionicons
        name="search-outline"
        size={20}
        color={colors.textSecondary}
      />

      <TextInput
        style={[styles.input, inputStyle]}
        placeholder={placeholder}
        placeholderTextColor={colors.textSecondary}
        value={value}
        onChangeText={onChangeText}
        editable={!!onChangeText}
        pointerEvents={onChangeText ? "auto" : "none"}
        returnKeyType="search"
        onSubmitEditing={() => {
          if (onChangeText && value?.trim()) {
            onPress?.();
          }
        }}
      />

      {loading && (
        <View style={styles.loadingIndicator}>
          <ActivityIndicator size="small" color={colors.primary} />
        </View>
      )}

      {value && onChangeText && (
        <Pressable
          onPress={() => onChangeText("")}
          style={styles.clearButton}
          accessibilityLabel="Clear search"
        >
          <Ionicons
            name="close-circle"
            size={18}
            color={colors.textSecondary}
          />
        </Pressable>
      )}
    </Pressable>
  );
});

SearchBar.displayName = "SearchBar";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface || "#F3F4F6",
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border || "#E5E7EB",
    minHeight: 48,
  },

  input: {
    flex: 1,
    marginLeft: spacing.sm,
    fontSize: typography.fontSize.md,
    color: colors.text,
    paddingVertical: spacing.xs,
  },

  loadingIndicator: {
    marginLeft: spacing.sm,
  },

  clearButton: {
    marginLeft: spacing.sm,
    padding: spacing.xs,
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default SearchBar;