/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/utils/pricing.js                          */
/* -------------------------------------------------------------------------- */

/**
 * ============================================================================
 * Ecommerce Pricing Utilities
 * ============================================================================
 *
 * Centralized pricing calculations used throughout the ecommerce module.
 *
 * Used by:
 * - Cart
 * - Checkout
 * - Product Details
 * - Order Summary
 * - Shipping
 * - Coupons
 * - Taxes
 * - Seller Pages
 *
 * ============================================================================
 */

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

export const DEFAULT_TAX_RATE = 0.075;

export const FREE_SHIPPING_THRESHOLD = 10000;

export const DEFAULT_SHIPPING_FEE = 1500;

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const toNumber = (value) => {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : 0;
};

const round = (value) =>
  Math.round((value + Number.EPSILON) * 100) / 100;

/* -------------------------------------------------------------------------- */
/* Item Price                                                                 */
/* -------------------------------------------------------------------------- */

/**
 * Returns the total price of a single cart item.
 */

export function calculateItemTotal(item = {}) {
  return round(
    toNumber(item.price_per_unit) *
      toNumber(item.quantity)
  );
}

/* -------------------------------------------------------------------------- */
/* Cart Subtotal                                                              */
/* -------------------------------------------------------------------------- */

export function calculateSubtotal(cart = []) {
  return round(
    cart.reduce(
      (total, item) =>
        total +
        calculateItemTotal(item),
      0
    )
  );
}

/* -------------------------------------------------------------------------- */
/* Total Quantity                                                             */
/* -------------------------------------------------------------------------- */

export function calculateItemCount(cart = []) {
  return cart.reduce(
    (total, item) =>
      total +
      toNumber(item.quantity),
    0
  );
}

/* -------------------------------------------------------------------------- */
/* Discount                                                                   */
/* -------------------------------------------------------------------------- */

export function calculateDiscount(
  subtotal = 0,
  discount = 0
) {
  return round(
    Math.min(
      toNumber(discount),
      toNumber(subtotal)
    )
  );
}

/* -------------------------------------------------------------------------- */
/* Coupon                                                                      */
/* -------------------------------------------------------------------------- */

export function calculateCouponDiscount(
  subtotal = 0,
  coupon = null
) {
  if (!coupon) return 0;

  if (coupon.type === "percentage") {
    return round(
      subtotal *
        (coupon.value / 100)
    );
  }

  if (coupon.type === "fixed") {
    return round(
      Math.min(
        coupon.value,
        subtotal
      )
    );
  }

  return 0;
}

/* -------------------------------------------------------------------------- */
/* Tax                                                                        */
/* -------------------------------------------------------------------------- */

export function calculateTax(
  subtotal = 0,
  taxRate = DEFAULT_TAX_RATE
) {
  return round(
    subtotal * taxRate
  );
}

/* -------------------------------------------------------------------------- */
/* Shipping                                                                   */
/* -------------------------------------------------------------------------- */

export function calculateShipping(
  subtotal = 0,
  {
    fee = DEFAULT_SHIPPING_FEE,

    freeShippingThreshold =
      FREE_SHIPPING_THRESHOLD,

    freeShipping = false,
  } = {}
) {
  if (freeShipping) {
    return 0;
  }

  if (
    subtotal >=
    freeShippingThreshold
  ) {
    return 0;
  }

  return round(fee);
}

/* -------------------------------------------------------------------------- */
/* Grand Total                                                                */
/* -------------------------------------------------------------------------- */

export function calculateGrandTotal({
  subtotal = 0,

  tax = 0,

  shipping = 0,

  discount = 0,
}) {
  return round(
    subtotal +
      tax +
      shipping -
      discount
  );
}

/* -------------------------------------------------------------------------- */
/* Full Cart Summary                                                          */
/* -------------------------------------------------------------------------- */

/**
 * Generates every pricing value needed by the UI.
 */

export function calculateCartSummary(
  cart = [],
  options = {}
) {
  const subtotal =
    calculateSubtotal(cart);

  const couponDiscount =
    calculateCouponDiscount(
      subtotal,
      options.coupon
    );

  const manualDiscount =
    calculateDiscount(
      subtotal,
      options.discount
    );

  const discount =
    couponDiscount +
    manualDiscount;

  const taxableAmount =
    Math.max(
      subtotal - discount,
      0
    );

  const tax =
    calculateTax(
      taxableAmount,
      options.taxRate ??
        DEFAULT_TAX_RATE
    );

  const shipping =
    calculateShipping(
      taxableAmount,
      {
        fee:
          options.shippingFee,

        freeShipping:
          options.freeShipping,

        freeShippingThreshold:
          options.freeShippingThreshold,
      }
    );

  const total =
    calculateGrandTotal({
      subtotal:
        taxableAmount,

      tax,

      shipping,

      discount: 0,
    });

  return {
    itemCount:
      calculateItemCount(cart),

    subtotal,

    discount,

    taxableAmount,

    tax,

    shipping,

    total,

    freeShipping:
      shipping === 0,
  };
}

/* -------------------------------------------------------------------------- */
/* Currency                                                                   */
/* -------------------------------------------------------------------------- */

/**
 * Formats a value as currency.
 */

export function formatPrice(
  value,
  {
    currency = "NGN",

    locale = "en-NG",
  } = {}
) {
  return new Intl.NumberFormat(
    locale,
    {
      style: "currency",

      currency,

      maximumFractionDigits: 2,
    }
  ).format(
    toNumber(value)
  );
}

/* -------------------------------------------------------------------------- */
/* Price Saving                                                               */
/* -------------------------------------------------------------------------- */

export function calculateSavings(
  originalPrice,
  currentPrice
) {
  return round(
    Math.max(
      toNumber(originalPrice) -
        toNumber(currentPrice),
      0
    )
  );
}

/* -------------------------------------------------------------------------- */
/* Discount Percentage                                                        */
/* -------------------------------------------------------------------------- */

export function calculateDiscountPercent(
  originalPrice,
  currentPrice
) {
  originalPrice =
    toNumber(originalPrice);

  currentPrice =
    toNumber(currentPrice);

  if (originalPrice <= 0)
    return 0;

  return Math.round(
    ((originalPrice -
      currentPrice) /
      originalPrice) *
      100
  );
}

/* -------------------------------------------------------------------------- */
/* Default Export                                                             */
/* -------------------------------------------------------------------------- */

export default {
  calculateItemTotal,

  calculateSubtotal,

  calculateItemCount,

  calculateDiscount,

  calculateCouponDiscount,

  calculateTax,

  calculateShipping,

  calculateGrandTotal,

  calculateCartSummary,

  calculateSavings,

  calculateDiscountPercent,

  formatPrice,
};