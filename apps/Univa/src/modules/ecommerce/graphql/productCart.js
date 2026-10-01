/* -------------------------------------------------------------------------- */
/* productCart.js                                                             */
/* apps/Univa/src/modules/ecommerce/graphql/productCart.js                    */
/* -------------------------------------------------------------------------- */

import {
  gql,
} from "@apollo/client";


/* -------------------------------------------------------------------------- */
/* Cart Product Fragment                                                      */
/* -------------------------------------------------------------------------- */

export const CART_PRODUCT_FRAGMENT =
  gql`
    fragment CartProductFields on Product {
      id

      name

      slug


      images {
        id

        url

        alt
      }


      brand


      seller {
        id

        name

        verified
      }
    }
  `;


/* -------------------------------------------------------------------------- */
/* Cart Variant Fragment                                                      */
/* -------------------------------------------------------------------------- */

export const CART_VARIANT_FRAGMENT =
  gql`
    fragment CartVariantFields on ProductVariant {
      id

      sku

      name

      price


      options {
        id

        label

        value
      }
    }
  `;


/* -------------------------------------------------------------------------- */
/* Cart Item Fragment                                                         */
/* -------------------------------------------------------------------------- */

export const CART_ITEM_FRAGMENT =
  gql`
    fragment CartItemFields on CartItem {
      id


      quantity


      price


      total


      product {
        ...CartProductFields
      }


      variant {
        ...CartVariantFields
      }


      createdAt

      updatedAt
    }


    ${CART_PRODUCT_FRAGMENT}

    ${CART_VARIANT_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Cart Fragment                                                              */
/* -------------------------------------------------------------------------- */

export const CART_FRAGMENT =
  gql`
    fragment CartFields on Cart {

      id


      items {
        ...CartItemFields
      }


      subtotal


      discount


      shippingFee


      tax


      total


      itemCount


      currency


      updatedAt

    }


    ${CART_ITEM_FRAGMENT}
  `;

  /* -------------------------------------------------------------------------- */
/* Add To Cart Mutation                                                       */
/* -------------------------------------------------------------------------- */

export const ADD_TO_CART_MUTATION =
  gql`
    mutation AddToCart(
      $input: AddToCartInput!
    ) {

      addToCart(
        input: $input
      ) {

        success

        message


        cart {
          ...CartFields
        }

      }

    }


    ${CART_FRAGMENT}
  `;

  /* -------------------------------------------------------------------------- */
/* Update Cart Item Mutation                                                  */
/* -------------------------------------------------------------------------- */

export const UPDATE_CART_ITEM_MUTATION =
  gql`
    mutation UpdateCartItem(
      $input: UpdateCartItemInput!
    ) {

      updateCartItem(
        input: $input
      ) {

        success

        message


        cart {
          ...CartFields
        }

      }

    }


    ${CART_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Remove Cart Item Mutation                                                  */
/* -------------------------------------------------------------------------- */

export const REMOVE_CART_ITEM_MUTATION =
  gql`
    mutation RemoveCartItem(
      $input: RemoveCartItemInput!
    ) {

      removeCartItem(
        input: $input
      ) {

        success

        message


        cart {
          ...CartFields
        }

      }

    }


    ${CART_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Clear Cart Mutation                                                        */
/* -------------------------------------------------------------------------- */

export const CLEAR_CART_MUTATION =
  gql`
    mutation ClearCart {

      clearCart {

        success

        message


        cart {
          ...CartFields
        }

      }

    }


    ${CART_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Current Cart Query                                                         */
/* -------------------------------------------------------------------------- */

export const CART_QUERY =
  gql`
    query Cart {

      cart {

        ...CartFields

      }

    }


    ${CART_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Mini Cart Query                                                            */
/* -------------------------------------------------------------------------- */

export const MINI_CART_QUERY =
  gql`
    query MiniCart {

      cart {

        id


        itemCount


        items {

          id

          quantity


          product {

            id

            name


            images {

              url

            }

          }

        }


        total

        currency

      }

    }
  `;

  /* -------------------------------------------------------------------------- */
/* Cart Summary Fragment                                                      */
/* -------------------------------------------------------------------------- */

export const CART_SUMMARY_FRAGMENT =
  gql`
    fragment CartSummaryFields on Cart {

      id


      itemCount


      subtotal


      discount


      shippingFee


      tax


      total


      currency


      coupon {

        code

        discountAmount

      }

    }
  `;


/* -------------------------------------------------------------------------- */
/* Checkout Cart Query                                                        */
/* -------------------------------------------------------------------------- */

export const CHECKOUT_CART_QUERY =
  gql`
    query CheckoutCart {

      cart {

        ...CartFields


        shippingAddress {

          id

          firstName

          lastName

          phone

          addressLine1

          city

          state

          country

        }


        paymentMethods {

          id

          type

          provider

        }

      }

    }


    ${CART_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Shipping Calculation Query                                                 */
/* -------------------------------------------------------------------------- */

export const CALCULATE_SHIPPING_QUERY =
  gql`
    query CalculateShipping(
      $addressId: ID!
    ) {

      calculateShipping(
        addressId: $addressId
      ) {

        available

        fee

        estimatedDays


        methods {

          id

          name

          price

          deliveryTime

        }

      }

    }
  `;


/* -------------------------------------------------------------------------- */
/* Apply Coupon Mutation                                                      */
/* -------------------------------------------------------------------------- */

export const APPLY_COUPON_MUTATION =
  gql`
    mutation ApplyCoupon(
      $code: String!
    ) {

      applyCoupon(
        code: $code
      ) {

        success

        message


        cart {

          ...CartFields

        }

      }

    }


    ${CART_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Remove Coupon Mutation                                                     */
/* -------------------------------------------------------------------------- */

export const REMOVE_COUPON_MUTATION =
  gql`
    mutation RemoveCoupon {

      removeCoupon {

        success

        message


        cart {

          ...CartFields

        }

      }

    }


    ${CART_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Product Cart Exports                                                       */
/* -------------------------------------------------------------------------- */

export default {

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

};