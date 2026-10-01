import { useMutation } from '@apollo/client/react';
import {
  UPDATE_CLIENT_LOCATION,
  UPDATE_AGENT_LOCATION,
  CREATE_LISTING_TYPE,
  ADD_LISTING_IMAGE,
  ADD_LISTING_FILE,
  CREATE_LISTING,
  UPDATE_LISTING,
  DELETE_LISTING,
  NEARBY_PROPERTIES,
  CREATE_PROPERTY_SUBSCRIPTION,
  UPDATE_PROPERTY_SUBSCRIPTION,
  DELETE_PROPERTY_SUBSCRIPTION,
  CREATE_VIRTUAL_TOUR,
  SCHEDULE_LIVE_TOUR,
  REGISTER_FOR_LIVE_TOUR,
} from "@/modules/real-estate/api/mutations";

export const useRealEstateMutations = () => {
  // Location updates
  const [updateClientLocation, { loading: updatingClientLocation }] = useMutation(UPDATE_CLIENT_LOCATION);
  const [updateAgentLocation, { loading: updatingAgentLocation }] = useMutation(UPDATE_AGENT_LOCATION);

  // Listing types
  const [createListingType, { loading: creatingListingType }] = useMutation(CREATE_LISTING_TYPE);

  // Listing operations
  const [createListing, { loading: creatingListing }] = useMutation(CREATE_LISTING);
  const [updateListing, { loading: updatingListing }] = useMutation(UPDATE_LISTING);
  const [deleteListing, { loading: deletingListing }] = useMutation(DELETE_LISTING);

  // Media operations
  const [addListingImage, { loading: addingImage }] = useMutation(ADD_LISTING_IMAGE);
  const [addListingFile, { loading: addingFile }] = useMutation(ADD_LISTING_FILE);

  // Search and location-based
  const [getNearbyProperties, { loading: loadingNearby }] = useMutation(NEARBY_PROPERTIES);

  // Virtual Tours
  const [createVirtualTour, { loading: creatingTour }] = useMutation(CREATE_VIRTUAL_TOUR);
  const [scheduleLiveTour, { loading: schedulingTour }] = useMutation(SCHEDULE_LIVE_TOUR);
  const [registerForLiveTour, { loading: registeringTour }] = useMutation(REGISTER_FOR_LIVE_TOUR);

  // Property Subscriptions
  const [createPropertySubscription, { loading: creatingSubscription }] = useMutation(CREATE_PROPERTY_SUBSCRIPTION);
  const [updatePropertySubscription, { loading: updatingSubscription }] = useMutation(UPDATE_PROPERTY_SUBSCRIPTION);
  const [deletePropertySubscription, { loading: deletingSubscription }] = useMutation(DELETE_PROPERTY_SUBSCRIPTION);

  return {
    // Location updates
    updateClientLocation: async (locationData) => {
      try {
        const result = await updateClientLocation({ variables: locationData });
        return result.data.updateClientLocation;
      } catch (error) {
        console.error('Error updating client location:', error);
        throw error;
      }
    },
    
    updateAgentLocation: async (locationData) => {
      try {
        const result = await updateAgentLocation({ variables: locationData });
        return result.data.updateAgentLocation;
      } catch (error) {
        console.error('Error updating agent location:', error);
        throw error;
      }
    },

    // Listing types
    createListingType: async (propertyType) => {
      try {
        const result = await createListingType({ variables: { propertyType } });
        return result.data.createListingType;
      } catch (error) {
        console.error('Error creating listing type:', error);
        throw error;
      }
    },

    // Listing operations
    createListing: async (listingData) => {
      try {
        const result = await createListing({ variables: listingData });
        return result.data.createListing;
      } catch (error) {
        console.error('Error creating listing:', error);
        throw error;
      }
    },
    
    updateListing: async (listingData) => {
      try {
        const result = await updateListing({ variables: listingData });
        return result.data.updateListing;
      } catch (error) {
        console.error('Error updating listing:', error);
        throw error;
      }
    },
    
    deleteListing: async (id) => {
      try {
        const result = await deleteListing({ variables: { id } });
        return result.data.deleteListing;
      } catch (error) {
        console.error('Error deleting listing:', error);
        throw error;
      }
    },

    // Media operations
    addListingImage: async (imageData) => {
      try {
        const result = await addListingImage({ variables: imageData });
        return result.data.addListingImage;
      } catch (error) {
        console.error('Error adding listing image:', error);
        throw error;
      }
    },

    addListingFile: async (fileData) => {
      try {
        const result = await addListingFile({ variables: fileData });
        return result.data.addListingFile;
      } catch (error) {
        console.error('Error adding listing file:', error);
        throw error;
      }
    },

    // Location-based search
    getNearbyProperties: async (searchData) => {
      try {
        const result = await getNearbyProperties({ variables: searchData });
        return result.data.nearbyProperties;
      } catch (error) {
        console.error('Error getting nearby properties:', error);
        throw error;
      }
    },

    // Tour operations
    createVirtualTour: async (tourData) => {
      try {
        const result = await createVirtualTour({ variables: { input: tourData } });
        return result.data.createVirtualTour;
      } catch (error) {
        console.error('Error creating virtual tour:', error);
        throw error;
      }
    },

    scheduleLiveTour: async (tourData) => {
      try {
        const result = await scheduleLiveTour({ variables: { input: tourData } });
        return result.data.scheduleLiveTour;
      } catch (error) {
        console.error('Error scheduling live tour:', error);
        throw error;
      }
    },

    registerForLiveTour: async (registrationData) => {
      try {
        const result = await registerForLiveTour({ variables: { input: registrationData } });
        return result.data.registerForLiveTour;
      } catch (error) {
        console.error('Error registering for live tour:', error);
        throw error;
      }
    },

    // Subscription operations
    createPropertySubscription: async (subscriptionData) => {
      try {
        const result = await createPropertySubscription({ variables: { input: subscriptionData } });
        return result.data.createPropertySubscription;
      } catch (error) {
        console.error('Error creating property subscription:', error);
        throw error;
      }
    },

    updatePropertySubscription: async (subscriptionData) => {
      try {
        const result = await updatePropertySubscription({ variables: { input: subscriptionData } });
        return result.data.updatePropertySubscription;
      } catch (error) {
        console.error('Error updating property subscription:', error);
        throw error;
      }
    },

    deletePropertySubscription: async (subscriptionId) => {
      try {
        const result = await deletePropertySubscription({ variables: { subscriptionId } });
        return result.data.deletePropertySubscription;
      } catch (error) {
        console.error('Error deleting property subscription:', error);
        throw error;
      }
    },

    // Loading states
    loading: {
      updatingClientLocation,
      updatingAgentLocation,
      creatingListingType,
      creatingListing,
      updatingListing,
      deletingListing,
      addingImage,
      addingFile,
      loadingNearby,
      creatingTour,
      schedulingTour,
      registeringTour,
      creatingSubscription,
      updatingSubscription,
      deletingSubscription,
    }
  };
};