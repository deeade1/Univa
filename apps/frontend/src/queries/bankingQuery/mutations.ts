// GraphQL mutations
import { gql } from '@apollo/client';

// Create Bank Mutation
export const CREATE_BANK_MUTATION = gql`
  mutation CreateBank($input: CreateBankMutationInput!) {
    createBank(input: $input) {
      bank {
        id
        name
        code
        logo
        isActive
      }
    }
  }
`;

// Create Account Mutation
export const CREATE_ACCOUNT_MUTATION = gql`
  mutation CreateAccount($input: CreateAccountMutationInput!) {
    createAccount(input: $input) {
      account {
        id
        accountType
        bvn
        isActive
        user {
          id
          firstName
          lastName
        }
        bank {
          id
          name
        }
      }
    }
  }
`;

// Transfer Money Mutation
export const TRANSFER_MONEY_MUTATION = gql`
  mutation TransferMoney($input: TransferMoneyMutationInput!) {
    transferMoney(input: $input) {
      transaction {
        id
        amount
        status
        reference
        createdAt
      }
      transfer {
        id
        amount
        status
        reference
        createdAt
      }
    }
  }
`;

// Pay Bill Mutation
export const PAY_BILL_MUTATION = gql`
  mutation PayBill($input: PayBillMutationInput!) {
    payBill(input: $input) {
      billPayment {
        id
        amount
        status
        reference
        billType
        provider
      }
    }
  }
`;

// Purchase Airtime Mutation
export const PURCHASE_AIRTIME_MUTATION = gql`
  mutation PurchaseAirtime($input: PurchaseAirtimeMutationInput!) {
    purchaseAirtime(input: $input) {
      airtimePurchase {
        id
        amount
        network
        status
        reference
      }
    }
  }
`;

// Create Contact Mutation
export const CREATE_CONTACT_MUTATION = gql`
  mutation CreateContact($input: CreateContactMutationInput!) {
    createContact(input: $input) {
      contact {
        id
        accountNumber
        bankName
        isBeneficiary
        user {
          id
          firstName
        }
      }
    }
  }
`;

// Create ATM Card Mutation
export const CREATE_ATM_CARD_MUTATION = gql`
  mutation CreateATMCard($input: CreateATMCardMutationInput!) {
    createATMCard(input: $input) {
      card {
        id
        cardNumber
        cardType
        expiryDate
        status
      }
    }
  }
`;

// Create ATM Transaction Mutation
export const CREATE_ATM_TRANSACTION_MUTATION = gql`
  mutation CreateATMTransaction($input: CreateATMTransactionMutationInput!) {
    createATMTransaction(input: $input) {
      atmTransaction {
        id
        transactionType
        amount
        status
        reference
      }
    }
  }
`;

// Create Fraud Detection Rule Mutation
export const CREATE_FRAUD_DETECTION_RULE_MUTATION = gql`
  mutation CreateFraudDetectionRule($input: CreateFraudDetectionRuleMutationInput!) {
    createFraudDetectionRule(input: $input) {
      rule {
        id
        name
        ruleType
        isActive
        threshold
      }
    }
  }
`;

// Create Fraud Alert Mutation
export const CREATE_FRAUD_ALERT_MUTATION = gql`
  mutation CreateFraudAlert($input: CreateFraudAlertMutationInput!) {
    createFraudAlert(input: $input) {
      alert {
        id
        detectedValue
        status
        createdAt
      }
    }
  }
`;

// Create Currency Exchange Rate Mutation
export const CREATE_CURRENCY_EXCHANGE_RATE_MUTATION = gql`
  mutation CreateCurrencyExchangeRate($input: CreateCurrencyExchangeRateMutationInput!) {
    createCurrencyExchangeRate(input: $input) {
      rateObj {
        id
        baseCurrency
        targetCurrency
        rate
      }
    }
  }
`;

// Create Notification Mutation
export const CREATE_NOTIFICATION_MUTATION = gql`
  mutation CreateNotification($input: CreateBankingNotificationInput!) {
    createBankingNotification(input: $input) {
      notification {
        id
        title
        message
        notificationType
        isRead
      }
    }
  }
`;

// Input types
export const CREATE_BANK_INPUT = gql`
  input CreateBankMutationInput {
    name: String!
    code: String!
    logo: String!
    isActive: Boolean
  }
`;

export const CREATE_ACCOUNT_INPUT = gql`
  input CreateAccountMutationInput {
    userId: ID!
    accountType: String!
    bvn: String
    pin: String
    bankId: ID
  }
`;

export const TRANSFER_MONEY_INPUT = gql`
  input TransferMoneyMutationInput {
    senderId: ID!
    receiverId: ID!
    senderAccountId: ID!
    receiverAccountId: ID!
    amount: Float!
    narration: String
  }
`;

export const PAY_BILL_INPUT = gql`
  input PayBillMutationInput {
    userId: ID!
    accountId: ID!
    billType: String!
    amount: Float!
    provider: String!
    customerReference: String!
  }
`;

export const PURCHASE_AIRTIME_INPUT = gql`
  input PurchaseAirtimeMutationInput {
    userId: ID!
    accountId: ID!
    network: String!
    amount: Float!
  }
`;

export const CREATE_CONTACT_INPUT = gql`
  input CreateContactMutationInput {
    userId: ID!
    accountNumber: String!
    bankName: String!
    isBeneficiary: Boolean
  }
`;

export const CREATE_ATM_CARD_INPUT = gql`
  input CreateATMCardMutationInput {
    userId: ID!
    accountId: ID!
    cardNumber: String!
    cardType: String!
    cvv: String!
    expiryDate: Date!
    pin: String!
  }
`;

export const CREATE_ATM_TRANSACTION_INPUT = gql`
  input CreateATMTransactionMutationInput {
    cardId: ID!
    accountId: ID!
    transactionType: String!
    amount: Float
    terminalId: String
    location: String
  }
`;

export const CREATE_FRAUD_DETECTION_RULE_INPUT = gql`
  input CreateFraudDetectionRuleMutationInput {
    name: String!
    description: String
    ruleType: String!
    isActive: Boolean!
    threshold: Float!
    conditions: JSONString!
    action: String!
    createdById: ID
  }
`;

export const CREATE_FRAUD_ALERT_INPUT = gql`
  input CreateFraudAlertMutationInput {
    ruleId: ID!
    userId: ID
    transactionReference: String
    detectedValue: Float!
    status: String
    evidenceData: JSONString
    notes: String
    resolvedById: ID
  }
`;

export const CREATE_CURRENCY_EXCHANGE_RATE_INPUT = gql`
  input CreateCurrencyExchangeRateMutationInput {
    baseCurrency: String!
    targetCurrency: String!
    rate: Float!
  }
`;

export const CREATE_NOTIFICATION_INPUT = gql`
  input CreateBankingNotificationInput {
    title: String!
    message: String!
    notificationType: String!
    relatedTransactionId: ID
    userId: ID!
  }
`;