// app/hooks/useUnivaPayment.js

import { useMutation, useQuery, useLazyQuery } from '@apollo/client';
import {
  INITIATE_UNIVA_PAYMENT,
  CONFIRM_UNIVA_PAYMENT,
  APPLY_UNIVA_DISCOUNT,
  GET_USER_BENEFITS,
  UPDATE_UNIVA_PREFERENCES,
  GET_UNIVA_BENEFITS,
  GET_UNIVA_TRANSACTIONS,
  CHECK_UNIVA_ELIGIBILITY,
} from '../api/graphql/mutations';
import { GET_UNIVA_BENEFITS, CHECK_UNIVA_ELIGIBILITY } from '../api/graphql/queries';

export const useUnivaPayment = () => {
  // Mutations
  const [initiatePaymentMutation, { loading: initiating }] = useMutation(
    INITIATE_UNIVA_PAYMENT
  );
  
  const [confirmPaymentMutation, { loading: confirming }] = useMutation(
    CONFIRM_UNIVA_PAYMENT
  );
  
  const [applyDiscountMutation, { loading: discountLoading }] = useMutation(
    APPLY_UNIVA_DISCOUNT
  );
  
  const [getUserBenefitsMutation, { loading: benefitsLoading }] = useMutation(
    GET_USER_BENEFITS
  );
  
  const [updatePreferencesMutation, { loading: updating }] = useMutation(
    UPDATE_UNIVA_PREFERENCES
  );
  
  // Queries
  const { data: benefitsData, loading: benefitsQueryLoading, refetch: refetchBenefits } =
    useQuery(GET_UNIVA_BENEFITS);
  
  const { data: transactionsData, loading: transactionsLoading, refetch: refetchTransactions } =
    useQuery(GET_UNIVA_TRANSACTIONS, {
      variables: { limit: 10 },
    });
  
  const [checkEligibility, { data: eligibilityData, loading: eligibilityLoading }] =
    useLazyQuery(CHECK_UNIVA_ELIGIBILITY);
  
  // Helper functions
  const initiatePayment = async (amount, options = {}) => {
    try {
      const { data } = await initiatePaymentMutation({
        variables: {
          input: {
            amount: amount.toString(),
            currency: options.currency || 'USD',
            description: options.description || 'Univa Payment',
            source: options.source,
            clientMutationId: `payment_${Date.now()}`,
          },
        },
      });
      
      return data?.initiateUnivaPayment;
    } catch (error) {
      console.error('Initiate payment error:', error);
      throw error;
    }
  };
  
  const confirmPayment = async (transactionId, confirmationData = {}) => {
    try {
      const { data } = await confirmPaymentMutation({
        variables: {
          input: {
            transactionId,
            confirmationData,
            clientMutationId: `confirm_${Date.now()}`,
          },
        },
      });
      
      return data?.confirmUnivaPayment;
    } catch (error) {
      console.error('Confirm payment error:', error);
      throw error;
    }
  };
  
  const checkDiscount = async (amount) => {
    try {
      const { data } = await applyDiscountMutation({
        variables: {
          input: {
            amount: amount.toString(),
            clientMutationId: `discount_${Date.now()}`,
          },
        },
        update: (cache, { data }) => {
          // Update cache with discount information
          const discountResult = data?.applyUnivaDiscount;
          if (discountResult?.isEligible) {
            cache.modify({
              fields: {
                univaDiscount: () => discountResult.discount,
              },
            });
          }
        },
      });
      
      return data?.applyUnivaDiscount;
    } catch (error) {
      console.error('Check discount error:', error);
      throw error;
    }
  };
  
  const getBenefits = async (userId) => {
    try {
      const { data } = await getUserBenefitsMutation({
        variables: {
          input: {
            userId,
            clientMutationId: `benefits_${Date.now()}`,
          },
        },
      });
      
      return data?.getUserBenefits;
    } catch (error) {
      console.error('Get benefits error:', error);
      throw error;
    }
  };
  
  const updatePreferences = async (preferences) => {
    try {
      const { data } = await updatePreferencesMutation({
        variables: {
          input: {
            enableNotifications: preferences.enableNotifications,
            autoApplyDiscount: preferences.autoApplyDiscount,
            clientMutationId: `prefs_${Date.now()}`,
          },
        },
        update: (cache, { data }) => {
          // Update cache with new preferences
          const updatedUser = data?.updateUnivaPreferences?.user;
          if (updatedUser) {
            cache.modify({
              fields: {
                univaUser: () => updatedUser,
              },
            });
          }
        },
      });
      
      return data?.updateUnivaPreferences;
    } catch (error) {
      console.error('Update preferences error:', error);
      throw error;
    }
  };
  
  return {
    // Mutations
    initiatePayment,
    confirmPayment,
    checkDiscount,
    getBenefits,
    updatePreferences,
    
    // Queries
    benefits: benefitsData?.univaBenefits,
    transactions: transactionsData?.univaTransactions,
    eligibility: eligibilityData?.univaCheckEligibility,
    
    // Loading states
    initiating,
    confirming,
    discountLoading,
    benefitsLoading,
    transactionsLoading,
    eligibilityLoading,
    updating,
    
    // Refetch functions
    refetchBenefits,
    refetchTransactions,
    checkEligibility,
  };
};