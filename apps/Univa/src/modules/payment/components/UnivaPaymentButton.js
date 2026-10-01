// app/components/UnivaPaymentButton.js

import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { useUnivaPayment } from '../hooks/useUnivaPayment';

export const UnivaPaymentButton = ({ amount, onSuccess, onError }) => {
  const [loading, setLoading] = useState(false);
  const [discountInfo, setDiscountInfo] = useState(null);
  const {
    initiatePayment,
    checkDiscount,
    benefits,
    refetchBenefits,
  } = useUnivaPayment();
  
  // Check discount eligibility
  const checkDiscountEligibility = async () => {
    try {
      const result = await checkDiscount(amount);
      if (result?.isEligible) {
        setDiscountInfo({
          discount: result.discountAmount,
          finalAmount: result.finalAmount,
          formattedDiscount: result.formattedDiscount,
          formattedFinal: result.formattedFinal,
        });
      }
    } catch (error) {
      console.error('Discount check error:', error);
    }
  };
  
  useEffect(() => {
    if (amount > 0) {
      checkDiscountEligibility();
      refetchBenefits();
    }
  }, [amount]);
  
  // Handle payment
  const handlePayment = async () => {
    setLoading(true);
    
    try {
      const result = await initiatePayment(amount, {
        description: 'Purchase via Univa',
      });
      
      if (result?.status === 'error') {
        const errorMessage = Object.values(result.errors || {}).join('\n');
        Alert.alert('Error', errorMessage);
        onError?.(new Error(errorMessage));
        setLoading(false);
        return;
      }
      
      setLoading(false);
      
      if (result?.requiresAction) {
        // Handle 3DS authentication
        handleAction(result.actionData, result);
      } else {
        Alert.alert(
          'Success',
          `Payment initiated!\nDiscount: ${result.formattedDiscount}\nFinal: ${result.formattedFinal}`,
          [
            {
              text: 'OK',
              onPress: () => {
                onSuccess?.(result);
              },
            },
          ]
        );
      }
    } catch (error) {
      setLoading(false);
      Alert.alert('Error', error.message);
      onError?.(error);
    }
  };
  
  // Handle 3DS authentication
  const handleAction = (actionData, paymentResult) => {
    Alert.alert(
      'Authentication Required',
      'Please complete the authentication process',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Continue',
          onPress: () => completeAction(actionData, paymentResult),
        },
      ]
    );
  };
  
  const completeAction = async (actionData, paymentResult) => {
    // Navigate to authentication screen
    Alert.alert('Info', 'Redirecting to authentication...');
  };
  
  return (
    <View style={styles.container}>
      {discountInfo && (
        <View style={styles.discountBanner}>
          <Text style={styles.discountText}>
            🎉 Save {discountInfo.formattedDiscount} with Univa!
          </Text>
          <Text style={styles.savingsText}>
            Final: {discountInfo.formattedFinal}
          </Text>
        </View>
      )}
      
      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handlePayment}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <>
            <Text style={styles.buttonText}>Pay with Univa</Text>
            <Text style={styles.benefitText}>
              {benefits?.cashbackRate ? `Earn ${benefits.cashbackRate} cashback` : 'Earn cashback'}
            </Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 10,
  },
  discountBanner: {
    backgroundColor: '#4CAF50',
    padding: 12,
    borderRadius: 8,
    marginBottom: 10,
  },
  discountText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  savingsText: {
    color: '#fff',
    fontSize: 14,
    marginTop: 4,
  },
  button: {
    backgroundColor: '#FF6B35',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  benefitText: {
    color: '#fff',
    fontSize: 12,
    marginTop: 4,
  },
});