import { gql } from "@apollo/client";

export const GET_ATM_CARDS = gql`
  query GetATMCards($first: Int, $after: String) {
    atmCards(first: $first, after: $after) {
      edges {
        node {
          id
          cardNumber
          cardType
          expiryDate
          status
          dailyWithdrawalLimit
          dailyPosLimit
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_BALANCE = gql`
  query GetBalance {
    balance {
      id
      amountUsd
      availableBalance
      lockedAmount
      lastUpdated
    }
  }
`;

export const GET_NOTIFICATIONS = gql`
  query GetNotifications($first: Int, $after: String) {
    notifications(first: $first, after: $after) {
      edges {
        node {
          id
          title
          message
          isRead
          notificationType
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_TRANSACTIONS = gql`
  query GetTransactions($first: Int, $after: String) {
    transactions(first: $first, after: $after) {
      edges {
        node {
          id
          transactionType
          amount
          reference
          status
          description
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_AIRTIME_PURCHASES = gql`
  query GetAirtimePurchases($first: Int, $after: String) {
    airtimePurchases(first: $first, after: $after) {
      edges {
        node {
          id
          network
          amount
          reference
          status
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_BILL_PAYMENTS = gql`
  query GetBillPayments($first: Int, $after: String) {
    billPayments(first: $first, after: $after) {
      edges {
        node {
          id
          billType
          amount
          reference
          provider
          status
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_CONTACTS = gql`
  query GetContacts($first: Int, $after: String) {
    contacts(first: $first, after: $after) {
      edges {
        node {
          id
          accountNumber
          bankName
          isBeneficiary
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_BANK = gql`
  query GetBank($code: String!) {
    bank(code: $code) {
      id
      name
      code
      logo
      isActive
    }
  }
`;

export const GET_BANKS = gql`
  query GetBanks($first: Int, $after: String, $activeOnly: Boolean = true) {
    banks(first: $first, after: $after, activeOnly: $activeOnly) {
      edges {
        node {
          id
          name
          code
          isActive
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_CONTACT = gql`
  query GetContact($id: ID!) {
    contact(id: $id) {
      id
      accountNumber
      bankName
      profileImage
      isBeneficiary
      createdAt
    }
  }
`;

export const GET_ATM_TRANSACTION = gql`
  query GetATMTransaction($reference: String!) {
    atmTransaction(reference: $reference) {
      id
      transactionType
      amount
      reference
      status
      terminalId
      location
      createdAt
    }
  }
`;

export const GET_MONEY_TRANSFER = gql`
  query GetMoneyTransfer($reference: String!) {
    moneyTransfer(reference: $reference) {
      id
      amount
      fee
      reference
      status
      narration
      createdAt
      sender {
        id
        firstName
        lastName
      }
      receiver {
        id
        firstName
        lastName
      }
    }
  }
`;

export const GET_ACCOUNT = gql`
  query GetAccount($phoneNumber: String!, $bankCode: String) {
    account(phoneNumber: $phoneNumber, bankCode: $bankCode) {
      id
      accountNumber
      accountType
      isActive
      bank {
        id
        name
        code
      }
    }
  }
`;

export const GET_ALL_ACCOUNTS = gql`
  query GetAllAccounts($first: Int, $after: String) {
    allAccounts(first: $first, after: $after) {
      edges {
        node {
          id
          accountNumber
          accountType
          isActive
          bank {
            id
            name
          }
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_ALL_TRANSACTIONS = gql`
  query GetAllTransactions($first: Int, $after: String) {
    allTransactions(first: $first, after: $after) {
      edges {
        node {
          id
          transactionType
          amount
          reference
          status
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_SUPPORTED_BANKS = gql`
  query GetSupportedBanks($activeOnly: Boolean = true) {
    getSupportedBanks(activeOnly: $activeOnly) {
      id
      name
      code
      isActive
    }
  }
`;

export const LOOKUP_ACCOUNT = gql`
  query LookupAccount($phoneNumber: String!, $bankCode: String) {
    lookupAccount(phoneNumber: $phoneNumber, bankCode: $bankCode) {
      id
      accountNumber
      accountType
      isActive
      bank {
        id
        name
        code
      }
    }
  }
`;

export const GET_MY_CONTACTS = gql`
  query GetMyContacts($first: Int, $after: String) {
    myContacts(first: $first, after: $after) {
      edges {
        node {
          id
          accountNumber
          bankName
          isBeneficiary
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_MY_TRANSFERS = gql`
  query GetMyTransfers($startDate: String, $endDate: String) {
    myTransfers(startDate: $startDate, endDate: $endDate) {
      edges {
        node {
          id
          amount
          reference
          status
          createdAt
          receiver {
            id
            firstName
            lastName
          }
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_TRANSFER = gql`
  query GetTransfer($reference: String!) {
    transfer(reference: $reference) {
      id
      amount
      fee
      reference
      status
      narration
      createdAt
      sender {
        id
        firstName
        lastName
      }
      receiver {
        id
        firstName
        lastName
      }
    }
  }
`;

export const GET_MY_ACCOUNTS = gql`
  query GetMyAccounts {
    myAccounts {
      edges {
        node {
          id
          accountNumber
          accountType
          isActive
          bank {
            id
            name
          }
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_MY_BALANCE = gql`
  query GetMyBalance {
    myBalance {
      id
      amountUsd
      availableBalance
      lockedAmount
      lastUpdated
    }
  }
`;

export const GET_MY_TRANSACTIONS = gql`
  query GetMyTransactions($first: Int, $after: String) {
    myTransactions(first: $first, after: $after) {
      edges {
        node {
          id
          transactionType
          amount
          reference
          status
          description
          createdAt
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;