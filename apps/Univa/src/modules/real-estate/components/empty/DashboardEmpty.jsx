import React, { memo } from "react";
import {
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Dashboard Empty */
/* -------------------------------------------------------------------------- */

const DashboardEmpty = memo(
  ({
    title = "Nothing to show yet",
    description = "We're unable to load properties, agents, or locations at the moment. Pull to refresh or try again shortly.",
    buttonText = "Refresh Dashboard",
    onRetry,
    icon = "home-search-outline",
  }) => {
    const { colors } = useTheme();

    return (
      <View style={styles.wrapper}>
        <View
          style={[
            styles.container,
            {
              backgroundColor: colors.card,
              borderColor: colors.border,
            },
          ]}
        >
          {/* ------------------------------------------------------------ */}
          {/* Icon */}
          {/* ------------------------------------------------------------ */}

          <View
            style={[
              styles.iconContainer,
              {
                backgroundColor: `${colors.primary}15`,
              },
            ]}
          >
            <MaterialCommunityIcons
              name={icon}
              size={60}
              color={colors.primary}
            />
          </View>

          {/* ------------------------------------------------------------ */}
          {/* Title */}
          {/* ------------------------------------------------------------ */}

          <Text
            style={[
              styles.title,
              {
                color: colors.text,
              },
            ]}
          >
            {title}
          </Text>

          {/* ------------------------------------------------------------ */}
          {/* Description */}
          {/* ------------------------------------------------------------ */}

          <Text
            style={[
              styles.description,
              {
                color: colors.textSecondary,
              },
            ]}
          >
            {description}
          </Text>

          {/* ------------------------------------------------------------ */}
          {/* Retry */}
          {/* ------------------------------------------------------------ */}

          {onRetry && (
            <Pressable
              onPress={onRetry}
              android_ripple={{
                color: colors.border,
              }}
              style={[
                styles.button,
                {
                  backgroundColor: colors.primary,
                },
              ]}
            >
              <MaterialCommunityIcons
                name="refresh"
                size={18}
                color={colors.onPrimary || "#FFFFFF"}
              />

              <Text
                style={[
                  styles.buttonText,
                  {
                    color: colors.onPrimary || "#FFFFFF",
                  },
                ]}
              >
                {buttonText}
              </Text>
            </Pressable>
          )}

          {/* ------------------------------------------------------------ */}
          {/* Hint */}
          {/* ------------------------------------------------------------ */}

          <View style={styles.tipRow}>
            <MaterialCommunityIcons
              name="information-outline"
              size={18}
              color={colors.textSecondary}
            />

            <Text
              style={[
                styles.tip,
                {
                  color: colors.textSecondary,
                },
              ]}
            >
              Check your internet connection if this issue persists.
            </Text>
          </View>
        </View>
      </View>
    );
  }
);

DashboardEmpty.displayName = "DashboardEmpty";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  wrapper: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 40,
  },

  container: {
    width: "100%",
    maxWidth: 420,
    borderWidth: 1,
    borderRadius: 24,
    paddingHorizontal: 28,
    paddingVertical: 40,
    alignItems: "center",
  },

  iconContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 24,
  },

  title: {
    fontSize: 24,
    fontWeight: "700",
    textAlign: "center",
  },

  description: {
    marginTop: 14,
    fontSize: 15,
    lineHeight: 24,
    textAlign: "center",
  },

  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 28,
    paddingHorizontal: 26,
    paddingVertical: 14,
    borderRadius: 14,
  },

  buttonText: {
    marginLeft: 10,
    fontSize: 15,
    fontWeight: "700",
  },

  tipRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 28,
    paddingHorizontal: 12,
  },

  tip: {
    flex: 1,
    marginLeft: 8,
    fontSize: 13,
    lineHeight: 20,
  },
});

export default DashboardEmpty;