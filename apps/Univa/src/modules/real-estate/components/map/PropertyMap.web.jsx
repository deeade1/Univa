// src/modules/real-estate/components/map/PropertyMap.web.jsx
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { View, StyleSheet, ActivityIndicator, Text, Platform } from 'react-native';
import { useTheme } from '@/theme';

function PropertyMapWeb({
  properties = [],
  region,
  onMarkerPress,
  style,
  height = 420,
}) {
  const { colors } = useTheme();
  const mapContainerRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [mapInstance, setMapInstance] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Only run on web
    if (Platform.OS !== 'web') return;

    const loadMap = async () => {
      try {
        // Load Leaflet CSS
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        link.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
        link.crossOrigin = '';
        document.head.appendChild(link);

        // Load Leaflet JS
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        script.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
        script.crossOrigin = '';
        script.onload = () => {
          initializeMap();
        };
        script.onerror = () => {
          setError('Failed to load map library');
          setIsLoading(false);
        };
        document.body.appendChild(script);
      } catch (err) {
        console.error('Error loading map:', err);
        setError('Failed to load map');
        setIsLoading(false);
      }
    };

    loadMap();

    return () => {
      if (mapInstance) {
        mapInstance.remove();
      }
    };
  }, []);

  const initializeMap = useCallback(() => {
    const L = window.L;
    if (!L || !mapContainerRef.current) {
      setError('Map library not loaded');
      setIsLoading(false);
      return;
    }

    try {
      const { latitude, longitude } = region || {
        latitude: 9.082,
        longitude: 8.6753,
      };

      const map = L.map(mapContainerRef.current, {
        center: [latitude, longitude],
        zoom: 6,
        zoomControl: true,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);

      // Add markers
      if (properties && properties.length > 0) {
        properties.forEach((property) => {
          if (!property.latitude || !property.longitude) return;

          const marker = L.marker([
            Number(property.latitude),
            Number(property.longitude),
          ]).addTo(map);

          const popupContent = `
            <div style="padding: 8px; max-width: 200px;">
              <strong>${property.title || 'Property'}</strong><br/>
              ${property.address || ''}<br/>
              <strong>₦${(property.price || 0).toLocaleString()}</strong>
            </div>
          `;

          marker.bindPopup(popupContent);

          marker.on('click', () => {
            onMarkerPress?.(property);
          });
        });
      }

      setMapInstance(map);
      setIsLoading(false);

      setTimeout(() => {
        map.invalidateSize();
      }, 100);

    } catch (err) {
      console.error('Error initializing map:', err);
      setError('Failed to initialize map');
      setIsLoading(false);
    }
  }, [region, properties, onMarkerPress]);

  // Update markers when properties change
  useEffect(() => {
    if (!mapInstance || !window.L) return;

    mapInstance.eachLayer((layer) => {
      if (layer instanceof window.L.Marker) {
        mapInstance.removeLayer(layer);
      }
    });

    if (properties && properties.length > 0) {
      properties.forEach((property) => {
        if (!property.latitude || !property.longitude) return;

        const marker = window.L.marker([
          Number(property.latitude),
          Number(property.longitude),
        ]).addTo(mapInstance);

        const popupContent = `
          <div style="padding: 8px; max-width: 200px;">
            <strong>${property.title || 'Property'}</strong><br/>
            ${property.address || ''}<br/>
            <strong>₦${(property.price || 0).toLocaleString()}</strong>
          </div>
        `;

        marker.bindPopup(popupContent);

        marker.on('click', () => {
          onMarkerPress?.(property);
        });
      });
    }
  }, [properties, mapInstance, onMarkerPress]);

  if (error) {
    return (
      <View style={[styles.errorContainer, { backgroundColor: colors.card, height }]}>
        <Text style={{ color: colors.error }}>Unable to load map</Text>
        <Text style={{ color: colors.textSecondary }}>{error}</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, style, { height }]}>
      {isLoading && (
        <View style={[styles.loadingContainer, { backgroundColor: colors.background }]}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={{ color: colors.textSecondary, marginTop: 8 }}>Loading map...</Text>
        </View>
      )}
      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '100%',
          display: isLoading ? 'none' : 'block',
          borderRadius: 12,
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    position: 'relative',
    overflow: 'hidden',
    borderRadius: 12,
  },

  loadingContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },

  errorContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
    borderRadius: 12,
  },
});

export default PropertyMapWeb;