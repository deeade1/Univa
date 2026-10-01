import React, { memo } from "react";

import {
  Text,
  View,
  StyleSheet,
} from "react-native";

import {
  Marker,
  Callout,
} from "react-native-maps";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Property Marker */
/* -------------------------------------------------------------------------- */

const PropertyMarker = memo(
  ({
    property,
    selected = false,
    showPrice = true,
    onPress,
    onCalloutPress,
  }) => {
    const { colors } = useTheme();

    if (
      !property ||
      property.latitude == null ||
      property.longitude == null
    ) {
      return null;
    }

    const {
      title,
      location,
      address,
      latitude,
      longitude,
      price,
      bedrooms,
      bathrooms,
      verified,
    } = property;

    return (
      <Marker
        coordinate={{
          latitude: Number(latitude),
          longitude: Number(longitude),
        }}
        tracksViewChanges={false}
        onPress={() => onPress?.(property)}
      >
        {/* -------------------------------------------------------------- */}
        {/* Marker Bubble */}
        {/* -------------------------------------------------------------- */}

        <View
          style={[
            styles.marker,
            {
              backgroundColor: selected
                ? colors.primary
                : colors.card,
              borderColor: selected
                ? colors.primary
                : colors.border,
            },
          ]}
        >
          <MaterialCommunityIcons
            name={
              verified
                ? "home-check"
                : "home-city"
            }
            size={18}
            color={
              selected
                ? colors.onPrimary || "#FFFFFF"
                : colors.primary
            }
          />

          {showPrice && (
            <Text
              style={[
                styles.price,
                {
                  color: selected
                    ? colors.onPrimary ||
                      "#FFFFFF"
                    : colors.text,
                },
              ]}
            >
              ₦
              {Number(
                price || 0
              ).toLocaleString()}
            </Text>
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Callout */}
        {/* -------------------------------------------------------------- */}

        <Callout
          tooltip={false}
          onPress={() =>
            onCalloutPress?.(property)
          }
        >
          <View
            style={[
              styles.callout,
              {
                backgroundColor:
                  colors.card,
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
              {title}
            </Text>

            <Text
              style={[
                styles.location,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {location || address}
            </Text>

            <View style={styles.infoRow}>
              <MaterialCommunityIcons
                name="bed-outline"
                size={15}
                color={colors.primary}
              />

              <Text
                style={[
                  styles.info,
                  {
                    color: colors.text,
                  },
                ]}
              >
                {bedrooms ?? 0}
              </Text>

              <MaterialCommunityIcons
                name="shower"
                size={15}
                color={colors.primary}
                style={styles.iconSpacing}
              />

              <Text
                style={[
                  styles.info,
                  {
                    color: colors.text,
                  },
                ]}
              >
                {bathrooms ?? 0}
              </Text>
            </View>

            <Text
              style={[
                styles.amount,
                {
                  color: colors.primary,
                },
              ]}
            >
              ₦
              {Number(
                price || 0
              ).toLocaleString()}
            </Text>
          </View>
        </Callout>
      </Marker>
    );
  }
);

PropertyMarker.displayName =
  "PropertyMarker";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  marker: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
    elevation: 3,
  },

  price: {
    marginLeft: 6,
    fontSize: 12,
    fontWeight: "700",
  },

  callout: {
    minWidth: 220,
    padding: 12,
    borderRadius: 12,
  },

  title: {
    fontSize: 16,
    fontWeight: "700",
  },

  location: {
    marginTop: 4,
    fontSize: 13,
  },

  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 10,
  },

  info: {
    marginLeft: 4,
    fontSize: 13,
    fontWeight: "600",
  },

  iconSpacing: {
    marginLeft: 16,
  },

  amount: {
    marginTop: 12,
    fontSize: 17,
    fontWeight: "700",
  },
});

export default PropertyMarker;