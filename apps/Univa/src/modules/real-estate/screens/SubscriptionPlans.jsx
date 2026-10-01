// src/modules/real-estate/screens/SubscriptionPlans.jsx
import React, {
  memo,
  useCallback,
  useMemo,
  useState,
  useEffect,
  useRef,
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
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useTheme } from "@/theme";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";

const { width } = Dimensions.get("window");

// Mock subscription plans - replace with GraphQL later
const SUBSCRIPTION_PLANS = [
  {
    id: "free",
    name: "Free",
    price: 0,
    currency: "NGN",
    period: "month",
    description: "Perfect for getting started",
    features: [
      "5 property listings",
      "Basic property analytics",
      "Email support",
      "24/7 security monitoring",
      "Standard listing visibility",
    ],
    limitations: [
      "No featured listings",
      "No agent profile",
      "No property insights",
      "Limited photos (5 per listing)",
    ],
    recommended: false,
    popular: false,
    color: "#94A3B8",
    badge: null,
  },
  {
    id: "professional",
    name: "Professional",
    price: 25000,
    currency: "NGN",
    period: "month",
    description: "For serious real estate professionals",
    features: [
      "50 property listings",
      "Advanced property analytics",
      "Priority email & chat support",
      "24/7 security monitoring",
      "Premium listing visibility",
      "Featured listings (5 per month)",
      "Professional agent profile",
      "Property insights & market trends",
      "Unlimited photos per listing",
    ],
    limitations: [],
    recommended: true,
    popular: true,
    color: "#1DC66C",
    badge: "Most Popular",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: 75000,
    currency: "NGN",
    period: "month",
    description: "For large agencies and teams",
    features: [
      "Unlimited property listings",
      "Enterprise analytics & reporting",
      "Dedicated account manager",
      "24/7 priority support",
      "Premium listing visibility",
      "Unlimited featured listings",
      "Team member accounts (up to 10)",
      "Advanced property insights",
      "Unlimited photos per listing",
      "API access",
      "White-label solutions",
      "Custom integrations",
    ],
    limitations: [],
    recommended: false,
    popular: false,
    color: "#8B5CF6",
    badge: "Best Value",
  },
];

// Mock current subscription - replace with GraphQL later
const MOCK_CURRENT_SUBSCRIPTION = {
  id: "free",
  planId: "free",
  status: "active",
  startDate: "2024-01-01T00:00:00Z",
  endDate: "2024-12-31T23:59:59Z",
  autoRenew: false,
};

function SubscriptionPlans() {
  const router = useRouter();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();

  // State
  const [selectedPlanId, setSelectedPlanId] = useState(null);
  const [currentSubscription, setCurrentSubscription] = useState(MOCK_CURRENT_SUBSCRIPTION);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [selectedPlanForUpgrade, setSelectedPlanForUpgrade] = useState(null);

  // Animation
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

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

  // Format currency
  const formatCurrency = useCallback((amount) => {
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: "NGN",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  }, []);

  // Check if plan is current
  const isCurrentPlan = useCallback((planId) => {
    return currentSubscription?.planId === planId;
  }, [currentSubscription]);

  // Handle plan selection
  const handlePlanSelect = useCallback((plan) => {
    if (isCurrentPlan(plan.id)) {
      // If already subscribed, show manage subscription
      router.push("/real-estate/subscription/manage");
      return;
    }
    setSelectedPlanId(plan.id);
    setSelectedPlanForUpgrade(plan);
    setShowConfirmation(true);
  }, [isCurrentPlan, router]);

  // Handle upgrade confirmation
  const handleUpgradeConfirm = useCallback(async () => {
    if (!selectedPlanForUpgrade) return;

    try {
      setIsLoading(true);
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Update subscription
      setCurrentSubscription({
        id: selectedPlanForUpgrade.id,
        planId: selectedPlanForUpgrade.id,
        status: "active",
        startDate: new Date().toISOString(),
        endDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        autoRenew: true,
      });

      setShowConfirmation(false);
      setSelectedPlanForUpgrade(null);
      
      // Show success message (you can use a toast notification here)
      alert(`Successfully upgraded to ${selectedPlanForUpgrade.name} plan!`);
    } catch (error) {
      console.error("Upgrade error:", error);
      alert("Failed to upgrade subscription. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [selectedPlanForUpgrade]);

  // Handle cancel upgrade
  const handleCancelUpgrade = useCallback(() => {
    setShowConfirmation(false);
    setSelectedPlanForUpgrade(null);
    setSelectedPlanId(null);
  }, []);

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    try {
      setIsRefreshing(true);
      // Simulate refresh
      await new Promise(resolve => setTimeout(resolve, 1500));
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // Render feature list
  const renderFeatures = useCallback((features, limitations, isCurrent) => {
    const allFeatures = features.map(f => ({ text: f, included: true }));
    const allLimitations = limitations.map(f => ({ text: f, included: false }));
    const items = [...allFeatures, ...allLimitations];

    // If it's the current plan, show all features as included
    if (isCurrent) {
      return items.map((item, index) => (
        <View key={index} style={styles.featureRow}>
          <Ionicons
            name="checkmark-circle"
            size={18}
            color="#22C55E"
            style={styles.featureIcon}
          />
          <Text style={[styles.featureText, { color: colors.text }]}>
            {item.text}
          </Text>
        </View>
      ));
    }

    return items.map((item, index) => (
      <View key={index} style={styles.featureRow}>
        <Ionicons
          name={item.included ? "checkmark-circle" : "close-circle"}
          size={18}
          color={item.included ? "#22C55E" : "#EF4444"}
          style={styles.featureIcon}
        />
        <Text
          style={[
            styles.featureText,
            {
              color: item.included ? colors.text : colors.textSecondary,
              textDecorationLine: item.included ? "none" : "line-through",
              opacity: item.included ? 1 : 0.6,
            },
          ]}
        >
          {item.text}
        </Text>
      </View>
    ));
  }, [colors]);

  // Render plan card
  const renderPlanCard = useCallback((plan) => {
    const isCurrent = isCurrentPlan(plan.id);
    const isSelected = selectedPlanId === plan.id;
    const isPopular = plan.popular;
    const isRecommended = plan.recommended;

    return (
      <View
        key={plan.id}
        style={[
          styles.planCard,
          {
            backgroundColor: colors.card,
            borderColor: isCurrent ? colors.primary : (isSelected ? colors.primary : colors.border),
            borderWidth: isCurrent || isSelected ? 2 : 1,
            shadowColor: colors.shadow || "#000",
          },
        ]}
      >
        {/* Badge */}
        {(isPopular || isRecommended) && (
          <View style={[styles.planBadge, { backgroundColor: plan.color }]}>
            <Text style={styles.planBadgeText}>{plan.badge}</Text>
          </View>
        )}

        {/* Plan Name */}
        <Text style={[styles.planName, { color: colors.text }]}>
          {plan.name}
        </Text>

        {/* Price */}
        <View style={styles.priceContainer}>
          <Text style={[styles.planPrice, { color: colors.text }]}>
            {plan.price === 0 ? "Free" : formatCurrency(plan.price)}
          </Text>
          {plan.price > 0 && (
            <Text style={[styles.planPeriod, { color: colors.textSecondary }]}>
              /{plan.period}
            </Text>
          )}
        </View>

        {/* Description */}
        <Text style={[styles.planDescription, { color: colors.textSecondary }]}>
          {plan.description}
        </Text>

        {/* Features */}
        <View style={styles.featuresContainer}>
          {renderFeatures(plan.features, plan.limitations, isCurrent)}
        </View>

        {/* Action Button */}
        <Pressable
          style={[
            styles.planButton,
            {
              backgroundColor: isCurrent ? colors.border : (isSelected ? colors.primary : colors.primary),
              opacity: isCurrent ? 0.6 : 1,
            },
          ]}
          onPress={() => handlePlanSelect(plan)}
          disabled={isLoading}
        >
          <Text
            style={[
              styles.planButtonText,
              {
                color: isCurrent ? colors.text : "#FFFFFF",
              },
            ]}
          >
            {isCurrent ? "Current Plan" : (isSelected ? "Selected" : "Select Plan")}
          </Text>
        </Pressable>
      </View>
    );
  }, [colors, isCurrentPlan, selectedPlanId, isLoading, formatCurrency, handlePlanSelect, renderFeatures]);

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
            Subscription Plans
          </Text>
          <View style={styles.headerPlaceholder} />
        </View>

        {/* Current Plan Status */}
        {currentSubscription && (
          <View style={[styles.currentPlanCard, { backgroundColor: colors.card }]}>
            <View style={styles.currentPlanHeader}>
              <Ionicons name="checkmark-circle" size={24} color="#22C55E" />
              <Text style={[styles.currentPlanTitle, { color: colors.text }]}>
                Current Plan: {currentSubscription.planId.charAt(0).toUpperCase() + currentSubscription.planId.slice(1)}
              </Text>
            </View>
            <Text style={[styles.currentPlanDetails, { color: colors.textSecondary }]}>
              Status: {currentSubscription.status.charAt(0).toUpperCase() + currentSubscription.status.slice(1)}
            </Text>
            <Text style={[styles.currentPlanDetails, { color: colors.textSecondary }]}>
              Renews: {new Date(currentSubscription.endDate).toLocaleDateString("en-NG", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </Text>
          </View>
        )}

        {/* Plans List */}
        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.plansContainer}
          refreshControl={
            <RefreshControl
              refreshing={isRefreshing}
              onRefresh={handleRefresh}
              tintColor={colors.primary}
              colors={[colors.primary]}
            />
          }
        >
          {SUBSCRIPTION_PLANS.map(plan => renderPlanCard(plan))}

          {/* Comparison Note */}
          <View style={[styles.comparisonNote, { backgroundColor: colors.card }]}>
            <Ionicons name="information-circle-outline" size={20} color={colors.primary} />
            <Text style={[styles.comparisonNoteText, { color: colors.textSecondary }]}>
              All plans include 24/7 security monitoring and standard listing visibility.
            </Text>
          </View>

          {/* FAQ Section */}
          <View style={[styles.faqSection, { backgroundColor: colors.card }]}>
            <Text style={[styles.faqTitle, { color: colors.text }]}>
              Frequently Asked Questions
            </Text>

            <View style={[styles.faqItem, { borderBottomColor: colors.border }]}>
              <Text style={[styles.faqQuestion, { color: colors.text }]}>
                Can I cancel my subscription anytime?
              </Text>
              <Text style={[styles.faqAnswer, { color: colors.textSecondary }]}>
                Yes, you can cancel your subscription at any time. Your plan will remain active until the end of the current billing period.
              </Text>
            </View>

            <View style={[styles.faqItem, { borderBottomColor: colors.border }]}>
              <Text style={[styles.faqQuestion, { color: colors.text }]}>
                What payment methods do you accept?
              </Text>
              <Text style={[styles.faqAnswer, { color: colors.textSecondary }]}>
                We accept all major credit cards, debit cards, and bank transfers through our secure payment gateway.
              </Text>
            </View>

            <View style={[styles.faqItem, { borderBottomColor: colors.border }]}>
              <Text style={[styles.faqQuestion, { color: colors.text }]}>
                Can I switch between plans?
              </Text>
              <Text style={[styles.faqAnswer, { color: colors.textSecondary }]}>
                Yes, you can upgrade or downgrade your plan at any time. Changes will take effect on your next billing cycle.
              </Text>
            </View>

            <View style={styles.faqItem}>
              <Text style={[styles.faqQuestion, { color: colors.text }]}>
                Is there a free trial?
              </Text>
              <Text style={[styles.faqAnswer, { color: colors.textSecondary }]}>
                Yes, the Free plan is available for you to get started and explore the platform. Upgrade anytime to access more features.
              </Text>
            </View>
          </View>

          {/* Bottom Spacing */}
          <View style={styles.bottomSpacing} />
        </ScrollView>
      </Animated.View>

      {/* Confirmation Modal */}
      {showConfirmation && selectedPlanForUpgrade && (
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.background }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.text }]}>
                Confirm Upgrade
              </Text>
              <Pressable onPress={handleCancelUpgrade} hitSlop={8}>
                <Ionicons name="close" size={24} color={colors.text} />
              </Pressable>
            </View>

            <View style={styles.modalBody}>
              <View style={[styles.modalPlanCard, { backgroundColor: colors.card }]}>
                <Text style={[styles.modalPlanName, { color: colors.text }]}>
                  {selectedPlanForUpgrade.name}
                </Text>
                <Text style={[styles.modalPlanPrice, { color: colors.primary }]}>
                  {selectedPlanForUpgrade.price === 0 ? "Free" : formatCurrency(selectedPlanForUpgrade.price)}
                  <Text style={[styles.modalPlanPeriod, { color: colors.textSecondary }]}>
                    /{selectedPlanForUpgrade.period}
                  </Text>
                </Text>
              </View>

              <Text style={[styles.modalDescription, { color: colors.textSecondary }]}>
                You are about to upgrade to the {selectedPlanForUpgrade.name} plan. Your account will be charged immediately.
              </Text>

              <View style={styles.modalActions}>
                <Pressable
                  style={[styles.modalCancelButton, { borderColor: colors.border }]}
                  onPress={handleCancelUpgrade}
                >
                  <Text style={[styles.modalCancelText, { color: colors.text }]}>
                    Cancel
                  </Text>
                </Pressable>

                <Pressable
                  style={[
                    styles.modalConfirmButton,
                    {
                      backgroundColor: colors.primary,
                      opacity: isLoading ? 0.6 : 1,
                    },
                  ]}
                  onPress={handleUpgradeConfirm}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <ActivityIndicator color="#FFFFFF" />
                  ) : (
                    <Text style={styles.modalConfirmText}>Confirm Upgrade</Text>
                  )}
                </Pressable>
              </View>
            </View>
          </View>
        </View>
      )}
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

  headerPlaceholder: {
    width: 24,
  },

  currentPlanCard: {
    marginHorizontal: 20,
    marginTop: 16,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#22C55E",
  },

  currentPlanHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },

  currentPlanTitle: {
    fontSize: 16,
    fontWeight: "700",
  },

  currentPlanDetails: {
    fontSize: 14,
    marginTop: 2,
  },

  plansContainer: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 40,
  },

  planCard: {
    padding: 20,
    borderRadius: 16,
    borderWidth: 1,
    marginBottom: 16,
    position: "relative",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },

  planBadge: {
    position: "absolute",
    top: -8,
    right: 16,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },

  planBadgeText: {
    color: "#FFFFFF",
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
  },

  planName: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 4,
  },

  priceContainer: {
    flexDirection: "row",
    alignItems: "baseline",
    marginBottom: 4,
  },

  planPrice: {
    fontSize: 28,
    fontWeight: "800",
  },

  planPeriod: {
    fontSize: 14,
    marginLeft: 4,
  },

  planDescription: {
    fontSize: 14,
    marginBottom: 16,
  },

  featuresContainer: {
    marginBottom: 20,
  },

  featureRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 6,
  },

  featureIcon: {
    marginRight: 8,
  },

  featureText: {
    fontSize: 14,
    flex: 1,
  },

  planButton: {
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: "center",
  },

  planButtonText: {
    fontSize: 15,
    fontWeight: "700",
  },

  comparisonNote: {
    flexDirection: "row",
    alignItems: "center",
    padding: 16,
    borderRadius: 12,
    marginTop: 8,
    gap: 8,
  },

  comparisonNoteText: {
    flex: 1,
    fontSize: 13,
    lineHeight: 18,
  },

  faqSection: {
    marginTop: 20,
    padding: 16,
    borderRadius: 12,
  },

  faqTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 16,
  },

  faqItem: {
    paddingVertical: 12,
    borderBottomWidth: 1,
  },

  faqQuestion: {
    fontSize: 15,
    fontWeight: "600",
    marginBottom: 4,
  },

  faqAnswer: {
    fontSize: 14,
    lineHeight: 20,
  },

  bottomSpacing: {
    height: 40,
  },

  modalOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "center",
    alignItems: "center",
  },

  modalContent: {
    width: width - 40,
    borderRadius: 20,
    padding: 20,
  },

  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },

  modalTitle: {
    fontSize: 20,
    fontWeight: "700",
  },

  modalBody: {
    gap: 16,
  },

  modalPlanCard: {
    padding: 16,
    borderRadius: 12,
    alignItems: "center",
  },

  modalPlanName: {
    fontSize: 18,
    fontWeight: "700",
  },

  modalPlanPrice: {
    fontSize: 24,
    fontWeight: "800",
    marginTop: 4,
  },

  modalPlanPeriod: {
    fontSize: 14,
    fontWeight: "400",
  },

  modalDescription: {
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
  },

  modalActions: {
    flexDirection: "row",
    gap: 12,
  },

  modalCancelButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: "center",
  },

  modalCancelText: {
    fontSize: 15,
    fontWeight: "600",
  },

  modalConfirmButton: {
    flex: 2,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
  },

  modalConfirmText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
  },
});

export default memo(SubscriptionPlans);