/* -------------------------------------------------------------------------- */
/* productCheckout.js                                                         */
/* apps/Univa/src/modules/ecommerce/graphql/productCheckout.js                */
/* -------------------------------------------------------------------------- */

import {
  gql,
} from "@apollo/client";



/* -------------------------------------------------------------------------- */
/* Checkout Address Fragment                                                  */
/* -------------------------------------------------------------------------- */

export const CHECKOUT_ADDRESS_FRAGMENT =
  gql`
    fragment CheckoutAddressFields on Address {

      id

      firstName

      lastName

      phone


      addressLine1

      addressLine2


      city

      state

      country


      postalCode


      isDefault

    }
  `;



/* -------------------------------------------------------------------------- */
/* Shipping Method Fragment                                                   */
/* -------------------------------------------------------------------------- */

export const SHIPPING_METHOD_FRAGMENT =
  gql`
    fragment ShippingMethodFields on ShippingMethod {

      id

      name

      description


      price


      currency


      estimatedDays


      provider

    }
  `;



/* -------------------------------------------------------------------------- */
/* Payment Method Fragment                                                    */
/* -------------------------------------------------------------------------- */

export const PAYMENT_METHOD_FRAGMENT =
  gql`
    fragment PaymentMethodFields on PaymentMethod {

      id

      name

      type


      provider


      enabled

    }
  `;



/* -------------------------------------------------------------------------- */
/* Checkout Item Fragment                                                     */
/* -------------------------------------------------------------------------- */

export const CHECKOUT_ITEM_FRAGMENT =
  gql`
    fragment CheckoutItemFields on CartItem {

      id

      quantity


      price

      total


      product {

        id

        name


        images {

          id

          url

        }

      }


      variant {

        id

        name

      }

    }
  `;



/* -------------------------------------------------------------------------- */
/* Checkout Fragment                                                          */
/* -------------------------------------------------------------------------- */

export const CHECKOUT_FRAGMENT =
  gql`
    fragment CheckoutFields on Checkout {

      id


      items {

        ...CheckoutItemFields

      }


      subtotal


      discount


      shippingFee


      tax


      total


      currency


      address {

        ...CheckoutAddressFields

      }


      shippingMethod {

        ...ShippingMethodFields

      }


      paymentMethod {

        ...PaymentMethodFields

      }


      status


      createdAt

    }


    ${CHECKOUT_ITEM_FRAGMENT}

    ${CHECKOUT_ADDRESS_FRAGMENT}

    ${SHIPPING_METHOD_FRAGMENT}

    ${PAYMENT_METHOD_FRAGMENT}
  `;



/* -------------------------------------------------------------------------- */
/* Checkout Summary Query                                                     */
/* -------------------------------------------------------------------------- */

export const CHECKOUT_SUMMARY_QUERY =
  gql`
    query CheckoutSummary {

      checkoutSummary {

        ...CheckoutFields

      }

    }


    ${CHECKOUT_FRAGMENT}
  `;



/* -------------------------------------------------------------------------- */
/* User Addresses Query                                                       */
/* -------------------------------------------------------------------------- */

export const USER_ADDRESSES_QUERY =
  gql`
    query UserAddresses {

      userAddresses {

        ...CheckoutAddressFields

      }

    }


    ${CHECKOUT_ADDRESS_FRAGMENT}
  `;



/* -------------------------------------------------------------------------- */
/* Shipping Methods Query                                                     */
/* -------------------------------------------------------------------------- */

export const SHIPPING_METHODS_QUERY =
  gql`
    query ShippingMethods(
      $addressId: ID!
    ) {

      shippingMethods(
        addressId: $addressId
      ) {

        ...ShippingMethodFields

      }

    }


    ${SHIPPING_METHOD_FRAGMENT}
  `;



/* -------------------------------------------------------------------------- */
/* Payment Methods Query                                                      */
/* -------------------------------------------------------------------------- */

export const PAYMENT_METHODS_QUERY =
  gql`
    query PaymentMethods {

      paymentMethods {

        ...PaymentMethodFields

      }

    }


    ${PAYMENT_METHOD_FRAGMENT}
  `;



/* -------------------------------------------------------------------------- */
/* Create Order Mutation                                                      */
/* -------------------------------------------------------------------------- */

export const CREATE_ORDER_MUTATION =
  gql`
    mutation CreateOrder(
      $input: CreateOrderInput!
    ) {

      createOrder(
        input: $input
      ) {

        success

        message


        order {

          id

          orderNumber

          status

          total

          createdAt

        }

      }

    }
  `;



/* -------------------------------------------------------------------------- */
/* Initialize Payment Mutation                                                */
/* -------------------------------------------------------------------------- */

export const INITIALIZE_PAYMENT_MUTATION =
  gql`
    mutation InitializePayment(
      $input: InitializePaymentInput!
    ) {

      initializePayment(
        input: $input
      ) {

        success

        message


        payment {

          id

          reference

          amount

          currency


          authorizationUrl

        }

      }

    }
  `;



/* -------------------------------------------------------------------------- */
/* Confirm Payment Mutation                                                   */
/* -------------------------------------------------------------------------- */

export const CONFIRM_PAYMENT_MUTATION =
  gql`
    mutation ConfirmPayment(
      $reference: String!
    ) {

      confirmPayment(
        reference: $reference
      ) {

        success

        message


        order {

          id

          status

          orderNumber

        }

      }

    }
  `;



/* -------------------------------------------------------------------------- */
/* Order Details Query                                                        */
/* -------------------------------------------------------------------------- */

export const ORDER_DETAILS_QUERY =
  gql`
    query OrderDetails(
      $id: ID!
    ) {

      order(
        id: $id
      ) {

        id

        orderNumber


        status


        items {

          id

          quantity

          price


          product {

            id

            name

          }

        }


        total


        createdAt

      }

    }
  `;



/* -------------------------------------------------------------------------- */
/* Product Checkout GraphQL Exports                                           */
/* -------------------------------------------------------------------------- */

export default {

  CHECKOUT_SUMMARY_QUERY,

  USER_ADDRESSES_QUERY,

  SHIPPING_METHODS_QUERY,

  PAYMENT_METHODS_QUERY,


  CREATE_ORDER_MUTATION,

  INITIALIZE_PAYMENT_MUTATION,

  CONFIRM_PAYMENT_MUTATION,


  ORDER_DETAILS_QUERY,

};