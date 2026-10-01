/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/screens/SellerProfile.jsx                 */
/* -------------------------------------------------------------------------- */

import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Image,
  Linking,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { ArrowLeft, Star, Mail, Phone, MapPin, Globe } from "lucide-react-native";

import useSeller from "@/modules/ecommerce/hooks/useSeller";
import useProducts from "@/modules/ecommerce/hooks/useProducts";

import SellerProducts from "@/modules/ecommerce/components/sellers/SellerProducts";
import SellerStats from "@/modules/ecommerce/components/sellers/SellerStats";
import SellerPolicies from "@/modules/ecommerce/components/sellers/SellerPolicies";
import SellerSkeleton from "@/modules/ecommerce/components/sellers/SellerSkeleton";
import ErrorState from "@/modules/ecommerce/components/common/ErrorState";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Screen                                                                     */
/* -------------------------------------------------------------------------- */

export default function SellerProfileScreen() {
  const router = useRouter();
  const { colors } = theme;
  const { id } = useLocalSearchParams();

  const [refreshing, setRefreshing] = useState(false);

  const {
    seller,
    profile,
    loading,
    error,
    refresh,
    isSeller,
  } = useSeller({ sellerId: id });

  const {
    products: sellerProducts,
    loading: productsLoading,
    refreshProducts,
  } = useProducts({
    sellerId: id,
    first: 20,
  });

  /* ------------------------------------------------------------------------ */
  /* Handlers                                                                 */
  /* ------------------------------------------------------------------------ */

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([refresh(), refreshProducts()]);
    setRefreshing(false);
  }, [refresh, refreshProducts]);

  const handleProductPress = useCallback((product) => {
    router.push({
      pathname: "/ecommerce/[slug]",
      params: { slug: product.slug || product.id },
    });
  }, [router]);

  const handleEmail = useCallback(() => {
    if (seller?.email) {
      Linking.openURL(`mailto:${seller.email}`);
    }
  }, [seller]);

  const handlePhone = useCallback(() => {
    if (seller?.phone) {
      Linking.openURL(`tel:${seller.phone}`);
    }
  }, [seller]);

  const handleWebsite = useCallback(() => {
    if (profile?.website) {
      Linking.openURL(profile.website);
    }
  }, [profile]);

  /* ------------------------------------------------------------------------ */
  /* Loading State                                                            */
  /* ------------------------------------------------------------------------ */

  if (loading && !seller) {
    return <SellerSkeleton />;
  }

  /* ------------------------------------------------------------------------ */
  /* Error State                                                              */
  /* ------------------------------------------------------------------------ */

  if (error) {
    return (
      <ErrorState
        title="Unable to load seller"
        description={error.message || "Please try again."}
        onRetry={handleRefresh}
      />
    );
  }

  /* ------------------------------------------------------------------------ */
  /* Empty State                                                              */
  /* ------------------------------------------------------------------------ */

  if (!seller || !isSeller) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.header}>
          <TouchableOpacity onPress={handleBack} style={styles.backButton}>
            <ArrowLeft size={24} color={colors.text} />
          </TouchableOpacity>
        </View>
        <View style={styles.emptyContainer}>
          <Text style={[styles.emptyText, { color: colors.text }]}>
            Seller not found
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  /* ------------------------------------------------------------------------ */
  /* Render                                                                   */
  /* ------------------------------------------------------------------------ */

  const fullName = `${seller.firstName || ""} ${seller.lastName || ""}`.trim() || seller.email;

  return (
    <SafeAreaView
      style={[
        styles.container,
        { backgroundColor: colors.background },
      ]}
    >
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={handleBack} style={styles.backButton}>
            <ArrowLeft size={24} color={colors.text} />
          </TouchableOpacity>
          <Text style={[styles.headerTitle, { color: colors.text }]}>
            Seller Profile
          </Text>
          <View style={{ width: 40 }} />
        </View>

        {/* Seller Info */}
        <View style={styles.sellerInfo}>
          <View style={styles.avatarContainer}>
            {seller.avatar || profile?.avatar ? (
              <Image
                source={{ uri: seller.avatar || profile?.avatar }}
                style={styles.avatar}
              />
            ) : (
              <View style={[styles.avatarPlaceholder, { backgroundColor: colors.primary }]}>
                <Text style={styles.avatarText}>
                  {fullName.charAt(0).toUpperCase()}
                </Text>
              </View>
            )}
          </View>

          <Text style={[styles.sellerName, { color: colors.text }]}>
            {fullName}
          </Text>
          {profile?.companyName && (
            <Text style={[styles.companyName, { color: colors.textSecondary }]}>
              {profile.companyName}
            </Text>
          )}
          <Text style={[styles.sellerRole, { color: colors.textSecondary }]}>
            {seller.roleLabel || "Seller"}
          </Text>

          {/* Contact Buttons */}
          <View style={styles.contactRow}>
            {seller.email && (
              <TouchableOpacity style={styles.contactButton} onPress={handleEmail}>
                <Mail size={20} color={colors.primary} />
                <Text style={[styles.contactText, { color: colors.primary }]}>Email</Text>
              </TouchableOpacity>
            )}
            {seller.phone && (
              <TouchableOpacity style={styles.contactButton} onPress={handlePhone}>
                <Phone size={20} color={colors.primary} />
                <Text style={[styles.contactText, { color: colors.primary }]}>Call</Text>
              </TouchableOpacity>
            )}
            {profile?.website && (
              <TouchableOpacity style={styles.contactButton} onPress={handleWebsite}>
                <Globe size={20} color={colors.primary} />
                <Text style={[styles.contactText, { color: colors.primary }]}>Website</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>

        {/* Seller Stats */}
        <View style={styles.section}>
          <SellerStats
            totalProducts={seller.totalProducts || 0}
            totalSales={seller.totalSales || 0}
            rating={seller.rating || 0}
            reviewsCount={seller.reviewsCount || 0}
            joinDate={seller.joinDate}
          />
        </View>

        {/* Seller Policies */}
        {profile?.policies && (
          <View style={styles.section}>
            <SellerPolicies policies={profile.policies} />
          </View>
        )}

        {/* Seller Products */}
        <View style={styles.section}>
          <SellerProducts
            products={sellerProducts}
            loading={productsLoading}
            onProductPress={handleProductPress}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 12,
  },

  backButton: {
    padding: 4,
  },

  headerTitle: {
    fontSize: 18,
    fontWeight: "600",
  },

  content: {
    paddingBottom: 40,
  },

  sellerInfo: {
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 16,
  },

  avatarContainer: {
    marginBottom: 12,
  },

  avatar: {
    width: 100,
    height: 100,
    borderRadius: 50,
  },

  avatarPlaceholder: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: "center",
    alignItems: "center",
  },

  avatarText: {
    fontSize: 40,
    color: "#FFFFFF",
    fontWeight: "700",
  },

  sellerName: {
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 4,
  },

  companyName: {
    fontSize: 16,
    marginBottom: 2,
  },

  sellerRole: {
    fontSize: 14,
    marginBottom: 12,
  },

  contactRow: {
    flexDirection: "row",
    gap: 16,
    marginTop: 8,
  },

  contactButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },

  contactText: {
    fontSize: 14,
    fontWeight: "500",
  },

  section: {
    paddingHorizontal: 16,
    marginTop: 16,
  },

  emptyContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },

  emptyText: {
    fontSize: 16,
  },
});