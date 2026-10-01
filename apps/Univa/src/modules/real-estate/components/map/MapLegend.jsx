import React, { memo } from "react";
import {
  StyleSheet,
  Text,
  View,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Legend Item */
/* -------------------------------------------------------------------------- */

const LegendItem = memo(
  ({
    icon,
    color,
    label,
  }) => {
    const { colors } = useTheme();

    return (
      <View style={styles.item}>
        <MaterialCommunityIcons
          name={icon}
          size={18}
          color={color}
        />

        <Text
          style={[
            styles.label,
            {
              color: colors.text,
            },
          ]}
        >
          {label}
        </Text>
      </View>
    );
  }
);

LegendItem.displayName = "LegendItem";

/* -------------------------------------------------------------------------- */
/* Map Legend */
/* -------------------------------------------------------------------------- */

const MapLegend = memo(() => {
  const { colors } = useTheme();

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: colors.card,
          borderColor: colors.border,
        },
      ]}
    >
      <Text
        style={[
          styles.title,
          {
            color: colors.text,
          },
        ]}
      >
        Map Legend
      </Text>

      <LegendItem
        icon="home-city"
        color={colors.primary}
        label="Property"
      />

      <LegendItem
        icon="home-check"
        color="#22C55E"
        label="Verified Property"
      />

      <LegendItem
        icon="star-circle"
        color="#F59E0B"
        label="Featured Property"
      />

      <LegendItem
        icon="map-marker-radius"
        color="#EF4444"
        label="Nearby Property"
      />

      <LegendItem
        icon="account-tie"
        color="#6366F1"
        label="Real Estate Agent"
      />
    </View>
  );
});

MapLegend.displayName = "MapLegend";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 18,
  },

  title: {
    fontSize: 17,
    fontWeight: "700",
    marginBottom: 16,
  },

  item: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 14,
  },

  label: {
    marginLeft: 12,
    fontSize: 14,
    fontWeight: "500",
  },
});

export default MapLegend;