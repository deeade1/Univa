/* -------------------------------------------------------------------------- */
/* useCheckout.js                                                             */
/* apps/Univa/src/modules/ecommerce/hooks/useCheckout.js                      */
/* -------------------------------------------------------------------------- */

import {
  useCallback,
  useMemo,
  useState,
  useEffect,
} from "react";

import {
  useQuery,
  useMutation,
} from "@apollo/client/react";

import {
  GET_CHECKOUT_BY_TOKEN,
  GET_CHECKOUT_LINES,
  COMPLETE_CHECKOUT,
  VALIDATE_CHECKOUT_STOCK,
} from "@/modules/ecommerce/api/productQuery/queries/checkout";

import {
  CREATE_CHECKOUT,
  UPDATE_CHECKOUT,
  DELETE_CHECKOUT,
  CREATE_CHECKOUT_LINE,
  UPDATE_CHECKOUT_LINE,
  DELETE_CHECKOUT_LINE,
} from "@/modules/ecommerce/api/productQuery/mutations/checkout";

import { useAddresses } from "@/modules/auth/hooks";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

export const CHECKOUT_STEPS = Object.freeze({
  ADDRESS: "ADDRESS",
  SHIPPING: "SHIPPING",
  PAYMENT: "PAYMENT",
  REVIEW: "REVIEW",
  COMPLETE: "COMPLETE",
});

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

const useCheckout = ({
  checkoutToken = null,
  skip = false,
  onOrderCreated,
  onCompleted,
} = {}) => {

  /* ------------------------------------------------------------------------ */
  /* Addresses from Shared Module                                             */
  /* ------------------------------------------------------------------------ */

  const {
    addresses,
    defaultAddress,
    loading: addressesLoading,
    error: addressesError,
    refetch: refetchAddresses,
  } = useAddresses({ skip });

  /* ------------------------------------------------------------------------ */
  /* Checkout Selection State                                                 */
  /* ------------------------------------------------------------------------ */

  const [selectedAddress, setSelectedAddress] = useState(null);
  const [selectedShipping, setSelectedShipping] = useState(null);
  const [checkoutStep, setCheckoutStep] = useState(CHECKOUT_STEPS.ADDRESS);
  const [cartItems, setCartItems] = useState([]);

  /* ------------------------------------------------------------------------ */
  /* Automatically select the default address                                 */
  /* ------------------------------------------------------------------------ */

  useEffect(() => {
    if (!selectedAddress && defaultAddress) {
      setSelectedAddress(defaultAddress);
    }
  }, [defaultAddress, selectedAddress]);

  /* ------------------------------------------------------------------------ */
  /* Checkout Query                                                           */
  /* ------------------------------------------------------------------------ */

  const {
    data: checkoutData,
    loading: checkoutLoading,
    error: checkoutError,
    refetch: refetchCheckout,
  } = useQuery(
    GET_CHECKOUT_BY_TOKEN,
    {
      variables: { token: checkoutToken },
      skip: skip || !checkoutToken,
      fetchPolicy: "cache-and-network",
      notifyOnNetworkStatusChange: true,
    }
  );

  /* ------------------------------------------------------------------------ */
  /* Checkout Lines Query                                                     */
  /* ------------------------------------------------------------------------ */

  const {
    data: linesData,
    loading: linesLoading,
    error: linesError,
    refetch: refetchLines,
  } = useQuery(
    GET_CHECKOUT_LINES,
    {
      variables: { checkoutId: checkoutData?.allCheckouts?.edges?.[0]?.node?.id },
      skip: skip || !checkoutData?.allCheckouts?.edges?.[0]?.node?.id,
      fetchPolicy: "cache-and-network",
    }
  );

  /* ------------------------------------------------------------------------ */
  /* Mutations                                                                */
  /* ------------------------------------------------------------------------ */

  const [
    createCheckout,
    {
      loading: creatingCheckout,
      error: createCheckoutError,
    },
  ] = useMutation(CREATE_CHECKOUT);

  const [
    updateCheckout,
    {
      loading: updatingCheckout,
      error: updateCheckoutError,
    },
  ] = useMutation(UPDATE_CHECKOUT);

  const [
    deleteCheckout,
    {
      loading: deletingCheckout,
      error: deleteCheckoutError,
    },
  ] = useMutation(DELETE_CHECKOUT);

  const [
    addLine,
    {
      loading: addingLine,
      error: addLineError,
    },
  ] = useMutation(CREATE_CHECKOUT_LINE);

  const [
    updateLine,
    {
      loading: updatingLine,
      error: updateLineError,
    },
  ] = useMutation(UPDATE_CHECKOUT_LINE);

  const [
    removeLine,
    {
      loading: removingLine,
      error: removeLineError,
    },
  ] = useMutation(DELETE_CHECKOUT_LINE);

  const [
    completeCheckout,
    {
      loading: completingCheckout,
      error: completeCheckoutError,
    },
  ] = useMutation(COMPLETE_CHECKOUT);

  const [
    validateStock,
    {
      loading: validatingStock,
      error: validateStockError,
    },
  ] = useMutation(VALIDATE_CHECKOUT_STOCK);

  /* ------------------------------------------------------------------------ */
  /* Memoized Data                                                            */
  /* ------------------------------------------------------------------------ */

  const checkout = useMemo(() => {
    // GET_CHECKOUT_BY_TOKEN returns allCheckouts (connection) → first edge node
    // GET_CHECKOUT returns checkout (single node)
    return (
      checkoutData?.allCheckouts?.edges?.[0]?.node ??
      checkoutData?.checkout ??
      null
    );
  }, [checkoutData]);

  const checkoutLines = useMemo(() => {
    // GET_CHECKOUT_LINES returns allCheckoutLines (connection)
    // GET_ALL_CHECKOUT_LINES returns allCheckoutLines (connection)
    // Fall back to nested checkout.lines if present
    return (
      linesData?.allCheckoutLines?.edges?.map(e => e.node) ??
      linesData?.checkoutLines?.edges?.map(e => e.node) ??
      checkout?.lines?.edges?.map(e => e.node) ??
      checkout?.lines ??
      []
    );
  }, [linesData, checkout]);

  /* ------------------------------------------------------------------------ */
  /* Checkout Totals                                                          */
  /* ------------------------------------------------------------------------ */

  const totals = useMemo(() => {
    if (!checkout) {
      return {
        subtotal: 0,
        discount: 0,
        shippingFee: 0,
        tax: 0,
        total: 0,
      };
    }

    const subtotal = checkout.subtotal?.gross?.amount ?? 0;
    const total = checkout.total?.gross?.amount ?? 0;
    const shippingFee = checkout.shippingPrice?.gross?.amount ?? 0;
    const discount = checkout.discount?.amount ?? 0;
    const tax =
      (checkout.total?.gross?.amount ?? 0) -
      (checkout.total?.net?.amount ?? 0);

    return {
      subtotal,
      discount,
      shippingFee,
      tax,
      total,
    };
  }, [checkout]);

  /* ------------------------------------------------------------------------ */
  /* Create a New Checkout                                                    */
  /* ------------------------------------------------------------------------ */

  const initializeCheckout = useCallback(async (email, channelId, currency) => {
    try {
      const { data } = await createCheckout({
        variables: {
          input: {
            email,
            channel: channelId,
            currency: currency || "USD",
            country: "US",
            languageCode: "en",
          },
        },
      });

      const newCheckout = data?.createCheckout?.checkout;

      if (newCheckout) {
        await refetchCheckout();
        return {
          success: true,
          checkout: newCheckout,
        };
      }

      return {
        success: false,
        error: "Failed to create checkout",
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    }
  }, [createCheckout, refetchCheckout]);

  /* ------------------------------------------------------------------------ */
  /* Reset Checkout                                                           */
  /* ------------------------------------------------------------------------ */

  const resetCheckout = useCallback(() => {
    setSelectedAddress(defaultAddress ?? null);
    setSelectedShipping(null);
    setCheckoutStep(CHECKOUT_STEPS.ADDRESS);
    setCartItems([]);
  }, [defaultAddress]);

  /* ------------------------------------------------------------------------ */
  /* Actions                                                                  */
  /* ------------------------------------------------------------------------ */

  const selectAddress = useCallback((address) => {
    setSelectedAddress(address);
    setCheckoutStep(CHECKOUT_STEPS.SHIPPING);

    if (checkout?.id) {
      updateCheckout({
        variables: {
          input: {
            id: checkout.id,
            shippingAddress: address.id,
            country: address.country?.code || "US",
          },
        },
      });
    }
  }, [checkout, updateCheckout]);

  const selectShipping = useCallback((shipping) => {
    setSelectedShipping(shipping);
    setCheckoutStep(CHECKOUT_STEPS.PAYMENT);

    if (checkout?.id) {
      updateCheckout({
        variables: {
          input: {
            id: checkout.id,
            shippingMethod: shipping.id,
          },
        },
      });
    }
  }, [checkout, updateCheckout]);

  const goToStep = useCallback((step) => {
    setCheckoutStep(step);
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Add Item to Cart                                                         */
  /* ------------------------------------------------------------------------ */

  const addToCart = useCallback(async (variantId, quantity = 1) => {
    if (!checkout?.id) {
      return {
        success: false,
        error: "No active checkout",
      };
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

      const newLine = data?.createCheckoutLine?.line;

      if (newLine) {
        await refetchLines();
        return {
          success: true,
          line: newLine,
        };
      }

      return {
        success: false,
        error: "Failed to add item",
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    }
  }, [checkout, addLine, refetchLines]);

  /* ------------------------------------------------------------------------ */
  /* Update Cart Item                                                         */
  /* ------------------------------------------------------------------------ */

  const updateCartItem = useCallback(async (lineId, quantity) => {
    try {
      const { data } = await updateLine({
        variables: {
          input: {
            id: lineId,
            quantity,
          },
        },
      });

      const updatedLine = data?.updateCheckoutLine?.line;

      if (updatedLine) {
        await refetchLines();
        return {
          success: true,
          line: updatedLine,
        };
      }

      return {
        success: false,
        error: "Failed to update item",
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    }
  }, [updateLine, refetchLines]);

  /* ------------------------------------------------------------------------ */
  /* Remove Cart Item                                                         */
  /* ------------------------------------------------------------------------ */

  const removeFromCart = useCallback(async (lineId) => {
    try {
      const { data } = await removeLine({
        variables: {
          input: { id: lineId },
        },
      });

      if (data?.deleteCheckoutLine?.success) {
        await refetchLines();
        return {
          success: true,
        };
      }

      return {
        success: false,
        error: "Failed to remove item",
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    }
  }, [removeLine, refetchLines]);

  /* ------------------------------------------------------------------------ */
  /* Validate Stock                                                           */
  /* ------------------------------------------------------------------------ */

  const validateCartStock = useCallback(async () => {
    if (!checkout?.id) {
      return {
        isValid: false,
        errors: ["No checkout found"],
      };
    }

    try {
      const { data } = await validateStock({
        variables: {
          input: { checkoutId: checkout.id },
        },
      });

      const result = data?.validateCheckoutStock;

      return {
        isValid: result?.isValid ?? false,
        availableQuantities: result?.availableQuantities,
        errors: result?.errors ?? [],
      };
    } catch (error) {
      return {
        isValid: false,
        errors: [error.message || "Stock validation failed"],
      };
    }
  }, [checkout, validateStock]);

  /* ------------------------------------------------------------------------ */
  /* Validation                                                               */
  /* ------------------------------------------------------------------------ */

  const validateCheckout = useCallback(async () => {
    const errors = {};

    if (!selectedAddress) {
      errors.address = "Please select a delivery address.";
    }

    if (!selectedShipping) {
      errors.shipping = "Please select a shipping method.";
    }

    if (!checkoutLines?.length) {
      errors.lines = "Your cart is empty.";
    }

    if (checkoutLines?.length) {
      const stockValidation = await validateCartStock();
      if (!stockValidation.isValid) {
        errors.stock = stockValidation.errors;
      }
    }

    return {
      valid: Object.keys(errors).length === 0,
      errors,
    };
  }, [selectedAddress, selectedShipping, checkoutLines, validateCartStock]);

  /* ------------------------------------------------------------------------ */
  /* Place Order                                                              */
  /* ------------------------------------------------------------------------ */

  const placeOrder = useCallback(async (redirectUrl) => {
    const validation = await validateCheckout();

    if (!validation.valid) {
      return {
        success: false,
        errors: validation.errors,
      };
    }

    try {
      const { data } = await completeCheckout({
        variables: {
          input: {
            checkoutId: checkout.id,
            redirectUrl:
              redirectUrl ||
              (typeof window !== "undefined"
                ? window.location.origin + "/order-confirmation"
                : "/order-confirmation"),
          },
        },
      });

      const response = data?.completeCheckout;

      if (response?.success) {
        setCheckoutStep(CHECKOUT_STEPS.COMPLETE);
        onOrderCreated?.(response.order);
        onCompleted?.(response.order);

        return {
          success: true,
          order: response.order,
        };
      }

      return {
        success: false,
        errors: response?.errors || ["Order failed"],
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    }
  }, [checkout, completeCheckout, validateCheckout, onOrderCreated, onCompleted]);

  /* ------------------------------------------------------------------------ */
  /* Error Normalization                                                      */
  /* ------------------------------------------------------------------------ */

  const error = useMemo(() => {
    const currentError =
      checkoutError ??
      addressesError ??
      linesError ??
      createCheckoutError ??
      updateCheckoutError ??
      deleteCheckoutError ??
      addLineError ??
      updateLineError ??
      removeLineError ??
      completeCheckoutError ??
      validateStockError;

    if (!currentError) {
      return null;
    }

    return {
      message: currentError.message ?? "Checkout failed.",
      graphQLErrors: currentError.graphQLErrors ?? [],
      networkError: currentError.networkError ?? null,
    };
  }, [
    checkoutError,
    addressesError,
    linesError,
    createCheckoutError,
    updateCheckoutError,
    deleteCheckoutError,
    addLineError,
    updateLineError,
    removeLineError,
    completeCheckoutError,
    validateStockError,
  ]);

  /* ------------------------------------------------------------------------ */
  /* Loading States                                                           */
  /* ------------------------------------------------------------------------ */

  const loading = (
    checkoutLoading ||
    addressesLoading ||
    linesLoading ||
    creatingCheckout ||
    updatingCheckout ||
    deletingCheckout ||
    addingLine ||
    updatingLine ||
    removingLine ||
    completingCheckout ||
    validatingStock
  );

  /* ------------------------------------------------------------------------ */
  /* Hook Return                                                              */
  /* ------------------------------------------------------------------------ */

  return {
    checkout,
    checkoutLines,

    customer: {
      addresses,
      defaultAddress,
      selectedAddress,
      hasAddresses: addresses?.length > 0,
    },

    shipping: {
      selected: selectedShipping,
      selectedId: selectedShipping?.id,
      methods: [],
      loading: false,
    },

    cart: {
      items: checkoutLines,
      count: checkoutLines?.length || 0,
      totalItems:
        checkoutLines?.reduce((sum, item) => sum + item.quantity, 0) || 0,
    },

    totals,

    state: {
      step: checkoutStep,
      steps: CHECKOUT_STEPS,
    },

    actions: {
      initializeCheckout,
      selectAddress,
      selectShipping,
      goToStep,
      addToCart,
      updateCartItem,
      removeFromCart,
      validateCartStock,
      placeOrder,
      resetCheckout,
      refetchCheckout,
      refetchAddresses,
      refetchLines,
    },

    loading,

    error,

    loadingStates: {
      checkout: checkoutLoading,
      addresses: addressesLoading,
      lines: linesLoading,
      creating: creatingCheckout,
      updating: updatingCheckout,
      deleting: deletingCheckout,
      addingLine: addingLine,
      updatingLine: updatingLine,
      removingLine: removingLine,
      completing: completingCheckout,
      validating: validatingStock,
    },
  };
};

export default useCheckout;