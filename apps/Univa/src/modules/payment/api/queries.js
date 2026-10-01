// app/api/graphql/queries.js

import { gql } from "@apollo/client";

export const GET_UNIVA_BENEFITS = gql`
  query GetUnivaBenefits($userId: ID) {
    univaBenefits(userId: $userId) {
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
  }
`;

export const GET_UNIVA_USER = gql`
  query GetUnivaUser($userId: ID) {
    univaUser(userId: $userId) {
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
  }
`;

export const GET_UNIVA_TRANSACTIONS = gql`
  query GetUnivaTransactions($limit: Int = 10) {
    univaTransactions(limit: $limit) {
      id
      transactionId
      amount
      originalAmount
      discountApplied
      cashbackEarned
      status
      paymentMethod
      createdAt
      formattedAmount
      formattedDiscount
      formattedOriginal
      finalAmount
    }
  }
`;

export const GET_UNIVA_TRANSACTION = gql`
  query GetUnivaTransaction($id: ID!) {
    univaTransaction(id: $id) {
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
  }
`;

export const GET_UNIVA_DISCOUNT = gql`
  query GetUnivaDiscount {
    univaDiscount {
      id
      discountPercentage
      minTransactionAmount
      maxDiscountAmount
      isActive
      validFrom
      validTo
    }
  }
`;

export const CHECK_UNIVA_ELIGIBILITY = gql`
  query CheckUnivaEligibility($amount: Decimal!) {
    univaCheckEligibility(amount: $amount) {
      id
      discountPercentage
      minTransactionAmount
      maxDiscountAmount
      isActive
      validFrom
      validTo
      discountAmount(amount: $amount)
      finalAmount(amount: $amount)
    }
  }
`;

export const GET_ACTIVE_PROMOTIONS = gql`
  query GetActivePromotions {
    univaActivePromotions {
      id
      name
      description
      discountPercentage
      cashbackPercentage
      startDate
      endDate
      isActive
      minTransactionAmount
      maxTransactionAmount
      isEligible
    }
  }
`;