// src/modules/real-estate/screens/PropertyMap.jsx
import React, {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  RefreshControl,
  ActivityIndicator,
  Animated,
  Dimensions,
  Platform,
  TextInput,
  Modal,
  TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { useRouter, useLocalSearchParams } from "expo-router";
import { useTheme } from "@/theme";
import { useSafeAreaInsets } from "react-native-safe-area-context";

// Map components - these will use platform-specific implementations
import PropertyMap from "../components/map/PropertyMap";
import MapLegend from "../components/map/MapLegend";
import PropertyMarker from "../components/map/PropertyMarker";

// Mock data - replace with GraphQL later
const MOCK_PROPERTIES = [
  {
    id: "prop_1",
    title: "Modern 3-Bedroom Apartment in Ikoyi",
    price: 45000000,
    currency: "NGN",
    address: "123 Bourdillon Road, Ikoyi, Lagos",
    city: "Lagos",
    state: "Lagos",
    coordinates: { latitude: 6.4654, longitude: 3.4064 },
    type: "Apartment",
    bedrooms: 3,
    bathrooms: 2,
    area: 150,
    image: "https://via.placeholder.com/100x100",
    status: "available",
    featured: true,
    category: "Residential",
  },
  {
    id: "prop_2",
    title: "Luxury 4-Bedroom Duplex in Banana Island",
    price: 250000000,
    currency: "NGN",
    address: "456 Banana Island, Lagos",
    city: "Lagos",
    state: "Lagos",
    coordinates: { latitude: 6.4712, longitude: 3.3988 },
    type: "Duplex",
    bedrooms: 4,
    bathrooms: 3.5,
    area: 250,
    image: "https://via.placeholder.com/100x100",
    status: "available",
    featured: true,
    category: "Luxury",
  },
  {
    id: "prop_3",
    title: "Cozy Studio Apartment in VI",
    price: 12000000,
    currency: "NGN",
    address: "789 Victoria Island, Lagos",
    city: "Lagos",
    state: "Lagos",
    coordinates: { latitude: 6.4281, longitude: 3.4216 },
    type: "Studio",
    bedrooms: 1,
    bathrooms: 1,
    area: 45,
    image: "https://via.placeholder.com/100x100",
    status: "available",
    featured: false,
    category: "Residential",
  },
  {
    id: "prop_4",
    title: "Spacious 5-Bedroom House in Surulere",
    price: 80000000,
    currency: "NGN",
    address: "101 Surulere, Lagos",
    city: "Lagos",
    state: "Lagos",
    coordinates: { latitude: 6.4933, longitude: 3.3558 },
    type: "House",
    bedrooms: 5,
    bathrooms: 4,
    area: 300,
    image: "https://via.placeholder.com/100x100",
    status: "available",
    featured: false,
    category: "Residential",
  },
  {
    id: "prop_5",
    title: "Commercial Office Space in Ikeja",
    price: 65000000,
    currency: "NGN",
    address: "202 Ikeja, Lagos",
    city: "Lagos",
    state: "Lagos",
    coordinates: { latitude: 6.6018, longitude: 3.3515 },
    type: "Commercial",
    bedrooms: 0,
    bathrooms: 2,
    area: 200,
    image: "https://via.placeholder.com/100x100",
    status: "available",
    featured: false,
    category: "Commercial",
  },
];

const { width, height } = Dimensions.get("window");

function PropertyMapScreen() {
  const router = useRouter();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams();

  // State
  const [properties, setProperties] = useState(MOCK_PROPERTIES);
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [mapRegion, setMapRegion] = useState({
    latitude: 6.5244,
    longitude: 3.3792,
    latitudeDelta: 0.0922,
    longitudeDelta: 0.0421,
  });
  const [filterOptions, setFilterOptions] = useState({
    type: "all",
    minPrice: 0,
    maxPrice: 1000000000,
    bedrooms: "any",
    status: "all",
  });

  // Animation
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;
  const bottomSheetAnim = useRef(new Animated.Value(height)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        friction: 8,
        tension: 60,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  // Filter properties
  const filteredProperties = useMemo(() => {
    let filtered = [...properties];

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      filtered = filtered.filter(p =>
        p.title.toLowerCase().includes(query) ||
        p.address.toLowerCase().includes(query) ||
        p.city.toLowerCase().includes(query) ||
        p.state.toLowerCase().includes(query)
      );
    }

    // Type filter
    if (filterOptions.type !== "all") {
      filtered = filtered.filter(p =>
        p.type.toLowerCase() === filterOptions.type.toLowerCase()
      );
    }

    // Price filter
    filtered = filtered.filter(p =>
      p.price >= filterOptions.minPrice &&
      p.price <= filterOptions.maxPrice
    );

    // Bedrooms filter
    if (filterOptions.bedrooms !== "any") {
      filtered = filtered.filter(p =>
        p.bedrooms >= parseInt(filterOptions.bedrooms)
      );
    }

    // Status filter
    if (filterOptions.status !== "all") {
      filtered = filtered.filter(p =>
        p.status.toLowerCase() === filterOptions.status.toLowerCase()
      );
    }

    return filtered;
  }, [properties, searchQuery, filterOptions]);

  // Format currency
  const formatCurrency = useCallback((amount) => {
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: "NGN",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  }, []);

  // Handle marker press
  const handleMarkerPress = useCallback((property) => {
    setSelectedProperty(property);
    // Animate bottom sheet up
    Animated.spring(bottomSheetAnim, {
      toValue: height * 0.35,
      friction: 8,
      tension: 60,
      useNativeDriver: true,
    }).start();
  }, []);

  // Handle property press from bottom sheet
  const handlePropertyPress = useCallback((property) => {
    router.push(`/real-estate/property/${property.id}`);
  }, [router]);

  // Handle map region change
  const handleRegionChange = useCallback((region) => {
    setMapRegion(region);
  }, []);

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    try {
      setIsRefreshing(true);
      await new Promise(resolve => setTimeout(resolve, 1500));
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // Handle search submit
  const handleSearchSubmit = useCallback(() => {
    // Filter properties based on search
  }, []);

  // Clear search
  const clearSearch = useCallback(() => {
    setSearchQuery("");
  }, []);

  // Reset filters
  const resetFilters = useCallback(() => {
    setFilterOptions({
      type: "all",
      minPrice: 0,
      maxPrice: 1000000000,
      bedrooms: "any",
      status: "all",
    });
    setShowFilters(false);
  }, []);

  // Handle filter apply
  const applyFilters = useCallback(() => {
    setShowFilters(false);
  }, []);

  // Render property bottom sheet
  const renderBottomSheet = useCallback(() => {
    if (!selectedProperty) return null;

    return (
      <Animated.View
        style={[
          styles.bottomSheet,
          {
            backgroundColor: colors.background,
            transform: [{ translateY: bottomSheetAnim }],
            borderTopColor: colors.border,
          },
        ]}
      >
        <View style={styles.bottomSheetHandle}>
          <View style={[styles.bottomSheetHandleBar, { backgroundColor: colors.border }]} />
        </View>

        <View style={styles.bottomSheetContent}>
          <View style={styles.bottomSheetHeader}>
            <View style={styles.bottomSheetTitleContainer}>
              <Text style={[styles.bottomSheetTitle, { color: colors.text }]} numberOfLines={1}>
                {selectedProperty.title}
              </Text>
              <View style={styles.bottomSheetPriceContainer}>
                <Text style={[styles.bottomSheetPrice, { color: colors.primary }]}>
                  {formatCurrency(selectedProperty.price)}
                </Text>
                {selectedProperty.featured && (
                  <View style={[styles.featuredBadge, { backgroundColor: colors.primary }]}>
                    <Text style={styles.featuredBadgeText}>Featured</Text>
                  </View>
                )}
              </View>
            </View>
          </View>

          <View style={styles.bottomSheetDetails}>
            <View style={styles.bottomSheetDetailItem}>
              <Ionicons name="bed-outline" size={16} color={colors.textSecondary} />
              <Text style={[styles.bottomSheetDetailText, { color: colors.textSecondary }]}>
                {selectedProperty.bedrooms} Bedroom{selectedProperty.bedrooms > 1 ? "s" : ""}
              </Text>
            </View>
            <View style={styles.bottomSheetDetailItem}>
              <Ionicons name="shower-outline" size={16} color={colors.textSecondary} />
              <Text style={[styles.bottomSheetDetailText, { color: colors.textSecondary }]}>
                {selectedProperty.bathrooms} Bathroom{selectedProperty.bathrooms > 1 ? "s" : ""}
              </Text>
            </View>
            <View style={styles.bottomSheetDetailItem}>
              <Ionicons name="square-outline" size={16} color={colors.textSecondary} />
              <Text style={[styles.bottomSheetDetailText, { color: colors.textSecondary }]}>
                {selectedProperty.area} m²
              </Text>
            </View>
          </View>

          <View style={styles.bottomSheetAddress}>
            <Ionicons name="location-outline" size={16} color={colors.textSecondary} />
            <Text style={[styles.bottomSheetAddressText, { color: colors.textSecondary }]} numberOfLines={1}>
              {selectedProperty.address}
            </Text>
          </View>

          <View style={styles.bottomSheetActions}>
            <Pressable
              style={[styles.bottomSheetViewButton, { backgroundColor: colors.primary }]}
              onPress={() => handlePropertyPress(selectedProperty)}
            >
              <Text style={styles.bottomSheetViewButtonText}>View Details</Text>
            </Pressable>
            <Pressable
              style={[styles.bottomSheetCloseButton, { borderColor: colors.border }]}
              onPress={() => {
                setSelectedProperty(null);
                Animated.spring(bottomSheetAnim, {
                  toValue: height,
                  friction: 8,
                  tension: 60,
                  useNativeDriver: true,
                }).start();
              }}
            >
              <Ionicons name="close" size={20} color={colors.text} />
            </Pressable>
          </View>
        </View>
      </Animated.View>
    );
  }, [selectedProperty, colors, formatCurrency, bottomSheetAnim, handlePropertyPress]);

  // Render filter modal
  const renderFilterModal = useCallback(() => {
    return (
      <Modal
        visible={showFilters}
        transparent
        animationType="slide"
        onRequestClose={() => setShowFilters(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.background }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.text }]}>
                Filter Properties
              </Text>
              <Pressable onPress={() => setShowFilters(false)} hitSlop={8}>
                <Ionicons name="close" size={24} color={colors.text} />
              </Pressable>
            </View>

            <ScrollView showsVerticalScrollIndicator={false}>
              {/* Property Type */}
              <View style={styles.filterSection}>
                <Text style={[styles.filterLabel, { color: colors.text }]}>
                  Property Type
                </Text>
                <View style={styles.filterOptions}>
                  {["all", "Apartment", "Duplex", "House", "Studio", "Commercial"].map((type) => (
                    <Pressable
                      key={type}
                      style={[
                        styles.filterChip,
                        {
                          backgroundColor: filterOptions.type === type.toLowerCase()
                            ? colors.primary
                            : colors.card,
                          borderColor: filterOptions.type === type.toLowerCase()
                            ? colors.primary
                            : colors.border,
                        },
                      ]}
                      onPress={() => setFilterOptions(prev => ({ ...prev, type: type.toLowerCase() }))}
                    >
                      <Text
                        style={[
                          styles.filterChipText,
                          {
                            color: filterOptions.type === type.toLowerCase()
                              ? "#FFFFFF"
                              : colors.text,
                          },
                        ]}
                      >
                        {type === "all" ? "All" : type}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>

              {/* Price Range */}
              <View style={styles.filterSection}>
                <Text style={[styles.filterLabel, { color: colors.text }]}>
                  Price Range
                </Text>
                <View style={styles.priceRangeContainer}>
                  <View style={[styles.priceInputContainer, { borderColor: colors.border }]}>
                    <Text style={[styles.priceInputLabel, { color: colors.textSecondary }]}>
                      Min
                    </Text>
                    <TextInput
                      style={[styles.priceInput, { color: colors.text }]}
                      placeholder="0"
                      placeholderTextColor={colors.textSecondary}
                      keyboardType="numeric"
                      value={filterOptions.minPrice.toString()}
                      onChangeText={(text) => {
                        const value = parseInt(text) || 0;
                        setFilterOptions(prev => ({ ...prev, minPrice: value }));
                      }}
                    />
                  </View>
                  <Text style={[styles.priceRangeSeparator, { color: colors.textSecondary }]}>
                    -
                  </Text>
                  <View style={[styles.priceInputContainer, { borderColor: colors.border }]}>
                    <Text style={[styles.priceInputLabel, { color: colors.textSecondary }]}>
                      Max
                    </Text>
                    <TextInput
                      style={[styles.priceInput, { color: colors.text }]}
                      placeholder="1,000,000,000"
                      placeholderTextColor={colors.textSecondary}
                      keyboardType="numeric"
                      value={filterOptions.maxPrice === 1000000000 ? "" : filterOptions.maxPrice.toString()}
                      onChangeText={(text) => {
                        const value = parseInt(text) || 1000000000;
                        setFilterOptions(prev => ({ ...prev, maxPrice: value }));
                      }}
                    />
                  </View>
                </View>
              </View>

              {/* Bedrooms */}
              <View style={styles.filterSection}>
                <Text style={[styles.filterLabel, { color: colors.text }]}>
                  Bedrooms
                </Text>
                <View style={styles.filterOptions}>
                  {["any", "1", "2", "3", "4", "5+"].map((bed) => (
                    <Pressable
                      key={bed}
                      style={[
                        styles.filterChip,
                        {
                          backgroundColor: filterOptions.bedrooms === bed
                            ? colors.primary
                            : colors.card,
                          borderColor: filterOptions.bedrooms === bed
                            ? colors.primary
                            : colors.border,
                        },
                      ]}
                      onPress={() => setFilterOptions(prev => ({ ...prev, bedrooms: bed }))}
                    >
                      <Text
                        style={[
                          styles.filterChipText,
                          {
                            color: filterOptions.bedrooms === bed
                              ? "#FFFFFF"
                              : colors.text,
                          },
                        ]}
                      >
                        {bed === "any" ? "Any" : bed}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>

              {/* Status */}
              <View style={styles.filterSection}>
                <Text style={[styles.filterLabel, { color: colors.text }]}>
                  Status
                </Text>
                <View style={styles.filterOptions}>
                  {["all", "available", "pending", "sold"].map((status) => (
                    <Pressable
                      key={status}
                      style={[
                        styles.filterChip,
                        {
                          backgroundColor: filterOptions.status === status
                            ? colors.primary
                            : colors.card,
                          borderColor: filterOptions.status === status
                            ? colors.primary
                            : colors.border,
                        },
                      ]}
                      onPress={() => setFilterOptions(prev => ({ ...prev, status }))}
                    >
                      <Text
                        style={[
                          styles.filterChipText,
                          {
                            color: filterOptions.status === status
                              ? "#FFFFFF"
                              : colors.text,
                          },
                        ]}
                      >
                        {status.charAt(0).toUpperCase() + status.slice(1)}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>

              {/* Filter Actions */}
              <View style={styles.filterActions}>
                <Pressable
                  style={[styles.filterActionButton, { borderColor: colors.border }]}
                  onPress={resetFilters}
                >
                  <Text style={[styles.filterActionText, { color: colors.text }]}>
                    Reset All
                  </Text>
                </Pressable>
                <Pressable
                  style={[styles.filterActionButton, styles.filterApplyButton, { backgroundColor: colors.primary }]}
                  onPress={applyFilters}
                >
                  <Text style={styles.filterApplyText}>
                    Apply Filters
                  </Text>
                </Pressable>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    );
  }, [showFilters, colors, filterOptions, resetFilters, applyFilters]);

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Animated.View
        style={[
          styles.content,
          {
            opacity: fadeAnim,
            transform: [{ translateY: slideAnim }],
          },
        ]}
      >
        {/* Header */}
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Pressable onPress={() => router.back()} hitSlop={8}>
            <Ionicons name="arrow-back" size={24} color={colors.text} />
          </Pressable>
          <Text style={[styles.headerTitle, { color: colors.text }]}>
            Property Map
          </Text>
          <View style={styles.headerActions}>
            <Pressable onPress={() => setShowFilters(true)} hitSlop={8}>
              <Ionicons name="options-outline" size={24} color={colors.text} />
            </Pressable>
          </View>
        </View>

        {/* Search Bar */}
        <View style={[styles.searchContainer, { borderBottomColor: colors.border }]}>
          <View style={[styles.searchBar, { backgroundColor: colors.card }]}>
            <Ionicons name="search-outline" size={20} color={colors.textSecondary} />
            <TextInput
              style={[styles.searchInput, { color: colors.text }]}
              placeholder="Search properties..."
              placeholderTextColor={colors.textSecondary}
              value={searchQuery}
              onChangeText={setSearchQuery}
              onSubmitEditing={handleSearchSubmit}
              returnKeyType="search"
            />
            {searchQuery.length > 0 && (
              <TouchableOpacity onPress={clearSearch}>
                <Ionicons name="close-circle" size={20} color={colors.textSecondary} />
              </TouchableOpacity>
            )}
          </View>
          <Pressable
            style={[styles.filterButton, { backgroundColor: colors.card }]}
            onPress={() => setShowFilters(true)}
          >
            <Ionicons name="filter" size={20} color={colors.primary} />
          </Pressable>
        </View>

        {/* Map */}
        <View style={styles.mapContainer}>
          <PropertyMap
            properties={filteredProperties}
            region={mapRegion}
            onRegionChange={handleRegionChange}
            onMarkerPress={handleMarkerPress}
            showsUserLocation
            showsMyLocationButton
            followsUserLocation={false}
          />

          {/* Map Legend */}
          <View style={styles.legendContainer}>
            <MapLegend />
          </View>

          {/* Result Count */}
          <View style={[styles.resultCount, { backgroundColor: colors.card }]}>
            <Text style={[styles.resultCountText, { color: colors.text }]}>
              {filteredProperties.length} Properties Found
            </Text>
          </View>
        </View>

        {/* Bottom Sheet */}
        {renderBottomSheet()}

        {/* Filter Modal */}
        {renderFilterModal()}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  content: {
    flex: 1,
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
  },

  headerTitle: {
    fontSize: 18,
    fontWeight: "700",
  },

  headerActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },

  searchContainer: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    gap: 10,
  },

  searchBar: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    gap: 10,
  },

  searchInput: {
    flex: 1,
    fontSize: 15,
    paddingVertical: 0,
  },

  filterButton: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },

  mapContainer: {
    flex: 1,
    position: "relative",
  },

  legendContainer: {
    position: "absolute",
    bottom: 16,
    left: 16,
    right: 16,
  },

  resultCount: {
    position: "absolute",
    top: 16,
    left: 16,
    right: 16,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    alignItems: "center",
    elevation: 4,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
  },

  resultCountText: {
    fontSize: 14,
    fontWeight: "600",
  },

  bottomSheet: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderTopWidth: 1,
    elevation: 10,
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: -4 },
  },

  bottomSheetHandle: {
    alignItems: "center",
    paddingVertical: 12,
  },

  bottomSheetHandleBar: {
    width: 40,
    height: 4,
    borderRadius: 2,
  },

  bottomSheetContent: {
    paddingHorizontal: 20,
    paddingBottom: 20,
  },

  bottomSheetHeader: {
    marginBottom: 12,
  },

  bottomSheetTitleContainer: {
    gap: 4,
  },

  bottomSheetTitle: {
    fontSize: 16,
    fontWeight: "700",
  },

  bottomSheetPriceContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },

  bottomSheetPrice: {
    fontSize: 18,
    fontWeight: "700",
  },

  featuredBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },

  featuredBadgeText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontWeight: "700",
    textTransform: "uppercase",
  },

  bottomSheetDetails: {
    flexDirection: "row",
    gap: 16,
    marginBottom: 8,
  },

  bottomSheetDetailItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },

  bottomSheetDetailText: {
    fontSize: 13,
  },

  bottomSheetAddress: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginBottom: 12,
  },

  bottomSheetAddressText: {
    flex: 1,
    fontSize: 13,
  },

  bottomSheetActions: {
    flexDirection: "row",
    gap: 10,
  },

  bottomSheetViewButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: "center",
  },

  bottomSheetViewButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "700",
  },

  bottomSheetCloseButton: {
    width: 44,
    height: 44,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },

  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "flex-end",
  },

  modalContent: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    maxHeight: "80%",
  },

  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },

  modalTitle: {
    fontSize: 20,
    fontWeight: "700",
  },

  filterSection: {
    marginBottom: 20,
  },

  filterLabel: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 10,
  },

  filterOptions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },

  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
  },

  filterChipText: {
    fontSize: 13,
    fontWeight: "500",
  },

  priceRangeContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },

  priceInputContainer: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    height: 44,
  },

  priceInputLabel: {
    fontSize: 14,
    fontWeight: "500",
    marginRight: 8,
  },

  priceInput: {
    flex: 1,
    fontSize: 14,
    paddingVertical: 0,
  },

  priceRangeSeparator: {
    fontSize: 16,
  },

  filterActions: {
    flexDirection: "row",
    gap: 10,
    marginTop: 10,
    marginBottom: 20,
  },

  filterActionButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: "center",
  },

  filterActionText: {
    fontSize: 15,
    fontWeight: "600",
  },

  filterApplyButton: {
    borderWidth: 0,
  },

  filterApplyText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
  },
});

export default memo(PropertyMapScreen);