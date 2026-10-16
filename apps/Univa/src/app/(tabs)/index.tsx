
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

const COLORS = {
  background: '#F7F8FC',
  surface: '#FFFFFF',
  primary: '#3659E3',
  primaryDark: '#2445C5',
  primarySoft: '#EAF0FF',
  text: '#172033',
  muted: '#758096',
  border: '#E8EBF2',
  green: '#16865C',
};

const SERVICES = [
  {
    id: 'ecommerce',
    title: 'Shopping',
    subtitle: 'Products & deals',
    icon: '🛍️',
    color: '#EEF1FF',
  },
  {
    id: 'transport',
    title: 'Transport',
    subtitle: 'Move with ease',
    icon: '🚗',
    color: '#E8F5FF',
  },
  {
    id: 'real-estate',
    title: 'Real Estate',
    subtitle: 'Find your space',
    icon: '🏡',
    color: '#EAF7EF',
  },
  {
    id: 'banking',
    title: 'Banking',
    subtitle: 'Manage your money',
    icon: '💳',
    color: '#FFF1E6',
  },
  {
    id: 'social',
    title: 'Social',
    subtitle: 'Connect with people',
    icon: '🌐',
    color: '#F4EAFE',
  },
  {
    id: 'chat',
    title: 'Chat',
    subtitle: 'Messages & calls',
    icon: '💬',
    color: '#E6F8F5',
  },
  {
    id: 'investments',
    title: 'Investments',
    subtitle: 'Grow your future',
    icon: '📈',
    color: '#FFF4D9',
  },
];

export default function HomeScreen() {
  const [search, setSearch] = useState('');

  const filteredServices = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) return SERVICES;

    return SERVICES.filter((service) =>
      `${service.title} ${service.subtitle}`
        .toLowerCase()
        .includes(query)
    );
  }, [search]);

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar
        barStyle="dark-content"
        backgroundColor={COLORS.background}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={styles.scrollContent}
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.brandRow}>
            <View style={styles.brandMark}>
              <Text style={styles.brandMarkText}>u</Text>
            </View>

            <View>
              <Text style={styles.brandName}>univa</Text>
              <Text style={styles.brandCaption}>
                YOUR WORLD, CONNECTED
              </Text>
            </View>
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Open sign in"
            onPress={() => router.push('/auth/sign-in')}
            style={({ pressed }) => [
              styles.profileButton,
              pressed && styles.pressed,
            ]}
          >
            <Text style={styles.profileInitial}>U</Text>
          </Pressable>
        </View>

        {/* Welcome */}
        <View style={styles.welcomeSection}>
          <Text style={styles.eyebrow}>WELCOME TO UNIVA</Text>

          <Text style={styles.heading}>
            Everything you need,{' '}
            <Text style={styles.headingAccent}>in one place.</Text>
          </Text>

          <Text style={styles.description}>
            Shop, move, connect and grow — all from one simple app.
          </Text>
        </View>

        {/* Search */}
        <View style={styles.searchBox}>
          <Text style={styles.searchIcon}>⌕</Text>

          <TextInput
            value={search}
            onChangeText={setSearch}
            placeholder="What are you looking for?"
            placeholderTextColor={COLORS.muted}
            style={styles.searchInput}
            returnKeyType="search"
            accessibilityLabel="Search Univa services"
          />

          {search.length > 0 && (
            <Pressable
              onPress={() => setSearch('')}
              accessibilityRole="button"
              accessibilityLabel="Clear search"
              hitSlop={10}
              style={styles.clearButton}
            >
              <Text style={styles.clearText}>×</Text>
            </Pressable>
          )}
        </View>

        {/* Featured card */}
        <Pressable
          accessibilityRole="button"
          onPress={() => router.push('/explore')}
          style={({ pressed }) => [
            styles.featuredCard,
            pressed && styles.pressed,
          ]}
        >
          <View style={styles.featuredContent}>
            <View style={styles.featuredBadge}>
              <View style={styles.badgeDot} />
              <Text style={styles.featuredBadgeText}>
                THE UNIVA EXPERIENCE
              </Text>
            </View>

            <Text style={styles.featuredTitle}>
              More possibilities.{' '}
              <Text style={styles.featuredTitleLight}>
                One destination.
              </Text>
            </Text>

            <Text style={styles.featuredDescription}>
              Discover services designed to make everyday life easier.
            </Text>

            <View style={styles.featuredAction}>
              <Text style={styles.featuredActionText}>
                Explore Univa
              </Text>
              <Text style={styles.featuredArrow}>→</Text>
            </View>
          </View>

          <View style={styles.featuredDecoration}>
            <View style={styles.orbitOuter} />
            <View style={styles.orbitInner} />
            <View style={styles.featuredLogo}>
              <Text style={styles.featuredLogoText}>u</Text>
            </View>
          </View>
        </Pressable>

        {/* Services */}
        <View style={styles.sectionHeader}>
          <View>
            <Text style={styles.sectionTitle}>Explore services</Text>
            <Text style={styles.sectionSubtitle}>
              A little bit of everything, all in Univa.
            </Text>
          </View>

          <Pressable
            accessibilityRole="button"
            onPress={() => router.push('/explore')}
            hitSlop={8}
            style={styles.seeAllButton}
          >
            <Text style={styles.seeAllText}>See all</Text>
            <Text style={styles.seeAllArrow}>→</Text>
          </Pressable>
        </View>

        {filteredServices.length > 0 ? (
          <View style={styles.servicesGrid}>
            {filteredServices.map((service) => (
              <Pressable
                key={service.id}
                accessibilityRole="button"
                accessibilityLabel={`Explore ${service.title}`}
                                
                onPress={() => {
                  if (service.id === 'ecommerce') {
                    console.log('[Univa] Opening Shopping: /shopping');
                    router.push('/shopping');
                  } else {
                    router.push('/explore');
                  }
                }}

                style={({ pressed }) => [
                  styles.serviceCard,
                  pressed && styles.serviceCardPressed,
                ]}
              >
                <View
                  style={[
                    styles.serviceIconBox,
                    { backgroundColor: service.color },
                  ]}
                >
                  <Text style={styles.serviceIcon}>{service.icon}</Text>
                </View>

                <Text style={styles.serviceTitle}>
                  {service.title}
                </Text>

                <Text style={styles.serviceSubtitle}>
                  {service.subtitle}
                </Text>

                <View style={styles.serviceArrow}>
                  <Text style={styles.serviceArrowText}>↗</Text>
                </View>
              </Pressable>
            ))}
          </View>
        ) : (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>⌕</Text>
            <Text style={styles.emptyTitle}>No services found</Text>
            <Text style={styles.emptyDescription}>
              Try another search term.
            </Text>
            <Pressable
              onPress={() => setSearch('')}
              style={styles.resetButton}
            >
              <Text style={styles.resetButtonText}>Clear search</Text>
            </Pressable>
          </View>
        )}

        {/* Footer */}
        <View style={styles.footer}>
          <View style={styles.footerLine} />
          <Text style={styles.footerBrand}>univa</Text>
          <Text style={styles.footerText}>
            One app. More possibilities.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 30,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 34,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 11,
  },
  brandMark: {
    width: 44,
    height: 44,
    borderRadius: 15,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  brandMarkText: {
    color: '#FFFFFF',
    fontSize: 29,
    fontWeight: '800',
    lineHeight: 34,
  },
  brandName: {
    color: COLORS.text,
    fontSize: 23,
    fontWeight: '800',
    letterSpacing: -0.8,
  },
  brandCaption: {
    color: COLORS.muted,
    fontSize: 8,
    fontWeight: '700',
    letterSpacing: 1.6,
    marginTop: 1,
  },
  profileButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  profileInitial: {
    color: COLORS.primary,
    fontSize: 17,
    fontWeight: '800',
  },
  welcomeSection: {
    marginBottom: 23,
  },
  eyebrow: {
    color: COLORS.primary,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 2,
    marginBottom: 12,
  },
  heading: {
    color: COLORS.text,
    fontSize: 32,
    fontWeight: '800',
    lineHeight: 39,
    letterSpacing: -1.25,
  },
  headingAccent: {
    color: COLORS.primary,
  },
  description: {
    color: COLORS.muted,
    fontSize: 14,
    lineHeight: 22,
    marginTop: 11,
    maxWidth: 320,
  },
  searchBox: {
    minHeight: 56,
    backgroundColor: COLORS.surface,
    borderRadius: 17,
    borderWidth: 1,
    borderColor: COLORS.border,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 15,
    marginBottom: 24,
  },
  searchIcon: {
    fontSize: 29,
    color: COLORS.primary,
    marginRight: 11,
    lineHeight: 34,
  },
  searchInput: {
    flex: 1,
    color: COLORS.text,
    fontSize: 14,
    paddingVertical: 14,
  },
  clearButton: {
    paddingHorizontal: 5,
    paddingVertical: 4,
  },
  clearText: {
    fontSize: 25,
    color: COLORS.muted,
  },
  featuredCard: {
    minHeight: 258,
    borderRadius: 25,
    backgroundColor: COLORS.primary,
    padding: 22,
    overflow: 'hidden',
    marginBottom: 32,
  },
  featuredContent: {
    zIndex: 2,
    maxWidth: '88%',
  },
  featuredBadge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    backgroundColor: 'rgba(255,255,255,0.15)',
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 20,
    marginBottom: 17,
  },
  badgeDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#AFC2FF',
  },
  featuredBadgeText: {
    color: '#FFFFFF',
    fontSize: 8,
    fontWeight: '800',
    letterSpacing: 1,
  },
  featuredTitle: {
    color: '#FFFFFF',
    fontSize: 25,
    fontWeight: '800',
    lineHeight: 31,
    letterSpacing: -0.6,
  },
  featuredTitleLight: {
    color: '#D7E0FF',
  },
  featuredDescription: {
    color: '#E1E7FF',
    fontSize: 12,
    lineHeight: 19,
    marginTop: 10,
    maxWidth: 255,
  },
  featuredAction: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 13,
    backgroundColor: '#FFFFFF',
    borderRadius: 13,
    paddingHorizontal: 15,
    paddingVertical: 11,
    marginTop: 17,
  },
  featuredActionText: {
    color: COLORS.primaryDark,
    fontSize: 12,
    fontWeight: '800',
  },
  featuredArrow: {
    color: COLORS.primaryDark,
    fontSize: 17,
    fontWeight: '700',
  },
  featuredDecoration: {
    position: 'absolute',
    right: -46,
    bottom: -60,
    width: 190,
    height: 190,
    alignItems: 'center',
    justifyContent: 'center',
  },
  orbitOuter: {
    position: 'absolute',
    width: 190,
    height: 190,
    borderRadius: 95,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.17)',
  },
  orbitInner: {
    position: 'absolute',
    width: 138,
    height: 138,
    borderRadius: 69,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.22)',
  },
  featuredLogo: {
    width: 82,
    height: 82,
    borderRadius: 27,
    backgroundColor: 'rgba(255,255,255,0.16)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.25)',
    alignItems: 'center',
    justifyContent: 'center',
    transform: [{ rotate: '-10deg' }],
  },
  featuredLogoText: {
    color: '#FFFFFF',
    fontSize: 54,
    fontWeight: '800',
    lineHeight: 62,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 17,
  },
  sectionTitle: {
    color: COLORS.text,
    fontSize: 20,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  sectionSubtitle: {
    color: COLORS.muted,
    fontSize: 11,
    lineHeight: 17,
    marginTop: 5,
  },
  seeAllButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingVertical: 8,
    paddingLeft: 8,
  },
  seeAllText: {
    color: COLORS.primary,
    fontSize: 12,
    fontWeight: '800',
  },
  seeAllArrow: {
    color: COLORS.primary,
    fontSize: 16,
  },
  servicesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    rowGap: 12,
  },
  serviceCard: {
    width: '48%',
    minHeight: 162,
    backgroundColor: COLORS.surface,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 15,
  },
  serviceCardPressed: {
    backgroundColor: COLORS.primarySoft,
    borderColor: '#CBD6FF',
    transform: [{ scale: 0.98 }],
  },
  serviceIconBox: {
    width: 46,
    height: 46,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 15,
  },
  serviceIcon: {
    fontSize: 23,
  },
  serviceTitle: {
    color: COLORS.text,
    fontSize: 14,
    fontWeight: '800',
  },
  serviceSubtitle: {
    color: COLORS.muted,
    fontSize: 10,
    lineHeight: 15,
    marginTop: 5,
    paddingRight: 2,
  },
  serviceArrow: {
    position: 'absolute',
    right: 13,
    top: 13,
    width: 25,
    height: 25,
    borderRadius: 9,
    backgroundColor: COLORS.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  serviceArrowText: {
    color: COLORS.primary,
    fontSize: 14,
    fontWeight: '800',
  },
  emptyState: {
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 20,
    padding: 26,
    alignItems: 'center',
  },
  emptyIcon: {
    fontSize: 35,
    color: COLORS.primary,
  },
  emptyTitle: {
    color: COLORS.text,
    fontSize: 16,
    fontWeight: '800',
    marginTop: 8,
  },
  emptyDescription: {
    color: COLORS.muted,
    fontSize: 12,
    marginTop: 5,
  },
  resetButton: {
    marginTop: 16,
    backgroundColor: COLORS.primarySoft,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  resetButtonText: {
    color: COLORS.primary,
    fontSize: 12,
    fontWeight: '800',
  },
  footer: {
    alignItems: 'center',
    paddingTop: 35,
    paddingBottom: 10,
  },
  footerLine: {
    width: 38,
    height: 3,
    borderRadius: 2,
    backgroundColor: COLORS.primary,
    marginBottom: 14,
  },
  footerBrand: {
    color: COLORS.text,
    fontSize: 18,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  footerText: {
    color: COLORS.muted,
    fontSize: 11,
    marginTop: 5,
  },
  pressed: {
    opacity: 0.86,
  },
});
