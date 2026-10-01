// src/modules/real-estate/components/map/WebPropertyMap.jsx
import React, { useEffect, useRef, useState } from "react";
import { View, StyleSheet, ActivityIndicator } from "react-native";
import { useTheme } from "@/theme";

// Use CDN for Leaflet on web
const LEAFLET_CDN = {
  css: "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
  js: "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
};

function WebPropertyMap({ 
  properties = [], 
  region, 
  onRegionChange, 
  onMarkerPress,
  showsUserLocation = false,
}) {
  const { colors } = useTheme();
  const mapRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [mapInstance, setMapInstance] = useState(null);

  useEffect(() => {
    // Load Leaflet CSS
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = LEAFLET_CDN.css;
    document.head.appendChild(link);

    // Load Leaflet JS
    const script = document.createElement('script');
    script.src = LEAFLET_CDN.js;
    script.onload = () => {
      if (window.L && mapRef.current) {
        initializeMap();
      }
    };
    document.body.appendChild(script);

    return () => {
      if (mapInstance) {
        mapInstance.remove();
      }
    };
  }, []);

  const initializeMap = () => {
    const L = window.L;
    if (!L || !mapRef.current) return;

    const { latitude, longitude, latitudeDelta, longitudeDelta } = region || {
      latitude: 6.5244,
      longitude: 3.3792,
      latitudeDelta: 0.0922,
      longitudeDelta: 0.0421,
    };

    const map = L.map(mapRef.current, {
      center: [latitude, longitude],
      zoom: 13,
      zoomControl: true,
    });

    // Use OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map);

    // Add markers
    properties.forEach((property) => {
      const marker = L.marker([
        property.coordinates.latitude,
        property.coordinates.longitude,
      ]).addTo(map);

      marker.bindPopup(`
        <div style="padding: 8px;">
          <strong>${property.title}</strong><br/>
          ${property.address}<br/>
          <strong>${property.price.toLocaleString()}</strong>
        </div>
      `);

      marker.on('click', () => {
        onMarkerPress?.(property);
      });
    });

    setMapInstance(map);
    setIsLoading(false);

    // Handle region changes
    map.on('moveend', () => {
      const center = map.getCenter();
      const bounds = map.getBounds();
      const newRegion = {
        latitude: center.lat,
        longitude: center.lng,
        latitudeDelta: bounds.getNorth() - bounds.getSouth(),
        longitudeDelta: bounds.getEast() - bounds.getWest(),
      };
      onRegionChange?.(newRegion);
    });

    // Handle zoom changes
    map.on('zoomend', () => {
      const center = map.getCenter();
      const bounds = map.getBounds();
      const newRegion = {
        latitude: center.lat,
        longitude: center.lng,
        latitudeDelta: bounds.getNorth() - bounds.getSouth(),
        longitudeDelta: bounds.getEast() - bounds.getWest(),
      };
      onRegionChange?.(newRegion);
    });
  };

  return (
    <View style={styles.container}>
      {isLoading && (
        <View style={[styles.loadingContainer, { backgroundColor: colors.background }]}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      )}
      <div
        ref={mapRef}
        style={{
          width: '100%',
          height: '100%',
          display: isLoading ? 'none' : 'block',
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    position: 'relative',
  },
  loadingContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
});

export default WebPropertyMap;