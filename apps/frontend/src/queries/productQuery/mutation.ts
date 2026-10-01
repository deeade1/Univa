import { gql } from '@apollo/client';

// Create Attribute Mutation
export const CREATE_ATTRIBUTE_MUTATION = gql`
  mutation CreateAttribute($attributeData: AttributeInput!) {
    createAttribute(input: { attributeData: $attributeData }) {
      attribute {
        id
        name
        slug
        # Include other fields you need from AttributeNode
      }
    }
  }
`;

// Update Attribute Mutation
export const UPDATE_ATTRIBUTE_MUTATION = gql`
  mutation UpdateAttribute($id: ID!, $attributeData: AttributeInput!) {
    updateAttribute(input: { id: $id, attributeData: $attributeData }) {
      attribute {
        id
        name
        slug
        # Include other fields you need from AttributeNode
      }
    }
  }
`;

// Delete Attribute Mutation
export const DELETE_ATTRIBUTE_MUTATION = gql`
  mutation DeleteAttribute($id: ID!) {
    deleteAttribute(input: { id: $id }) {
      success
    }
  }
`;

// Assign Attribute to Product Type Mutation
export const ASSIGN_ATTRIBUTE_TO_PRODUCT_TYPE_MUTATION = gql`
  mutation AssignAttributeToProductType($attributeId: ID!, $productTypeId: ID!) {
    assignAttributeToProductType(input: { attributeId: $attributeId, productTypeId: $productTypeId }) {
      attributeProduct {
        id
        # Include other fields you need from AttributeProductNode
      }
    }
  }
`;

// Create Attribute Value Mutation
export const CREATE_ATTRIBUTE_VALUE_MUTATION = gql`
  mutation CreateAttributeValue(
    $name: String!
    $value: String
    $slug: String
    $attributeId: ID!
    $fileUrl: String
    $contentType: String
    $richText: JSONString
    $plainText: String
    $boolean: Boolean
    $dateTime: DateTime
    $referenceProductId: ID
    $referenceVariantId: ID
  ) {
    createAttributeValue(input: {
      name: $name
      value: $value
      slug: $slug
      attributeId: $attributeId
      fileUrl: $fileUrl
      contentType: $contentType
      richText: $richText
      plainText: $plainText
      boolean: $boolean
      dateTime: $dateTime
      referenceProductId: $referenceProductId
      referenceVariantId: $referenceVariantId
    }) {
      attributeValue {
        id
        name
        value
        # Include other fields you need from AttributeValueNode
      }
    }
  }
`;

// Update Attribute Value Mutation
export const UPDATE_ATTRIBUTE_VALUE_MUTATION = gql`
  mutation UpdateAttributeValue($id: ID!, $attributeValueData: AttributeValueInput!) {
    updateAttributeValue(input: { id: $id, attributeValueData: $attributeValueData }) {
      attributeValue {
        id
        name
        value
        # Include other fields you need from AttributeValueNode
      }
    }
  }
`;

// Delete Attribute Value Mutation
export const DELETE_ATTRIBUTE_VALUE_MUTATION = gql`
  mutation DeleteAttributeValue($id: ID!) {
    deleteAttributeValue(input: { id: $id }) {
      success
    }
  }
`;

// Assign Attribute to Product Mutation
export const ASSIGN_ATTRIBUTE_TO_PRODUCT_MUTATION = gql`
  mutation AssignAttributeToProduct($productId: ID!, $attributeValueId: ID!) {
    assignAttributeToProduct(input: { productId: $productId, attributeValueId: $attributeValueId }) {
      assignment {
        id
        # Include other fields you need from AssignedProductAttributeValueNode
      }
    }
  }
`;

// Assign Attribute to Variant Mutation
export const ASSIGN_ATTRIBUTE_TO_VARIANT_MUTATION = gql`
  mutation AssignAttributeToVariant(
    $variantId: ID!
    $attributeId: ID!
    $values: [ID!]
  ) {
    assignAttributeToVariant(input: {
      variantId: $variantId
      attributeId: $attributeId
      values: $values
    }) {
      assignment {
        id
        # Include other fields you need from AssignedVariantAttributeNode
      }
    }
  }
`;

// Update Variant Attribute Assignment Mutation
export const UPDATE_VARIANT_ATTRIBUTE_ASSIGNMENT_MUTATION = gql`
  mutation UpdateVariantAttributeAssignment($assignmentId: ID!, $values: [ID!]!) {
    updateVariantAttributeAssignment(input: {
      assignmentId: $assignmentId
      values: $values
    }) {
      assignment {
        id
        # Include other fields you need from AssignedVariantAttributeNode
      }
    }
  }
`;

// Create Attribute Variant Mutation
export const CREATE_ATTRIBUTE_VARIANT_MUTATION = gql`
  mutation CreateAttributeVariant(
    $attributeId: ID!
    $productTypeId: ID!
    $variantSelection: Boolean
  ) {
    createAttributeVariant(input: {
      attributeId: $attributeId
      productTypeId: $productTypeId
      variantSelection: $variantSelection
    }) {
      attributeVariant {
        id
        # Include other fields you need from AttributeVariantNode
      }
    }
  }
`;


// Channel Mutations
export const CREATE_CHANNEL_MUTATION = gql`
  mutation CreateChannel(
    $name: String!
    $slug: String!
    $currencyCode: String!
    $defaultCountry: String!
  ) {
    createChannel(input: {
      name: $name
      slug: $slug
      currencyCode: $currencyCode
      defaultCountry: $defaultCountry
    }) {
      channel {
        id
        name
        slug
        currencyCode
        defaultCountry
        isActive
      }
    }
  }
`;

export const UPDATE_CHANNEL_MUTATION = gql`
  mutation UpdateChannel(
    $id: ID!
    $name: String
    $slug: String
    $currencyCode: String
    $defaultCountry: String
  ) {
    updateChannel(input: {
      id: $id
      name: $name
      slug: $slug
      currencyCode: $currencyCode
      defaultCountry: $defaultCountry
    }) {
      channel {
        id
        name
        slug
        currencyCode
        defaultCountry
        isActive
      }
    }
  }
`;

export const CHANNEL_ACTIVATE_MUTATION = gql`
  mutation ChannelActivate($id: ID!) {
    channelActivate(input: { id: $id }) {
      channel {
        id
        isActive
      }
    }
  }
`;

export const CHANNEL_DEACTIVATE_MUTATION = gql`
  mutation ChannelDeactivate($id: ID!) {
    channelDeactivate(input: { id: $id }) {
      channel {
        id
        isActive
      }
    }
  }
`;

export const CHANNEL_DELETE_MUTATION = gql`
  mutation ChannelDelete(
    $id: ID!
    $channelId: ID
  ) {
    channelDelete(input: {
      id: $id
      channelId: $channelId
    }) {
      channel {
        id
      }
    }
  }
`;

export const CHANNEL_REORDER_WAREHOUSES_MUTATION = gql`
  mutation ChannelReorderWarehouses(
    $channelId: ID!
    $moves: [ReorderInput!]!
  ) {
    channelReorderWarehouses(input: {
      channelId: $channelId
      moves: $moves
    }) {
      channel {
        id
        warehouses {
          id
          name
        }
      }
    }
  }
`;

// Input types
export const REORDER_INPUT = gql`
  input ReorderInput {
    id: ID!
    sortOrder: Int
  }
`;

export const STOCK_SETTINGS_INPUT = gql`
  input StockSettingsInput {
    allocationStrategy: AllocationStrategyEnum!
  }
`;

export const ORDER_SETTINGS_INPUT = gql`
  input OrderSettingsInput {
    automaticallyConfirmAllNewOrders: Boolean
    automaticallyFulfillNonShippableGiftCard: Boolean
    expireOrdersAfter: Minute
    deleteExpiredOrdersAfter: Day
    markAsPaidStrategy: MarkAsPaidStrategyEnum
    defaultTransactionFlowStrategy: TransactionFlowStrategyEnum
  }
`;

// Enum types
export const ALLOCATION_STRATEGY_ENUM = gql`
  enum AllocationStrategyEnum {
    PRIORITIZE_SORTING_ORDER
    PRIORITIZE_HIGH_STOCK
  }
`;

export const MARK_AS_PAID_STRATEGY_ENUM = gql`
  enum MarkAsPaidStrategyEnum {
    PAYMENT_FLOW
    TRANSACTION_FLOW
  }
`;

export const TRANSACTION_FLOW_STRATEGY_ENUM = gql`
  enum TransactionFlowStrategyEnum {
    AUTHORIZATION
    CHARGE
  }
`;


// Checkout Mutations
export const CREATE_CHECKOUT_MUTATION = gql`
  mutation CreateCheckout($email: String!, $channelId: ID!) {
    createCheckout(input: {
      email: $email
      channelId: $channelId
    }) {
      checkout {
        id
        email
        token
        currency
        channel {
          id
          name
        }
      }
    }
  }
`;

export const UPDATE_CHECKOUT_MUTATION = gql`
  mutation UpdateCheckout(
    $checkoutId: ID!
    $email: String
    $note: String
    $redirectUrl: String
  ) {
    updateCheckout(input: {
      checkoutId: $checkoutId
      email: $email
      note: $note
      redirectUrl: $redirectUrl
    }) {
      checkout {
        id
        email
        note
        redirectUrl
      }
    }
  }
`;

export const DELETE_CHECKOUT_MUTATION = gql`
  mutation DeleteCheckout($checkoutId: ID!) {
    deleteCheckout(input: { checkoutId: $checkoutId }) {
      success
    }
  }
`;

// Checkout Line Mutations
export const CREATE_CHECKOUT_LINE_MUTATION = gql`
  mutation CreateCheckoutLine(
    $checkoutToken: UUID!
    $variantId: ID!
    $quantity: Int!
  ) {
    createCheckoutLine(input: {
      checkoutToken: $checkoutToken
      variantId: $variantId
      quantity: $quantity
    }) {
      checkoutLine {
        id
        quantity
        variant {
          id
          name
        }
        checkout {
          id
        }
      }
    }
  }
`;

export const UPDATE_CHECKOUT_LINE_MUTATION = gql`
  mutation UpdateCheckoutLine($lineId: ID!, $quantity: Int!) {
    updateCheckoutLine(input: {
      lineId: $lineId
      quantity: $quantity
    }) {
      checkoutLine {
        id
        quantity
        variant {
          id
          name
        }
      }
    }
  }
`;

export const DELETE_CHECKOUT_LINE_MUTATION = gql`
  mutation DeleteCheckoutLine($lineId: ID!) {
    deleteCheckoutLine(input: { lineId: $lineId }) {
      success
    }
  }
`;

// Checkout Metadata Mutations
export const CREATE_CHECKOUT_METADATA_MUTATION = gql`
  mutation CreateCheckoutMetadata(
    $checkoutId: ID!
    $metadata: JSONString!
  ) {
    createCheckoutMetadata(input: {
      checkoutId: $checkoutId
      metadata: $metadata
    }) {
      metadataStorage {
        id
        metadata
        checkout {
          id
        }
      }
    }
  }
`;

export const UPDATE_CHECKOUT_METADATA_MUTATION = gql`
  mutation UpdateCheckoutMetadata(
    $checkoutId: ID!
    $metadata: JSONString!
  ) {
    updateCheckoutMetadata(input: {
      checkoutId: $checkoutId
      metadata: $metadata
    }) {
      metadataStorage {
        id
        metadata
      }
    }
  }
`;

export const DELETE_CHECKOUT_METADATA_MUTATION = gql`
  mutation DeleteCheckoutMetadata($checkoutId: ID!) {
    deleteCheckoutMetadata(input: { checkoutId: $checkoutId }) {
      success
    }
  }
`;

export const MERGE_CHECKOUT_METADATA_MUTATION = gql`
  mutation MergeCheckoutMetadata(
    $checkoutId: ID!
    $metadata: JSONString!
  ) {
    mergeCheckoutMetadata(input: {
      checkoutId: $checkoutId
      metadata: $metadata
    }) {
      metadataStorage {
        id
        metadata
      }
    }
  }
`;

export const REMOVE_CHECKOUT_METADATA_KEYS_MUTATION = gql`
  mutation RemoveCheckoutMetadataKeys(
    $checkoutId: ID!
    $keys: [String!]!
  ) {
    removeCheckoutMetadataKeys(input: {
      checkoutId: $checkoutId
      keys: $keys
    }) {
      metadataStorage {
        id
        metadata
      }
    }
  }
`;

export const OVERWRITE_CHECKOUT_METADATA_MUTATION = gql`
  mutation OverwriteCheckoutMetadata(
    $checkoutId: ID!
    $metadata: JSONString!
  ) {
    overwriteCheckoutMetadata(input: {
      checkoutId: $checkoutId
      metadata: $metadata
    }) {
      metadataStorage {
        id
        metadata
      }
    }
  }
`;



// Voucher Mutations
export const CREATE_VOUCHER_MUTATION = gql`
  mutation CreateVoucher(
    $name: String
    $type: String!
    $usageLimit: Int
    $startDate: DateTime
    $endDate: DateTime
    $discountValueType: String!
    $applyOncePerOrder: Boolean
    $applyOncePerCustomer: Boolean
    $onlyForStaff: Boolean
    $channelListings: [JSONString]
  ) {
    createVoucher(input: {
      name: $name
      type: $type
      usageLimit: $usageLimit
      startDate: $startDate
      endDate: $endDate
      discountValueType: $discountValueType
      applyOncePerOrder: $applyOncePerOrder
      applyOncePerCustomer: $applyOncePerCustomer
      onlyForStaff: $onlyForStaff
      channelListings: $channelListings
    }) {
      voucher {
        id
        name
        type
        usageLimit
        discountValueType
        startDate
        endDate
        channelListings {
          id
          channel {
            id
            name
          }
          discountValue
        }
      }
    }
  }
`;

export const UPDATE_VOUCHER_MUTATION = gql`
  mutation UpdateVoucher(
    $id: ID!
    $name: String
    $usageLimit: Int
    $endDate: DateTime
    $startDate: DateTime
    $applyOncePerOrder: Boolean
    $applyOncePerCustomer: Boolean
    $onlyForStaff: Boolean
  ) {
    updateVoucher(input: {
      id: $id
      name: $name
      usageLimit: $usageLimit
      endDate: $endDate
      startDate: $startDate
      applyOncePerOrder: $applyOncePerOrder
      applyOncePerCustomer: $applyOncePerCustomer
      onlyForStaff: $onlyForStaff
    }) {
      voucher {
        id
        name
        usageLimit
        startDate
        endDate
      }
    }
  }
`;

export const DELETE_VOUCHER_MUTATION = gql`
  mutation DeleteVoucher($id: ID!) {
    deleteVoucher(input: { id: $id }) {
      voucher {
        id
      }
    }
  }
`;

// Voucher Code Mutations
export const CREATE_VOUCHER_CODE_MUTATION = gql`
  mutation CreateVoucherCode($code: String!, $voucherId: ID!, $isActive: Boolean) {
    createVoucherCode(input: {
      code: $code
      voucherId: $voucherId
      isActive: $isActive
    }) {
      voucherCode {
        id
        code
        isActive
        voucher {
          id
        }
      }
    }
  }
`;

export const UPDATE_VOUCHER_CODE_MUTATION = gql`
  mutation UpdateVoucherCode($id: ID!, $code: String, $isActive: Boolean) {
    updateVoucherCode(input: {
      id: $id
      code: $code
      isActive: $isActive
    }) {
      voucherCode {
        id
        code
        isActive
      }
    }
  }
`;

export const DELETE_VOUCHER_CODE_MUTATION = gql`
  mutation DeleteVoucherCode($id: ID!) {
    deleteVoucherCode(input: { id: $id }) {
      voucherCode {
        id
      }
    }
  }
`;

// Voucher Channel Listing Mutations
export const CREATE_VOUCHER_CHANNEL_LISTING_MUTATION = gql`
  mutation CreateVoucherChannelListing(
    $voucherId: ID!
    $channelId: ID!
    $discountValue: Decimal!
    $currency: String!
    $minSpentAmount: Decimal
  ) {
    createVoucherChannelListing(input: {
      voucherId: $voucherId
      channelId: $channelId
      discountValue: $discountValue
      currency: $currency
      minSpentAmount: $minSpentAmount
    }) {
      listing {
        id
        discountValue
        currency
        minSpentAmount
        channel {
          id
          name
        }
      }
    }
  }
`;

export const UPDATE_VOUCHER_CHANNEL_LISTING_MUTATION = gql`
  mutation UpdateVoucherChannelListing(
    $id: ID!
    $discountValue: Decimal
    $currency: String
    $minSpentAmount: Decimal
  ) {
    updateVoucherChannelListing(input: {
      id: $id
      discountValue: $discountValue
      currency: $currency
      minSpentAmount: $minSpentAmount
    }) {
      listing {
        id
        discountValue
        currency
        minSpentAmount
      }
    }
  }
`;

export const DELETE_VOUCHER_CHANNEL_LISTING_MUTATION = gql`
  mutation DeleteVoucherChannelListing($id: ID!) {
    deleteVoucherChannelListing(input: { id: $id }) {
      listing {
        id
      }
    }
  }
`;

// Promotion Mutations
export const CREATE_PROMOTION_MUTATION = gql`
  mutation CreatePromotion(
    $name: String!
    $type: String!
    $description: JSONString
    $startDate: DateTime
    $endDate: DateTime
  ) {
    createPromotion(input: {
      name: $name
      type: $type
      description: $description
      startDate: $startDate
      endDate: $endDate
    }) {
      promotion {
        id
        name
        type
        startDate
        endDate
      }
    }
  }
`;

export const UPDATE_PROMOTION_MUTATION = gql`
  mutation UpdatePromotion(
    $id: ID!
    $name: String
    $type: String
    $description: JSONString
    $startDate: DateTime
    $endDate: DateTime
  ) {
    updatePromotion(input: {
      id: $id
      name: $name
      type: $type
      description: $description
      startDate: $startDate
      endDate: $endDate
    }) {
      promotion {
        id
        name
        type
        startDate
        endDate
      }
    }
  }
`;

export const DELETE_PROMOTION_MUTATION = gql`
  mutation DeletePromotion($id: ID!) {
    deletePromotion(input: { id: $id }) {
      promotion {
        id
      }
    }
  }
`;

// Promotion Rule Mutations
export const CREATE_PROMOTION_RULE_MUTATION = gql`
  mutation CreatePromotionRule(
    $promotionId: ID!
    $name: String
    $description: JSONString
    $cataloguePredicate: JSONString
    $orderPredicate: JSONString
    $rewardType: String
    $rewardValueType: String
    $rewardValue: Decimal
    $channels: [ID]
    $gifts: [ID]
  ) {
    createPromotionRule(input: {
      promotionId: $promotionId
      name: $name
      description: $description
      cataloguePredicate: $cataloguePredicate
      orderPredicate: $orderPredicate
      rewardType: $rewardType
      rewardValueType: $rewardValueType
      rewardValue: $rewardValue
      channels: $channels
      gifts: $gifts
    }) {
      promotionRule {
        id
        name
        rewardType
        rewardValue
        channels {
          id
          name
        }
      }
    }
  }
`;

export const UPDATE_PROMOTION_RULE_MUTATION = gql`
  mutation UpdatePromotionRule(
    $id: ID!
    $name: String
    $description: JSONString
    $cataloguePredicate: JSONString
    $orderPredicate: JSONString
    $rewardType: String
    $rewardValueType: String
    $rewardValue: Decimal
    $channels: [ID]
    $gifts: [ID]
  ) {
    updatePromotionRule(input: {
      id: $id
      name: $name
      description: $description
      cataloguePredicate: $cataloguePredicate
      orderPredicate: $orderPredicate
      rewardType: $rewardType
      rewardValueType: $rewardValueType
      rewardValue: $rewardValue
      channels: $channels
      gifts: $gifts
    }) {
      promotionRule {
        id
        name
        rewardType
        rewardValue
      }
    }
  }
`;

export const DELETE_PROMOTION_RULE_MUTATION = gql`
  mutation DeletePromotionRule($id: ID!) {
    deletePromotionRule(input: { id: $id }) {
      promotionRule {
        id
      }
    }
  }
`;

// Catalogue Mutations
export const ADD_VOUCHER_CATALOGUES_MUTATION = gql`
  mutation AddVoucherCatalogues($id: ID!, $input: CatalogueInput!) {
    voucherAddCatalogues(input: {
      id: $id
      input: $input
    }) {
      voucher {
        id
        products {
          id
          name
        }
        collections {
          id
          name
        }
        categories {
          id
          name
        }
        variants {
          id
          name
        }
      }
    }
  }
`;

export const REMOVE_VOUCHER_CATALOGUES_MUTATION = gql`
  mutation RemoveVoucherCatalogues($id: ID!, $input: CatalogueInput!) {
    voucherRemoveCatalogues(input: {
      id: $id
      input: $input
    }) {
      voucher {
        id
        products {
          id
          name
        }
        collections {
          id
          name
        }
        categories {
          id
          name
        }
        variants {
          id
          name
        }
      }
    }
  }
`;

export const ADD_PROMOTION_CATALOGUES_MUTATION = gql`
  mutation AddPromotionCatalogues($id: ID!, $input: CatalogueInput!) {
    promotionAddCatalogues(input: {
      id: $id
      input: $input
    }) {
      promotion {
        id
        products {
          id
          name
        }
        collections {
          id
          name
        }
        categories {
          id
          name
        }
        variants {
          id
          name
        }
      }
    }
  }
`;

export const REMOVE_PROMOTION_CATALOGUES_MUTATION = gql`
  mutation RemovePromotionCatalogues($id: ID!, $input: CatalogueInput!) {
    promotionRemoveCatalogues(input: {
      id: $id
      input: $input
    }) {
      promotion {
        id
        products {
          id
          name
        }
        collections {
          id
          name
        }
        categories {
          id
          name
        }
        variants {
          id
          name
        }
      }
    }
  }
`;

// Order Discount Mutations
export const CREATE_ORDER_DISCOUNT_MUTATION = gql`
  mutation CreateOrderDiscount(
    $orderId: ID!
    $valueType: String!
    $value: Decimal!
    $reason: String
    $promotionRuleId: ID
    $voucherId: ID
  ) {
    orderDiscountCreate(input: {
      orderId: $orderId
      valueType: $valueType
      value: $value
      reason: $reason
      promotionRuleId: $promotionRuleId
      voucherId: $voucherId
    }) {
      orderDiscount {
        id
        valueType
        value
        reason
        promotionRule {
          id
        }
        voucher {
          id
        }
      }
    }
  }
`;

export const UPDATE_ORDER_DISCOUNT_MUTATION = gql`
  mutation UpdateOrderDiscount(
    $id: ID!
    $valueType: String
    $value: Decimal
    $reason: String
    $promotionRuleId: ID
    $voucherId: ID
  ) {
    orderDiscountUpdate(input: {
      id: $id
      valueType: $valueType
      value: $value
      reason: $reason
      promotionRuleId: $promotionRuleId
      voucherId: $voucherId
    }) {
      orderDiscount {
        id
        valueType
        value
        reason
      }
    }
  }
`;

export const DELETE_ORDER_DISCOUNT_MUTATION = gql`
  mutation DeleteOrderDiscount($id: ID!) {
    orderDiscountDelete(input: { id: $id }) {
      orderDiscount {
        id
      }
    }
  }
`;

// Order Line Discount Mutations
export const CREATE_ORDER_LINE_DISCOUNT_MUTATION = gql`
  mutation CreateOrderLineDiscount(
    $orderLineId: ID!
    $valueType: String!
    $value: Decimal!
    $reason: String
    $promotionRuleId: ID
    $voucherId: ID
    $uniqueType: String
  ) {
    orderLineDiscountCreate(input: {
      orderLineId: $orderLineId
      valueType: $valueType
      value: $value
      reason: $reason
      promotionRuleId: $promotionRuleId
      voucherId: $voucherId
      uniqueType: $uniqueType
    }) {
      orderLineDiscount {
        id
        valueType
        value
        reason
        uniqueType
      }
    }
  }
`;

export const UPDATE_ORDER_LINE_DISCOUNT_MUTATION = gql`
  mutation UpdateOrderLineDiscount(
    $id: ID!
    $valueType: String
    $value: Decimal
    $reason: String
    $promotionRuleId: ID
    $voucherId: ID
    $uniqueType: String
  ) {
    orderLineDiscountUpdate(input: {
      id: $id
      valueType: $valueType
      value: $value
      reason: $reason
      promotionRuleId: $promotionRuleId
      voucherId: $voucherId
      uniqueType: $uniqueType
    }) {
      orderLineDiscount {
        id
        valueType
        value
        reason
        uniqueType
      }
    }
  }
`;

export const DELETE_ORDER_LINE_DISCOUNT_MUTATION = gql`
  mutation DeleteOrderLineDiscount($id: ID!) {
    orderLineDiscountDelete(input: { id: $id }) {
      orderLineDiscount {
        id
      }
    }
  }
`;

// Checkout Discount Mutations
export const CREATE_CHECKOUT_DISCOUNT_MUTATION = gql`
  mutation CreateCheckoutDiscount(
    $checkoutId: ID!
    $valueType: String!
    $value: Decimal!
    $reason: String
    $promotionRuleId: ID
    $voucherId: ID
  ) {
    checkoutDiscountCreate(input: {
      checkoutId: $checkoutId
      valueType: $valueType
      value: $value
      reason: $reason
      promotionRuleId: $promotionRuleId
      voucherId: $voucherId
    }) {
      checkoutDiscount {
        id
        valueType
        value
        reason
      }
    }
  }
`;

export const UPDATE_CHECKOUT_DISCOUNT_MUTATION = gql`
  mutation UpdateCheckoutDiscount(
    $id: ID!
    $valueType: String
    $value: Decimal
    $reason: String
    $promotionRuleId: ID
    $voucherId: ID
  ) {
    checkoutDiscountUpdate(input: {
      id: $id
      valueType: $valueType
      value: $value
      reason: $reason
      promotionRuleId: $promotionRuleId
      voucherId: $voucherId
    }) {
      checkoutDiscount {
        id
        valueType
        value
        reason
      }
    }
  }
`;

export const DELETE_CHECKOUT_DISCOUNT_MUTATION = gql`
  mutation DeleteCheckoutDiscount($id: ID!) {
    checkoutDiscountDelete(input: { id: $id }) {
      checkoutDiscount {
        id
      }
    }
  }
`;

// Checkout Line Discount Mutations
export const CREATE_CHECKOUT_LINE_DISCOUNT_MUTATION = gql`
  mutation CreateCheckoutLineDiscount(
    $checkoutLineId: ID!
    $valueType: String!
    $value: Decimal!
    $reason: String
    $promotionRuleId: ID
    $voucherId: ID
    $uniqueType: String
  ) {
    checkoutLineDiscountCreate(input: {
      checkoutLineId: $checkoutLineId
      valueType: $valueType
      value: $value
      reason: $reason
      promotionRuleId: $promotionRuleId
      voucherId: $voucherId
      uniqueType: $uniqueType
    }) {
      checkoutLineDiscount {
        id
        valueType
        value
        reason
        uniqueType
      }
    }
  }
`;

export const UPDATE_CHECKOUT_LINE_DISCOUNT_MUTATION = gql`
  mutation UpdateCheckoutLineDiscount(
    $id: ID!
    $valueType: String
    $value: Decimal
    $reason: String
    $promotionRuleId: ID
    $voucherId: ID
    $uniqueType: String
  ) {
    checkoutLineDiscountUpdate(input: {
      id: $id
      valueType: $valueType
      value: $value
      reason: $reason
      promotionRuleId: $promotionRuleId
      voucherId: $voucherId
      uniqueType: $uniqueType
    }) {
      checkoutLineDiscount {
        id
        valueType
        value
        reason
        uniqueType
      }
    }
  }
`;

export const DELETE_CHECKOUT_LINE_DISCOUNT_MUTATION = gql`
  mutation DeleteCheckoutLineDiscount($id: ID!) {
    checkoutLineDiscountDelete(input: { id: $id }) {
      checkoutLineDiscount {
        id
      }
    }
  }
`;

// Input Types
export const CATALOGUE_INPUT = gql`
  input CatalogueInput {
    products: [ID]
    collections: [ID]
    categories: [ID]
    variants: [ID]
  }
`;

export const PROMOTION_RULE_INPUT = gql`
  input PromotionRuleInput {
    name: String
    description: JSONString
    cataloguePredicate: JSONString
    orderPredicate: JSONString
    rewardType: String
    rewardValueType: String
    rewardValue: Decimal
    channels: [ID]
    gifts: [ID]
  }
`;

export const ORDER_DISCOUNT_CREATE_INPUT = gql`
  input OrderDiscountCreateInput {
    orderId: ID!
    valueType: String!
    value: Decimal!
    reason: String
    promotionRuleId: ID
    voucherId: ID
  }
`;

export const ORDER_DISCOUNT_UPDATE_INPUT = gql`
  input OrderDiscountUpdateInput {
    id: ID!
    valueType: String
    value: Decimal
    reason: String
    promotionRuleId: ID
    voucherId: ID
  }
`;

export const ORDER_LINE_DISCOUNT_CREATE_INPUT = gql`
  input OrderLineDiscountCreateInput {
    orderLineId: ID!
    valueType: String!
    value: Decimal!
    reason: String
    promotionRuleId: ID
    voucherId: ID
    uniqueType: String
  }
`;

export const ORDER_LINE_DISCOUNT_UPDATE_INPUT = gql`
  input OrderLineDiscountUpdateInput {
    id: ID!
    valueType: String
    value: Decimal
    reason: String
    promotionRuleId: ID
    voucherId: ID
    uniqueType: String
  }
`;

export const CHECKOUT_DISCOUNT_CREATE_INPUT = gql`
  input CheckoutDiscountCreateInput {
    checkoutId: ID!
    valueType: String!
    value: Decimal!
    reason: String
    promotionRuleId: ID
    voucherId: ID
  }
`;

export const CHECKOUT_DISCOUNT_UPDATE_INPUT = gql`
  input CheckoutDiscountUpdateInput {
    id: ID!
    valueType: String
    value: Decimal
    reason: String
    promotionRuleId: ID
    voucherId: ID
  }
`;

export const CHECKOUT_LINE_DISCOUNT_CREATE_INPUT = gql`
  input CheckoutLineDiscountCreateInput {
    checkoutLineId: ID!
    valueType: String!
    value: Decimal!
    reason: String
    promotionRuleId: ID
    voucherId: ID
    uniqueType: String
  }
`;

export const CHECKOUT_LINE_DISCOUNT_UPDATE_INPUT = gql`
  input CheckoutLineDiscountUpdateInput {
    id: ID!
    valueType: String
    value: Decimal
    reason: String
    promotionRuleId: ID
    voucherId: ID
    uniqueType: String
  }
`;



// Gift Card Mutations
export const CREATE_GIFT_CARD_MUTATION = gql`
  mutation CreateGiftCard(
    $expiryDate: Date!
    $balance: PriceInput!
    $userEmail: String
    $channel: String
    $isActive: Boolean!
    $note: String
    $addTags: [String!]
    $balanceAmount: Decimal!
  ) {
    createGiftCard(input: {
      expiryDate: $expiryDate
      balance: $balance
      userEmail: $userEmail
      channel: $channel
      isActive: $isActive
      note: $note
      addTags: $addTags
      balanceAmount: $balanceAmount
    }) {
      giftCard {
        id
        code
        expiryDate
        currentBalance {
          amount
          currency
        }
        isActive
        tags {
          name
        }
      }
    }
  }
`;

export const UPDATE_GIFT_CARD_MUTATION = gql`
  mutation UpdateGiftCard(
    $id: ID!
    $expiryDate: Date
    $balanceAmount: Float
    $addTags: [String!]
    $removeTags: [String!]
  ) {
    updateGiftCard(input: {
      id: $id
      expiryDate: $expiryDate
      balanceAmount: $balanceAmount
      addTags: $addTags
      removeTags: $removeTags
    }) {
      giftCard {
        id
        expiryDate
        currentBalance {
          amount
          currency
        }
        tags {
          name
        }
      }
    }
  }
`;

export const DELETE_GIFT_CARD_MUTATION = gql`
  mutation DeleteGiftCard($id: ID!) {
    deleteGiftCard(input: { id: $id }) {
      success
    }
  }
`;

export const ACTIVATE_GIFT_CARD_MUTATION = gql`
  mutation ActivateGiftCard($id: ID!) {
    activateGiftCard(input: { id: $id }) {
      giftCard {
        id
        isActive
      }
    }
  }
`;

export const DEACTIVATE_GIFT_CARD_MUTATION = gql`
  mutation DeactivateGiftCard($id: ID!) {
    deactivateGiftCard(input: { id: $id }) {
      giftCard {
        id
        isActive
      }
    }
  }
`;

export const RESEND_GIFT_CARD_MUTATION = gql`
  mutation ResendGiftCard(
    $id: ID!
    $email: String
    $channel: String!
  ) {
    resendGiftCard(input: {
      id: $id
      email: $email
      channel: $channel
    }) {
      giftCard {
        id
      }
    }
  }
`;

export const ADD_GIFT_CARD_NOTE_MUTATION = gql`
  mutation AddGiftCardNote(
    $id: ID!
    $message: String!
  ) {
    addGiftCardNote(input: {
      id: $id
      message: $message
    }) {
      giftCard {
        id
        events {
          id
          type
          message
          date
        }
      }
      event {
        id
        type
        message
        date
      }
    }
  }
`;

// Input Types
export const PRICE_INPUT = gql`
  input PriceInput {
    amount: Decimal!
    currency: String!
  }
`;



// Invoice Mutations
export const INVOICE_REQUEST_MUTATION = gql`
  mutation InvoiceRequest($orderId: ID!, $number: String) {
    invoiceRequest(input: {
      orderId: $orderId
      number: $number
    }) {
      invoice {
        id
        number
        status
        createdAt
        externalUrl
      }
      order {
        id
        status
      }
    }
  }
`;

export const INVOICE_CREATE_MUTATION = gql`
  mutation InvoiceCreate($orderId: ID!, $input: InvoiceCreateInput!) {
    invoiceCreate(input: {
      orderId: $orderId
      input: $input
    }) {
      invoice {
        id
        number
        externalUrl
        status
        createdAt
      }
    }
  }
`;

export const INVOICE_REQUEST_DELETE_MUTATION = gql`
  mutation InvoiceRequestDelete($id: ID!) {
    invoiceRequestDelete(input: { id: $id }) {
      invoice {
        id
        status
      }
    }
  }
`;

export const INVOICE_DELETE_MUTATION = gql`
  mutation InvoiceDelete($id: ID!) {
    invoiceDelete(input: { id: $id }) {
      invoice {
        id
      }
    }
  }
`;

export const INVOICE_UPDATE_MUTATION = gql`
  mutation InvoiceUpdate($id: ID!, $input: UpdateInvoiceInput!) {
    invoiceUpdate(input: {
      id: $id
      input: $input
    }) {
      invoice {
        id
        number
        externalUrl
        status
        updatedAt
      }
    }
  }
`;

export const INVOICE_SEND_NOTIFICATION_MUTATION = gql`
  mutation InvoiceSendNotification($id: ID!) {
    invoiceSendNotification(input: { id: $id }) {
      invoice {
        id
        status
        sentAt
      }
    }
  }
`;

// Input Types
export const INVOICE_CREATE_INPUT = gql`
  input InvoiceCreateInput {
    number: String!
    url: String!
    metadata: [String]
    privateMetadata: [String]
  }
`;

export const UPDATE_INVOICE_INPUT = gql`
  input UpdateInvoiceInput {
    number: String
    url: String
    metadata: [String]
    privateMetadata: [String]
  }
`;




// Discount value type enum
export const DISCOUNT_VALUE_TYPE_ENUM = gql`
  enum DiscountValueTypeEnum {
    fixed
    percentage
  }
`;

// Input types
export const ORDER_LINE_INPUT = gql`
  input OrderLineInput {
    quantity: Int!
  }
`;

export const ORDER_LINE_CREATE_INPUT = gql`
  input OrderLineCreateInput {
    variantId: ID!
    quantity: Int!
    forceNewLine: Boolean = false
    price: Decimal
  }
`;

export const ORDER_DISCOUNT_COMMON_INPUT = gql`
  input OrderDiscountCommonInput {
    valueType: DiscountValueTypeEnum!
    value: Decimal!
    reason: String
  }
`;

export const ADDRESS_INPUT = gql`
  input AddressInput {
    streetAddress1: String!
    streetAddress2: String
    city: String!
    state: String!
    postalCode: String
    country: String!
    isDefault: Boolean = false
    addressType: String!
  }
`;

export const ORDER_FULFILL_STOCK_INPUT = gql`
  input OrderFulfillStockInput {
    quantity: Int!
    warehouse: ID!
  }
`;

export const ORDER_FULFILL_LINE_INPUT = gql`
  input OrderFulfillLineInput {
    orderLineId: ID!
    stocks: [OrderFulfillStockInput!]!
  }
`;

export const ORDER_FULFILL_INPUT = gql`
  input OrderFulfillInput {
    lines: [OrderFulfillLineInput!]!
    notifyCustomer: Boolean = true
  }
`;

export const ORDER_REFUND_LINE_INPUT = gql`
  input OrderRefundLineInput {
    orderLineId: ID!
    quantity: Int!
  }
`;

export const ORDER_REFUND_FULFILLMENT_LINE_INPUT = gql`
  input OrderRefundFulfillmentLineInput {
    fulfillmentLineId: ID!
    quantity: Int!
  }
`;

export const ORDER_REFUND_PRODUCTS_INPUT = gql`
  input OrderRefundProductsInput {
    orderLines: [OrderRefundLineInput!]
    fulfillmentLines: [OrderRefundFulfillmentLineInput!]
    amountToRefund: Decimal
    includeShippingCosts: Boolean = false
  }
`;

export const DRAFT_ORDER_CREATE_INPUT = gql`
  input DraftOrderCreateInput {
    billingAddress: AddressInput
    user: ID
    userEmail: String
    channel: ID!
    shippingAddress: AddressInput
    shippingMethod: ID
    voucher: ID
    customerNote: String
    redirectUrl: String
    lines: [OrderLineCreateInput!]
  }
`;

export const ORDER_UPDATE_SHIPPING_INPUT = gql`
  input OrderUpdateShippingInput {
    shippingMethod: ID
  }
`;

export const ORDER_ADD_NOTE_INPUT = gql`
  input OrderAddNoteInput {
    message: String!
  }
`;

export const ORDER_GRANT_REFUND_CREATE_INPUT = gql`
  input OrderGrantRefundCreateInput {
    amount: Decimal!
    reason: String
  }
`;

export const ORDER_GRANT_REFUND_UPDATE_INPUT = gql`
  input OrderGrantRefundUpdateInput {
    amount: Decimal
    reason: String
  }
`;

export const ORDER_RETURN_LINE_INPUT = gql`
  input OrderReturnLineInput {
    orderLineId: ID!
    quantity: Int!
  }
`;

export const ORDER_RETURN_FULFILLMENT_LINE_INPUT = gql`
  input OrderReturnFulfillmentLineInput {
    fulfillmentLineId: ID!
    quantity: Int!
  }
`;

export const ORDER_RETURN_PRODUCTS_INPUT = gql`
  input OrderReturnProductsInput {
    orderLines: [OrderReturnLineInput!]
    fulfillmentLines: [OrderReturnFulfillmentLineInput!]
    amountToRefund: Decimal
    includeShippingCosts: Boolean = false
    refund: Boolean = false
  }
`;

export const FULFILLMENT_UPDATE_TRACKING_INPUT = gql`
  input FulfillmentUpdateTrackingInput {
    trackingNumber: String!
    notifyCustomer: Boolean = false
  }
`;

export const ORDER_UPDATE_INPUT = gql`
  input OrderUpdateInput {
    email: String
    shippingAddress: AddressInput
    billingAddress: AddressInput
    customerNote: String
  }
`;

// Mutation definitions
export const DRAFT_ORDER_COMPLETE = gql`
  mutation DraftOrderComplete($id: ID!) {
    draftOrderComplete(id: $id) {
      order {
        id
        status
        created
      }
    }
  }
`;

export const DRAFT_ORDER_CREATE = gql`
  mutation DraftOrderCreate($input: DraftOrderCreateInput!) {
    draftOrderCreate(input: $input) {
      order {
        id
        status
        created
      }
    }
  }
`;

export const DRAFT_ORDER_DELETE = gql`
  mutation DraftOrderDelete($id: ID!) {
    draftOrderDelete(id: $id) {
      order {
        id
      }
    }
  }
`;

export const DRAFT_ORDER_UPDATE = gql`
  mutation DraftOrderUpdate($id: ID!, $input: DraftOrderInput!) {
    draftOrderUpdate(id: $id, input: $input) {
      order {
        id
        status
        updatedAt
      }
    }
  }
`;

export const ORDER_ADD_NOTE = gql`
  mutation OrderAddNote($id: ID!, $input: OrderAddNoteInput!) {
    orderAddNote(id: $id, input: $input) {
      order {
        id
      }
    }
  }
`;

export const ORDER_CANCEL = gql`
  mutation OrderCancel($id: ID!) {
    orderCancel(id: $id) {
      order {
        id
        status
      }
    }
  }
`;

export const ORDER_CAPTURE = gql`
  mutation OrderCapture($id: ID!, $amount: Decimal!) {
    orderCapture(id: $id, amount: $amount) {
      order {
        id
        paymentStatus
        totalCaptured {
          amount
        }
      }
    }
  }
`;

export const ORDER_CONFIRM = gql`
  mutation OrderConfirm($id: ID!) {
    orderConfirm(id: $id) {
      order {
        id
        status
      }
    }
  }
`;

export const ORDER_FULFILL = gql`
  mutation OrderFulfill($orderId: ID!, $input: OrderFulfillInput!) {
    orderFulfill(orderId: $orderId, input: $input) {
      fulfillments {
        id
        status
      }
      order {
        id
        status
      }
    }
  }
`;

export const FULFILLMENT_CANCEL = gql`
  mutation FulfillmentCancel($id: ID!) {
    fulfillmentCancel(id: $id) {
      fulfillment {
        id
        status
      }
      order {
        id
        status
      }
    }
  }
`;

export const FULFILLMENT_APPROVE = gql`
  mutation FulfillmentApprove($id: ID!) {
    fulfillmentApprove(id: $id) {
      fulfillment {
        id
        status
      }
      order {
        id
        status
      }
    }
  }
`;

export const FULFILLMENT_UPDATE_TRACKING = gql`
  mutation FulfillmentUpdateTracking($id: ID!, $input: FulfillmentUpdateTrackingInput!) {
    fulfillmentUpdateTracking(id: $id, input: $input) {
      fulfillment {
        id
        trackingNumber
      }
      order {
        id
      }
    }
  }
`;

export const FULFILLMENT_REFUND_PRODUCTS = gql`
  mutation FulfillmentRefundProducts($order: ID!, $input: OrderRefundProductsInput!) {
    fulfillmentRefundProducts(order: $order, input: $input) {
      fulfillment {
        id
        status
      }
      order {
        id
        paymentStatus
      }
    }
  }
`;

export const FULFILLMENT_RETURN_PRODUCTS = gql`
  mutation FulfillmentReturnProducts($order: ID!, $input: OrderReturnProductsInput!) {
    fulfillmentReturnProducts(order: $order, input: $input) {
      returnFulfillment {
        id
        status
      }
      order {
        id
        status
      }
    }
  }
`;

export const ORDER_GRANT_REFUND_CREATE = gql`
  mutation OrderGrantRefundCreate($orderId: ID!, $input: OrderGrantRefundCreateInput!) {
    orderGrantRefundCreate(orderId: $orderId, input: $input) {
      order {
        id
      }
      grantedRefund {
        id
        amount {
          amount
        }
      }
    }
  }
`;

export const ORDER_GRANT_REFUND_UPDATE = gql`
  mutation OrderGrantRefundUpdate($id: ID!, $input: OrderGrantRefundUpdateInput!) {
    orderGrantRefundUpdate(id: $id, input: $input) {
      order {
        id
      }
      grantedRefund {
        id
        amount {
          amount
        }
      }
    }
  }
`;

export const ORDER_LINES_CREATE = gql`
  mutation OrderLinesCreate($id: ID!, $input: [OrderLineCreateInput!]!) {
    orderLinesCreate(id: $id, input: $input) {
      order {
        id
      }
      orderLines {
        id
        quantity
      }
    }
  }
`;

export const ORDER_LINE_DELETE = gql`
  mutation OrderLineDelete($id: ID!) {
    orderLineDelete(id: $id) {
      order {
        id
      }
      orderLine {
        id
      }
    }
  }
`;

export const ORDER_LINE_UPDATE = gql`
  mutation OrderLineUpdate($id: ID!, $input: OrderLineInput!) {
    orderLineUpdate(id: $id, input: $input) {
      order {
        id
      }
      orderLine {
        id
        quantity
      }
    }
  }
`;

export const ORDER_DISCOUNT_ADD = gql`
  mutation OrderDiscountAdd($orderId: ID!, $input: OrderDiscountCommonInput!) {
    orderDiscountAdd(orderId: $orderId, input: $input) {
      order {
        id
        total {
          gross {
            amount
          }
        }
      }
    }
  }
`;

export const ORDER_DISCOUNT_UPDATE = gql`
  mutation OrderDiscountUpdate($discountId: ID!, $input: OrderDiscountCommonInput!) {
    orderDiscountUpdate(discountId: $discountId, input: $input) {
      order {
        id
        total {
          gross {
            amount
          }
        }
      }
    }
  }
`;

export const ORDER_DISCOUNT_DELETE = gql`
  mutation OrderDiscountDelete($discountId: ID!) {
    orderDiscountDelete(discountId: $discountId) {
      order {
        id
        total {
          gross {
            amount
          }
        }
      }
    }
  }
`;

export const ORDER_LINE_DISCOUNT_UPDATE = gql`
  mutation OrderLineDiscountUpdate($orderLineId: ID!, $input: OrderDiscountCommonInput!) {
    orderLineDiscountUpdate(orderLineId: $orderLineId, input: $input) {
      order {
        id
      }
      orderLine {
        id
        unitPrice {
          gross {
            amount
          }
        }
      }
    }
  }
`;

export const ORDER_LINE_DISCOUNT_REMOVE = gql`
  mutation OrderLineDiscountRemove($orderLineId: ID!) {
    orderLineDiscountRemove(orderLineId: $orderLineId) {
      order {
        id
      }
      orderLine {
        id
        unitPrice {
          gross {
            amount
          }
        }
      }
    }
  }
`;

export const ORDER_MARK_AS_PAID = gql`
  mutation OrderMarkAsPaid($id: ID!, $transactionReference: String) {
    orderMarkAsPaid(id: $id, transactionReference: $transactionReference) {
      order {
        id
        paymentStatus
      }
    }
  }
`;

export const ORDER_REFUND = gql`
  mutation OrderRefund($id: ID!, $amount: Decimal!) {
    orderRefund(id: $id, amount: $amount) {
      order {
        id
        paymentStatus
        totalRefunded {
          amount
        }
      }
    }
  }
`;

export const ORDER_UPDATE = gql`
  mutation OrderUpdate($id: ID!, $input: OrderUpdateInput!) {
    orderUpdate(id: $id, input: $input) {
      order {
        id
        userEmail
        customerNote
        shippingAddress {
          id
        }
        billingAddress {
          id
        }
      }
    }
  }
`;

export const ORDER_UPDATE_SHIPPING = gql`
  mutation OrderUpdateShipping($id: ID!, $input: OrderUpdateShippingInput!) {
    orderUpdateShipping(id: $id, input: $input) {
      order {
        id
        shippingMethod {
          id
          name
        }
        shippingPrice {
          gross {
            amount
          }
        }
      }
    }
  }
`;

export const ORDER_VOID = gql`
  mutation OrderVoid($id: ID!) {
    orderVoid(id: $id) {
      order {
        id
        paymentStatus
      }
    }
  }
`;



// Input types
export const MONEY_INPUT = gql`
  input MoneyInput {
    currency: String!
    amount: Decimal!
  }
`;

export const TRANSACTION_EVENT_INPUT = gql`
  input TransactionEventInput {
    status: String
    pspReference: String
    name: String
    message: String
    amount: Decimal
    type: String
  }
`;

export const TRANSACTION_CREATE_INPUT = gql`
  input TransactionCreateInput {
    checkoutId: ID
    orderId: ID
    amountAuthorized: MoneyInput
    amountCharged: MoneyInput
    amountRefunded: MoneyInput
    amountCanceled: MoneyInput
    availableActions: [String!]
    status: String
    pspReference: String
    name: String
    message: String
    metadata: JSONString
    privateMetadata: JSONString
    externalUrl: String
    transactionEvent: TransactionEventInput
  }
`;

export const TRANSACTION_UPDATE_INPUT = gql`
  input TransactionUpdateInput {
    amountAuthorized: MoneyInput
    amountCharged: MoneyInput
    amountRefunded: MoneyInput
    amountCanceled: MoneyInput
    availableActions: [String!]
    status: String
    pspReference: String
    name: String
    message: String
    metadata: JSONString
    privateMetadata: JSONString
    externalUrl: String
    transactionEvent: TransactionEventInput
  }
`;

export const TRANSACTION_REQUEST_ACTION_INPUT = gql`
  input TransactionRequestActionInput {
    transactionId: ID!
    actionType: String!
    amount: Decimal
  }
`;

export const PAYMENT_CAPTURE_INPUT = gql`
  input PaymentCaptureInput {
    paymentId: ID!
    amount: Decimal
  }
`;

export const PAYMENT_REFUND_INPUT = gql`
  input PaymentRefundInput {
    paymentId: ID!
    amount: Decimal
  }
`;

export const PAYMENT_VOID_INPUT = gql`
  input PaymentVoidInput {
    paymentId: ID!
  }
`;

// Mutation definitions
export const TRANSACTION_CREATE = gql`
  mutation TransactionCreate($transactionData: TransactionCreateInput!) {
    transactionCreate(transactionData: $transactionData) {
      transaction {
        id
        status
        authorizedAmount {
          amount
          currency
        }
        chargedAmount {
          amount
          currency
        }
        refundedAmount {
          amount
          currency
        }
        canceledAmount {
          amount
          currency
        }
        pspReference
        events {
          id
          status
          pspReference
          amount {
            amount
            currency
          }
        }
      }
    }
  }
`;

export const TRANSACTION_UPDATE = gql`
  mutation TransactionUpdate($id: ID!, $transactionData: TransactionUpdateInput!) {
    transactionUpdate(id: $id, transactionData: $transactionData) {
      transaction {
        id
        status
        authorizedAmount {
          amount
          currency
        }
        chargedAmount {
          amount
          currency
        }
        refundedAmount {
          amount
          currency
        }
        canceledAmount {
          amount
          currency
        }
        pspReference
        events {
          id
          status
          pspReference
          amount {
            amount
            currency
          }
        }
      }
    }
  }
`;

export const TRANSACTION_REQUEST_ACTION = gql`
  mutation TransactionRequestAction($input: TransactionRequestActionInput!) {
    transactionRequestAction(input: $input) {
      transaction {
        id
        status
        authorizedAmount {
          amount
          currency
        }
        chargedAmount {
          amount
          currency
        }
        refundedAmount {
          amount
          currency
        }
        canceledAmount {
          amount
          currency
        }
        availableActions
      }
    }
  }
`;

export const PAYMENT_CAPTURE = gql`
  mutation PaymentCapture($input: PaymentCaptureInput!) {
    paymentCapture(input: $input) {
      payment {
        id
        chargeStatus
        capturedAmount {
          amount
          currency
        }
        total {
          amount
          currency
        }
      }
    }
  }
`;

export const PAYMENT_REFUND = gql`
  mutation PaymentRefund($input: PaymentRefundInput!) {
    paymentRefund(input: $input) {
      payment {
        id
        chargeStatus
        capturedAmount {
          amount
          currency
        }
        total {
          amount
          currency
        }
      }
    }
  }
`;

export const PAYMENT_VOID = gql`
  mutation PaymentVoid($input: PaymentVoidInput!) {
    paymentVoid(input: $input) {
      payment {
        id
        chargeStatus
        capturedAmount {
          amount
          currency
        }
      }
    }
  }
`;




// Enums
export const PRODUCT_TYPE_KIND_ENUM = gql`
  enum ProductTypeKindEnum {
    NORMAL
    GIFT_CARD
  }
`;

export const PRODUCT_MEDIA_TYPES_ENUM = gql`
  enum ProductMediaTypesEnum {
    IMAGE
    VIDEO
  }
`;

export const PRODUCT_ATTRIBUTE_TYPE_ENUM = gql`
  enum ProductAttributeTypeEnum {
    PRODUCT
    VARIANT
  }
`;

// Input types
export const SEO_INPUT = gql`
  input SeoInput {
    title: String
    description: String
  }
`;

export const MOVE_PRODUCT_INPUT = gql`
  input MoveProductInput {
    productId: ID!
    sortOrder: Int!
  }
`;



export const PRODUCT_ATTRIBUTE_ASSIGN_INPUT = gql`
  input ProductAttributeAssignInput {
    id: ID!
    type: ProductAttributeTypeEnum!
    variantSelection: Boolean
  }
`;

export const PRODUCT_ATTRIBUTE_ASSIGNMENT_UPDATE_INPUT = gql`
  input ProductAttributeAssignmentUpdateInput {
    id: ID!
    variantSelection: Boolean!
  }
`;

export const PRODUCT_MEDIA_UPDATE_INPUT = gql`
  input ProductMediaUpdateInput {
    alt: String
    type: ProductMediaTypesEnum
    product: ID
    url: String
    file: String
  }
`;

export const PRODUCT_MEDIA_CREATE_INPUT = gql`
  input ProductMediaCreateInput {
    alt: String
    type: ProductMediaTypesEnum!
    product: ID!
    url: String
    file: String
  }
`;

export const PRODUCT_MEDIA_REORDER_INPUT = gql`
  input ProductMediaReorderInput {
    id: ID!
    sortOrder: Int!
  }
`;

export const CATEGORY_INPUT = gql`
  input CategoryInput {
    name: String!
    slug: String
    description: JSONString
    descriptionPlaintext: String
    seo: SeoInput
    backgroundImageAlt: String
    metadata: JSONString
    privateMetadata: JSONString
    parentId: ID
  }
`;

export const PRODUCT_INPUT = gql`
  input ProductInput {
    name: String!
    slug: String
    description: JSONString
    descriptionPlaintext: String
    productType: ID!
    category: ID
    weight: Float
    taxClass: ID
    metadata: JSONString
    privateMetadata: JSONString
    seo: SeoInput
  }
`;

export const PRODUCT_VARIANT_INPUT = gql`
  input ProductVariantInput {
    sku: String!
    name: String
    product: ID!
    weight: Float
    trackInventory: Boolean
    preorder: Boolean
    quantityLimitPerCustomer: Int
    metadata: JSONString
    privateMetadata: JSONString
  }
`;

export const COLLECTION_INPUT = gql`
  input CollectionInput {
    name: String!
    slug: String
    description: JSONString
    backgroundImageAlt: String
    seo: SeoInput
    metadata: JSONString
    privateMetadata: JSONString
    products: [ID!]
  }
`;

export const PRODUCT_TYPE_INPUT = gql`
  input ProductTypeInput {
    name: String
    slug: String
    kind: ProductTypeKindEnum
    hasVariants: Boolean
    isShippingRequired: Boolean
    isDigital: Boolean
    weight: Float
    taxClass: ID
  }
`;

export const DIGITAL_CONTENT_INPUT = gql`
  input DigitalContentInput {
    useDefaultSettings: Boolean
    automaticFulfillment: Boolean
    contentType: String
    contentFile: String
    maxDownloads: Int
    urlValidDays: Int
  }
`;

export const PRODUCT_CHANNEL_LISTING_INPUT = gql`
  input ProductChannelListingInput {
    isPublished: Boolean
    publishedAt: DateTime
    visibleInListings: Boolean
    availableForPurchaseAt: DateTime
    price: Decimal
    discountedPrice: Decimal
  }
`;

export const PRODUCT_VARIANT_CHANNEL_LISTING_INPUT = gql`
  input ProductVariantChannelListingInput {
    price: Decimal
    costPrice: Decimal
    preorderQuantityThreshold: Int
  }
`;

export const COLLECTION_CHANNEL_LISTING_INPUT = gql`
  input CollectionChannelListingInput {
    isPublished: Boolean
    publishedAt: DateTime
  }
`;

export const TRANSLATION_INPUT = gql`
  input TranslationInput {
    name: String
    description: JSONString
    seoTitle: String
    seoDescription: String
    languageCode: String!
  }
`;

// Category Mutations
export const CATEGORY_CREATE = gql`
  mutation CategoryCreate($input: CategoryInput!) {
    categoryCreate(input: $input) {
      category {
        id
        name
        slug
        parent {
          id
        }
        seoTitle
        seoDescription
      }
    }
  }
`;

export const CATEGORY_UPDATE = gql`
  mutation CategoryUpdate($id: ID!, $input: CategoryInput!) {
    categoryUpdate(id: $id, input: $input) {
      category {
        id
        name
        slug
        parent {
          id
        }
        seoTitle
        seoDescription
      }
    }
  }
`;

export const CATEGORY_DELETE = gql`
  mutation CategoryDelete($id: ID!) {
    categoryDelete(id: $id) {
      success
    }
  }
`;

// Product Mutations
export const PRODUCT_CREATE = gql`
  mutation ProductCreate($input: ProductInput!) {
    productCreate(input: $input) {
      product {
        id
        name
        slug
        productType {
          id
        }
        category {
          id
        }
        seoTitle
        seoDescription
      }
    }
  }
`;

export const PRODUCT_UPDATE = gql`
  mutation ProductUpdate($id: ID!, $input: ProductInput!) {
    productUpdate(id: $id, input: $input) {
      product {
        id
        name
        slug
        productType {
          id
        }
        category {
          id
        }
        seoTitle
        seoDescription
      }
    }
  }
`;

export const PRODUCT_DELETE = gql`
  mutation ProductDelete($id: ID!) {
    productDelete(id: $id) {
      success
    }
  }
`;

// Product Variant Mutations
export const PRODUCT_VARIANT_CREATE = gql`
  mutation ProductVariantCreate($input: ProductVariantInput!) {
    productVariantCreate(input: $input) {
      variant {
        id
        sku
        name
        product {
          id
        }
      }
    }
  }
`;

export const PRODUCT_VARIANT_UPDATE = gql`
  mutation ProductVariantUpdate($id: ID!, $input: ProductVariantInput!) {
    productVariantUpdate(id: $id, input: $input) {
      variant {
        id
        sku
        name
        product {
          id
        }
      }
    }
  }
`;

export const PRODUCT_VARIANT_DELETE = gql`
  mutation ProductVariantDelete($id: ID!) {
    productVariantDelete(id: $id) {
      success
    }
  }
`;

export const PRODUCT_VARIANT_REORDER = gql`
  mutation ProductVariantReorder($productId: ID!, $moves: [ReorderInput!]!) {
    productVariantReorder(productId: $productId, moves: $moves) {
      product {
        id
        variants {
          id
          sku
        }
      }
    }
  }
`;

// Product Media Mutations
export const PRODUCT_MEDIA_CREATE = gql`
  mutation ProductMediaCreate($input: ProductMediaCreateInput!) {
    productMediaCreate(input: $input) {
      media {
        id
        alt
        type
        product {
          id
        }
      }
    }
  }
`;

export const PRODUCT_MEDIA_UPDATE = gql`
  mutation ProductMediaUpdate($id: ID!, $input: ProductMediaUpdateInput!) {
    productMediaUpdate(id: $id, input: $input) {
      media {
        id
        alt
        type
        product {
          id
        }
      }
    }
  }
`;

export const PRODUCT_MEDIA_DELETE = gql`
  mutation ProductMediaDelete($id: ID!) {
    productMediaDelete(id: $id) {
      success
    }
  }
`;

export const PRODUCT_MEDIA_REORDER = gql`
  mutation ProductMediaReorder($productId: ID!, $mediaIds: [ID!]!) {
    productMediaReorder(productId: $productId, mediaIds: $mediaIds) {
      product {
        id
        media {
          id
          sortOrder
        }
      }
      media {
        id
        sortOrder
      }
    }
  }
`;

// Collection Mutations
export const COLLECTION_CREATE = gql`
  mutation CollectionCreate($input: CollectionInput!) {
    collectionCreate(input: $input) {
      collection {
        id
        name
        slug
        products {
          edges {
            node {
              id
            }
          }
        }
        seoTitle
        seoDescription
      }
    }
  }
`;

export const COLLECTION_UPDATE = gql`
  mutation CollectionUpdate($id: ID!, $input: CollectionInput!) {
    collectionUpdate(id: $id, input: $input) {
      collection {
        id
        name
        slug
        products {
          edges {
            node {
              id
            }
          }
        }
        seoTitle
        seoDescription
      }
    }
  }
`;

export const COLLECTION_DELETE = gql`
  mutation CollectionDelete($id: ID!) {
    collectionDelete(id: $id) {
      success
    }
  }
`;

export const COLLECTION_ADD_PRODUCTS = gql`
  mutation CollectionAddProducts($collectionId: ID!, $products: [ID!]!) {
    collectionAddProducts(collectionId: $collectionId, products: $products) {
      collection {
        id
        products {
          edges {
            node {
              id
            }
          }
        }
      }
    }
  }
`;

export const COLLECTION_REMOVE_PRODUCTS = gql`
  mutation CollectionRemoveProducts($collectionId: ID!, $products: [ID!]!) {
    collectionRemoveProducts(collectionId: $collectionId, products: $products) {
      collection {
        id
        products {
          edges {
            node {
              id
            }
          }
        }
      }
    }
  }
`;

export const COLLECTION_REORDER_PRODUCTS = gql`
  mutation CollectionReorderProducts($collectionId: ID!, $moves: [MoveProductInput!]!) {
    collectionReorderProducts(collectionId: $collectionId, moves: $moves) {
      collection {
        id
        products {
          edges {
            node {
              id
              sortOrder
            }
          }
        }
      }
    }
  }
`;

// Product Type Mutations
export const PRODUCT_TYPE_CREATE = gql`
  mutation ProductTypeCreate($input: ProductTypeInput!) {
    productTypeCreate(input: $input) {
      productType {
        id
        name
        slug
        kind
        hasVariants
        isShippingRequired
      }
    }
  }
`;

export const PRODUCT_TYPE_UPDATE = gql`
  mutation ProductTypeUpdate($id: ID!, $input: ProductTypeInput!) {
    productTypeUpdate(id: $id, input: $input) {
      productType {
        id
        name
        slug
        kind
        hasVariants
        isShippingRequired
      }
    }
  }
`;

export const PRODUCT_TYPE_DELETE = gql`
  mutation ProductTypeDelete($id: ID!) {
    productTypeDelete(id: $id) {
      success
    }
  }
`;

// Variant Media Mutations
export const VARIANT_MEDIA_ASSIGN = gql`
  mutation VariantMediaAssign($mediaId: ID!, $variantId: ID!) {
    variantMediaAssign(mediaId: $mediaId, variantId: $variantId) {
      productVariant {
        id
        media {
          id
        }
      }
      media {
        id
      }
    }
  }
`;

export const VARIANT_MEDIA_UNASSIGN = gql`
  mutation VariantMediaUnassign($mediaId: ID!, $variantId: ID!) {
    variantMediaUnassign(mediaId: $mediaId, variantId: $variantId) {
      productVariant {
        id
        media {
          id
        }
      }
      media {
        id
      }
    }
  }
`;

// Digital Content Mutations
export const DIGITAL_CONTENT_CREATE = gql`
  mutation DigitalContentCreate($variantId: ID!, $input: DigitalContentInput!) {
    digitalContentCreate(variantId: $variantId, input: $input) {
      content {
        id
        useDefaultSettings
        automaticFulfillment
        maxDownloads
        urlValidDays
      }
    }
  }
`;

export const DIGITAL_CONTENT_UPDATE = gql`
  mutation DigitalContentUpdate($id: ID!, $input: DigitalContentInput!) {
    digitalContentUpdate(id: $id, input: $input) {
      content {
        id
        useDefaultSettings
        automaticFulfillment
        maxDownloads
        urlValidDays
      }
    }
  }
`;

export const DIGITAL_CONTENT_DELETE = gql`
  mutation DigitalContentDelete($id: ID!) {
    digitalContentDelete(id: $id) {
      success
    }
  }
`;

export const DIGITAL_CONTENT_URL_CREATE = gql`
  mutation DigitalContentUrlCreate($contentId: ID!) {
    digitalContentUrlCreate(contentId: $contentId) {
      url {
        id
        token
        downloadNum
        created
      }
    }
  }
`;

// Channel Listing Mutations
export const PRODUCT_CHANNEL_LISTING_UPDATE = gql`
  mutation ProductChannelListingUpdate($id: ID!, $input: ProductChannelListingInput!) {
    productChannelListingUpdate(id: $id, input: $input) {
      listing {
        id
        isPublished
        publishedAt
        visibleInListings
        availableForPurchaseAt
        discountedPrice {
          amount
          currency
        }
      }
    }
  }
`;

export const PRODUCT_VARIANT_CHANNEL_LISTING_UPDATE = gql`
  mutation ProductVariantChannelListingUpdate($id: ID!, $input: ProductVariantChannelListingInput!) {
    productVariantChannelListingUpdate(id: $id, input: $input) {
      listing {
        id
        price {
          amount
          currency
        }
        costPrice {
          amount
          currency
        }
      }
    }
  }
`;

export const COLLECTION_CHANNEL_LISTING_UPDATE = gql`
  mutation CollectionChannelListingUpdate($id: ID!, $input: CollectionChannelListingInput!) {
    collectionChannelListingUpdate(id: $id, input: $input) {
      listing {
        id
        isPublished
        publishedAt
      }
    }
  }
`;

// Translation Mutations
export const PRODUCT_TRANSLATE = gql`
  mutation ProductTranslate($id: ID!, $input: TranslationInput!) {
    productTranslate(id: $id, input: $input) {
      product {
        id
        translation(languageCode: $input.languageCode) {
          name
          description
          seoTitle
          seoDescription
        }
      }
    }
  }
`;

// Special Variant Operations
export const PRODUCT_VARIANT_SET_DEFAULT = gql`
  mutation ProductVariantSetDefault($productId: ID!, $variantId: ID!) {
    productVariantSetDefault(productId: $productId, variantId: $variantId) {
      product {
        id
        defaultVariant {
          id
        }
      }
    }
  }
`;

export const PRODUCT_VARIANT_PREORDER_DEACTIVATE = gql`
  mutation ProductVariantPreorderDeactivate($id: ID!) {
    productVariantPreorderDeactivate(id: $id) {
      variant {
        id
        isPreorder
        preorderEndDate
      }
    }
  }
`;




// Input types
export const SHIPPING_METHOD_CHANNEL_LISTING_INPUT = gql`
  input ShippingMethodChannelListingInput {
    channelId: ID!
    priceAmount: Decimal!
    minimumOrderPriceAmount: Decimal
    maximumOrderPriceAmount: Decimal
    currency: String!
    isActive: Boolean = true
  }
`;

export const SHIPPING_METHOD_CHANNEL_LISTING_UPDATE_INPUT = gql`
  input ShippingMethodChannelListingUpdateInput {
    id: ID!
    addChannels: [ShippingMethodChannelListingInput!]
    removeChannels: [ID!]
  }
`;

export const SHIPPING_ZONE_INPUT = gql`
  input ShippingZoneInput {
    name: String!
    countries: [String!]
    default: Boolean
    description: String
    addChannels: [ID!]
    removeChannels: [ID!]
    addWarehouses: [ID!]
    removeWarehouses: [ID!]
  }
`;

export const SHIPPING_METHOD_POSTAL_CODE_RULE_INPUT = gql`
  input ShippingMethodPostalCodeRuleInput {
    shippingMethodId: ID!
    start: String!
    end: String
    inclusionType: String!
  }
`;

export const SHIPPING_METHOD_INPUT = gql`
  input ShippingMethodInput {
    name: String!
    type: String!
    shippingZoneId: ID!
    minimumOrderWeight: Float
    maximumOrderWeight: Float
    taxClassId: ID
    excludedProducts: [ID!]
  }
`;

export const SHIPPING_METHOD_UPDATE_INPUT = gql`
  input ShippingMethodUpdateInput {
    id: ID!
    name: String
    type: String
    minimumOrderWeight: Float
    maximumOrderWeight: Float
    taxClassId: ID
    addExcludedProducts: [ID!]
    removeExcludedProducts: [ID!]
  }
`;

// Shipping Method Channel Listing Mutations
export const SHIPPING_METHOD_CHANNEL_LISTING_UPDATE = gql`
  mutation ShippingMethodChannelListingUpdate($input: ShippingMethodChannelListingUpdateInput!) {
    shippingMethodChannelListingUpdate(input: $input) {
      shippingMethod {
        id
        name
        channelListings {
          id
          channel {
            id
            name
          }
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
        }
      }
    }
  }
`;

// Shipping Zone Mutations
export const SHIPPING_ZONE_CREATE = gql`
  mutation ShippingZoneCreate($input: ShippingZoneInput!) {
    shippingZoneCreate(input: $input) {
      shippingZone {
        id
        name
        description
        countries
        default
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
  }
`;

export const SHIPPING_ZONE_UPDATE = gql`
  mutation ShippingZoneUpdate($input: ShippingZoneUpdateInput!) {
    shippingZoneUpdate(input: $input) {
      shippingZone {
        id
        name
        description
        countries
        default
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
  }
`;

export const SHIPPING_ZONE_DELETE = gql`
  mutation ShippingZoneDelete($input: ShippingZoneDeleteInput!) {
    shippingZoneDelete(input: $input) {
      shippingZone {
        id
        name
      }
    }
  }
`;

// Shipping Method Postal Code Rule Mutations
export const SHIPPING_METHOD_POSTAL_CODE_RULE_CREATE = gql`
  mutation ShippingMethodPostalCodeRuleCreate($input: ShippingMethodPostalCodeRuleInput!) {
    shippingMethodPostalCodeRuleCreate(input: $input) {
      postalCodeRule {
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
  }
`;

export const SHIPPING_METHOD_POSTAL_CODE_RULE_UPDATE = gql`
  mutation ShippingMethodPostalCodeRuleUpdate($input: ShippingMethodPostalCodeRuleUpdateInput!) {
    shippingMethodPostalCodeRuleUpdate(input: $input) {
      postalCodeRule {
        id
        start
        end
        inclusionType
      }
    }
  }
`;

export const SHIPPING_METHOD_POSTAL_CODE_RULE_DELETE = gql`
  mutation ShippingMethodPostalCodeRuleDelete($input: ShippingMethodPostalCodeRuleDeleteInput!) {
    shippingMethodPostalCodeRuleDelete(input: $input) {
      postalCodeRule {
        id
      }
    }
  }
`;

// Shipping Method Mutations
export const SHIPPING_METHOD_CREATE = gql`
  mutation ShippingMethodCreate($input: ShippingMethodInput!) {
    shippingMethodCreate(input: $input) {
      shippingMethod {
        id
        name
        type
        minimumOrderWeight
        maximumOrderWeight
        shippingZone {
          id
          name
        }
        taxClass {
          id
          name
        }
        excludedProducts {
          id
          name
        }
      }
    }
  }
`;

export const SHIPPING_METHOD_UPDATE = gql`
  mutation ShippingMethodUpdate($input: ShippingMethodUpdateInput!) {
    shippingMethodUpdate(input: $input) {
      shippingMethod {
        id
        name
        type
        minimumOrderWeight
        maximumOrderWeight
        taxClass {
          id
          name
        }
        excludedProducts {
          id
          name
        }
      }
    }
  }
`;

export const SHIPPING_METHOD_DELETE = gql`
  mutation ShippingMethodDelete($input: ShippingMethodDeleteInput!) {
    shippingMethodDelete(input: $input) {
      shippingMethod {
        id
        name
      }
    }
  }
`;


// Input types
export const COUNTRY_RATE_INPUT = gql`
  input CountryRateInput {
    countryCode: CountryCodeEnum!
    rate: Float!
  }
`;

export const TAX_CLASS_CREATE_INPUT = gql`
  input TaxClassCreateInput {
    name: String!
    createCountryRates: [CountryRateInput!]
  }
`;

export const COUNTRY_RATE_UPDATE_INPUT = gql`
  input CountryRateUpdateInput {
    countryCode: CountryCodeEnum!
    rate: Float
  }
`;

export const TAX_CLASS_UPDATE_INPUT = gql`
  input TaxClassUpdateInput {
    name: String
    updateCountryRates: [CountryRateUpdateInput!]
    removeCountryRates: [CountryCodeEnum!]
  }
`;

export const TAX_CONFIGURATION_PER_COUNTRY_INPUT = gql`
  input TaxConfigurationPerCountryInput {
    countryCode: CountryCodeEnum!
    chargeTaxes: Boolean!
    taxCalculationStrategy: TaxCalculationStrategy
    displayGrossPrices: Boolean!
  }
`;

export const TAX_CONFIGURATION_UPDATE_INPUT = gql`
  input TaxConfigurationUpdateInput {
    chargeTaxes: Boolean
    taxCalculationStrategy: TaxCalculationStrategy
    displayGrossPrices: Boolean
    pricesEnteredWithTax: Boolean
    updateCountriesConfiguration: [TaxConfigurationPerCountryInput!]
    removeCountriesConfiguration: [CountryCodeEnum!]
  }
`;

export const TAX_CLASS_RATE_INPUT = gql`
  input TaxClassRateInput {
    taxClassId: ID
    rate: Float
  }
`;

// Tax Class Mutations
export const TAX_CLASS_CREATE = gql`
  mutation TaxClassCreate($input: TaxClassCreateInput!) {
    taxClassCreate(input: $input) {
      taxClass {
        id
        name
        countries {
          countryCode
          rate
        }
      }
    }
  }
`;

export const TAX_CLASS_UPDATE = gql`
  mutation TaxClassUpdate($id: ID!, $input: TaxClassUpdateInput!) {
    taxClassUpdate(id: $id, input: $input) {
      taxClass {
        id
        name
        countries {
          countryCode
          rate
        }
      }
    }
  }
`;

export const TAX_CLASS_DELETE = gql`
  mutation TaxClassDelete($id: ID!) {
    taxClassDelete(id: $id) {
      success
    }
  }
`;

// Tax Configuration Mutations
export const TAX_CONFIGURATION_UPDATE = gql`
  mutation TaxConfigurationUpdate($id: ID!, $input: TaxConfigurationUpdateInput!) {
    taxConfigurationUpdate(id: $id, input: $input) {
      taxConfiguration {
        id
        chargeTaxes
        taxCalculationStrategy
        displayGrossPrices
        pricesEnteredWithTax
        countries {
          countryCode
          chargeTaxes
          taxCalculationStrategy
          displayGrossPrices
        }
      }
    }
  }
`;

export const TAX_COUNTRY_CONFIGURATION_UPDATE = gql`
  mutation TaxCountryConfigurationUpdate(
    $countryCode: CountryCodeEnum!
    $updateTaxClassRates: [TaxClassRateInput!]!
  ) {
    taxCountryConfigurationUpdate(
      countryCode: $countryCode
      updateTaxClassRates: $updateTaxClassRates
    ) {
      taxCountryConfiguration {
        countryCode
        taxClassRates {
          taxClass {
            id
            name
          }
          rate
        }
      }
    }
  }
`;

export const TAX_COUNTRY_CONFIGURATION_DELETE = gql`
  mutation TaxCountryConfigurationDelete($countryCode: CountryCodeEnum!) {
    taxCountryConfigurationDelete(countryCode: $countryCode) {
      taxCountryConfiguration {
        countryCode
        taxClassRates {
          taxClass {
            id
            name
          }
          rate
        }
      }
    }
  }
`;




export const CREATE_ALLOCATION = gql`
  mutation CreateAllocation($input: AllocationInput!) {
    createAllocation(input: $input) {
      allocation {
        id
        orderLine {
          id
        }
        stock {
          id
        }
        quantityAllocated
      }
    }
  }
`;

export const UPDATE_ALLOCATION = gql`
  mutation UpdateAllocation($id: ID!, $quantityAllocated: Int!) {
    updateAllocation(id: $id, quantityAllocated: $quantityAllocated) {
      allocation {
        id
        quantityAllocated
      }
    }
  }
`;

export const DELETE_ALLOCATION = gql`
  mutation DeleteAllocation($id: ID!) {
    deleteAllocation(id: $id) {
      success
    }
  }
`;

export const CREATE_PREORDER_ALLOCATION = gql`
  mutation CreatePreorderAllocation($input: PreorderAllocationInput!) {
    createPreorderAllocation(input: $input) {
      preorderAllocation {
        id
        orderLine {
          id
        }
        productVariantChannelListing {
          id
        }
        quantity
      }
    }
  }
`;

export const UPDATE_PREORDER_ALLOCATION = gql`
  mutation UpdatePreorderAllocation($id: ID!, $quantity: Int!) {
    updatePreorderAllocation(id: $id, quantity: $quantity) {
      preorderAllocation {
        id
        quantity
      }
    }
  }
`;

export const DELETE_PREORDER_ALLOCATION = gql`
  mutation DeletePreorderAllocation($id: ID!) {
    deletePreorderAllocation(id: $id) {
      success
    }
  }
`;

export const CREATE_RESERVATION = gql`
  mutation CreateReservation($input: ReservationInput!) {
    createReservation(input: $input) {
      reservation {
        id
        checkoutLine {
          id
        }
        stock {
          id
        }
        quantityReserved
        reservedUntil
      }
    }
  }
`;

export const UPDATE_RESERVATION = gql`
  mutation UpdateReservation(
    $id: ID!
    $quantityReserved: Int
    $reservedUntil: DateTime
  ) {
    updateReservation(
      id: $id
      quantityReserved: $quantityReserved
      reservedUntil: $reservedUntil
    ) {
      reservation {
        id
        quantityReserved
        reservedUntil
      }
    }
  }
`;

export const DELETE_RESERVATION = gql`
  mutation DeleteReservation($id: ID!) {
    deleteReservation(id: $id) {
      success
    }
  }
`;

export const CREATE_PREORDER_RESERVATION = gql`
  mutation CreatePreorderReservation($input: PreorderReservationInput!) {
    createPreorderReservation(input: $input) {
      preorderReservation {
        id
        checkoutLine {
          id
        }
        productVariantChannelListing {
          id
        }
        quantityReserved
        reservedUntil
      }
    }
  }
`;

export const UPDATE_PREORDER_RESERVATION = gql`
  mutation UpdatePreorderReservation(
    $id: ID!
    $quantityReserved: Int
    $reservedUntil: DateTime
  ) {
    updatePreorderReservation(
      id: $id
      quantityReserved: $quantityReserved
      reservedUntil: $reservedUntil
    ) {
      preorderReservation {
        id
        quantityReserved
        reservedUntil
      }
    }
  }
`;

export const DELETE_PREORDER_RESERVATION = gql`
  mutation DeletePreorderReservation($id: ID!) {
    deletePreorderReservation(id: $id) {
      success
    }
  }
`;

export const CREATE_CHANNEL_WAREHOUSE = gql`
  mutation CreateChannelWarehouse($input: ChannelWarehouseInput!) {
    createChannelWarehouse(input: $input) {
      channelWarehouse {
        id
        channel {
          id
        }
        warehouse {
          id
        }
        sortOrder
      }
    }
  }
`;

export const UPDATE_CHANNEL_WAREHOUSE = gql`
  mutation UpdateChannelWarehouse($id: ID!, $sortOrder: Int!) {
    updateChannelWarehouse(id: $id, sortOrder: $sortOrder) {
      channelWarehouse {
        id
        sortOrder
      }
    }
  }
`;

export const DELETE_CHANNEL_WAREHOUSE = gql`
  mutation DeleteChannelWarehouse($id: ID!) {
    deleteChannelWarehouse(id: $id) {
      success
    }
  }
`;