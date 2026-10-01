/* -------------------------------------------------------------------------- */
/* CheckoutScreen.jsx                                                         */
/* apps/Univa/src/modules/ecommerce/screens/CheckoutScreen.jsx                */
/* -------------------------------------------------------------------------- */

import React, { useCallback, useMemo, useState } from "react";
import { useRouter } from "expo-router";
import {
  ScrollView,
  StyleSheet,
  View,
  SafeAreaView,
  Alert,
} from "react-native";

import { useCheckout } from "@/modules/ecommerce/hooks/useCheckout";
import { useCart } from "@/modules/ecommerce/context/CartContext";
import { useChannel } from "@/modules/ecommerce/context/ChannelContext";

import CheckoutProgress from "@/modules/ecommerce/components/checkout/CheckoutProgress";
import CheckoutAddressCard from "@/modules/ecommerce/components/checkout/CheckoutAddressCard";
import CheckoutAddressSelector from "@/modules/ecommerce/components/checkout/CheckoutAddressSelector";
import ShippingMethodList from "@/modules/ecommerce/components/checkout/ShippingMethodList";
import PaymentMethodList from "@/modules/ecommerce/components/checkout/PaymentMethodList";
import CheckoutReview from "@/modules/ecommerce/components/checkout/CheckoutReview";
import CheckoutSuccess from "@/modules/ecommerce/components/checkout/CheckoutSuccess";
import CheckoutFooter from "@/modules/ecommerce/components/checkout/CheckoutFooter";
import CheckoutSkeleton from "@/modules/ecommerce/components/checkout/CheckoutSkeleton";
import ErrorState from "@/modules/ecommerce/components/common/ErrorState";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Screen                                                                     */
/* -------------------------------------------------------------------------- */

const CheckoutScreen = () => {
  const router = useRouter();
  const { colors } = theme;
  const { channel, currency } = useChannel();
  const { items, totals, clearCart } = useCart();

  const [orderPlaced, setOrderPlaced] = useState(false);
  const [orderData, setOrderData] = useState(null);

  const checkout = useCheckout({
    onOrderCreated: (order) => {
      setOrderData(order);
      setOrderPlaced(true);
      clearCart();
    },
    onError: (error) => {
      Alert.alert("Checkout Error", error.message || "Something went wrong.");
    },
  });

  /* ------------------------------------------------------------------------ */
  /* Memoized Values                                                          */
  /* ------------------------------------------------------------------------ */

  const cartItems = useMemo(() => {
    return items.map(item => ({
      id: item.id || item.variantId,
      name: item.name || item.productName,
      quantity: item.quantity,
      price: item.price || 0,
      image: item.image,
      variant: item.variantName || null,
    }));
  }, [items]);

  /* ------------------------------------------------------------------------ */
  /* Loading State                                                            */
  /* ------------------------------------------------------------------------ */

  if (
    checkout.loadingStates.checkout ||
    checkout.loadingStates.addresses
  ) {
    return <CheckoutSkeleton />;
  }

  /* ------------------------------------------------------------------------ */
  /* Error State                                                              */
  /* ------------------------------------------------------------------------ */

  if (checkout.error) {
    return (
      <ErrorState
        title="Checkout Error"
        message={checkout.error.message}
        onRetry={checkout.actions.refetchCheckout}
      />
    );
  }

  /* ------------------------------------------------------------------------ */
  /* Success State                                                            */
  /* ------------------------------------------------------------------------ */

  if (orderPlaced || checkout.state.step === checkout.state.steps.COMPLETE) {
    return (
      <CheckoutSuccess
        order={orderData || checkout.order}
        onContinue={() => router.push("/ecommerce/orders")}
      />
    );
  }

  /* ------------------------------------------------------------------------ */
  /* Render Step Content                                                      */
  /* ------------------------------------------------------------------------ */

  const renderStepContent = () => {
    switch (checkout.state.step) {
      case checkout.state.steps.ADDRESS:
        return (
          <>
            <CheckoutAddressCard
              address={checkout.customer.selectedAddress}
              title="Shipping Address"
              onChange={() => {
                // Show address selector
              }}
              onEdit={() => {
                if (checkout.customer.selectedAddress) {
                  router.push({
                    pathname: "/ecommerce/edit-address",
                    params: { id: checkout.customer.selectedAddress.id },
                  });
                }
              }}
              onAddAddress={() => {
                router.push("/ecommerce/new-address");
              }}
              showEditButton={!!checkout.customer.selectedAddress}
              showChangeButton={checkout.customer.addresses.length > 0}
              showDefaultBadge
            />

            {checkout.customer.addresses.length > 0 && (
              <CheckoutAddressSelector
                addresses={checkout.customer.addresses}
                selectedAddress={checkout.customer.selectedAddress}
                onSelectAddress={checkout.actions.selectAddress}
                onAddAddress={() => {
                  router.push("/ecommerce/new-address");
                }}
              />
            )}
          </>
        );

      case checkout.state.steps.SHIPPING:
        return (
          <ShippingMethodList
            methods={checkout.shipping.methods}
            selected={checkout.shipping.selected}
            selectedId={checkout.shipping.selectedId}
            loading={checkout.shipping.loading}
            onSelect={checkout.actions.selectShipping}
            onRefresh={checkout.actions.refetchShippingMethods}
          />
        );

      case checkout.state.steps.PAYMENT:
        return (
          <PaymentMethodList
            methods={checkout.payment.methods}
            selected={checkout.payment.selected}
            selectedId={checkout.payment.selectedId}
            loading={checkout.payment.loading}
            onSelect={checkout.actions.selectPayment}
          />
        );

      case checkout.state.steps.REVIEW:
        return (
          <CheckoutReview
            customer={checkout.customer}
            shipping={checkout.shipping}
            payment={checkout.payment}
            checkout={checkout.checkout}
            items={cartItems}
            totals={checkout.totals}
            onPlaceOrder={checkout.actions.placeOrder}
            loading={checkout.loading}
            errors={checkout.validation?.errors}
          />
        );

      default:
        return null;
    }
  };

  /* ------------------------------------------------------------------------ */
  /* Check if can continue                                                    */
  /* ------------------------------------------------------------------------ */

  const canContinue = useMemo(() => {
    switch (checkout.state.step) {
      case checkout.state.steps.ADDRESS:
        return !!checkout.customer.selectedAddress;
      case checkout.state.steps.SHIPPING:
        return !!checkout.shipping.selected;
      case checkout.state.steps.PAYMENT:
        return !!checkout.payment.selected;
      case checkout.state.steps.REVIEW:
        return true;
      default:
        return false;
    }
  }, [checkout]);

  /* ------------------------------------------------------------------------ */
  /* Can go back                                                              */
  /* ------------------------------------------------------------------------ */

  const canGoBack = useMemo(() => {
    return checkout.state.step !== checkout.state.steps.ADDRESS;
  }, [checkout]);

  /* ------------------------------------------------------------------------ */
  /* Handle Continue                                                          */
  /* ------------------------------------------------------------------------ */

  const handleContinue = () => {
    if (checkout.state.step === checkout.state.steps.REVIEW) {
      checkout.actions.placeOrder();
    } else {
      checkout.actions.nextStep();
    }
  };

  /* ------------------------------------------------------------------------ */
  /* Handle Back                                                              */
  /* ------------------------------------------------------------------------ */

  const handleBack = () => {
    if (canGoBack) {
      checkout.actions.previousStep();
    }
  };

  /* ------------------------------------------------------------------------ */
  /* Render                                                                   */
  /* ------------------------------------------------------------------------ */

  const isReviewStep = checkout.state.step === checkout.state.steps.REVIEW;

  return (
    <SafeAreaView
      style={[
        styles.container,
        { backgroundColor: colors.background },
      ]}
    >
      <ScrollView
        contentContainerStyle={[
          styles.content,
          isReviewStep && styles.reviewContent,
        ]}
        showsVerticalScrollIndicator={false}
      >
        {/* Progress Indicator */}
        <CheckoutProgress
          step={checkout.state.step}
          steps={checkout.state.steps}
        />

        {/* Step Content */}
        {renderStepContent()}
      </ScrollView>

      {/* Footer */}
      {checkout.state.step !== checkout.state.steps.COMPLETE && (
        <CheckoutFooter
          total={checkout.totals.total}
          currency={checkout.checkout?.currency || currency || "USD"}
          primaryLabel={
            checkout.state.step === checkout.state.steps.REVIEW
              ? "Place Order"
              : "Continue"
          }
          onPrimaryPress={handleContinue}
          loading={checkout.loading}
          disabled={!canContinue}
          secondaryLabel={canGoBack ? "Back" : undefined}
          onSecondaryPress={handleBack}
        />
      )}
    </SafeAreaView>
  );
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  content: {
    padding: 16,
    paddingBottom: 120,
    gap: 16,
  },

  reviewContent: {
    paddingBottom: 100,
    gap: 0,
  },
});

export default CheckoutScreen;