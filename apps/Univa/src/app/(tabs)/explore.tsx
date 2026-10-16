import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import {
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

type Service = {
  id: string;
  title: string;
  subtitle: string;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
  backgroundColor: string;
};

const SERVICES: Service[] = [
  {
    id: 'ecommerce',
    title: 'Shopping',
    subtitle: 'Discover products and deals',
    icon: 'bag-handle-outline',
    color: '#6941C6',
    backgroundColor: '#F0EAFE',
  },
  {
    id: 'transport',
    title: 'Ride',
    subtitle: 'Get where you need to go',
    icon: 'car-outline',
    color: '#1570EF',
    backgroundColor: '#EAF3FF',
  },
  {
    id: 'logistics',
    title: 'Delivery',
    subtitle: 'Send packages with ease',
    icon: 'cube-outline',
    color: '#039855',
    backgroundColor: '#E8F8F0',
  },
  {
    id: 'real-estate',
    title: 'Real Estate',
    subtitle: 'Find a place to call home',
    icon: 'home-outline',
    color: '#DC6803',
    backgroundColor: '#FFF2E5',
  },
  {
    id: 'banking',
    title: 'Banking',
    subtitle: 'Manage your finances',
    icon: 'wallet-outline',
    color: '#0E9384',
    backgroundColor: '#E5F7F4',
  },
  {
    id: 'social',
    title: 'Social',
    subtitle: 'Connect with your community',
    icon: 'people-outline',
    color: '#C11574',
    backgroundColor: '#FCE7F3',
  },
];

export default function ExploreScreen() {
  const router = useRouter();
  const [search, setSearch] = useState('');

  const filteredServices = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return SERVICES;
    }

    return SERVICES.filter(
      (service) =>
        service.title.toLowerCase().includes(query) ||
        service.subtitle.toLowerCase().includes(query),
    );
  }, [search]);

  function openService(service: Service) {
    if (service.id === 'ecommerce') {
      console.log('[Univa] Opening Shopping route: /shopping');
      router.push('/shopping');
      return;
    }

    console.log(
      `[Univa] ${service.title} navigation has not been configured yet.`,
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <View>
            <Text style={styles.eyebrow}>DISCOVER UNIVA</Text>
            <Text style={styles.title}>Explore</Text>
            <Text style={styles.subtitle}>
              Everything you need, all in one place.
            </Text>
          </View>

          <View style={styles.headerIcon}>
            <Ionicons
              name="compass-outline"
              size={26}
              color="#6941C6"
            />
          </View>
        </View>

        <View style={styles.searchContainer}>
          <Ionicons
            name="search-outline"
            size={21}
            color="#667085"
          />

          <TextInput
            value={search}
            onChangeText={setSearch}
            placeholder="Search services..."
            placeholderTextColor="#98A2B3"
            style={styles.searchInput}
            returnKeyType="search"
            accessibilityLabel="Search services"
          />

          {search.length > 0 && (
            <Pressable
              onPress={() => setSearch('')}
              accessibilityRole="button"
              accessibilityLabel="Clear search"
              hitSlop={8}
            >
              <Ionicons
                name="close-circle"
                size={20}
                color="#98A2B3"
              />
            </Pressable>
          )}
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>All services</Text>
          <Text style={styles.serviceCount}>
            {filteredServices.length}{' '}
            {filteredServices.length === 1 ? 'service' : 'services'}
          </Text>
        </View>

        {filteredServices.length > 0 ? (
          <View style={styles.servicesGrid}>
            {filteredServices.map((service) => (
              <Pressable
                key={service.id}
                onPress={() => openService(service)}
                style={({ pressed }) => [
                  styles.serviceCard,
                  pressed && styles.serviceCardPressed,
                ]}
                accessibilityRole="button"
                accessibilityLabel={`Open ${service.title}`}
              >
                <View
                  style={[
                    styles.serviceIcon,
                    { backgroundColor: service.backgroundColor },
                  ]}
                >
                  <Ionicons
                    name={service.icon}
                    size={27}
                    color={service.color}
                  />
                </View>

                <Text style={styles.serviceTitle}>
                  {service.title}
                </Text>

                <Text style={styles.serviceSubtitle}>
                  {service.subtitle}
                </Text>

                <View style={styles.cardFooter}>
                  <Text style={styles.exploreLabel}>
                    Explore
                  </Text>
                  <Ionicons
                    name="arrow-forward"
                    size={16}
                    color="#6941C6"
                  />
                </View>
              </Pressable>
            ))}
          </View>
        ) : (
          <View style={styles.emptyState}>
            <Ionicons
              name="search-outline"
              size={38}
              color="#98A2B3"
            />
            <Text style={styles.emptyTitle}>
              No services found
            </Text>
            <Text style={styles.emptySubtitle}>
              Try searching with a different word.
            </Text>

            <Pressable
              onPress={() => setSearch('')}
              style={styles.clearSearchButton}
              accessibilityRole="button"
            >
              <Text style={styles.clearSearchText}>
                Clear search
              </Text>
            </Pressable>
          </View>
        )}

        <View style={styles.infoBanner}>
          <View style={styles.infoIcon}>
            <Ionicons
              name="apps-outline"
              size={23}
              color="#6941C6"
            />
          </View>

          <View style={styles.infoTextContainer}>
            <Text style={styles.infoTitle}>
              One app. Many possibilities.
            </Text>
            <Text style={styles.infoSubtitle}>
              Explore Univa services and discover what you can do.
            </Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  content: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 36,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  eyebrow: {
    color: '#6941C6',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.4,
    marginBottom: 7,
  },
  title: {
    color: '#101828',
    fontSize: 30,
    fontWeight: '800',
    letterSpacing: -0.8,
  },
  subtitle: {
    color: '#667085',
    fontSize: 14,
    marginTop: 6,
  },
  headerIcon: {
    width: 54,
    height: 54,
    borderRadius: 18,
    backgroundColor: '#F0EAFE',
    alignItems: 'center',
    justifyContent: 'center',
  },
  searchContainer: {
    minHeight: 54,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F9FAFB',
    borderWidth: 1,
    borderColor: '#EAECF0',
    borderRadius: 16,
    paddingHorizontal: 15,
    marginBottom: 28,
    gap: 10,
  },
  searchInput: {
    flex: 1,
    minHeight: 52,
    color: '#101828',
    fontSize: 15,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  sectionTitle: {
    color: '#101828',
    fontSize: 19,
    fontWeight: '800',
  },
  serviceCount: {
    color: '#667085',
    fontSize: 12,
    fontWeight: '600',
  },
  servicesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    rowGap: 14,
  },
  serviceCard: {
    width: '48.2%',
    minHeight: 190,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#EAECF0',
    borderRadius: 20,
    padding: 15,
  },
  serviceCardPressed: {
    backgroundColor: '#F9F7FF',
    borderColor: '#D6C8FA',
    transform: [{ scale: 0.98 }],
  },
  serviceIcon: {
    width: 49,
    height: 49,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  serviceTitle: {
    color: '#101828',
    fontSize: 16,
    fontWeight: '800',
    marginBottom: 6,
  },
  serviceSubtitle: {
    color: '#667085',
    fontSize: 12,
    lineHeight: 18,
    minHeight: 36,
  },
  cardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 12,
  },
  exploreLabel: {
    color: '#6941C6',
    fontSize: 12,
    fontWeight: '700',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
    paddingVertical: 44,
    backgroundColor: '#F9FAFB',
    borderRadius: 20,
  },
  emptyTitle: {
    color: '#101828',
    fontSize: 17,
    fontWeight: '800',
    marginTop: 14,
  },
  emptySubtitle: {
    color: '#667085',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 6,
  },
  clearSearchButton: {
    marginTop: 18,
    paddingHorizontal: 18,
    paddingVertical: 10,
    backgroundColor: '#F0EAFE',
    borderRadius: 12,
  },
  clearSearchText: {
    color: '#6941C6',
    fontSize: 13,
    fontWeight: '700',
  },
  infoBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F9F7FF',
    borderWidth: 1,
    borderColor: '#E9DFFF',
    borderRadius: 18,
    padding: 16,
    marginTop: 26,
    gap: 13,
  },
  infoIcon: {
    width: 45,
    height: 45,
    borderRadius: 14,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  infoTextContainer: {
    flex: 1,
  },
  infoTitle: {
    color: '#101828',
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 5,
  },
  infoSubtitle: {
    color: '#667085',
    fontSize: 12,
    lineHeight: 18,
  },
});
