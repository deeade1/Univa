import { gql } from "@apollo/client";

export const GET_ATTRIBUTE = gql`
  query GetAttribute($id: ID!) {
    attribute(id: $id) {
      id
      slug
      name
      type
      inputType
      entityType
      unit
      valueRequired
      isVariantOnly
      visibleInStorefront
      filterableInStorefront
      filterableInDashboard
      storefrontSearchPosition
      availableInGrid
      values {
        edges {
          node {
            id
            name
            slug
            value
          }
        }
      }
    }
  }
`;

export const GET_ALL_ATTRIBUTES = gql`
  query GetAllAttributes(
    $first: Int
    $after: String
    $filter: AttributeFilterInput
  ) {
    allAttributes(first: $first, after: $after, filters: $filter) {
      edges {
        node {
          id
          slug
          name
          type
          inputType
          visibleInStorefront
          values {
            edges {
              node {
                id
                name
              }
            }
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

export const GET_ATTRIBUTE_VALUE = gql`
  query GetAttributeValue($id: ID!) {
    attributeValue(id: $id) {
      id
      name
      value
      slug
      fileUrl
      contentType
      attribute {
        id
        name
      }
      richText
      plainText
      boolean
      dateTime
      referenceProduct {
        id
        name
      }
      referenceVariant {
        id
        name
      }
    }
  }
`;

export const GET_ALL_ATTRIBUTE_VALUES = gql`
  query GetAllAttributeValues(
    $first: Int
    $after: String
    $filter: AttributeValueFilterInput
  ) {
    allAttributeValues(first: $first, after: $after, filters: $filter) {
      edges {
        node {
          id
          name
          slug
          value
          attribute {
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

export const GET_ASSIGNED_PRODUCT_ATTRIBUTE_VALUES = gql`
  query GetAssignedProductAttributeValues(
    $first: Int
    $after: String
    $filter: AssignedProductAttributeValueFilterInput
  ) {
    assignedProductAttributeValues: allAssignedProductAttributeValues(
      first: $first
      after: $after
      filters: $filter
    ) {
      edges {
        node {
          id
          value {
            id
            name
          }
          product {
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

export const GET_ATTRIBUTE_PRODUCTS = gql`
  query GetAttributeProducts(
    $first: Int
    $after: String
    $filter: AttributeProductFilterInput
  ) {
    attributeProducts: allAttributeProducts(
      first: $first
      after: $after
      filters: $filter
    ) {
      edges {
        node {
          id
          attribute {
            id
            name
          }
          productType {
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

export const GET_ASSIGNED_VARIANT_ATTRIBUTE_VALUES = gql`
  query GetAssignedVariantAttributeValues(
    $first: Int
    $after: String
    $filter: AssignedVariantAttributeValueFilterInput
  ) {
    assignedVariantAttributeValues: allAssignedVariantAttributeValues(
      first: $first
      after: $after
      filters: $filter
    ) {
      edges {
        node {
          id
          value {
            id
            name
          }
          assignment {
            id
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

export const GET_ATTRIBUTE_VARIANTS = gql`
  query GetAttributeVariants(
    $first: Int
    $after: String
    $filter: AttributeVariantFilterInput
  ) {
    attributeVariants: allAttributeVariants(
      first: $first
      after: $after
      filters: $filter
    ) {
      edges {
        node {
          id
          attribute {
            id
            name
          }
          productType {
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

export const GET_ASSIGNED_VARIANT_ATTRIBUTES = gql`
  query GetAssignedVariantAttributes(
    $first: Int
    $after: String
    $filter: AssignedVariantAttributeFilterInput
  ) {
    assignedVariantAttributes: allAssignedVariantAttributes(
      first: $first
      after: $after
      filters: $filter
    ) {
      edges {
        node {
          id
          variant {
            id
            name
          }
          assignment {
            id
          }
          values {
            edges {
              node {
                id
                name
              }
            }
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





export const GET_CHANNEL = gql`
  query GetChannel($id: ID, $slug: String) {
    channel(id: $id, slug: $slug) {
      id
      name
      isActive
      slug
      currencyCode
      defaultCountry
      allocationStrategy
      orderMarkAsPaidStrategy
      defaultTransactionFlowStrategy
      automaticallyConfirmAllNewOrders
      allowUnpaidOrders
      automaticallyFulfillNonShippableGiftCard
      expireOrdersAfter
      deleteExpiredOrdersAfter
      includeDraftOrderInVoucherUsage
      useLegacyErrorFlowForCheckout
    }
  }
`;

export const GET_ALL_CHANNELS = gql`
  query GetAllChannels($first: Int, $after: String) {
    allChannels(first: $first, after: $after) {
      edges {
        node {
          id
          name
          isActive
          slug
          currencyCode
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

export const GET_CHANNEL_BY_SLUG = gql`
  query GetChannelBySlug($slug: String!) {
    channelBySlug(slug: $slug) {
      id
      name
      isActive
      slug
      currencyCode
      defaultCountry
      allocationStrategy
      orderMarkAsPaidStrategy
      defaultTransactionFlowStrategy
      automaticallyConfirmAllNewOrders
      allowUnpaidOrders
      automaticallyFulfillNonShippableGiftCard
      expireOrdersAfter
      deleteExpiredOrdersAfter
      includeDraftOrderInVoucherUsage
      useLegacyErrorFlowForCheckout
    }
  }
`;

export const GET_STOCK_SETTINGS = gql`
  query GetStockSettings {
    stockSettings {
      allocationStrategy
    }
  }
`;

export const GET_ORDER_SETTINGS = gql`
  query GetOrderSettings {
    orderSettings {
      markAsPaidStrategy
      automaticallyConfirmAllNewOrders
      allowUnpaidOrders
      expireOrdersAfter
      deleteExpiredOrdersAfter
    }
  }
`;

export const GET_CHANNEL_WITH_SETTINGS = gql`
  query GetChannelWithSettings($slug: String!) {
    channelBySlug(slug: $slug) {
      id
      name
      isActive
      slug
      currencyCode
      defaultCountry
      allocationStrategy
      orderMarkAsPaidStrategy
      defaultTransactionFlowStrategy
      automaticallyConfirmAllNewOrders
      allowUnpaidOrders
      automaticallyFulfillNonShippableGiftCard
      expireOrdersAfter
      deleteExpiredOrdersAfter
      includeDraftOrderInVoucherUsage
      useLegacyErrorFlowForCheckout
    }
    stockSettings {
      allocationStrategy
    }
    orderSettings {
      markAsPaidStrategy
      automaticallyConfirmAllNewOrders
      allowUnpaidOrders
      expireOrdersAfter
      deleteExpiredOrdersAfter
    }
  }
`;

//CheckoutQueries


export const GET_CHECKOUT = gql`
  query GetCheckout($id: ID!) {
    checkout(id: $id) {
      id
      createdAt
      lastChange
      email
      token
      note
      currency
      country
      total {
        net {
          amount
        }
        gross {
          amount
        }
      }
      subtotal {
        net {
          amount
        }
        gross {
          amount
        }
      }
      shippingPrice {
        net {
          amount
        }
        gross {
          amount
        }
      }
      shippingTaxRate
      authorizeStatus
      chargeStatus
      discount {
        amount
      }
      discountName
      voucherCode
      redirectUrl
      trackingCode
      languageCode
      taxExemption
      user {
        id
        email
      }
      channel {
        id
        name
      }
      billingAddress {
        id
        firstName
        lastName
        streetAddress1
        city
        postalCode
        country {
          code
        }
      }
      shippingAddress {
        id
        firstName
        lastName
        streetAddress1
        city
        postalCode
        country {
          code
        }
      }
      shippingMethod {
        id
        name
        price {
          amount
        }
      }
      collectionPoint {
        id
        name
      }
      lines {
        edges {
          node {
            id
            quantity
            variant {
              id
              name
              sku
              product {
                id
                name
                thumbnail {
                  url
                }
              }
            }
            totalPrice {
              gross {
                amount
              }
            }
          }
        }
      }
      giftCards {
        edges {
          node {
            id
            displayCode
            currentBalance {
              amount
            }
          }
        }
      }
    }
  }
`;

export const GET_ALL_CHECKOUTS = gql`
  query GetAllCheckouts($first: Int, $after: String) {
    allCheckouts(first: $first, after: $after) {
      edges {
        node {
          id
          createdAt
          lastChange
          email
          total {
            gross {
              amount
            }
          }
          user {
            id
            email
          }
          lines {
            edges {
              node {
                id
                quantity
                variant {
                  id
                  name
                }
              }
            }
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

export const GET_CHECKOUT_LINE = gql`
  query GetCheckoutLine($id: ID!) {
    checkoutLine(id: $id) {
      id
      quantity
      isGift
      priceOverride {
        amount
      }
      totalPrice {
        net {
          amount
        }
        gross {
          amount
        }
      }
      taxRate
      variant {
        id
        name
        sku
        product {
          id
          name
        }
      }
      checkout {
        id
        token
      }
    }
  }
`;

export const GET_ALL_CHECKOUT_LINES = gql`
  query GetAllCheckoutLines($first: Int, $after: String) {
    allCheckoutLines(first: $first, after: $after) {
      edges {
        node {
          id
          quantity
          totalPrice {
            gross {
              amount
            }
          }
          variant {
            id
            name
          }
          checkout {
            id
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

export const GET_CHECKOUT_METADATA = gql`
  query GetCheckoutMetadata($id: ID!) {
    checkoutMetadata(id: $id) {
      id
      checkout {
        id
        token
      }
      metadata {
        key
        value
      }
    }
  }
`;

export const GET_ALL_CHECKOUT_METADATA = gql`
  query GetAllCheckoutMetadata($first: Int, $after: String) {
    allCheckoutMetadata(first: $first, after: $after) {
      edges {
        node {
          id
          checkout {
            id
          }
          metadata {
            key
            value
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

export const GET_CHECKOUT_WITH_DETAILS = gql`
  query GetCheckoutWithDetails($id: ID!) {
    checkout(id: $id) {
      id
      email
      total {
        gross {
          amount
        }
      }
      shippingAddress {
        id
        firstName
        lastName
        streetAddress1
        city
        country {
          code
        }
      }
      billingAddress {
        id
        firstName
        lastName
        streetAddress1
        city
        country {
          code
        }
      }
      shippingMethod {
        id
        name
        price {
          amount
        }
      }
      lines {
        edges {
          node {
            id
            quantity
            variant {
              id
              name
              sku
              product {
                id
                name
                thumbnail {
                  url
                }
              }
            }
            totalPrice {
              gross {
                amount
              }
            }
          }
        }
      }
      metadata {
        edges {
          node {
            key
            value
          }
        }
      }
    }
  }
`;
//DiscountQueries


export const GET_VOUCHER = gql`
  query GetVoucher($id: ID!, $channel: String) {
    voucher(id: $id, channel: $channel) {
      id
      name
      type
      startDate
      endDate
      usageLimit
      discountValueType
      applyOncePerOrder
      applyOncePerCustomer
      onlyForStaff
      countries
      minCheckoutItemsQuantity
      codes {
        edges {
          node {
            id
            code
            used
            isActive
          }
        }
      }
      channelListings {
        edges {
          node {
            id
            discountValue
            minSpentAmount
            currency
            channel {
              id
              name
            }
          }
        }
      }
    }
  }
`;

export const GET_ALL_VOUCHERS = gql`
  query GetAllVouchers($first: Int, $after: String, $channel: String) {
    vouchers(first: $first, after: $after, channel: $channel) {
      edges {
        node {
          id
          name
          type
          startDate
          endDate
          discountValueType
          codes {
            edges {
              node {
                id
                code
              }
            }
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

export const GET_PROMOTION = gql`
  query GetPromotion($id: ID!) {
    promotion(id: $id) {
      id
      name
      type
      description
      startDate
      endDate
      isActive
      rules {
        edges {
          node {
            id
            name
            rewardType
            rewardValue
            rewardValueType
          }
        }
      }
    }
  }
`;

export const GET_ALL_PROMOTIONS = gql`
  query GetAllPromotions($first: Int, $after: String) {
    promotions(first: $first, after: $after) {
      edges {
        node {
          id
          name
          type
          startDate
          endDate
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

export const GET_PROMOTION_RULE = gql`
  query GetPromotionRule($id: ID!) {
    promotionRule(id: $id) {
      id
      name
      description
      rewardType
      rewardValue
      rewardValueType
      promotion {
        id
        name
      }
      channels {
        edges {
          node {
            id
            name
          }
        }
      }
      variants {
        edges {
          node {
            id
            name
            sku
          }
        }
      }
    }
  }
`;

export const GET_ALL_PROMOTION_RULES = gql`
  query GetAllPromotionRules($first: Int, $after: String) {
    promotionRules(first: $first, after: $after) {
      edges {
        node {
          id
          name
          rewardType
          rewardValue
          promotion {
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

export const GET_VOUCHER_CODE = gql`
  query GetVoucherCode($id: ID!, $channelId: ID!) {
    voucherCode(id: $id) {
      id
      code
      used
      isActive
      isValidForStaff
      discountAmount(channelId: $channelId) {
        amount
        currency
      }
      discountPercentage(channelId: $channelId)
      voucher {
        id
        name
      }
    }
  }
`;

export const GET_VOUCHER_CHANNEL_LISTING = gql`
  query GetVoucherChannelListing($id: ID!) {
    voucherChannelListing(id: $id) {
      id
      discountValue
      minSpentAmount
      currency
      voucher {
        id
        name
      }
      channel {
        id
        name
      }
    }
  }
`;

export const GET_ORDER_DISCOUNT = gql`
  query GetOrderDiscount($id: ID!) {
    orderDiscount(id: $id) {
      id
      type
      valueType
      value
      name
      reason
      amount {
        amount
        currency
      }
      promotionRule {
        id
        name
      }
      voucher {
        id
        name
      }
      order {
        id
        number
      }
    }
  }
`;

export const GET_CHECKOUT_DISCOUNT = gql`
  query GetCheckoutDiscount($id: ID!) {
    checkoutDiscount(id: $id) {
      id
      type
      valueType
      value
      name
      amount {
        amount
        currency
      }
      promotionRule {
        id
        name
      }
      voucher {
        id
        name
      }
      checkout {
        id
      }
    }
  }
`;

export const GET_PROMOTION_EVENT = gql`
  query GetPromotionEvent($id: ID!) {
    promotionEvent(id: $id) {
      id
      type
      date
      parameters
      user {
        id
        email
      }
      promotion {
        id
        name
      }
    }
  }
`;

export const GET_VOUCHER_CUSTOMER = gql`
  query GetVoucherCustomer($id: ID!) {
    voucherCustomer(id: $id) {
      id
      voucherCode
      customerEmail
      createdAt
    }
  }
`;

export const GET_PROMOTION_WITH_RULES = gql`
  query GetPromotionWithRules($id: ID!) {
    promotion(id: $id) {
      id
      name
      type
      rules {
        edges {
          node {
            id
            name
            rewardType
            rewardValue
            channels {
              edges {
                node {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
  }
`;

//GiftCardQueries

export const GET_GIFT_CARD = gql`
  query GetGiftCard($id: ID!) {
    giftCard(id: $id) {
      id
      code
      displayCode
      isActive
      expiryDate
      currency
      initialBalance {
        amount
        currency
      }
      currentBalance {
        amount
        currency
      }
      createdBy {
        id
        email
      }
      usedBy {
        id
        email
      }
      createdByEmail
      usedByEmail
      created_at
      lastUsedOn
      tags {
        edges {
          node {
            id
            name
          }
        }
      }
      events {
        edges {
          node {
            id
            type
            date
            parameters
            user {
              id
              email
            }
            order {
              id
              number
            }
          }
        }
      }
    }
  }
`;

export const GET_ALL_GIFT_CARDS = gql`
  query GetAllGiftCards(
    $first: Int
    $after: String
    $sortBy: GiftCardSortingInput
    $filter: GiftCardFilterInput
  ) {
    giftCards(first: $first, after: $after, sortBy: $sortBy, filter: $filter) {
      edges {
        node {
          id
          code
          displayCode
          isActive
          currentBalance {
            amount
            currency
          }
          expiryDate
          createdBy {
            id
            email
          }
          created_at
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

export const GET_GIFT_CARD_CURRENCIES = gql`
  query GetGiftCardCurrencies {
    giftCardCurrencies {
      edges {
        node
      }
    }
  }
`;

export const GET_GIFT_CARD_TAGS = gql`
  query GetGiftCardTags($first: Int, $after: String) {
    giftCardTags(first: $first, after: $after) {
      edges {
        node {
          id
          name
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

export const GET_GIFT_CARD_EVENTS = gql`
  query GetGiftCardEvents($giftCardId: ID!, $first: Int, $after: String) {
    giftCard(id: $giftCardId) {
      id
      events(first: $first, after: $after) {
        edges {
          node {
            id
            type
            date
            parameters
            user {
              id
              email
            }
            order {
              id
              number
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
`;

export const GET_GIFT_CARD_WITH_TRANSACTIONS = gql`
  query GetGiftCardWithTransactions($id: ID!) {
    giftCard(id: $id) {
      id
      code
      currentBalance {
        amount
        currency
      }
      events {
        edges {
          node {
            id
            type
            date
            parameters
            order {
              id
              number
            }
          }
        }
      }
    }
  }
`;

export const SEARCH_GIFT_CARDS = gql`
  query SearchGiftCards($search: String!, $first: Int, $after: String) {
    giftCards(first: $first, after: $after, filter: { search: $search }) {
      edges {
        node {
          id
          code
          displayCode
          currentBalance {
            amount
          }
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

export const GET_GIFT_CARDS_BY_TAG = gql`
  query GetGiftCardsByTag($tagId: ID!, $first: Int, $after: String) {
    giftCards(first: $first, after: $after, filter: { tags: [$tagId] }) {
      edges {
        node {
          id
          code
          currentBalance {
            amount
          }
          expiryDate
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

//InvoiceQuery



export const GET_ALL_INVOICES = gql`
  query GetAllInvoices($first: Int, $after: String, $filter: InvoiceFilterInput) {
    allInvoices(first: $first, after: $after, filters: $filter) {
      edges {
        node {
          id
          number
          created
          url
          externalUrl
          order {
            id
            number
            created
          }
          metadata {
            key
            value
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

export const GET_INVOICE = gql`
  query GetInvoice($id: ID!) {
    invoice(id: $id) {
      id
      number
      created
      url
      externalUrl
      invoiceFile {
        url
        name
      }
      order {
        id
        number
        created
        user {
          id
          email
        }
        total {
          gross {
            amount
            currency
          }
        }
      }
      metadata {
        key
        value
      }
      events {
        edges {
          node {
            id
            type
            date
            parameters
            user {
              id
              email
            }
          }
        }
      }
    }
  }
`;

export const GET_INVOICE_EVENTS = gql`
  query GetInvoiceEvents($invoiceId: ID!, $first: Int, $after: String) {
    invoice(id: $invoiceId) {
      id
      events(first: $first, after: $after) {
        edges {
          node {
            id
            type
            date
            parameters
            user {
              id
              email
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
`;

export const GET_INVOICES_BY_ORDER = gql`
  query GetInvoicesByOrder($orderId: ID!, $first: Int, $after: String) {
    allInvoices(first: $first, after: $after, filters: { order: $orderId }) {
      edges {
        node {
          id
          number
          created
          url
          metadata {
            key
            value
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

export const SEARCH_INVOICES = gql`
  query SearchInvoices($search: String!, $first: Int, $after: String) {
    allInvoices(first: $first, after: $after, filters: { search: $search }) {
      edges {
        node {
          id
          number
          created
          order {
            id
            number
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

//OrderQueries



// Homepage events query
export const HOMEPAGE_EVENTS_QUERY = gql`
  query HomepageEvents {
    homepageEvents {
      edges {
        node {
          id
          type
          date
          order {
            id
            number
          }
          user {
            id
            email
          }
          parameters
        }
      }
    }
  }
`;

// Single order query by ID or external reference
export const ORDER_QUERY = gql`
  query Order($id: ID, $externalReference: String) {
    order(id: $id, externalReference: $externalReference) {
      id
      number
      status
      userEmail
      created
      updated
      total {
        gross {
          amount
          currency
        }
        net {
          amount
          currency
        }
      }
      subtotal {
        gross {
          amount
          currency
        }
        net {
          amount
          currency
        }
      }
      isFullyPaid
      channel {
        id
        slug
      }
      user {
        id
        email
      }
      shippingAddress {
        id
        firstName
        lastName
        streetAddress1
        city
        postalCode
        country {
          code
        }
      }
      billingAddress {
        id
        firstName
        lastName
        streetAddress1
        city
        postalCode
        country {
          code
        }
      }
    }
  }
`;

// Orders list query with channel filtering
export const ORDERS_QUERY = gql`
  query Orders($channel: String, $first: Int, $after: String) {
    orders(channel: $channel, first: $first, after: $after) {
      edges {
        node {
          id
          number
          status
          created
          total {
            gross {
              amount
              currency
            }
          }
          userEmail
          channel {
            id
            slug
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

// Draft orders query
export const DRAFT_ORDERS_QUERY = gql`
  query DraftOrders($first: Int, $after: String) {
    draftOrders(first: $first, after: $after) {
      edges {
        node {
          id
          number
          status
          created
          total {
            gross {
              amount
              currency
            }
          }
          userEmail
          channel {
            id
            slug
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

// Orders total amount query for reporting
export const ORDERS_TOTAL_QUERY = gql`
  query OrdersTotal($period: ReportingPeriod!, $channel: String) {
    ordersTotal(period: $period, channel: $channel) {
      gross {
        amount
        currency
      }
      net {
        amount
        currency
      }
    }
  }
`;

// Order by token query
export const ORDER_BY_TOKEN_QUERY = gql`
  query OrderByToken($token: UUID!) {
    orderByToken(token: $token) {
      id
      number
      status
      userEmail
      created
      total {
        gross {
          amount
          currency
        }
      }
      lines {
        id
        productName
        variantName
        quantity
        unitPrice {
          gross {
            amount
            currency
          }
        }
      }
    }
  }
`;

// Order lines query
export const ORDER_LINES_QUERY = gql`
  query OrderLines($orderId: ID!) {
    order(id: $orderId) {
      id
      lines {
        id
        productName
        variantName
        productSku
        quantity
        quantityFulfilled
        isShippingRequired
        isDigital
        unitPrice {
          gross {
            amount
            currency
          }
        }
        totalPrice {
          gross {
            amount
            currency
          }
        }
      }
    }
  }
`;

// Fulfillments query
export const FULFILLMENTS_QUERY = gql`
  query Fulfillments($orderId: ID!) {
    order(id: $orderId) {
      id
      fulfillments {
        id
        status
        trackingNumber
        created
        lines {
          id
          quantity
          orderLine {
            id
            productName
            variantName
          }
        }
      }
    }
  }
`;

// Order events query
export const ORDER_EVENTS_QUERY = gql`
  query OrderEvents($orderId: ID!) {
    order(id: $orderId) {
      id
      events {
        id
        type
        date
        user {
          id
          email
        }
        parameters
      }
    }
  }
`;

// Order granted refunds query
export const ORDER_GRANTED_REFUNDS_QUERY = gql`
  query OrderGrantedRefunds($orderId: ID!) {
    order(id: $orderId) {
      id
      grantedRefunds {
        id
        amount {
          amount
          currency
        }
        reason
        status
        created
        updated
        user {
          id
          email
        }
      }
    }
  }
`;

//PaymentQueries



// Single transaction item query
export const TRANSACTION_ITEM_QUERY = gql`
  query TransactionItem($id: ID!) {
    transaction(id: $id) {
      id
      token
      name
      message
      pspReference
      currency
      amountCharged {
        amount
        currency
      }
      amountAuthorized {
        amount
        currency
      }
      amountRefunded {
        amount
        currency
      }
      amountCanceled {
        amount
        currency
      }
      createdAt
      modifiedAt
      checkout {
        id
      }
      order {
        id
        number
      }
      availableActions
      events {
        id
        type
        createdAt
        amount {
          amount
          currency
        }
      }
    }
  }
`;

// All transactions query with filtering
export const ALL_TRANSACTIONS_QUERY = gql`
  query AllTransactions(
    $token: UUID
    $checkoutId: ID
    $orderId: ID
    $currency: String
    $createdAt: DateTime
    $createdAtGte: DateTime
    $createdAtLte: DateTime
    $first: Int
    $after: String
  ) {
    allTransactions(
      token: $token
      checkoutId: $checkoutId
      orderId: $orderId
      currency: $currency
      createdAt: $createdAt
      createdAt_Gte: $createdAtGte
      createdAt_Lte: $createdAtLte
      first: $first
      after: $after
    ) {
      edges {
        node {
          id
          token
          name
          currency
          amountCharged {
            amount
            currency
          }
          createdAt
          checkout {
            id
          }
          order {
            id
            number
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

// Single transaction event query
export const TRANSACTION_EVENT_QUERY = gql`
  query TransactionEvent($id: ID!) {
    transactionEvent(id: $id) {
      id
      type
      createdAt
      amount {
        amount
        currency
      }
      message
      pspReference
      transaction {
        id
        token
      }
      user {
        id
        email
      }
    }
  }
`;

// All transaction events query with filtering
export const ALL_TRANSACTION_EVENTS_QUERY = gql`
  query AllTransactionEvents(
    $transactionId: ID
    $type: String
    $createdAt: DateTime
    $createdAtGte: DateTime
    $createdAtLte: DateTime
    $first: Int
    $after: String
  ) {
    allTransactionEvents(
      transactionId: $transactionId
      type: $type
      createdAt: $createdAt
      createdAt_Gte: $createdAtGte
      createdAt_Lte: $createdAtLte
      first: $first
      after: $after
    ) {
      edges {
        node {
          id
          type
          createdAt
          amount {
            amount
            currency
          }
          transaction {
            id
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

// Single payment query
export const PAYMENT_QUERY = gql`
  query Payment($id: ID!) {
    payment(id: $id) {
      id
      gateway
      isActive
      chargeStatus
      token
      total {
        amount
        currency
      }
      capturedAmount {
        amount
        currency
      }
      currency
      createdAt
      modifiedAt
      checkout {
        id
      }
      order {
        id
        number
      }
      billingEmail
      billingFirstName
      billingLastName
      ccBrand
      ccLastDigits
      transactions {
        id
        kind
        isSuccess
        amount {
          amount
          currency
        }
        createdAt
      }
    }
  }
`;

// All payments query with filtering
export const ALL_PAYMENTS_QUERY = gql`
  query AllPayments(
    $gateway: String
    $isActive: Boolean
    $chargeStatus: String
    $checkoutId: ID
    $orderId: ID
    $createdAt: DateTime
    $createdAtGte: DateTime
    $createdAtLte: DateTime
    $first: Int
    $after: String
  ) {
    allPayments(
      gateway: $gateway
      isActive: $isActive
      chargeStatus: $chargeStatus
      checkoutId: $checkoutId
      orderId: $orderId
      createdAt: $createdAt
      createdAt_Gte: $createdAtGte
      createdAt_Lte: $createdAtLte
      first: $first
      after: $after
    ) {
      edges {
        node {
          id
          gateway
          isActive
          chargeStatus
          total {
            amount
            currency
          }
          currency
          createdAt
          order {
            id
            number
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

// Single transaction record query
export const TRANSACTION_RECORD_QUERY = gql`
  query TransactionRecord($id: ID!) {
    transactionRecord(id: $id) {
      id
      kind
      isSuccess
      currency
      amount {
        amount
        currency
      }
      createdAt
      error
      payment {
        id
        gateway
      }
      gatewayResponse
    }
  }
`;

// All transaction records query with filtering
export const ALL_TRANSACTION_RECORDS_QUERY = gql`
  query AllTransactionRecords(
    $paymentId: ID
    $kind: String
    $isSuccess: Boolean
    $currency: String
    $createdAt: DateTime
    $createdAtGte: DateTime
    $createdAtLte: DateTime
    $first: Int
    $after: String
  ) {
    allTransactionRecords(
      paymentId: $paymentId
      kind: $kind
      isSuccess: $isSuccess
      currency: $currency
      createdAt: $createdAt
      createdAt_Gte: $createdAtGte
      createdAt_Lte: $createdAtLte
      first: $first
      after: $after
    ) {
      edges {
        node {
          id
          kind
          isSuccess
          currency
          amount {
            amount
            currency
          }
          createdAt
          payment {
            id
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`;

//ProductQueries



// Digital Content Queries
export const DIGITAL_CONTENT_QUERY = gql`
  query DigitalContent($id: ID!) {
    digitalContent(id: $id) {
      id
      useDefaultSettings
      automaticFulfillment
      contentFile
      maxDownloads
      urlValidDays
      productVariant {
        id
        name
        sku
      }
    }
  }
`;

export const ALL_DIGITAL_CONTENTS_QUERY = gql`
  query AllDigitalContents {
    digitalContents {
      edges {
        node {
          id
          contentFile
          maxDownloads
          productVariant {
            id
            name
          }
        }
      }
    }
  }
`;

// Category Queries
export const CATEGORIES_QUERY = gql`
  query Categories($level: Int, $first: Int, $after: String) {
    categories(level: $level, first: $first, after: $after) {
      edges {
        node {
          id
          name
          slug
          level
          description
          backgroundImage {
            url
          }
          children {
            id
            name
          }
          parent {
            id
            name
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const CATEGORY_QUERY = gql`
  query Category($id: ID, $slug: String) {
    category(id: $id, slug: $slug) {
      id
      name
      slug
      description
      backgroundImage {
        url
        alt
      }
      products {
        id
        name
      }
      children {
        id
        name
      }
      parent {
        id
        name
      }
    }
  }
`;

// Collection Queries
export const COLLECTION_QUERY = gql`
  query Collection($id: ID, $slug: String, $channel: String) {
    collection(id: $id, slug: $slug, channel: $channel) {
      id
      name
      slug
      description
      backgroundImage {
        url
        alt
      }
      channelListings {
        id
        publishedAt
        channel {
          id
          name
        }
      }
      products(first: 10) {
        edges {
          node {
            id
            name
            thumbnail {
              url
            }
          }
        }
      }
    }
  }
`;

export const COLLECTIONS_QUERY = gql`
  query Collections($channel: String, $first: Int, $after: String) {
    collections(channel: $channel, first: $first, after: $after) {
      edges {
        node {
          id
          name
          slug
          description
          backgroundImage {
            url
          }
          products(first: 3) {
            edges {
              node {
                id
                name
              }
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const COLLECTION_TRANSLATION_QUERY = gql`
  query CollectionTranslation($id: ID!) {
    collectionTranslation(id: $id) {
      id
      name
      description
      languageCode
      collection {
        id
        name
      }
    }
  }
`;

// Product Queries
export const PRODUCT_QUERY = gql`
  query Product($id: ID!) {
    product(id: $id) {
      id
      name
      slug
      description
      category {
        id
        name
      }
      productType {
        id
        name
      }
      thumbnail {
        url
      }
      variants {
        id
        name
        sku
      }
      media {
        id
        url
        alt
      }
      channelListings {
        id
        publishedAt
        channel {
          id
          name
        }
      }
    }
  }
`;

export const PRODUCTS_QUERY = gql`
  query Products($search: String, $channel: String, $first: Int, $after: String) {
    products(search: $search, channel: $channel, first: $first, after: $after) {
      edges {
        node {
          id
          name
          slug
          thumbnail {
            url
          }
          variants {
            id
            name
            sku
          }
          channelListings {
            id
            publishedAt
            channel {
              id
              name
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// Product Type Queries
export const PRODUCT_TYPE_QUERY = gql`
  query ProductType($id: ID!) {
    productType(id: $id) {
      id
      name
      slug
      hasVariants
      isShippingRequired
      isDigital
      productAttributes {
        id
        name
      }
      variantAttributes {
        id
        name
      }
    }
  }
`;

export const PRODUCT_TYPES_QUERY = gql`
  query ProductTypes($first: Int, $after: String) {
    productTypes(first: $first, after: $after) {
      edges {
        node {
          id
          name
          slug
          hasVariants
          isShippingRequired
          products {
            totalCount
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// Product Variant Queries
export const PRODUCT_VARIANT_QUERY = gql`
  query ProductVariant($id: ID, $sku: String, $channel: String) {
    productVariant(id: $id, sku: $sku, channel: $channel) {
      id
      name
      sku
      product {
        id
        name
      }
      media {
        id
        url
      }
      channelListings {
        id
        price {
          amount
          currency
        }
        channel {
          id
          name
        }
      }
      attributes {
        id
        name
        values {
          id
          name
        }
      }
    }
  }
`;

export const PRODUCT_VARIANTS_QUERY = gql`
  query ProductVariants($ids: [String!], $channel: String, $first: Int, $after: String) {
    productVariants(ids: $ids, channel: $channel, first: $first, after: $after) {
      edges {
        node {
          id
          name
          sku
          product {
            id
            name
          }
          channelListings {
            id
            price {
              amount
              currency
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// Media Queries
export const PRODUCT_MEDIA_QUERY = gql`
  query ProductMedia($productId: ID!) {
    product(id: $productId) {
      id
      media {
        id
        url
        alt
        type
      }
    }
  }
`;

// Variant Media Queries
export const VARIANT_MEDIA_QUERY = gql`
  query VariantMedia($variantId: ID!) {
    productVariant(id: $variantId) {
      id
      media {
        id
        url
        alt
      }
    }
  }
`;

//ShippingQueries


// =====================
// Shipping Zone Queries
// =====================

export const SHIPPING_ZONE_QUERY = gql`
  query ShippingZone($id: ID!, $channel: String) {
    shippingZone(id: $id, channel: $channel) {
      id
      name
      default
      description
      priceRange(channelSlug: $channel) {
        start {
          amount
          currency
        }
        stop {
          amount
          currency
        }
      }
      countries {
        code
        country
      }
      warehouses {
        id
        name
      }
      channels {
        id
        name
      }
    }
  }
`;

export const SHIPPING_ZONES_QUERY = gql`
  query ShippingZones($channel: String, $first: Int, $after: String) {
    shippingZones(channel: $channel, first: $first, after: $after) {
      edges {
        node {
          id
          name
          default
          countries {
            code
            country
          }
          priceRange(channelSlug: $channel) {
            start {
              amount
              currency
            }
            stop {
              amount
              currency
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Shipping Method Queries
// =====================

export const SHIPPING_METHOD_QUERY = gql`
  query ShippingMethod($id: ID!, $channelSlug: String) {
    shippingMethod(id: $id) {
      id
      name
      type
      price(channelSlug: $channelSlug) {
        amount
        currency
      }
      minimumOrderPrice(channelSlug: $channelSlug) {
        amount
        currency
      }
      maximumOrderPrice(channelSlug: $channelSlug) {
        amount
        currency
      }
      active(channelSlug: $channelSlug)
      maximumOrderWeight {
        unit
        value
      }
      minimumOrderWeight {
        unit
        value
      }
      shippingZone {
        id
        name
      }
      taxClass {
        id
        name
      }
    }
  }
`;

export const SHIPPING_METHODS_QUERY = gql`
  query ShippingMethods($first: Int, $after: String) {
    shippingMethods(first: $first, after: $after) {
      edges {
        node {
          id
          name
          type
          shippingZone {
            id
            name
          }
          channelListings {
            id
            price {
              amount
              currency
            }
            channel {
              id
              name
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Shipping Method Postal Code Rule Queries
// =====================

export const SHIPPING_METHOD_POSTAL_CODE_RULE_QUERY = gql`
  query ShippingMethodPostalCodeRule($id: ID!) {
    shippingMethodPostalCodeRule(id: $id) {
      id
      start
      end
      inclusionType
      shippingMethod {
        id
        name
      }
    }
  }
`;

export const SHIPPING_METHOD_POSTAL_CODE_RULES_QUERY = gql`
  query ShippingMethodPostalCodeRules($first: Int, $after: String) {
    shippingMethodPostalCodeRules(first: $first, after: $after) {
      edges {
        node {
          id
          start
          end
          inclusionType
          shippingMethod {
            id
            name
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Shipping Method Channel Listing Queries
// =====================

export const SHIPPING_METHOD_CHANNEL_LISTING_QUERY = gql`
  query ShippingMethodChannelListing($id: ID!) {
    shippingMethodChannelListing(id: $id) {
      id
      price {
        amount
        currency
      }
      minimumOrderPrice {
        amount
        currency
      }
      maximumOrderPrice {
        amount
        currency
      }
      isActive
      channel {
        id
        name
      }
      shippingMethod {
        id
        name
      }
    }
  }
`;

export const SHIPPING_METHOD_CHANNEL_LISTINGS_QUERY = gql`
  query ShippingMethodChannelListings($first: Int, $after: String) {
    shippingMethodChannelListings(first: $first, after: $after) {
      edges {
        node {
          id
          price {
            amount
            currency
          }
          isActive
          channel {
            id
            name
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Combined Shipping Data Queries
// =====================

export const SHIPPING_ZONE_WITH_METHODS_QUERY = gql`
  query ShippingZoneWithMethods($id: ID!, $channel: String) {
    shippingZone(id: $id, channel: $channel) {
      id
      name
      countries {
        code
        country
      }
      shippingMethods {
        id
        name
        type
        price(channelSlug: $channel) {
          amount
          currency
        }
        minimumOrderPrice(channelSlug: $channel) {
          amount
          currency
        }
        maximumOrderPrice(channelSlug: $channel) {
          amount
          currency
        }
        active(channelSlug: $channel)
        postalCodeRules {
          id
          start
          end
          inclusionType
        }
      }
    }
  }
`;

export const CHANNEL_SHIPPING_METHODS_QUERY = gql`
  query ChannelShippingMethods($channelSlug: String!) {
    shippingZones(channel: $channelSlug) {
      edges {
        node {
          id
          name
          shippingMethods {
            id
            name
            type
            price(channelSlug: $channelSlug) {
              amount
              currency
            }
            active(channelSlug: $channelSlug)
          }
        }
      }
    }
  }
`;


//TaxQueries 



// =====================
// Tax Configuration Queries
// =====================

export const TAX_CONFIGURATION_QUERY = gql`
  query TaxConfiguration($id: ID!) {
    taxConfiguration(id: $id) {
      id
      channel {
        id
        name
      }
      chargeTaxes
      taxCalculationStrategy
      displayGrossPrices
      pricesEnteredWithTax
      taxAppId
      countryExceptions {
        id
        country {
          code
          country
        }
        chargeTaxes
        taxCalculationStrategy
        displayGrossPrices
      }
    }
  }
`;

export const TAX_CONFIGURATIONS_QUERY = gql`
  query TaxConfigurations($first: Int, $after: String) {
    taxConfigurations(first: $first, after: $after) {
      edges {
        node {
          id
          channel {
            id
            name
          }
          chargeTaxes
          taxCalculationStrategy
          displayGrossPrices
          pricesEnteredWithTax
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Tax Class Queries
// =====================

export const TAX_CLASS_QUERY = gql`
  query TaxClass($id: ID!) {
    taxClass(id: $id) {
      id
      name
      isDefault
      countries
      rates {
        id
        country {
          code
          country
        }
        rate
      }
    }
  }
`;

export const TAX_CLASSES_QUERY = gql`
  query TaxClasses($first: Int, $after: String) {
    taxClasses(first: $first, after: $after) {
      edges {
        node {
          id
          name
          isDefault
          countries
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Tax Country Configuration Queries
// =====================

export const TAX_COUNTRY_CONFIGURATION_QUERY = gql`
  query TaxCountryConfiguration($countryCode: CountryCode!) {
    taxCountryConfiguration(countryCode: $countryCode) {
      country {
        code
        country
      }
      taxClassCountryRates {
        id
        taxClass {
          id
          name
        }
        rate
      }
    }
  }
`;

export const TAX_COUNTRY_CONFIGURATIONS_QUERY = gql`
  query TaxCountryConfigurations($first: Int, $after: String) {
    taxCountryConfigurations(first: $first, after: $after) {
      edges {
        node {
          country {
            code
            country
          }
          taxClassCountryRates {
            id
            taxClass {
              id
              name
            }
            rate
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Tax Class Country Rate Queries
// =====================

export const TAX_CLASS_COUNTRY_RATE_QUERY = gql`
  query TaxClassCountryRate($id: ID!) {
    taxClassCountryRate(id: $id) {
      id
      country {
        code
        country
      }
      rate
      taxClass {
        id
        name
      }
    }
  }
`;

export const TAX_CLASS_COUNTRY_RATES_QUERY = gql`
  query TaxClassCountryRates($first: Int, $after: String) {
    taxClassCountryRates(first: $first, after: $after) {
      edges {
        node {
          id
          country {
            code
            country
          }
          rate
          taxClass {
            id
            name
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

// =====================
// Combined Tax Data Queries
// =====================

export const TAX_SETTINGS_QUERY = gql`
  query TaxSettings {
    taxConfigurations {
      edges {
        node {
          id
          channel {
            id
            name
          }
          chargeTaxes
          taxCalculationStrategy
          displayGrossPrices
          pricesEnteredWithTax
          countryExceptions {
            id
            country {
              code
              country
            }
            chargeTaxes
            taxCalculationStrategy
            displayGrossPrices
          }
        }
      }
    }
    taxClasses {
      edges {
        node {
          id
          name
          isDefault
          countries
        }
      }
    }
  }
`;

export const CHANNEL_TAX_CONFIGURATION_QUERY = gql`
  query ChannelTaxConfiguration($channelId: ID!) {
    taxConfiguration(channelId: $channelId) {
      id
      chargeTaxes
      taxCalculationStrategy
      displayGrossPrices
      pricesEnteredWithTax
      countryExceptions {
        id
        country {
          code
          country
        }
        chargeTaxes
        taxCalculationStrategy
        displayGrossPrices
      }
    }
  }
`;


// Warehouse queries
export const GET_WAREHOUSE = gql`
  query GetWarehouse($id: ID!) {
    warehouse(id: $id) {
      id
      name
      slug
      email
      clickAndCollectOption
      isPrivate
      createdAt
      updatedAt
      countries
      stockCount
      address {
        id
        # Add address fields as needed
      }
      shippingZones {
        id
        # Add shipping zone fields as needed
      }
      channels {
        id
        # Add channel fields as needed
      }
    }
  }
`;

export const GET_WAREHOUSES = gql`
  query GetWarehouses(
    $filter: WarehouseFilterInput
    $first: Int
    $after: String
    $last: Int
    $before: String
  ) {
    warehouses(
      filter: $filter
      first: $first
      after: $after
      last: $last
      before: $before
    ) {
      edges {
        node {
          id
          name
          slug
          email
          isPrivate
          createdAt
        }
      }
      pageInfo {
        hasNextPage
        hasPreviousPage
        startCursor
        endCursor
      }
    }
  }
`;

// Stock queries
export const GET_STOCK = gql`
  query GetStock($id: ID!) {
    stock(id: $id) {
      id
      quantity
      quantityAllocated
      availableQuantity
      quantityReserved
      warehouse {
        id
        name
      }
      productVariant {
        id
        sku
      }
    }
  }
`;

export const GET_STOCKS = gql`
  query GetStocks(
    $filter: StockFilterInput
    $first: Int
    $after: String
    $last: Int
    $before: String
  ) {
    allStocks(
      filter: $filter
      first: $first
      after: $after
      last: $last
      before: $before
    ) {
      edges {
        node {
          id
          quantity
          quantityAllocated
          availableQuantity
          warehouse {
            id
            name
          }
          productVariant {
            id
            sku
          }
        }
      }
      pageInfo {
        hasNextPage
        hasPreviousPage
        startCursor
        endCursor
      }
    }
  }
`;

// Allocation queries
export const GET_ALLOCATION = gql`
  query GetAllocation($id: ID!) {
    allocation(id: $id) {
      id
      quantityAllocated
      stockAvailableQuantity
      orderLine {
        id
        # Add order line fields as needed
      }
      stock {
        id
        # Add stock fields as needed
      }
    }
  }
`;

export const GET_ALLOCATIONS = gql`
  query GetAllocations(
    $filter: AllocationFilterInput
    $first: Int
    $after: String
    $last: Int
    $before: String
  ) {
    allocations(
      filter: $filter
      first: $first
      after: $after
      last: $last
      before: $before
    ) {
      edges {
        node {
          id
          quantityAllocated
          orderLine {
            id
          }
          stock {
            id
          }
        }
      }
      pageInfo {
        hasNextPage
        hasPreviousPage
        startCursor
        endCursor
      }
    }
  }
`;

// Channel Warehouse queries
export const GET_CHANNEL_WAREHOUSE = gql`
  query GetChannelWarehouse($id: ID!) {
    channelWarehouse(id: $id) {
      id
      sortOrder
      channel {
        id
        # Add channel fields as needed
      }
      warehouse {
        id
        name
      }
    }
  }
`;

export const GET_CHANNEL_WAREHOUSES = gql`
  query GetChannelWarehouses(
    $filter: ChannelWarehouseFilterInput
    $first: Int
    $after: String
    $last: Int
    $before: String
  ) {
    allChannelWarehouse(
      filter: $filter
      first: $first
      after: $after
      last: $last
      before: $before
    ) {
      edges {
        node {
          id
          sortOrder
          channel {
            id
            name
          }
          warehouse {
            id
            name
          }
        }
      }
      pageInfo {
        hasNextPage
        hasPreviousPage
        startCursor
        endCursor
      }
    }
  }
`;

// Preorder Allocation queries
export const GET_PREORDER_ALLOCATION = gql`
  query GetPreorderAllocation($id: ID!) {
    preorderAllocation(id: $id) {
      id
      quantity
      orderLine {
        id
        # Add order line fields as needed
      }
      productVariantChannelListing {
        id
        # Add channel listing fields as needed
      }
    }
  }
`;

export const GET_PREORDER_ALLOCATIONS = gql`
  query GetPreorderAllocations(
    $filter: PreorderAllocationFilterInput
    $first: Int
    $after: String
    $last: Int
    $before: String
  ) {
    allPreorderAllocation(
      filter: $filter
      first: $first
      after: $after
      last: $last
      before: $before
    ) {
      edges {
        node {
          id
          quantity
          orderLine {
            id
          }
          productVariantChannelListing {
            id
          }
        }
      }
      pageInfo {
        hasNextPage
        hasPreviousPage
        startCursor
        endCursor
      }
    }
  }
`;

// Reservation queries
export const GET_RESERVATION = gql`
  query GetReservation($id: ID!) {
    reservation(id: $id) {
      id
      quantityReserved
      reservedUntil
      isActive
      checkoutLine {
        id
        # Add checkout line fields as needed
      }
      stock {
        id
        # Add stock fields as needed
      }
    }
  }
`;

export const GET_RESERVATIONS = gql`
  query GetReservations(
    $filter: ReservationFilterInput
    $first: Int
    $after: String
    $last: Int
    $before: String
  ) {
    allReservation(
      filter: $filter
      first: $first
      after: $after
      last: $last
      before: $before
    ) {
      edges {
        node {
          id
          quantityReserved
          reservedUntil
          isActive
          checkoutLine {
            id
          }
          stock {
            id
          }
        }
      }
      pageInfo {
        hasNextPage
        hasPreviousPage
        startCursor
        endCursor
      }
    }
  }
`;

// Preorder Reservation queries
export const GET_PREORDER_RESERVATION = gql`
  query GetPreorderReservation($id: ID!) {
    preorderReservation(id: $id) {
      id
      quantityReserved
      reservedUntil
      isActive
      checkoutLine {
        id
        # Add checkout line fields as needed
      }
      productVariantChannelListing {
        id
        # Add channel listing fields as needed
      }
    }
  }
`;

export const GET_PREORDER_RESERVATIONS = gql`
  query GetPreorderReservations(
    $filter: PreorderReservationFilterInput
    $first: Int
    $after: String
    $last: Int
    $before: String
  ) {
    allPreorderReservation(
      filter: $filter
      first: $first
      after: $after
      last: $last
      before: $before
    ) {
      edges {
        node {
          id
          quantityReserved
          reservedUntil
          isActive
          checkoutLine {
            id
          }
          productVariantChannelListing {
            id
          }
        }
      }
      pageInfo {
        hasNextPage
        hasPreviousPage
        startCursor
        endCursor
      }
    }
  }
`;