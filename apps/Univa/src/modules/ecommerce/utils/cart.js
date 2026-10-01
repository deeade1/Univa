/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/utils/cart.js                             */
/* -------------------------------------------------------------------------- */

import {
  calculateItemTotal,
  calculateSubtotal,
  calculateItemCount,
  calculateCartSummary,
} from "./pricing";

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const toNumber = (value) => {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : 0;
};

const getProductId = (product) =>
  String(
    product.id ??
      product.productId ??
      product.node?.id
  );

/* -------------------------------------------------------------------------- */
/* Find Item                                                                  */
/* -------------------------------------------------------------------------- */

export function findCartItem(
  cart = [],
  productId
) {
  return cart.find(
    (item) =>
      String(item.id) ===
      String(productId)
  );
}

/* -------------------------------------------------------------------------- */
/* Exists                                                                     */
/* -------------------------------------------------------------------------- */

export function isInCart(
  cart = [],
  productId
) {
  return cart.some(
    (item) =>
      String(item.id) ===
      String(productId)
  );
}

/* -------------------------------------------------------------------------- */
/* Add Item                                                                   */
/* -------------------------------------------------------------------------- */

export function addToCart(
  cart = [],
  product,
  quantity = 1
) {
  if (!product)
    return cart;

  const id =
    getProductId(product);

  const stock =
    toNumber(
      product.stock ??
        Infinity
    );

  const existing =
    findCartItem(cart, id);

  if (existing) {
    return cart.map((item) => {
      if (
        String(item.id) !== id
      )
        return item;

      return {
        ...item,

        quantity: Math.min(
          item.quantity +
            quantity,
          stock
        ),
      };
    });
  }

  return [
    ...cart,
    {
      ...product,

      id,

      quantity: Math.min(
        quantity,
        stock
      ),
    },
  ];
}

/* -------------------------------------------------------------------------- */
/* Remove Item                                                                */
/* -------------------------------------------------------------------------- */

export function removeFromCart(
  cart = [],
  productId
) {
  return cart.filter(
    (item) =>
      String(item.id) !==
      String(productId)
  );
}

/* -------------------------------------------------------------------------- */
/* Update Quantity                                                            */
/* -------------------------------------------------------------------------- */

export function updateQuantity(
  cart = [],
  productId,
  quantity
) {
  quantity =
    toNumber(quantity);

  if (quantity <= 0) {
    return removeFromCart(
      cart,
      productId
    );
  }

  return cart.map((item) => {
    if (
      String(item.id) !==
      String(productId)
    ) {
      return item;
    }

    const stock =
      toNumber(
        item.stock ??
          Infinity
      );

    return {
      ...item,

      quantity:
        quantity > stock
          ? stock
          : quantity,
    };
  });
}

/* -------------------------------------------------------------------------- */
/* Increase Quantity                                                          */
/* -------------------------------------------------------------------------- */

export function increaseQuantity(
  cart = [],
  productId
) {
  return cart.map((item) => {
    if (
      String(item.id) !==
      String(productId)
    ) {
      return item;
    }

    const stock =
      toNumber(
        item.stock ??
          Infinity
      );

    return {
      ...item,

      quantity: Math.min(
        item.quantity + 1,
        stock
      ),
    };
  });
}

/* -------------------------------------------------------------------------- */
/* Decrease Quantity                                                          */
/* -------------------------------------------------------------------------- */

export function decreaseQuantity(
  cart = [],
  productId
) {
  return cart
    .map((item) => {
      if (
        String(item.id) !==
        String(productId)
      ) {
        return item;
      }

      return {
        ...item,

        quantity:
          item.quantity - 1,
      };
    })
    .filter(
      (item) =>
        item.quantity > 0
    );
}

/* -------------------------------------------------------------------------- */
/* Clear Cart                                                                 */
/* -------------------------------------------------------------------------- */

export function clearCart() {
  return [];
}

/* -------------------------------------------------------------------------- */
/* Toggle Item                                                                */
/* -------------------------------------------------------------------------- */

export function toggleCartItem(
  cart = [],
  product
) {
  if (
    isInCart(
      cart,
      product.id
    )
  ) {
    return removeFromCart(
      cart,
      product.id
    );
  }

  return addToCart(
    cart,
    product
  );
}

/* -------------------------------------------------------------------------- */
/* Cart Totals                                                                */
/* -------------------------------------------------------------------------- */

export function getCartTotals(
  cart = [],
  options = {}
) {
  return calculateCartSummary(
    cart,
    options
  );
}

/* -------------------------------------------------------------------------- */
/* Cart Item Total                                                            */
/* -------------------------------------------------------------------------- */

export function getItemTotal(
  item
) {
  return calculateItemTotal(
    item
  );
}

/* -------------------------------------------------------------------------- */
/* Cart Subtotal                                                              */
/* -------------------------------------------------------------------------- */

export function getSubtotal(
  cart = []
) {
  return calculateSubtotal(
    cart
  );
}

/* -------------------------------------------------------------------------- */
/* Cart Count                                                                 */
/* -------------------------------------------------------------------------- */

export function getItemCount(
  cart = []
) {
  return calculateItemCount(
    cart
  );
}

/* -------------------------------------------------------------------------- */
/* Cart Quantity                                                              */
/* -------------------------------------------------------------------------- */

export function getTotalQuantity(
  cart = []
) {
  return cart.reduce(
    (total, item) =>
      total +
      toNumber(
        item.quantity
      ),
    0
  );
}

/* -------------------------------------------------------------------------- */
/* Validation                                                                 */
/* -------------------------------------------------------------------------- */

export function validateCart(
  cart = []
) {
  const errors = [];

  cart.forEach((item) => {
    if (
      item.quantity <= 0
    ) {
      errors.push({
        productId:
          item.id,

        message:
          "Quantity must be greater than zero.",
      });
    }

    if (
      item.stock !==
        undefined &&
      item.quantity >
        item.stock
    ) {
      errors.push({
        productId:
          item.id,

        message:
          "Quantity exceeds available stock.",
      });
    }
  });

  return {
    valid:
      errors.length === 0,

    errors,
  };
}

/* -------------------------------------------------------------------------- */
/* Serialization                                                              */
/* -------------------------------------------------------------------------- */

export function serializeCart(
  cart = []
) {
  return cart.map(
    (item) => ({
      productId:
        item.id,

      quantity:
        item.quantity,

      price:
        item.price_per_unit,
    })
  );
}

/* -------------------------------------------------------------------------- */
/* Default Export                                                             */
/* -------------------------------------------------------------------------- */

export default {
  addToCart,

  removeFromCart,

  updateQuantity,

  increaseQuantity,

  decreaseQuantity,

  toggleCartItem,

  clearCart,

  findCartItem,

  isInCart,

  getItemTotal,

  getSubtotal,

  getItemCount,

  getTotalQuantity,

  getCartTotals,

  validateCart,

  serializeCart,
};