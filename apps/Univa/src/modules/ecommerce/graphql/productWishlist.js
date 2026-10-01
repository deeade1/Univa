/* -------------------------------------------------------------------------- */
/* productWishlist.js                                                         */
/* apps/Univa/src/modules/ecommerce/graphql/productWishlist.js                */
/* -------------------------------------------------------------------------- */

import {
  gql,
} from "@apollo/client";


/* -------------------------------------------------------------------------- */
/* Wishlist Product Fragment                                                  */
/* -------------------------------------------------------------------------- */

export const WISHLIST_PRODUCT_FRAGMENT =
  gql`
    fragment WishlistProductFields on Product {

      id

      name

      slug


      shortDescription


      images {

        id

        url

        alt

      }


      price {

        amount

        currency

        formatted

      }


      compareAtPrice {

        amount

        currency

        formatted

      }


      discountPercentage


      inStock


      rating

      reviewCount


      brand


      seller {

        id

        name

        verified

      }

    }
  `;


/* -------------------------------------------------------------------------- */
/* Wishlist Item Fragment                                                     */
/* -------------------------------------------------------------------------- */

export const WISHLIST_ITEM_FRAGMENT =
  gql`
    fragment WishlistItemFields on WishlistItem {

      id


      createdAt


      product {

        ...WishlistProductFields

      }

    }


    ${WISHLIST_PRODUCT_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Wishlist Fragment                                                          */
/* -------------------------------------------------------------------------- */

export const WISHLIST_FRAGMENT =
  gql`
    fragment WishlistFields on Wishlist {

      id


      items {

        ...WishlistItemFields

      }


      itemCount


      updatedAt

    }


    ${WISHLIST_ITEM_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Add Product To Wishlist                                                    */
/* -------------------------------------------------------------------------- */

export const ADD_TO_WISHLIST_MUTATION =
  gql`
    mutation AddToWishlist(
      $input: AddToWishlistInput!
    ) {

      addToWishlist(
        input: $input
      ) {

        success

        message


        wishlist {

          ...WishlistFields

        }

      }

    }


    ${WISHLIST_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Remove Product From Wishlist                                               */
/* -------------------------------------------------------------------------- */

export const REMOVE_FROM_WISHLIST_MUTATION =
  gql`
    mutation RemoveFromWishlist(
      $input: RemoveFromWishlistInput!
    ) {

      removeFromWishlist(
        input: $input
      ) {

        success

        message


        wishlist {

          ...WishlistFields

        }

      }

    }


    ${WISHLIST_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Wishlist Query                                                             */
/* -------------------------------------------------------------------------- */

export const WISHLIST_QUERY =
  gql`
    query Wishlist {

      wishlist {

        ...WishlistFields

      }

    }


    ${WISHLIST_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Wishlist Count Query                                                       */
/* -------------------------------------------------------------------------- */

export const WISHLIST_COUNT_QUERY =
  gql`
    query WishlistCount {

      wishlist {

        itemCount

      }

    }
  `;


/* -------------------------------------------------------------------------- */
/* Check Product Wishlist Status                                              */
/* -------------------------------------------------------------------------- */

export const PRODUCT_WISHLIST_STATUS_QUERY =
  gql`
    query ProductWishlistStatus(
      $productId: ID!
    ) {

      productWishlistStatus(
        productId: $productId
      ) {

        productId

        isWishlisted

      }

    }
  `;


/* -------------------------------------------------------------------------- */
/* Clear Wishlist Mutation                                                    */
/* -------------------------------------------------------------------------- */

export const CLEAR_WISHLIST_MUTATION =
  gql`
    mutation ClearWishlist {

      clearWishlist {

        success

        message


        wishlist {

          ...WishlistFields

        }

      }

    }


    ${WISHLIST_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Wishlist GraphQL Exports                                                   */
/* -------------------------------------------------------------------------- */

export default {

  ADD_TO_WISHLIST_MUTATION,

  REMOVE_FROM_WISHLIST_MUTATION,

  CLEAR_WISHLIST_MUTATION,


  WISHLIST_QUERY,

  WISHLIST_COUNT_QUERY,

  PRODUCT_WISHLIST_STATUS_QUERY,

};