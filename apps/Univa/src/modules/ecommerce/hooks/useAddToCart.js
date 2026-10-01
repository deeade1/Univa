/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useAddToCart.js                     */
/* -------------------------------------------------------------------------- */

import { useCallback, useMemo } from "react";
import { useMutation } from "@apollo/client/react";

import { CREATE_CHECKOUT_LINE } from "@/modules/ecommerce/api/productQuery/mutations/checkout";

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

const useAddToCart = ({
  checkoutId,
  onCompleted,
  onError,
  onSuccess,
} = {}) => {

  /* ------------------------------------------------------------------------ */
  /* Mutation                                                                 */
  /* ------------------------------------------------------------------------ */

  const [
    addToCartMutation,
    {
      data,
      loading,
      error,
    },
  ] = useMutation(CREATE_CHECKOUT_LINE, {
    onCompleted(response) {
      onCompleted?.(response);
      onSuccess?.(response);
    },
    onError(mutationError) {
      console.warn("Add to cart failed:", mutationError);
      onError?.(mutationError);
    },
  });

  /* ------------------------------------------------------------------------ */
  /* Error State                                                              */
  /* ------------------------------------------------------------------------ */

  const normalizedError = useMemo(() => {
    if (!error) return null;
    return {
      message: error.message ?? "Unable to add item to cart.",
      graphQLErrors: error.graphQLErrors ?? [],
      networkError: error.networkError ?? null,
    };
  }, [error]);

  /* ------------------------------------------------------------------------ */
  /* Build Cart Payload                                                       */
  /* ------------------------------------------------------------------------ */

  const buildCartPayload = useCallback(
    ({
      product,
      variant,
      quantity = 1,
      selections = {},
    }) => {
      if (!product) {
        return null;
      }

      return {
        productId: product.id,
        variantId: variant?.id ?? null,
        sku: variant?.sku ?? product.sku ?? null,
        quantity,
        selections,
        price: variant?.price?.amount ?? variant?.price ?? product?.price?.amount ?? product?.price ?? 0,
        currency: variant?.price?.currency ?? product?.price?.currency ?? "USD",
        image: variant?.image ?? product?.thumbnail?.url ?? null,
        name: product.name,
        variantName: variant?.name ?? "",
        stock: variant?.stockQuantity ?? product?.stockQuantity ?? 0,
      };
    },
    []
  );

  /* ------------------------------------------------------------------------ */
  /* Validate                                                                 */
  /* ------------------------------------------------------------------------ */

  const validateCartItem = useCallback((item) => {
    if (!item) {
      return {
        valid: false,
        message: "Invalid cart item.",
      };
    }

    if (!item.productId) {
      return {
        valid: false,
        message: "Product is required.",
      };
    }

    if (item.quantity <= 0) {
      return {
        valid: false,
        message: "Quantity must be greater than zero.",
      };
    }

    if (item.stock !== undefined && item.quantity > item.stock) {
      return {
        valid: false,
        message: `Only ${item.stock} items available in stock.`,
      };
    }

    return {
      valid: true,
      message: null,
    };
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Optimistic Response                                                      */
  /* ------------------------------------------------------------------------ */

  const createOptimisticResponse = useCallback((item) => {
    return {
      createCheckoutLine: {
        __typename: "CreateCheckoutLinePayload",
        line: {
          __typename: "CheckoutLineNode",
          id: `temp-${Date.now()}`,
          quantity: item.quantity,
          isGift: false,
          totalPrice: {
            __typename: "TaxedMoney",
            gross: {
              __typename: "Money",
              amount: item.price * item.quantity,
              currency: item.currency,
            },
          },
          variant: {
            __typename: "ProductVariantNode",
            id: item.variantId,
            name: item.variantName || item.name,
            sku: item.sku,
            product: {
              __typename: "ProductNode",
              id: item.productId,
              name: item.name,
            },
          },
        },
      },
    };
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Update Cache                                                             */
  /* ------------------------------------------------------------------------ */

  const updateCartCache = useCallback(
    (
      cache,
      { data: mutationData }
    ) => {
      const line = mutationData?.createCheckoutLine?.line;
      if (!line) return;

      // Update checkout query cache
      cache.modify({
        fields: {
          checkout(existingCheckout = {}) {
            const updatedLines = [...(existingCheckout.lines || []), line];
            return {
              ...existingCheckout,
              lines: updatedLines,
            };
          },
        },
      });
    },
    []
  );

  /* ------------------------------------------------------------------------ */
  /* Add To Cart                                                              */
  /* ------------------------------------------------------------------------ */

  const addToCart = useCallback(
    async ({
      product,
      variant,
      quantity = 1,
      selections = {},
    }) => {
      if (!checkoutId) {
        return {
          success: false,
          message: "No active checkout found. Please create a checkout first.",
        };
      }

      const payload = buildCartPayload({
        product,
        variant,
        quantity,
        selections,
      });

      if (!payload) {
        return {
          success: false,
          message: "Invalid product data.",
        };
      }

      const validation = validateCartItem(payload);
      if (!validation.valid) {
        return {
          success: false,
          message: validation.message,
        };
      }

      try {
        const result = await addToCartMutation({
          variables: {
            input: {
              checkoutId: checkoutId,
              variantId: payload.variantId || product.variants?.[0]?.id,
              quantity: payload.quantity,
            },
          },
          optimisticResponse: createOptimisticResponse(payload),
          update: updateCartCache,
        });

        const line = result.data?.createCheckoutLine?.line;

        if (line) {
          return {
            success: true,
            line,
            message: `${product?.name || "Item"} added to cart!`,
          };
        }

        return {
          success: false,
          message: "Failed to add item to cart.",
        };
      } catch (mutationError) {
        return {
          success: false,
          error: mutationError,
        };
      }
    },
    [addToCartMutation, checkoutId, buildCartPayload, validateCartItem, createOptimisticResponse, updateCartCache]
  );

  /* ------------------------------------------------------------------------ */
  /* Cart                                                                     */
  /* ------------------------------------------------------------------------ */

  const cart = useMemo(() => {
    return data?.createCheckoutLine?.checkout ?? null;
  }, [data]);

  /* ------------------------------------------------------------------------ */
  /* Cart Count                                                               */
  /* ------------------------------------------------------------------------ */

  const cartCount = useMemo(() => {
    if (!cart?.lines) return 0;
    return cart.lines.reduce((total, item) => total + (item.quantity ?? 0), 0);
  }, [cart]);

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    addToCart,
    buildCartPayload,
    validateCartItem,
    loading,
    isAdding: loading,
    canAdd: !loading && !error,
    data,
    cart,
    cartCount,
    error: normalizedError,
    reset: useCallback(() => {}, []),
  };
};

export default useAddToCart;