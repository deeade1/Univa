/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useCart.js                          */
/* -------------------------------------------------------------------------- */

import { useCallback, useMemo, useState } from "react";
import { useQuery, useMutation } from "@apollo/client/react";

import {
  GET_CHECKOUT_BY_TOKEN,
  GET_CHECKOUT_LINES,
} from "@/modules/ecommerce/api/productQuery/queries/checkout";

import {
  CREATE_CHECKOUT_LINE,
  UPDATE_CHECKOUT_LINE,
  DELETE_CHECKOUT_LINE,
  CREATE_CHECKOUT,
} from "@/modules/ecommerce/api/productQuery/mutations/checkout";

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

export default function useCart({
  checkoutToken = null,
  channelId = null,
  currency = "USD",
  email = "",
} = {}) {

  /* ---------------------------------------------------------------------- */
  /* State                                                                  */
  /* ---------------------------------------------------------------------- */

  const [selectedAddress, setSelectedAddress] = useState(null);
  const [selectedShipping, setSelectedShipping] = useState(null);

  /* ---------------------------------------------------------------------- */
  /* Checkout Query                                                         */
  /* ---------------------------------------------------------------------- */

  const {
    data: checkoutData,
    loading: checkoutLoading,
    error: checkoutError,
    refetch: refetchCheckout,
  } = useQuery(GET_CHECKOUT_BY_TOKEN, {
    variables: { token: checkoutToken },
    skip: !checkoutToken,
    fetchPolicy: "cache-and-network",
  });

  /* ---------------------------------------------------------------------- */
  /* Checkout Lines Query                                                   */
  /* ---------------------------------------------------------------------- */

  const {
    data: linesData,
    loading: linesLoading,
    error: linesError,
    refetch: refetchLines,
  } = useQuery(GET_CHECKOUT_LINES, {
    variables: { checkoutId: checkoutData?.checkout?.id },
    skip: !checkoutData?.checkout?.id,
    fetchPolicy: "cache-and-network",
  });

  /* ---------------------------------------------------------------------- */
  /* Mutations                                                              */
  /* ---------------------------------------------------------------------- */

  const [createCheckout] = useMutation(CREATE_CHECKOUT);
  const [addLine] = useMutation(CREATE_CHECKOUT_LINE);
  const [updateLine] = useMutation(UPDATE_CHECKOUT_LINE);
  const [removeLine] = useMutation(DELETE_CHECKOUT_LINE);

  /* ---------------------------------------------------------------------- */
  /* Derived Data                                                           */
  /* ---------------------------------------------------------------------- */

  const checkout = checkoutData?.checkout ?? null;
  const checkoutLines = linesData?.checkoutLines?.edges?.map(edge => edge.node) ?? [];

  const cartItems = checkoutLines.map(line => ({
    id: line.id,
    variantId: line.variant?.id,
    name: line.variant?.name || line.variant?.product?.name || "",
    sku: line.variant?.sku || "",
    quantity: line.quantity,
    price: line.totalPrice?.gross?.amount || 0,
    currency: line.currency,
    image: line.variant?.product?.thumbnail?.url || null,
  }));

  /* ---------------------------------------------------------------------- */
  /* Totals                                                                 */
  /* ---------------------------------------------------------------------- */

  const totals = useMemo(() => {
    if (!checkout) {
      return { subtotal: 0, shipping: 0, tax: 0, total: 0 };
    }

    return {
      subtotal: checkout.subtotal?.gross?.amount || 0,
      shipping: checkout.shippingPrice?.gross?.amount || 0,
      tax: (checkout.total?.gross?.amount || 0) - (checkout.total?.net?.amount || 0),
      total: checkout.total?.gross?.amount || 0,
    };
  }, [checkout]);

  /* ---------------------------------------------------------------------- */
  /* Actions                                                                */
  /* ---------------------------------------------------------------------- */

  const initializeCart = useCallback(async () => {
    try {
      const { data } = await createCheckout({
        variables: {
          input: {
            email: email || "guest@example.com",
            channel: channelId,
            currency: currency,
            country: "US",
          },
        },
      });

      const newCheckout = data?.createCheckout?.checkout;
      if (newCheckout) {
        await refetchCheckout();
        return { success: true, checkout: newCheckout };
      }
      return { success: false, error: "Failed to create checkout" };
    } catch (error) {
      return { success: false, error };
    }
  }, [createCheckout, refetchCheckout, channelId, currency, email]);

  const addToCart = useCallback(async (variantId, quantity = 1) => {
    if (!checkout?.id) {
      return { success: false, error: "No active checkout" };
    }

    try {
      const { data } = await addLine({
        variables: {
          input: {
            checkoutId: checkout.id,
            variantId: variantId,
            quantity: quantity,
          },
        },
      });

      const line = data?.createCheckoutLine?.line;
      if (line) {
        await refetchLines();
        return { success: true, line };
      }
      return { success: false, error: "Failed to add item" };
    } catch (error) {
      return { success: false, error };
    }
  }, [checkout, addLine, refetchLines]);

  const updateQuantity = useCallback(async (lineId, quantity) => {
    if (quantity <= 0) {
      return removeFromCart(lineId);
    }

    try {
      const { data } = await updateLine({
        variables: {
          input: {
            id: lineId,
            quantity: quantity,
          },
        },
      });

      const line = data?.updateCheckoutLine?.line;
      if (line) {
        await refetchLines();
        return { success: true, line };
      }
      return { success: false, error: "Failed to update quantity" };
    } catch (error) {
      return { success: false, error };
    }
  }, [updateLine, refetchLines]);

  const removeFromCart = useCallback(async (lineId) => {
    try {
      const { data } = await removeLine({
        variables: {
          input: { id: lineId },
        },
      });

      if (data?.deleteCheckoutLine?.success) {
        await refetchLines();
        return { success: true };
      }
      return { success: false, error: "Failed to remove item" };
    } catch (error) {
      return { success: false, error };
    }
  }, [removeLine, refetchLines]);

  const clearCart = useCallback(async () => {
    if (!checkout?.lines) return { success: true };
    
    const results = await Promise.all(
      checkout.lines.map(line => removeFromCart(line.id))
    );
    
    const allSuccess = results.every(r => r.success);
    return { success: allSuccess };
  }, [checkout, removeFromCart]);

  /* ---------------------------------------------------------------------- */
  /* Return                                                                 */
  /* ---------------------------------------------------------------------- */

  return {
    // Data
    checkout,
    items: cartItems,
    itemCount: cartItems.length,
    totalItems: cartItems.reduce((sum, item) => sum + item.quantity, 0),
    totals,

    // States
    loading: checkoutLoading || linesLoading,
    error: checkoutError || linesError,
    isEmpty: cartItems.length === 0,
    hasItems: cartItems.length > 0,

    // Actions
    initializeCart,
    addToCart,
    updateQuantity,
    removeFromCart,
    clearCart,
    refetchCheckout,
    refetchLines,

    // Selection (for checkout flow)
    selectedAddress,
    setSelectedAddress,
    selectedShipping,
    setSelectedShipping,
  };
}