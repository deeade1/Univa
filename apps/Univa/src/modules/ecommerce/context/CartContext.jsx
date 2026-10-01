/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/context/CartContext.jsx                  */
/* -------------------------------------------------------------------------- */

import React, { createContext, useContext, useReducer, useEffect, useCallback } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

import { useCheckout } from "@/modules/ecommerce/hooks";
import { useChannel } from "@/modules/ecommerce/context/ChannelContext";

// ============================================================================
// Initial State
// ============================================================================

const initialState = {
  // Local cart state (for offline/guest users)
  items: [],
  total: 0,
  subtotal: 0,
  discount: null,
  giftCards: [],
  shippingMethod: null,
  shippingAddress: null,
  billingAddress: null,
  taxAmount: 0,
  channel: 'default',
  currency: 'NGN',
  
  // Checkout integration
  checkoutId: null,
  checkoutToken: null,
  checkoutStatus: 'idle', // idle | loading | ready | completed
  
  // Error state
  error: null,
};

// ============================================================================
// Reducer
// ============================================================================

function cartReducer(state, action) {
  switch (action.type) {
    case "SET_CART":
      return { ...state, ...action.payload };

    case "SET_CHECKOUT":
      return {
        ...state,
        checkoutId: action.payload.id,
        checkoutToken: action.payload.token,
        checkoutStatus: 'ready',
        items: action.payload.lines?.map(line => ({
          id: line.id,
          variantId: line.variant?.id,
          productId: line.variant?.product?.id,
          name: line.variant?.name || line.variant?.product?.name || '',
          variantName: line.variant?.name || '',
          sku: line.variant?.sku || '',
          price: line.totalPrice?.gross?.amount || 0,
          currency: line.currency || state.currency,
          image: line.variant?.product?.thumbnail?.url || null,
          quantity: line.quantity,
          stock: line.variant?.stockQuantity || 0,
        })),
      };

    case "ADD_ITEM": {
      const existingItem = state.items.find(
        (item) => item.variantId === action.payload.variantId
      );
      
      let updatedItems;
      if (existingItem) {
        updatedItems = state.items.map((item) =>
          item.variantId === action.payload.variantId
            ? { ...item, quantity: item.quantity + action.payload.quantity }
            : item
        );
      } else {
        updatedItems = [...state.items, { ...action.payload, id: `temp-${Date.now()}` }];
      }
      
      return recalculateTotals({ ...state, items: updatedItems });
    }

    case "REMOVE_ITEM": {
      const updatedItems = state.items.filter(
        (item) => item.variantId !== action.payload
      );
      return recalculateTotals({ ...state, items: updatedItems });
    }

    case "UPDATE_QUANTITY": {
      const updatedItems = state.items.map((item) =>
        item.variantId === action.payload.variantId
          ? { ...item, quantity: action.payload.quantity }
          : item
      );
      return recalculateTotals({ ...state, items: updatedItems });
    }

    case "CLEAR_CART":
      return {
        ...initialState,
        channel: state.channel,
        currency: state.currency,
        checkoutId: state.checkoutId,
        checkoutToken: state.checkoutToken,
      };

    case "SYNC_WITH_CHECKOUT":
      return {
        ...state,
        items: action.payload.items || state.items,
        subtotal: action.payload.subtotal || state.subtotal,
        total: action.payload.total || state.total,
        checkoutStatus: 'synced',
      };

    case "SET_ERROR":
      return { ...state, error: action.payload };

    case "CLEAR_ERROR":
      return { ...state, error: null };

    case "APPLY_DISCOUNT":
      return recalculateTotals({ ...state, discount: action.payload });

    case "REMOVE_DISCOUNT":
      return recalculateTotals({ ...state, discount: null });

    case "APPLY_GIFT_CARD":
      return recalculateTotals({
        ...state,
        giftCards: [...state.giftCards, action.payload],
      });

    case "REMOVE_GIFT_CARD":
      return recalculateTotals({
        ...state,
        giftCards: state.giftCards.filter((card) => card.id !== action.payload),
      });

    case "SET_SHIPPING_METHOD":
      return recalculateTotals({
        ...state,
        shippingMethod: action.payload,
      });

    case "SET_SHIPPING_ADDRESS":
      return { ...state, shippingAddress: action.payload };

    case "SET_BILLING_ADDRESS":
      return { ...state, billingAddress: action.payload };

    case "UPDATE_CHANNEL":
      return {
        ...state,
        channel: action.payload.channel,
        currency: action.payload.currency,
      };

    default:
      return state;
  }
}

// ============================================================================
// Helper: Recalculate Totals
// ============================================================================

function recalculateTotals(state) {
  const subtotal = state.items.reduce(
    (sum, item) => sum + (item.price * item.quantity),
    0
  );

  // Calculate discount
  let discountAmount = 0;
  if (state.discount) {
    if (state.discount.type === 'percentage') {
      discountAmount = subtotal * (state.discount.value / 100);
    } else {
      discountAmount = state.discount.value;
    }
  }

  // Calculate gift card total
  const giftCardAmount = state.giftCards.reduce(
    (sum, card) => sum + (card.currentBalance || card.current_balance || 0),
    0
  );

  // Calculate shipping
  const shippingAmount = state.shippingMethod?.price?.amount || 
                         state.shippingMethod?.price?.gross?.amount || 0;

  // Calculate tax (simplified - you can adjust rate based on country/channel)
  const taxRate = 0.075; // 7.5%
  const taxableAmount = subtotal - discountAmount - giftCardAmount;
  const taxAmount = taxableAmount > 0 ? taxableAmount * taxRate : 0;

  const total = Math.max(0, subtotal - discountAmount - giftCardAmount + shippingAmount + taxAmount);

  return {
    ...state,
    subtotal,
    discountAmount,
    giftCardAmount,
    shippingAmount,
    taxAmount,
    total: Math.round(total * 100) / 100,
  };
}

// ============================================================================
// Context
// ============================================================================

const CartContext = createContext(null);

// ============================================================================
// Provider
// ============================================================================

export function CartProvider({ children, checkoutToken: initialCheckoutToken }) {
  const [state, dispatch] = useReducer(cartReducer, initialState);
  const { channel, currency } = useChannel();

  // ==========================================================================
  // Checkout Hook Integration
  // ==========================================================================

  const {
    checkout,
    checkoutLines,
    totals,
    actions: checkoutActions,
    loading: checkoutLoading,
    error: checkoutError,
  } = useCheckout({
    checkoutToken: initialCheckoutToken || state.checkoutToken,
    skip: false,
    onOrderCreated: (order) => {
      // Clear cart on successful order
      dispatch({ type: "CLEAR_CART" });
    },
  });

  // ==========================================================================
  // Sync checkout with cart state
  // ==========================================================================

  useEffect(() => {
    if (checkout) {
      dispatch({
        type: "SET_CHECKOUT",
        payload: {
          id: checkout.id,
          token: checkout.token,
          lines: checkout.lines || [],
        },
      });
    }
  }, [checkout]);

  // ==========================================================================
  // Load cart from AsyncStorage on mount
  // ==========================================================================

  useEffect(() => {
    (async () => {
      try {
        const savedCart = await AsyncStorage.getItem("@univa/cart");
        if (savedCart) {
          const parsed = JSON.parse(savedCart);
          dispatch({ type: "SET_CART", payload: parsed });
        }
      } catch (err) {
        console.warn("Failed to load cart:", err);
      }
    })();
  }, []);

  // ==========================================================================
  // Save cart on change
  // ==========================================================================

  useEffect(() => {
    if (state.items.length > 0 || state.checkoutId) {
      AsyncStorage.setItem("@univa/cart", JSON.stringify(state)).catch((err) =>
        console.warn("Failed to save cart:", err)
      );
    }
  }, [state]);

  // ==========================================================================
  // Sync channel changes
  // ==========================================================================

  useEffect(() => {
    if (channel?.slug && channel?.slug !== state.channel) {
      dispatch({
        type: "UPDATE_CHANNEL",
        payload: { channel: channel.slug, currency: channel.currencyCode || 'USD' },
      });
    }
  }, [channel, state.channel]);

  // ==========================================================================
  // Actions
  // ==========================================================================

  const addToCart = useCallback(async (product, variant, quantity = 1) => {
    try {
      // If we have a checkout, use the checkout line mutation
      if (checkout?.id) {
        const result = await checkoutActions.addToCart(variant.id, quantity);
        if (result.success) {
          return true;
        }
        throw new Error(result.error || "Failed to add to cart");
      }

      // Fallback to local cart
      const cartItem = {
        id: `${product.id}-${variant.id}`,
        productId: product.id,
        variantId: variant.id,
        name: product.name || product.title || '',
        variantName: variant.name || '',
        sku: variant.sku || '',
        price: variant.price?.amount || variant.price || 0,
        currency: variant.price?.currency || state.currency || 'USD',
        image: product.thumbnail?.url || variant.images?.[0]?.url || null,
        quantity: quantity,
        stock: variant.stock || variant.quantity_available || 0,
        attributes: variant.attributes || {},
      };

      dispatch({ type: "ADD_ITEM", payload: cartItem });
      return true;
    } catch (error) {
      dispatch({ type: "SET_ERROR", payload: error.message });
      return false;
    }
  }, [checkout, checkoutActions, state.currency]);

  const removeFromCart = useCallback(async (variantId) => {
    try {
      // Find the item in local state
      const item = state.items.find(i => i.variantId === variantId);
      
      if (checkout?.id && item?.id) {
        const result = await checkoutActions.removeFromCart(item.id);
        if (result.success) {
          return true;
        }
        throw new Error(result.error || "Failed to remove from cart");
      }

      dispatch({ type: "REMOVE_ITEM", payload: variantId });
      return true;
    } catch (error) {
      dispatch({ type: "SET_ERROR", payload: error.message });
      return false;
    }
  }, [checkout, checkoutActions, state.items]);

  const updateQuantity = useCallback(async (variantId, quantity) => {
    try {
      const item = state.items.find(i => i.variantId === variantId);
      
      if (checkout?.id && item?.id) {
        const result = await checkoutActions.updateCartItem(item.id, quantity);
        if (result.success) {
          return true;
        }
        throw new Error(result.error || "Failed to update quantity");
      }

      if (quantity <= 0) {
        dispatch({ type: "REMOVE_ITEM", payload: variantId });
      } else {
        dispatch({ type: "UPDATE_QUANTITY", payload: { variantId, quantity } });
      }
      return true;
    } catch (error) {
      dispatch({ type: "SET_ERROR", payload: error.message });
      return false;
    }
  }, [checkout, checkoutActions, state.items]);

  const applyDiscount = useCallback(async (code) => {
    try {
      // Validate discount with backend
      // const discount = await validateDiscount(code);
      
      // Mock discount for now
      const discount = {
        id: `discount_${Date.now()}`,
        code,
        type: 'percentage',
        value: 10,
        description: '10% off',
      };

      dispatch({ type: "APPLY_DISCOUNT", payload: discount });
      return true;
    } catch (error) {
      dispatch({ type: "SET_ERROR", payload: error.message });
      return false;
    }
  }, []);

  const removeDiscount = useCallback(() => {
    dispatch({ type: "REMOVE_DISCOUNT" });
  }, []);

  const applyGiftCard = useCallback(async (code) => {
    try {
      // Validate gift card with backend
      // const giftCard = await validateGiftCard(code);
      
      // Mock gift card
      const giftCard = {
        id: `gift_${Date.now()}`,
        code,
        displayCode: code.slice(-4),
        currentBalance: 50,
        currency: state.currency,
      };

      dispatch({ type: "APPLY_GIFT_CARD", payload: giftCard });
      return true;
    } catch (error) {
      dispatch({ type: "SET_ERROR", payload: error.message });
      return false;
    }
  }, [state.currency]);

  const removeGiftCard = useCallback((cardId) => {
    dispatch({ type: "REMOVE_GIFT_CARD", payload: cardId });
  }, []);

  const setShippingMethod = useCallback((method) => {
    dispatch({ type: "SET_SHIPPING_METHOD", payload: method });
    // If checkout exists, update it
    if (checkout?.id) {
      checkoutActions.selectShipping(method);
    }
  }, [checkout, checkoutActions]);

  const setShippingAddress = useCallback((address) => {
    dispatch({ type: "SET_SHIPPING_ADDRESS", payload: address });
    if (checkout?.id) {
      checkoutActions.selectAddress(address);
    }
  }, [checkout, checkoutActions]);

  const setBillingAddress = useCallback((address) => {
    dispatch({ type: "SET_BILLING_ADDRESS", payload: address });
  }, []);

  const clearCart = useCallback(async () => {
    if (checkout?.id) {
      // Remove all items from checkout
      for (const item of checkout.lines || []) {
        await checkoutActions.removeFromCart(item.id);
      }
    }
    dispatch({ type: "CLEAR_CART" });
  }, [checkout, checkoutActions]);

  const updateChannel = useCallback((channelSlug, currencyCode) => {
    dispatch({
      type: "UPDATE_CHANNEL",
      payload: { channel: channelSlug, currency: currencyCode },
    });
  }, []);

  const refreshCart = useCallback(async () => {
    await checkoutActions.refetchCheckout();
  }, [checkoutActions]);

  const placeOrder = useCallback(async (redirectUrl) => {
    const result = await checkoutActions.placeOrder(redirectUrl);
    if (result.success) {
      dispatch({ type: "CLEAR_CART" });
    }
    return result;
  }, [checkoutActions]);

  // ==========================================================================
  // Memoized Values
  // ==========================================================================

  const cartCount = state.items.reduce((sum, item) => sum + item.quantity, 0);
  const cartTotal = state.total || totals?.total || 0;
  const cartSubtotal = state.subtotal || totals?.subtotal || 0;

  const hasItems = state.items.length > 0 || (checkout?.lines?.length || 0) > 0;
  const isEmpty = !hasItems && !checkoutLoading;

  // ==========================================================================
  // Context Value
  // ==========================================================================

  const value = {
    // State
    cart: state,
    items: state.items,
    checkout: checkout,
    checkoutLines: checkoutLines || [],
    
    // Totals
    totals: {
      subtotal: state.subtotal || totals?.subtotal || 0,
      total: state.total || totals?.total || 0,
      discountAmount: state.discountAmount || 0,
      giftCardAmount: state.giftCardAmount || 0,
      shippingAmount: state.shippingAmount || 0,
      taxAmount: state.taxAmount || 0,
    },
    
    // Derived
    cartCount,
    cartTotal,
    cartSubtotal,
    hasItems,
    isEmpty,
    
    // Loading & Error
    loading: checkoutLoading,
    error: state.error || checkoutError,

    // Actions
    addToCart,
    removeFromCart,
    updateQuantity,
    applyDiscount,
    removeDiscount,
    applyGiftCard,
    removeGiftCard,
    setShippingMethod,
    setShippingAddress,
    setBillingAddress,
    clearCart,
    updateChannel,
    refreshCart,
    placeOrder,

    // Raw dispatch (for advanced usage)
    dispatch,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

// ============================================================================
// Hook
// ============================================================================

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
}

// ============================================================================
// Default Export
// ============================================================================

export default CartProvider;