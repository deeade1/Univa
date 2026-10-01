// app/api/graphql/mutations.js

import { gql } from "@apollo/client";

// Fragment for transaction details
export const TRANSACTION_FRAGMENT = gql`
  fragment TransactionFields on UnivaTransactionType {
    id
    transactionId
    amount
    originalAmount
    discountApplied
    cashbackEarned
    status
    paymentMethod
    createdAt
    completedAt
    formattedAmount
    formattedDiscount
    formattedOriginal
    finalAmount
  }
`;

// Fragment for user details
export const UNIVA_USER_FRAGMENT = gql`
  fragment UnivaUserFields on UnivaUserType {
    id
    userId
    email
    phone
    totalSavings
    totalCashback
    loyaltyPoints
    isActive
    hasUnivaCard
    enableNotifications
    autoApplyDiscount
  }
`;

// Fragment for discount details
export const DISCOUNT_FRAGMENT = gql`
  fragment DiscountFields on UnivaDiscountType {
    id
    discountPercentage
    minTransactionAmount
    maxDiscountAmount
    isActive
    validFrom
    validTo
  }
`;

// Fragment for benefits
export const BENEFITS_FRAGMENT = gql`
  fragment BenefitsFields on UnivaUserBenefits {
    cashbackRate
    discountRate
    minTransaction
    maxDiscount
    loyaltyPoints
    totalSavings
    totalTransactions
    nextTierPoints
    hasActivePromotion
    formattedSavings
  }
`;

// Initiate Payment Mutation
export const INITIATE_UNIVA_PAYMENT = gql`
  mutation InitiateUnivaPayment($input: InitiateUnivaPaymentInput!) {
    initiateUnivaPayment(input: $input) {
      status
      transaction {
        ...TransactionFields
      }
      originalAmount
      discount
      finalAmount
      cashback
      formattedDiscount
      formattedFinal
      paymentIntent
      requiresAction
      actionData
      errors
      clientMutationId
    }
  }
  ${TRANSACTION_FRAGMENT}
`;

// Confirm Payment Mutation
export const CONFIRM_UNIVA_PAYMENT = gql`
  mutation ConfirmUnivaPayment($input: ConfirmUnivaPaymentInput!) {
    confirmUnivaPayment(input: $input) {
      status
      transaction {
        ...TransactionFields
      }
      originalAmount
      discount
      finalAmount
      cashback
      formattedDiscount
      formattedFinal
      errors
      clientMutationId
    }
  }
  ${TRANSACTION_FRAGMENT}
`;

// Apply Discount Mutation
export const APPLY_UNIVA_DISCOUNT = gql`
  mutation ApplyUnivaDiscount($input: ApplyUnivaDiscountInput!) {
    applyUnivaDiscount(input: $input) {
      discount {
        ...DiscountFields
      }
      discountAmount
      finalAmount
      formattedDiscount
      formattedFinal
      isEligible
      errors
      clientMutationId
    }
  }
  ${DISCOUNT_FRAGMENT}
`;

// Get User Benefits Mutation
export const GET_USER_BENEFITS = gql`
  mutation GetUserBenefits($input: GetUserBenefitsInput!) {
    getUserBenefits(input: $input) {
      benefits {
        ...BenefitsFields
      }
      errors
      clientMutationId
    }
  }
  ${BENEFITS_FRAGMENT}
`;

// Update User Preferences Mutation
export const UPDATE_UNIVA_PREFERENCES = gql`
  mutation UpdateUnivaPreferences($input: UpdateUnivaPreferencesInput!) {
    updateUnivaPreferences(input: $input) {
      user {
        ...UnivaUserFields
      }
      errors
      clientMutationId
    }
  }
  ${UNIVA_USER_FRAGMENT}
`;