/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useProductVariants.js               */
/* -------------------------------------------------------------------------- */

import { useState, useMemo, useCallback, useEffect } from "react";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEFAULT_QUANTITY = 1;
const MIN_QUANTITY = 1;
const MAX_QUANTITY = 999;

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

const useProductVariants = ({
  product,
  variants = [],
  attributes = [],
  initialSelection = {},
  initialQuantity = DEFAULT_QUANTITY,
  minQuantity = MIN_QUANTITY,
  maxQuantity = MAX_QUANTITY,
} = {}) => {

  /* ------------------------------------------------------------------------ */
  /* State                                                                    */
  /* ------------------------------------------------------------------------ */

  const [selectedAttributes, setSelectedAttributes] = useState(initialSelection);
  const [quantity, setQuantity] = useState(initialQuantity);
  const [error, setError] = useState(null);

  /* ------------------------------------------------------------------------ */
  /* Variant Groups                                                           */
  /* ------------------------------------------------------------------------ */

  const variantGroups = useMemo(() => {
    const source = variants.length ? variants : product?.variants ?? [];
    if (source.length && !attributes.length) {
      // Try to extract attributes from variants
      const allAttributes = {};
      source.forEach(v => {
        if (v.attributes) {
          Object.entries(v.attributes).forEach(([key, value]) => {
            if (!allAttributes[key]) {
              allAttributes[key] = new Set();
            }
            allAttributes[key].add(value);
          });
        }
      });
      return Object.entries(allAttributes).map(([key, values]) => ({
        key,
        label: key.replace(/_/g, ' ').toUpperCase(),
        options: Array.from(values).map(value => ({
          value,
          label: value.replace(/_/g, ' '),
        })),
      }));
    }
    return attributes;
  }, [variants, product, attributes]);

  /* ------------------------------------------------------------------------ */
  /* Available Variants                                                       */
  /* ------------------------------------------------------------------------ */

  const availableVariants = useMemo(() => {
    const source = variants.length ? variants : product?.variants ?? [];
    return source.filter(v => v.stockQuantity > 0 || v.isPreorder);
  }, [variants, product]);

  /* ------------------------------------------------------------------------ */
  /* Find Matching Variant                                                    */
  /* ------------------------------------------------------------------------ */

  const matchedVariant = useMemo(() => {
    if (!Object.keys(selectedAttributes).length || !availableVariants.length) {
      return null;
    }

    return availableVariants.find(variant => {
      const variantAttrs = variant.attributes || {};
      return Object.entries(selectedAttributes).every(([key, value]) => {
        return variantAttrs[key] === value;
      });
    }) ?? null;
  }, [availableVariants, selectedAttributes]);

  /* ------------------------------------------------------------------------ */
  /* SKU Resolution                                                           */
  /* ------------------------------------------------------------------------ */

  const sku = useMemo(() => {
    return matchedVariant?.sku || product?.sku || null;
  }, [matchedVariant, product]);

  /* ------------------------------------------------------------------------ */
  /* Price                                                                    */
  /* ------------------------------------------------------------------------ */

  const price = useMemo(() => {
    if (matchedVariant?.price) {
      return typeof matchedVariant.price === 'object' 
        ? matchedVariant.price.amount 
        : matchedVariant.price;
    }
    if (product?.price) {
      return typeof product.price === 'object'
        ? product.price.amount
        : product.price;
    }
    return 0;
  }, [matchedVariant, product]);

  const currency = useMemo(() => {
    if (matchedVariant?.price?.currency) return matchedVariant.price.currency;
    if (product?.price?.currency) return product.price.currency;
    if (matchedVariant?.currency) return matchedVariant.currency;
    return 'USD';
  }, [matchedVariant, product]);

  const formattedPrice = useMemo(() => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(price);
  }, [price, currency]);

  /* ------------------------------------------------------------------------ */
  /* Stock                                                                    */
  /* ------------------------------------------------------------------------ */

  const stock = useMemo(() => {
    const available = matchedVariant?.stockQuantity ?? product?.stockQuantity ?? 0;
    const maxAllowed = matchedVariant?.quantityLimitPerCustomer ?? maxQuantity;
    const isPreorder = matchedVariant?.isPreorder ?? false;

    return {
      quantity: available,
      available: available > 0 || isPreorder,
      maxAllowed: Math.min(available, maxAllowed),
      label: available > 0 ? 'In Stock' : isPreorder ? 'Preorder Available' : 'Out of Stock',
      isPreorder,
    };
  }, [matchedVariant, product, maxQuantity]);

  /* ------------------------------------------------------------------------ */
  /* Selected Labels                                                          */
  /* ------------------------------------------------------------------------ */

  const selectedLabels = useMemo(() => {
    const labels = {};
    variantGroups.forEach(group => {
      const selected = selectedAttributes[group.key];
      const option = group.options?.find(item => item.value === selected);
      if (option) {
        labels[group.key] = option.label;
      }
    });
    return labels;
  }, [variantGroups, selectedAttributes]);

  /* ------------------------------------------------------------------------ */
  /* Validation                                                               */
  /* ------------------------------------------------------------------------ */

  const missingAttributes = useMemo(() => {
    if (!variantGroups.length) return [];
    return variantGroups
      .filter(group => !selectedAttributes[group.key])
      .map(group => group.label);
  }, [variantGroups, selectedAttributes]);

  const hasAllAttributes = missingAttributes.length === 0;
  const isReady = hasAllAttributes && stock.available;

  /* ------------------------------------------------------------------------ */
  /* Quantity Controls                                                        */
  /* ------------------------------------------------------------------------ */

  const canIncrease = quantity < stock.maxAllowed;
  const canDecrease = quantity > minQuantity;

  const increaseQuantity = useCallback(() => {
    if (canIncrease) {
      setQuantity(prev => Math.min(prev + 1, stock.maxAllowed));
    }
  }, [canIncrease, stock.maxAllowed]);

  const decreaseQuantity = useCallback(() => {
    if (canDecrease) {
      setQuantity(prev => Math.max(minQuantity, prev - 1));
    }
  }, [canDecrease, minQuantity]);

  const updateQuantity = useCallback((value) => {
    const next = Math.max(minQuantity, Math.min(Number(value) || minQuantity, stock.maxAllowed));
    setQuantity(next);
  }, [minQuantity, stock.maxAllowed]);

  /* ------------------------------------------------------------------------ */
  /* Select Variant Attribute                                                 */
  /* ------------------------------------------------------------------------ */

  const selectAttribute = useCallback((key, value) => {
    setError(null);
    setSelectedAttributes(prev => ({
      ...prev,
      [key]: value,
    }));
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Clear Selection                                                          */
  /* ------------------------------------------------------------------------ */

  const clearSelection = useCallback(() => {
    setSelectedAttributes({});
    setQuantity(initialQuantity);
    setError(null);
  }, [initialQuantity]);

  /* ------------------------------------------------------------------------ */
  /* Cart Payload                                                             */
  /* ------------------------------------------------------------------------ */

  const cartItem = useMemo(() => {
    if (!product || !isReady) return null;

    return {
      productId: product.id,
      variantId: matchedVariant?.id || null,
      sku: sku,
      name: product.name,
      variantName: matchedVariant?.name || '',
      price: price,
      currency: currency,
      quantity: quantity,
      attributes: selectedAttributes,
      selections: selectedLabels,
      image: matchedVariant?.image || product.thumbnail?.url || null,
      stock: stock.quantity,
      isPreorder: stock.isPreorder,
    };
  }, [product, matchedVariant, sku, price, currency, quantity, selectedAttributes, selectedLabels, stock, isReady]);

  /* ------------------------------------------------------------------------ */
  /* Summary                                                                  */
  /* ------------------------------------------------------------------------ */

  const summary = useMemo(() => ({
    attributes: selectedLabels,
    quantity,
    sku,
    price,
    formattedPrice,
    currency,
    stock,
    ready: isReady,
    hasAttributes: variantGroups.length > 0,
    missingAttributes,
  }), [selectedLabels, quantity, sku, price, formattedPrice, currency, stock, isReady, variantGroups, missingAttributes]);

  /* ------------------------------------------------------------------------ */
  /* Reset                                                                    */
  /* ------------------------------------------------------------------------ */

  const reset = useCallback(() => {
    setSelectedAttributes(initialSelection);
    setQuantity(initialQuantity);
    setError(null);
  }, [initialSelection, initialQuantity]);

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Variant Groups
    variantGroups,
    availableVariants,

    // Selection
    selectedAttributes,
    selectedLabels,
    selectAttribute,
    clearSelection,

    // Validation
    missingAttributes,
    hasAllAttributes,
    isReady,
    error,

    // Matching Variant
    matchedVariant,
    sku,

    // Pricing
    price,
    formattedPrice,
    currency,

    // Stock
    stock,

    // Quantity
    quantity,
    setQuantity,
    increaseQuantity,
    decreaseQuantity,
    updateQuantity,
    canIncrease,
    canDecrease,
    minQuantity,
    maxQuantity: stock.maxAllowed,

    // Cart
    cartItem,

    // Summary
    summary,

    // Reset
    reset,
  };
};

export default useProductVariants;