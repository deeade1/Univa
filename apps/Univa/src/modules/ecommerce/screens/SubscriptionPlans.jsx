/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/screens/SubscriptionPlans.jsx             */
/* -------------------------------------------------------------------------- */

import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
} from "react-native";
import { useRouter } from "expo-router";
import { ArrowLeft, Check, Crown, Star, Sparkles } from "lucide-react-native";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: 0,
    currency: "USD",
    period: "month",
    icon: Star,
    features: [
      "10 products",
      "Basic analytics",
      "24/7 support",
      "Standard listing",
    ],
    color: "#6B7280",
  },
  {
    id: "pro",
    name: "Pro",
    price: 29,
    currency: "USD",
    period: "month",
    icon: Crown,
    features: [
      "100 products",
      "Advanced analytics",
      "Priority support",
      "Featured listing",
      "Custom domain",
      "API access",
    ],
    color: "#F59E0B",
    popular: true,
  },
  {
    id: "business",
    name: "Business",
    price: 99,
    currency: "USD",
    period: "month",
    icon: Sparkles,
    features: [
      "Unlimited products",
      "Enterprise analytics",
      "Dedicated support",
      "Premium listing",
      "Custom domain",
      "API access",
      "Multiple users",
      "White-label",
    ],
    color: "#10B981",
  },
];

/* -------------------------------------------------------------------------- */
/* Screen                                                                     */
/* -------------------------------------------------------------------------- */

export default function SubscriptionPlansScreen() {
  const router = useRouter();
  const { colors } = theme;
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [loading, setLoading] = useState(false);

  /* ------------------------------------------------------------------------ */
  /* Handlers                                                                 */
  /* ------------------------------------------------------------------------ */

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleSelectPlan = useCallback((planId) => {
    setSelectedPlan(planId);
  }, []);

  const handleSubscribe = useCallback(async () => {
    if (!selectedPlan) return;
    setLoading(true);
    try {
      // Implement subscription logic here
      await new Promise((resolve) => setTimeout(resolve, 1500));
      console.log("Subscribed to plan:", selectedPlan);
    } catch (error) {
      console.error("Subscription failed:", error);
    } finally {
      setLoading(false);
    }
  }, [selectedPlan]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setRefreshing(false);
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Render                                                                   */
  /* ------------------------------------------------------------------------ */

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
            Subscription Plans
          </Text>
          <View style={{ width: 40 }} />
        </View>

        {/* Title */}
        <View style={styles.titleContainer}>
          <Text style={[styles.title, { color: colors.text }]}>
            Choose Your Plan
          </Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Select the perfect plan for your business needs
          </Text>
        </View>

        {/* Plans */}
        {PLANS.map((plan) => {
          const Icon = plan.icon;
          const isSelected = selectedPlan === plan.id;

          return (
            <TouchableOpacity
              key={plan.id}
              style={[
                styles.planCard,
                {
                  backgroundColor: colors.card || colors.background,
                  borderColor: isSelected ? plan.color : colors.border || "#E5E7EB",
                },
                isSelected && styles.planCardSelected,
              ]}
              onPress={() => handleSelectPlan(plan.id)}
              activeOpacity={0.8}
            >
              {plan.popular && (
                <View style={[styles.popularBadge, { backgroundColor: plan.color }]}>
                  <Text style={styles.popularText}>POPULAR</Text>
                </View>
              )}

              <View style={styles.planHeader}>
                <View style={[styles.planIcon, { backgroundColor: `${plan.color}20` }]}>
                  <Icon size={24} color={plan.color} />
                </View>
                <View style={styles.planInfo}>
                  <Text style={[styles.planName, { color: colors.text }]}>
                    {plan.name}
                  </Text>
                  <Text style={[styles.planPrice, { color: colors.text }]}>
                    ${plan.price}
                    <Text style={[styles.planPeriod, { color: colors.textSecondary }]}>
                      /{plan.period}
                    </Text>
                  </Text>
                </View>
              </View>

              {/* Features */}
              <View style={styles.featuresList}>
                {plan.features.map((feature, index) => (
                  <View key={index} style={styles.featureItem}>
                    <Check size={16} color={plan.color} />
                    <Text style={[styles.featureText, { color: colors.text }]}>
                      {feature}
                    </Text>
                  </View>
                ))}
              </View>

              {isSelected && (
                <View style={[styles.selectedIndicator, { backgroundColor: plan.color }]}>
                  <Text style={styles.selectedText}>Selected</Text>
                </View>
              )}
            </TouchableOpacity>
          );
        })}

        {/* Subscribe Button */}
        <TouchableOpacity
          style={[
            styles.subscribeButton,
            { backgroundColor: colors.primary },
            (!selectedPlan || loading) && styles.disabledButton,
          ]}
          onPress={handleSubscribe}
          disabled={!selectedPlan || loading}
        >
          <Text style={styles.subscribeButtonText}>
            {loading ? "Processing..." : selectedPlan ? "Subscribe Now" : "Select a Plan"}
          </Text>
        </TouchableOpacity>

        <View style={styles.footerSpacing} />
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

  content: {
    paddingBottom: 40,
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

  titleContainer: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    alignItems: "center",
  },

  title: {
    fontSize: 28,
    fontWeight: "700",
    marginBottom: 8,
  },

  subtitle: {
    fontSize: 16,
    textAlign: "center",
  },

  planCard: {
    marginHorizontal: 16,
    marginVertical: 8,
    padding: 16,
    borderRadius: 16,
    borderWidth: 2,
    position: "relative",
  },

  planCardSelected: {
    borderWidth: 2,
  },

  popularBadge: {
    position: "absolute",
    top: -10,
    right: 16,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },

  popularText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 1,
  },

  planHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },

  planIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
  },

  planInfo: {
    flex: 1,
  },

  planName: {
    fontSize: 18,
    fontWeight: "600",
  },

  planPrice: {
    fontSize: 22,
    fontWeight: "700",
  },

  planPeriod: {
    fontSize: 14,
    fontWeight: "400",
  },

  featuresList: {
    marginTop: 8,
  },

  featureItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 4,
    gap: 10,
  },

  featureText: {
    fontSize: 14,
  },

  selectedIndicator: {
    marginTop: 12,
    paddingVertical: 6,
    borderRadius: 8,
    alignItems: "center",
  },

  selectedText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },

  subscribeButton: {
    marginHorizontal: 16,
    marginTop: 24,
    height: 52,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
  },

  subscribeButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },

  disabledButton: {
    opacity: 0.5,
  },

  footerSpacing: {
    height: 40,
  },
});