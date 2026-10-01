/* -------------------------------------------------------------------------- */
/* productDetails.js                                                          */
/* apps/Univa/src/modules/ecommerce/graphql/productDetails.js                 */
/* -------------------------------------------------------------------------- */

import {
  gql,
} from "@apollo/client";


/* -------------------------------------------------------------------------- */
/* Image Fragment                                                             */
/* -------------------------------------------------------------------------- */

export const PRODUCT_IMAGE_FRAGMENT =
  gql`
    fragment ProductImageFields on ProductImage {
      id

      url

      alt

      width

      height
    }
  `;


/* -------------------------------------------------------------------------- */
/* Seller Fragment                                                            */
/* -------------------------------------------------------------------------- */

export const PRODUCT_SELLER_FRAGMENT =
  gql`
    fragment ProductSellerFields on Seller {
      id

      name

      avatar

      rating

      reviewsCount

      verified

      joinedAt
    }
  `;


/* -------------------------------------------------------------------------- */
/* Variant Option Fragment                                                    */
/* -------------------------------------------------------------------------- */

export const PRODUCT_VARIANT_OPTION_FRAGMENT =
  gql`
    fragment ProductVariantOptionFields on VariantOption {
      id

      label

      value

      color

      available
    }
  `;


/* -------------------------------------------------------------------------- */
/* Variant Fragment                                                           */
/* -------------------------------------------------------------------------- */

export const PRODUCT_VARIANT_FRAGMENT =
  gql`
    fragment ProductVariantFields on ProductVariant {
      id

      sku

      name

      price

      stockQuantity

      options {
        ...ProductVariantOptionFields
      }
    }

    ${PRODUCT_VARIANT_OPTION_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Review Summary Fragment                                                    */
/* -------------------------------------------------------------------------- */

export const PRODUCT_REVIEW_SUMMARY_FRAGMENT =
  gql`
    fragment ProductReviewSummaryFields on ProductReviewSummary {
      averageRating

      totalReviews

      ratingDistribution {
        rating

        count
      }
    }
  `;

  /* -------------------------------------------------------------------------- */
/* Pricing Fragment                                                           */
/* -------------------------------------------------------------------------- */

export const PRODUCT_PRICE_FRAGMENT =
  gql`
    fragment ProductPriceFields on ProductPrice {
      amount

      currency

      formatted
    }
  `;


/* -------------------------------------------------------------------------- */
/* Delivery Fragment                                                          */
/* -------------------------------------------------------------------------- */

export const PRODUCT_DELIVERY_FRAGMENT =
  gql`
    fragment ProductDeliveryFields on ProductDelivery {
      id

      estimatedDays

      shippingFee

      freeShipping

      availableLocations

      expressAvailable
    }
  `;


/* -------------------------------------------------------------------------- */
/* Warranty Fragment                                                          */
/* -------------------------------------------------------------------------- */

export const PRODUCT_WARRANTY_FRAGMENT =
  gql`
    fragment ProductWarrantyFields on ProductWarranty {
      id

      title

      duration

      description

      provider
    }
  `;


/* -------------------------------------------------------------------------- */
/* Return Policy Fragment                                                     */
/* -------------------------------------------------------------------------- */

export const PRODUCT_RETURN_POLICY_FRAGMENT =
  gql`
    fragment ProductReturnPolicyFields on ProductReturnPolicy {
      id

      allowed

      returnDays

      conditions

      description
    }
  `;


/* -------------------------------------------------------------------------- */
/* Main Product Fragment                                                      */
/* -------------------------------------------------------------------------- */

export const PRODUCT_DETAILS_FRAGMENT =
  gql`
    fragment ProductDetailsFields on Product {
      id

      name

      slug

      description

      shortDescription


      /* -------------------------------------------------------------- */
      /* Images                                                        */
      /* -------------------------------------------------------------- */

      images {
        ...ProductImageFields
      }


      /* -------------------------------------------------------------- */
      /* Pricing                                                       */
      /* -------------------------------------------------------------- */

      price {
        ...ProductPriceFields
      }


      compareAtPrice {
        ...ProductPriceFields
      }


      discountPercentage


      /* -------------------------------------------------------------- */
      /* Inventory                                                     */
      /* -------------------------------------------------------------- */

      sku

      stockQuantity

      inStock


      /* -------------------------------------------------------------- */
      /* Category                                                      */
      /* -------------------------------------------------------------- */

      category {
        id

        name

        slug
      }


      /* -------------------------------------------------------------- */
      /* Seller                                                        */
      /* -------------------------------------------------------------- */

      seller {
        ...ProductSellerFields
      }


      /* -------------------------------------------------------------- */
      /* Variants                                                      */
      /* -------------------------------------------------------------- */

      variants {
        ...ProductVariantFields
      }


      /* -------------------------------------------------------------- */
      /* Product Information                                           */
      /* -------------------------------------------------------------- */

      brand

      model

      tags


      highlights

      features


      specifications


      /* -------------------------------------------------------------- */
      /* Delivery                                                       */
      /* -------------------------------------------------------------- */

      delivery {
        ...ProductDeliveryFields
      }


      /* -------------------------------------------------------------- */
      /* Warranty                                                       */
      /* -------------------------------------------------------------- */

      warranty {
        ...ProductWarrantyFields
      }


      /* -------------------------------------------------------------- */
      /* Returns                                                        */
      /* -------------------------------------------------------------- */

      returnPolicy {
        ...ProductReturnPolicyFields
      }


      /* -------------------------------------------------------------- */
      /* Reviews                                                        */
      /* -------------------------------------------------------------- */

      reviewSummary {
        ...ProductReviewSummaryFields
      }


      createdAt

      updatedAt
    }


    ${PRODUCT_IMAGE_FRAGMENT}

    ${PRODUCT_PRICE_FRAGMENT}

    ${PRODUCT_SELLER_FRAGMENT}

    ${PRODUCT_VARIANT_FRAGMENT}

    ${PRODUCT_DELIVERY_FRAGMENT}

    ${PRODUCT_WARRANTY_FRAGMENT}

    ${PRODUCT_RETURN_POLICY_FRAGMENT}

    ${PRODUCT_REVIEW_SUMMARY_FRAGMENT}
  `;
  /* -------------------------------------------------------------------------- */
/* Product Details Query                                                      */
/* -------------------------------------------------------------------------- */

export const PRODUCT_DETAILS_QUERY =
  gql`
    query ProductDetails(
      $id: ID!
    ) {

      product(
        id: $id
      ) {

        ...ProductDetailsFields

      }
    }


    ${PRODUCT_DETAILS_FRAGMENT}
  `;

  /* -------------------------------------------------------------------------- */
/* Related Products Query                                                     */
/* -------------------------------------------------------------------------- */

export const RELATED_PRODUCTS_QUERY =
  gql`
    query RelatedProducts(
      $productId: ID!

      $categoryId: ID

      $first: Int

      $after: String

      $type: RecommendationType
    ) {

      relatedProducts(
        productId: $productId

        categoryId: $categoryId

        first: $first

        after: $after

        type: $type
      ) {

        edges {

          node {

            ...ProductDetailsFields

          }

        }


        pageInfo {

          hasNextPage

          endCursor

        }

      }

    }


    ${PRODUCT_DETAILS_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Product FAQs Query                                                         */
/* -------------------------------------------------------------------------- */

export const PRODUCT_FAQS_QUERY =
  gql`
    query ProductFAQs(
      $productId: ID!
    ) {

      productFAQs(
        productId: $productId
      ) {

        id

        question

        answer

        createdAt

      }

    }
  `;


/* -------------------------------------------------------------------------- */
/* Recently Viewed Products Query                                             */
/* -------------------------------------------------------------------------- */

export const RECENTLY_VIEWED_PRODUCTS_QUERY =
  gql`
    query RecentlyViewedProducts(
      $first: Int

      $after: String
    ) {

      recentlyViewedProducts(
        first: $first

        after: $after
      ) {

        edges {

          node {

            ...ProductDetailsFields

          }

        }


        pageInfo {

          hasNextPage

          endCursor

        }

      }

    }


    ${PRODUCT_DETAILS_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Similar Products Query                                                     */
/* -------------------------------------------------------------------------- */

export const SIMILAR_PRODUCTS_QUERY =
  gql`
    query SimilarProducts(
      $productId: ID!

      $first: Int
    ) {

      similarProducts(
        productId: $productId

        first: $first
      ) {

        edges {

          node {

            ...ProductDetailsFields

          }

        }

      }

    }


    ${PRODUCT_DETAILS_FRAGMENT}
  `;


/* -------------------------------------------------------------------------- */
/* Product Search Suggestions                                                 */
/* -------------------------------------------------------------------------- */

export const PRODUCT_SEARCH_SUGGESTIONS_QUERY =
  gql`
    query ProductSearchSuggestions(
      $term: String!
    ) {

      productSearchSuggestions(
        term: $term
      ) {

        id

        name

        slug

        image

      }

    }
  `;

  /* -------------------------------------------------------------------------- */
/* Product Details GraphQL Exports                                            */
/* -------------------------------------------------------------------------- */

export default {
  PRODUCT_DETAILS_QUERY,

  RELATED_PRODUCTS_QUERY,

  PRODUCT_FAQS_QUERY,

  RECENTLY_VIEWED_PRODUCTS_QUERY,

  SIMILAR_PRODUCTS_QUERY,

  PRODUCT_SEARCH_SUGGESTIONS_QUERY,
};