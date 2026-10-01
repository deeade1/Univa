// src/modules/real-estate/components/map/NativePropertyMap.jsx
import React, {
  memo,
  useEffect,
  useMemo,
  useRef,
} from "react";

import {
  Platform,
  StyleSheet,
  View,
  Text,
} from "react-native";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Default Region */
/* -------------------------------------------------------------------------- */

const DEFAULT_REGION = {
  latitude: 9.082,
  longitude: 8.6753,
  latitudeDelta: 6,
  longitudeDelta: 6,
};

// Only import on native platforms
let MapView, Callout, Marker, PROVIDER_GOOGLE;

if (Platform.OS !== 'web') {
  const Maps = require('react-native-maps');
  MapView = Maps.default;
  Callout = Maps.Callout;
  Marker = Maps.Marker;
  PROVIDER_GOOGLE = Maps.PROVIDER_GOOGLE;
}

/* -------------------------------------------------------------------------- */
/* Native Property Map */
/* -------------------------------------------------------------------------- */

const NativePropertyMap = memo(
  ({
    properties = [],
    region,
    initialRegion = DEFAULT_REGION,
    followsUserLocation = false,
    showsUserLocation = true,
    showsMyLocationButton = true,
    showsCompass = true,
    showsTraffic = false,
    onMarkerPress,
    onCalloutPress,
    style,
  }) => {
    const { colors } = useTheme();

    const mapRef = useRef(null);

    const markers = useMemo(
      () =>
        properties.filter(
          (item) =>
            item?.latitude != null &&
            item?.longitude != null
        ),
      [properties]
    );

    /* ---------------------------------------------------------------------- */
    /* Animate To Region */
    /* ---------------------------------------------------------------------- */

    useEffect(() => {
      if (!region || !mapRef.current) return;

      mapRef.current?.animateToRegion?.(region, 800);
    }, [region]);

    /* ---------------------------------------------------------------------- */
    /* Fit All Properties */
    /* ---------------------------------------------------------------------- */

    useEffect(() => {
      if (
        markers.length <= 1 ||
        !mapRef.current
      )
        return;

      const coordinates = markers.map((item) => ({
        latitude: Number(item.latitude),
        longitude: Number(item.longitude),
      }));

      mapRef.current?.fitToCoordinates?.(
        coordinates,
        {
          edgePadding: {
            top: 80,
            bottom: 80,
            left: 60,
            right: 60,
          },
          animated: true,
        }
      );
    }, [markers]);

    // If on web, show a placeholder
    if (Platform.OS === 'web') {
      return (
        <View style={[styles.container, styles.webPlaceholder, { backgroundColor: colors.card }]}>
          <Text style={{ color: colors.textSecondary }}>
            Map view is not available on web. Please use the mobile app.
          </Text>
        </View>
      );
    }

    // Only render map on native platforms
    return (
      <View style={[styles.container, style]}>
        {MapView && (
          <MapView
            ref={mapRef}
            style={StyleSheet.absoluteFill}
            provider={
              Platform.OS === "android"
                ? PROVIDER_GOOGLE
                : undefined
            }
            initialRegion={initialRegion}
            followsUserLocation={
              followsUserLocation
            }
            showsUserLocation={
              showsUserLocation
            }
            showsMyLocationButton={
              showsMyLocationButton
            }
            showsCompass={showsCompass}
            showsTraffic={showsTraffic}
            showsBuildings
            showsIndoors
            loadingEnabled
            loadingIndicatorColor={
              colors.primary
            }
            loadingBackgroundColor={
              colors.card
            }
          >
            {markers.map((property) => (
              <Marker
                key={property.id}
                coordinate={{
                  latitude: Number(
                    property.latitude
                  ),
                  longitude: Number(
                    property.longitude
                  ),
                }}
                title={property.title}
                description={
                  property.location ||
                  property.address
                }
                onPress={() =>
                  onMarkerPress?.(property)
                }
              >
                <Callout
                  tooltip={false}
                  onPress={() =>
                    onCalloutPress?.(
                      property
                    )
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
                    <View
                      style={[
                        styles.priceBadge,
                        {
                          backgroundColor:
                            colors.primary,
                        },
                      ]}
                    >
                      <Text
                        style={[
                          styles.price,
                          {
                            color:
                              colors.onPrimary ||
                              "#FFFFFF",
                          },
                        ]}
                      >
                        ₦
                        {Number(
                          property.price || 0
                        ).toLocaleString()}
                      </Text>
                    </View>
                  </View>
                </Callout>
              </Marker>
            ))}
          </MapView>
        )}
      </View>
    );
  }
);

NativePropertyMap.displayName =
  "NativePropertyMap";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    height: 420,
    borderRadius: 20,
    overflow: "hidden",
  },

  webPlaceholder: {
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },

  callout: {
    borderRadius: 10,
    overflow: "hidden",
  },

  priceBadge: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
  },

  price: {
    fontSize: 14,
    fontWeight: "700",
  },
});

export default NativePropertyMap;