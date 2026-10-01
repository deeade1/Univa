/* -------------------------------------------------------------------------- */
/* productReviews.js                                                          */
/* apps/Univa/src/modules/ecommerce/graphql/productReviews.js                 */
/* -------------------------------------------------------------------------- */

import {
  gql,
} from "@apollo/client";



/* -------------------------------------------------------------------------- */
/* Review User Fragment                                                       */
/* -------------------------------------------------------------------------- */

export const REVIEW_USER_FRAGMENT =
  gql`
    fragment ReviewUserFields on User {

      id

      firstName

      lastName

      username

      avatar

    }
  `;



/* -------------------------------------------------------------------------- */
/* Review Image Fragment                                                      */
/* -------------------------------------------------------------------------- */

export const REVIEW_IMAGE_FRAGMENT =
  gql`
    fragment ReviewImageFields on ReviewImage {

      id

      url

      alt

    }
  `;



/* -------------------------------------------------------------------------- */
/* Product Review Fragment                                                    */
/* -------------------------------------------------------------------------- */

export const PRODUCT_REVIEW_FRAGMENT =
  gql`
    fragment ProductReviewFields on ProductReview {

      id


      rating


      title


      comment


      verifiedPurchase


      helpfulCount


      user {

        ...ReviewUserFields

      }


      images {

        ...ReviewImageFields

      }


      createdAt


      updatedAt

    }


    ${REVIEW_USER_FRAGMENT}

    ${REVIEW_IMAGE_FRAGMENT}
  `;



/* -------------------------------------------------------------------------- */
/* Rating Distribution Fragment                                               */
/* -------------------------------------------------------------------------- */

export const RATING_DISTRIBUTION_FRAGMENT =
  gql`
    fragment RatingDistributionFields on RatingDistribution {

      rating

      count

      percentage

    }
  `;



/* -------------------------------------------------------------------------- */
/* Review Summary Fragment                                                    */
/* -------------------------------------------------------------------------- */

export const REVIEW_SUMMARY_FRAGMENT =
  gql`
    fragment ReviewSummaryFields on ReviewSummary {

      averageRating


      totalReviews


      distribution {

        ...RatingDistributionFields

      }

    }


    ${RATING_DISTRIBUTION_FRAGMENT}
  `;



/* -------------------------------------------------------------------------- */
/* Product Reviews Query                                                      */
/* -------------------------------------------------------------------------- */

export const PRODUCT_REVIEWS_QUERY =
  gql`
    query ProductReviews(
      $productId: ID!

      $first: Int

      $after: String

      $sort: ReviewSort
    ) {

      productReviews(
        productId: $productId

        first: $first

        after: $after

        sort: $sort
      ) {

        edges {

          node {

            ...ProductReviewFields

          }

        }


        pageInfo {

          hasNextPage

          endCursor

        }


        totalCount

      }

    }


    ${PRODUCT_REVIEW_FRAGMENT}
  `;



/* -------------------------------------------------------------------------- */
/* Review Summary Query                                                       */
/* -------------------------------------------------------------------------- */

export const PRODUCT_REVIEW_SUMMARY_QUERY =
  gql`
    query ProductReviewSummary(
      $productId: ID!
    ) {

      productReviewSummary(
        productId: $productId
      ) {

        ...ReviewSummaryFields

      }

    }


    ${REVIEW_SUMMARY_FRAGMENT}
  `;



/* -------------------------------------------------------------------------- */
/* Create Product Review Mutation                                             */
/* -------------------------------------------------------------------------- */

export const CREATE_PRODUCT_REVIEW_MUTATION =
  gql`
    mutation CreateProductReview(
      $input: CreateProductReviewInput!
    ) {

      createProductReview(
        input: $input
      ) {

        success

        message


        review {

          ...ProductReviewFields

        }


        summary {

          ...ReviewSummaryFields

        }

      }

    }


    ${PRODUCT_REVIEW_FRAGMENT}

    ${REVIEW_SUMMARY_FRAGMENT}
  `;



/* -------------------------------------------------------------------------- */
/* Mark Review Helpful Mutation                                               */
/* -------------------------------------------------------------------------- */

export const MARK_REVIEW_HELPFUL_MUTATION =
  gql`
    mutation MarkReviewHelpful(
      $reviewId: ID!
    ) {

      markReviewHelpful(
        reviewId: $reviewId
      ) {

        success

        message


        review {

          id

          helpfulCount

        }

      }

    }
  `;



/* -------------------------------------------------------------------------- */
/* Delete Review Mutation                                                     */
/* -------------------------------------------------------------------------- */

export const DELETE_PRODUCT_REVIEW_MUTATION =
  gql`
    mutation DeleteProductReview(
      $reviewId: ID!
    ) {

      deleteProductReview(
        reviewId: $reviewId
      ) {

        success

        message

      }

    }
  `;



/* -------------------------------------------------------------------------- */
/* Product Review GraphQL Exports                                             */
/* -------------------------------------------------------------------------- */

export default {

  PRODUCT_REVIEWS_QUERY,

  PRODUCT_REVIEW_SUMMARY_QUERY,


  CREATE_PRODUCT_REVIEW_MUTATION,

  MARK_REVIEW_HELPFUL_MUTATION,

  DELETE_PRODUCT_REVIEW_MUTATION,

};