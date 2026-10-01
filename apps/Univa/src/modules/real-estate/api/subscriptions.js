// apps\Univa\graphql\queries\realestateQueries\subscriptions.js
import { gql } from '@apollo/client';

// ----------------------------------------------------------------------
// 🏠 LISTING SUBSCRIPTIONS
// ----------------------------------------------------------------------

export const ON_LISTING_CREATED = gql`
  subscription OnListingCreated($agentId: ID, $locationPreferenceId: ID) {
    onListingCreated(agentId: $agentId, locationPreferenceId: $locationPreferenceId) {
      listing {
        id
        title
        description
        price
        status
        propertyType
        bedrooms
        bathrooms
        squareFootage
        location
        coordinates
        createdAt
        updatedAt
        agent {
          id
          firstName
          lastName
          email
        }
        owner {
          id
          firstName
          lastName
          email
        }
        images {
          id
          imageUrl
          caption
          isPrimary
        }
      }
    }
  }
`;

export const ON_LISTING_UPDATED = gql`
  subscription OnListingUpdated($listingId: ID!) {
    onListingUpdated(listingId: $listingId) {
      listing {
        id
        title
        description
        price
        status
        propertyType
        bedrooms
        bathrooms
        squareFootage
        location
        coordinates
        updatedAt
      }
      updatedFields
      updatedBy {
        id
        firstName
        lastName
        email
      }
    }
  }
`;

export const ON_LISTING_STATUS_CHANGED = gql`
  subscription OnListingStatusChanged($listingId: ID!) {
    onListingStatusChanged(listingId: $listingId) {
      listing {
        id
        title
        status
        price
        agent {
          id
          firstName
          lastName
        }
        owner {
          id
          firstName
          lastName
        }
      }
      oldStatus
      newStatus
      changedAt
    }
  }
`;

export const ON_LISTING_PRICE_CHANGED = gql`
  subscription OnListingPriceChanged($listingId: ID!) {
    onListingPriceChanged(listingId: $listingId) {
      listing {
        id
        title
        price
        status
        previousPrice
      }
      oldPrice
      newPrice
      priceDifference
      changedAt
    }
  }
`;

// ----------------------------------------------------------------------
// 🔍 SEARCH & PREFERENCE SUBSCRIPTIONS
// ----------------------------------------------------------------------

export const ON_PROPERTY_SUBSCRIPTION_MATCH = gql`
  subscription OnPropertySubscriptionMatch($subscriptionId: ID!) {
    onPropertySubscriptionMatch(subscriptionId: $subscriptionId) {
      subscription {
        id
        name
        filters
        isActive
        createdAt
      }
      matchingListings {
        id
        title
        price
        propertyType
        bedrooms
        bathrooms
        location
        images {
          id
          imageUrl
          isPrimary
        }
      }
      matchCount
      matchedAt
    }
  }
`;

export const ON_SAVED_SEARCH_UPDATED = gql`
  subscription OnSavedSearchUpdated($savedSearchId: ID!) {
    onSavedSearchUpdated(savedSearchId: $savedSearchId) {
      savedSearch {
        id
        name
        searchCriteria
        lastRunAt
        resultCount
      }
      newResultsCount
      updatedAt
    }
  }
`;

// ----------------------------------------------------------------------
// 🎥 VIRTUAL & LIVE TOUR SUBSCRIPTIONS
// ----------------------------------------------------------------------

export const ON_VIRTUAL_TOUR_CREATED = gql`
  subscription OnVirtualTourCreated($listingId: ID!) {
    onVirtualTourCreated(listingId: $listingId) {
      virtualTour {
        id
        title
        description
        tourUrl
        thumbnailUrl
        duration
        isInteractive
        createdAt
        listing {
          id
          title
          price
        }
      }
    }
  }
`;

export const ON_LIVE_TOUR_SCHEDULED = gql`
  subscription OnLiveTourScheduled($listingId: ID!) {
    onLiveTourScheduled(listingId: $listingId) {
      liveTour {
        id
        title
        description
        scheduledAt
        duration
        maxAttendees
        currentAttendees
        meetingLink
        status
        agent {
          id
          firstName
          lastName
        }
        listing {
          id
          title
          price
        }
      }
    }
  }
`;

export const ON_LIVE_TOUR_REGISTRATION = gql`
  subscription OnLiveTourRegistration($tourId: ID!) {
    onLiveTourRegistration(tourId: $tourId) {
      registration {
        id
        user {
          id
          firstName
          lastName
          email
        }
        registeredAt
        status
      }
      remainingSpots
    }
  }
`;

// ----------------------------------------------------------------------
// 📄 DOCUMENT & TRANSACTION SUBSCRIPTIONS
// ----------------------------------------------------------------------

export const ON_DOCUMENT_PACKAGE_CREATED = gql`
  subscription OnDocumentPackageCreated($transactionId: ID!) {
    onDocumentPackageCreated(transactionId: $transactionId) {
      documentPackage {
        id
        name
        description
        status
        createdAt
        createdBy {
          id
          firstName
          lastName
        }
        transaction {
          id
          property {
            id
            title
          }
        }
        documents {
          id
          name
          type
          status
        }
      }
    }
  }
`;

export const ON_DOCUMENT_SIGNED = gql`
  subscription OnDocumentSigned($documentId: ID!) {
    onDocumentSigned(documentId: $documentId) {
      documentSignature {
        id
        signedAt
        signatureData
        user {
          id
          firstName
          lastName
          email
        }
      }
      document {
        id
        name
        type
        status
        signedAt
        allSignaturesComplete
      }
    }
  }
`;



// ----------------------------------------------------------------------
// 📊 MARKET ANALYTICS SUBSCRIPTIONS
// ----------------------------------------------------------------------

export const ON_MARKET_TREND_UPDATED = gql`
  subscription OnMarketTrendUpdated($neighborhoodId: ID) {
    onMarketTrendUpdated(neighborhoodId: $neighborhoodId) {
      marketTrend {
        id
        type
        value
        changePercentage
        period
        dataPoints
        updatedAt
      }
      neighborhood {
        id
        name
        averagePrice
        priceTrend
        inventoryCount
      }
    }
  }
`;

export const ON_PROPERTY_VALUATION_UPDATED = gql`
  subscription OnPropertyValuationUpdated($listingId: ID!) {
    onPropertyValuationUpdated(listingId: $listingId) {
      listing {
        id
        title
        price
        estimatedValue
        valuationHistory {
          date
          value
          confidence
        }
      }
      valuation
      confidenceScore
      updatedAt
    }
  }
`;

// ----------------------------------------------------------------------
// 🤖 AI & RECOMMENDATION SUBSCRIPTIONS
// ----------------------------------------------------------------------

export const ON_PROPERTY_RECOMMENDATION = gql`
  subscription OnPropertyRecommendation($clientId: ID!) {
    onPropertyRecommendation(clientId: $clientId) {
      client {
        id
        firstName
        lastName
        email
        preferences {
          propertyTypes
          locations
          budgetRange
          bedrooms
          bathrooms
        }
      }
      recommendedListings {
        id
        title
        price
        propertyType
        bedrooms
        bathrooms
        location
        matchScore
        images {
          id
          imageUrl
          isPrimary
        }
      }
      recommendationScore
      generatedAt
    }
  }
`;

export const ON_AR_MODEL_CREATED = gql`
  subscription OnARModelCreated($listingId: ID!) {
    onARModelCreated(listingId: $listingId) {
      arModel {
        id
        name
        modelUrl
        thumbnailUrl
        fileSize
        format
        isInteractive
        createdAt
        listing {
          id
          title
        }
      }
    }
  }
`;
