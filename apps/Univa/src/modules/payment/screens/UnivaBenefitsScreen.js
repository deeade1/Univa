// app/screens/UnivaBenefitsScreen.js

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { useUnivaPayment } from '../hooks/useUnivaPayment';
import { useFocusEffect } from '@react-navigation/native';

export const UnivaBenefitsScreen = ({ userId }) => {
  const [refreshing, setRefreshing] = useState(false);
  const {
    benefits,
    transactions,
    getBenefits,
    refetchBenefits,
    refetchTransactions,
    benefitsLoading,
    transactionsLoading,
  } = useUnivaPayment();
  
  // Load benefits on focus
  useFocusEffect(
    useCallback(() => {
      if (userId) {
        getBenefits(userId);
      }
    }, [userId])
  );
  
  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await Promise.all([
        refetchBenefits(),
        refetchTransactions(),
      ]);
    } catch (error) {
      Alert.alert('Error', 'Failed to refresh data');
    } finally {
      setRefreshing(false);
    }
  }, [refetchBenefits, refetchTransactions]);
  
  if (benefitsLoading && !benefits) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#FF6B35" />
      </View>
    );
  }
  
  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.title}>Univa Benefits</Text>
        <Text style={styles.subtitle}>Save more with every purchase</Text>
      </View>
      
      <View style={styles.benefitsCard}>
        <View style={styles.benefitItem}>
          <Text style={styles.benefitLabel}>Cashback Rate</Text>
          <Text style={styles.benefitValue}>{benefits?.cashbackRate || '0%'}</Text>
        </View>
        <View style={styles.benefitItem}>
          <Text style={styles.benefitLabel}>Discount Rate</Text>
          <Text style={styles.benefitValue}>{benefits?.discountRate || '0%'}</Text>
        </View>
        <View style={styles.benefitItem}>
          <Text style={styles.benefitLabel}>Loyalty Points</Text>
          <Text style={styles.benefitValue}>{benefits?.loyaltyPoints || 0}</Text>
        </View>
        <View style={[styles.benefitItem, styles.lastBenefitItem]}>
          <Text style={styles.benefitLabel}>Total Savings</Text>
          <Text style={styles.benefitValue}>{benefits?.formattedSavings || '$0.00'}</Text>
        </View>
      </View>
      
      <View style={styles.progressSection}>
        <Text style={styles.sectionTitle}>Next Tier</Text>
        <View style={styles.progressBar}>
          <View
            style={[
              styles.progressFill,
              {
                width: benefits?.loyaltyPoints
                  ? `${(benefits.loyaltyPoints / 1000) * 100}%`
                  : '0%',
              },
            ]}
          />
        </View>
        <Text style={styles.progressText}>
          {benefits?.nextTierPoints || 1000} points to next tier
        </Text>
      </View>
      
      <View style={styles.detailsSection}>
        <Text style={styles.sectionTitle}>Transaction Details</Text>
        <View style={styles.detailItem}>
          <Text style={styles.detailLabel}>Minimum Transaction</Text>
          <Text style={styles.detailValue}>
            ${benefits?.minTransaction || '0.00'}
          </Text>
        </View>
        <View style={styles.detailItem}>
          <Text style={styles.detailLabel}>Maximum Discount</Text>
          <Text style={styles.detailValue}>
            ${benefits?.maxDiscount || '0.00'}
          </Text>
        </View>
        <View style={styles.detailItem}>
          <Text style={styles.detailLabel}>Total Transactions</Text>
          <Text style={styles.detailValue}>
            {benefits?.totalTransactions || 0}
          </Text>
        </View>
      </View>
      
      {benefits?.hasActivePromotion && (
        <View style={styles.promotionSection}>
          <Text style={styles.promotionTitle}>🎉 Active Promotion</Text>
          <Text style={styles.promotionText}>
            Special offers available! Check the promotions tab for details.
          </Text>
        </View>
      )}
      
      {/* Recent Transactions */}
      {transactions && transactions.length > 0 && (
        <View style={styles.transactionsSection}>
          <Text style={styles.sectionTitle}>Recent Transactions</Text>
          {transactions.slice(0, 3).map((transaction) => (
            <View key={transaction.id} style={styles.transactionItem}>
              <View>
                <Text style={styles.transactionAmount}>
                  ${transaction.originalAmount.toFixed(2)}
                </Text>
                <Text
                  style={[
                    styles.transactionStatus,
                    { color: transaction.status === 'completed' ? '#4CAF50' : '#FF9800' },
                  ]}
                >
                  {transaction.status}
                </Text>
              </View>
              <View style={styles.transactionRight}>
                <Text style={styles.transactionDiscount}>
                  Saved: {transaction.formattedDiscount}
                </Text>
                <Text style={styles.transactionDate}>
                  {new Date(transaction.createdAt).toLocaleDateString()}
                </Text>
              </View>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  benefitsCard: {
    margin: 16,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  benefitItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  lastBenefitItem: {
    borderBottomWidth: 0,
  },
  benefitLabel: {
    fontSize: 14,
    color: '#666',
  },
  benefitValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  progressSection: {
    margin: 16,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  progressBar: {
    height: 8,
    backgroundColor: '#e0e0e0',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#FF6B35',
  },
  progressText: {
    marginTop: 8,
    fontSize: 12,
    color: '#666',
  },
  detailsSection: {
    margin: 16,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  detailItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  detailLabel: {
    fontSize: 14,
    color: '#666',
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  promotionSection: {
    margin: 16,
    padding: 16,
    backgroundColor: '#FFF3E0',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#FFE0B2',
  },
  promotionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FF6B35',
    marginBottom: 4,
  },
  promotionText: {
    fontSize: 14,
    color: '#666',
  },
  transactionsSection: {
    margin: 16,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  transactionItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  transactionAmount: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  transactionStatus: {
    fontSize: 12,
    textTransform: 'capitalize',
    marginTop: 2,
  },
  transactionRight: {
    alignItems: 'flex-end',
  },
  transactionDiscount: {
    fontSize: 12,
    color: '#4CAF50',
  },
  transactionDate: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
});