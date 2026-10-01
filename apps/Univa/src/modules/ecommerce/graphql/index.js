/* -------------------------------------------------------------------------- */
/* graphql/index.js                                                           */
/* apps/Univa/src/modules/ecommerce/graphql/index.js                          */
/* -------------------------------------------------------------------------- */


/* -------------------------------------------------------------------------- */
/* Product Details                                                            */
/* -------------------------------------------------------------------------- */

export {

  PRODUCT_IMAGE_FRAGMENT,

  PRODUCT_SELLER_FRAGMENT,

  PRODUCT_VARIANT_FRAGMENT,

  PRODUCT_VARIANT_OPTION_FRAGMENT,

  PRODUCT_REVIEW_SUMMARY_FRAGMENT,

  PRODUCT_DETAILS_FRAGMENT,

  PRODUCT_DETAILS_QUERY,

  PRODUCT_FAQS_QUERY,

  RELATED_PRODUCTS_QUERY,

  SIMILAR_PRODUCTS_QUERY,

  RECENTLY_VIEWED_PRODUCTS_QUERY,

  PRODUCT_SEARCH_SUGGESTIONS_QUERY,

} from "./productDetails";



/* -------------------------------------------------------------------------- */
/* Product Cart                                                               */
/* -------------------------------------------------------------------------- */

export {

  CART_PRODUCT_FRAGMENT,

  CART_VARIANT_FRAGMENT,

  CART_ITEM_FRAGMENT,

  CART_FRAGMENT,

  CART_SUMMARY_FRAGMENT,


  ADD_TO_CART_MUTATION,

  UPDATE_CART_ITEM_MUTATION,

  REMOVE_CART_ITEM_MUTATION,

  CLEAR_CART_MUTATION,


  CART_QUERY,

  MINI_CART_QUERY,

  CHECKOUT_CART_QUERY,


  CALCULATE_SHIPPING_QUERY,


  APPLY_COUPON_MUTATION,

  REMOVE_COUPON_MUTATION,

} from "./productCart";



/* -------------------------------------------------------------------------- */
/* Wishlist                                                                   */
/* -------------------------------------------------------------------------- */

export {

  WISHLIST_PRODUCT_FRAGMENT,

  WISHLIST_ITEM_FRAGMENT,

  WISHLIST_FRAGMENT,


  ADD_TO_WISHLIST_MUTATION,

  REMOVE_FROM_WISHLIST_MUTATION,

  CLEAR_WISHLIST_MUTATION,


  WISHLIST_QUERY,

  WISHLIST_COUNT_QUERY,

  PRODUCT_WISHLIST_STATUS_QUERY,

} from "./productWishlist";



/* -------------------------------------------------------------------------- */
/* Product Reviews                                                            */
/* -------------------------------------------------------------------------- */

export {

  REVIEW_USER_FRAGMENT,

  REVIEW_IMAGE_FRAGMENT,

  PRODUCT_REVIEW_FRAGMENT,

  RATING_DISTRIBUTION_FRAGMENT,

  REVIEW_SUMMARY_FRAGMENT,


  PRODUCT_REVIEWS_QUERY,

  PRODUCT_REVIEW_SUMMARY_QUERY,


  CREATE_PRODUCT_REVIEW_MUTATION,

  MARK_REVIEW_HELPFUL_MUTATION,

  DELETE_PRODUCT_REVIEW_MUTATION,

} from "./productReviews";



/* -------------------------------------------------------------------------- */
/* Checkout                                                                    */
/* -------------------------------------------------------------------------- */

export {

  CHECKOUT_ADDRESS_FRAGMENT,

  SHIPPING_METHOD_FRAGMENT,

  PAYMENT_METHOD_FRAGMENT,

  CHECKOUT_ITEM_FRAGMENT,

  CHECKOUT_FRAGMENT,


  CHECKOUT_SUMMARY_QUERY,

  USER_ADDRESSES_QUERY,

  SHIPPING_METHODS_QUERY,

  PAYMENT_METHODS_QUERY,


  CREATE_ORDER_MUTATION,

  INITIALIZE_PAYMENT_MUTATION,

  CONFIRM_PAYMENT_MUTATION,


  ORDER_DETAILS_QUERY,

} from "./productCheckout";