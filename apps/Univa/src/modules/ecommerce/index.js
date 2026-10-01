/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/index.js                                  */
/* -------------------------------------------------------------------------- */

import * as api from "./api";
import * as hooks from "./hooks";
import { CHECKOUT_STEPS } from "./hooks/useCheckout";

// ============================================================================
// API
// ============================================================================

export * from "./api";

// ============================================================================
// Hooks
// ============================================================================

export * from "./hooks";

// ============================================================================
// Components - Re-export commonly used components
// ============================================================================

// Common
export { default as Button } from "./components/common/Button";
export { default as Price } from "./components/common/Price";
export { default as Rating } from "./components/common/Rating";
export { default as Badge } from "./components/common/Badge";
export { default as QuantitySelector } from "./components/common/QuantitySelector";
export { default as ProductImage } from "./components/common/ProductImage";

// Products
export { default as ProductCard } from "./components/products/ProductCard";
export { default as ProductGrid } from "./components/products/ProductGrid";
export { default as ProductCarousel } from "./components/products/ProductCarousel";

// Cart
export { default as CartItem } from "./components/cart/CartItem";
export { default as CartSummary } from "./components/cart/CartSummary";
export { default as MiniCart } from "./components/cart/MiniCart";
export { default as EmptyCart } from "./components/cart/EmptyCart";

// Checkout
export { default as CheckoutProgress } from "./components/checkout/CheckoutProgress";
export { default as CheckoutStepper } from "./components/checkout/CheckoutStepper";
export { default as CheckoutSuccess } from "./components/checkout/CheckoutSuccess";
export { default as PaymentMethodList } from "./components/checkout/PaymentMethodList";
export { default as ShippingMethodList } from "./components/checkout/ShippingMethodList";

// Wishlist
export { default as WishlistGrid } from "./components/wishlist/WishlistGrid";
export { default as WishlistCard } from "./components/wishlist/WishlistCard";

// Sellers
export { default as SellerCard } from "./components/sellers/SellerCard";
export { default as SellerProfile } from "./components/sellers/SellerProfile";

// ============================================================================
// Screens
// ============================================================================

export { default as CartScreen } from "./screens/Cart";
export { default as CheckoutScreen } from "./screens/CheckoutScreen";
export { default as EcommerceDashboard } from "./screens/EcommerceDashboard";
export { default as OrdersScreen } from "./screens/Orders";
export { default as ProductDetailsScreen } from "./screens/ProductDetailsScreen";
export { default as ProductSearchScreen } from "./screens/ProductSearch";
export { default as WishlistScreen } from "./screens/Wishlist";

// ============================================================================
// Utils
// ============================================================================

export * from "./utils/cart";
export * from "./utils/currency";
export * from "./utils/filters";
export * from "./utils/formatters";
export * from "./utils/pricing";
export * from "./utils/validators";

// ============================================================================
// Constants
// ============================================================================

export { CHECKOUT_STEPS };

// ============================================================================
// Default Export
// ============================================================================

export default {
  api,
  hooks,
  CHECKOUT_STEPS,
};