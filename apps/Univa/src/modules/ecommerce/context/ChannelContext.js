/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/context/ChannelContext.js                 */
/* -------------------------------------------------------------------------- */

import React, { createContext, useContext, useMemo, useCallback } from 'react';
import { useQuery, useMutation } from '@apollo/client/react';

import {
  GET_CHANNEL_BY_SLUG,
  GET_ALL_CHANNELS,
} from '@/modules/ecommerce/api/productQuery/queries/channel';

import {
  CREATE_CHANNEL,
  UPDATE_CHANNEL,
  DELETE_CHANNEL,
} from '@/modules/ecommerce/api/productQuery/mutations/channels';

/* -------------------------------------------------------------------------- */
/* Types                                                                      */
/* -------------------------------------------------------------------------- */

/**
 * @typedef {Object} Channel
 * @property {string} id
 * @property {string} name
 * @property {string} slug
 * @property {string} currencyCode
 * @property {string} defaultCountry
 * @property {boolean} isActive
 * @property {string} createdAt
 * @property {string} updatedAt
 */

/**
 * @typedef {Object} ChannelContextValue
 * @property {Channel|null} channel - Current channel
 * @property {string} currency - Current currency code (defaults to 'USD')
 * @property {string} country - Current country code (defaults to 'US')
 * @property {boolean} isActive - Whether channel is active
 * @property {boolean} loading - Whether channel is loading
 * @property {object|null} error - Error if any
 * @property {Function} refetch - Refetch channel data
 * @property {Function} setChannel - Set channel by slug
 * @property {Function} switchChannel - Switch to a different channel
 * @property {Array<Channel>} allChannels - All available channels
 * @property {Function} refreshChannels - Refresh all channels list
 * @property {Function} createChannel - Create a new channel (admin)
 * @property {Function} updateChannel - Update a channel (admin)
 * @property {Function} deleteChannel - Delete a channel (admin)
 */

/* -------------------------------------------------------------------------- */
/* Context                                                                    */
/* -------------------------------------------------------------------------- */

const ChannelContext = createContext(null);

/* -------------------------------------------------------------------------- */
/* Provider                                                                   */
/* -------------------------------------------------------------------------- */

export const ChannelProvider = ({
  children,
  defaultSlug = 'default',
  skip = false,
}) => {
  /* ------------------------------------------------------------------------ */
  /* State                                                                    */
  /* ------------------------------------------------------------------------ */

  const [currentSlug, setCurrentSlug] = React.useState(defaultSlug);

  /* ------------------------------------------------------------------------ */
  /* Get Current Channel                                                      */
  /* ------------------------------------------------------------------------ */

  const {
    data: channelData,
    loading: channelLoading,
    error: channelError,
    refetch: refetchChannel,
  } = useQuery(GET_CHANNEL_BY_SLUG, {
    variables: { slug: currentSlug },
    skip: skip || !currentSlug || currentSlug === 'default',
    fetchPolicy: 'cache-and-network',
    notifyOnNetworkStatusChange: true,
    errorPolicy: 'all',
  });

  /* ------------------------------------------------------------------------ */
  /* Get All Channels (for admin/selectors)                                   */
  /* ------------------------------------------------------------------------ */

  const {
    data: allChannelsData,
    loading: allChannelsLoading,
    error: allChannelsError,
    refetch: refetchAllChannels,
  } = useQuery(GET_ALL_CHANNELS, {
    variables: {
      first: 100,
      isActive: true,
    },
    skip: skip,
    fetchPolicy: 'cache-and-network',
    errorPolicy: 'all',
  });

  /* ------------------------------------------------------------------------ */
  /* Mutations (Admin)                                                        */
  /* ------------------------------------------------------------------------ */

  const [createChannelMutation] = useMutation(CREATE_CHANNEL);
  const [updateChannelMutation] = useMutation(UPDATE_CHANNEL);
  const [deleteChannelMutation] = useMutation(DELETE_CHANNEL);

  /* ------------------------------------------------------------------------ */
  /* Memoized Values                                                          */
  /* ------------------------------------------------------------------------ */

  const channel = channelData?.channelBySlug ?? null;

  const allChannels = useMemo(
    () => allChannelsData?.allChannels?.edges?.map(edge => edge.node) ?? [],
    [allChannelsData]
  );

  const activeChannels = useMemo(
    () => allChannels.filter(ch => ch.isActive),
    [allChannels]
  );

  /* ------------------------------------------------------------------------ */
  /* Derived Values                                                           */
  /* ------------------------------------------------------------------------ */

  const currency = channel?.currencyCode || 'USD';
  const country = channel?.defaultCountry || 'US';
  const isActive = channel?.isActive ?? false;

  /* ------------------------------------------------------------------------ */
  /* Loading & Error States                                                   */
  /* ------------------------------------------------------------------------ */

  const loading = channelLoading || allChannelsLoading;

  const error = useMemo(() => {
    const currentError = channelError || allChannelsError;
    if (!currentError) return null;

    return {
      message: currentError.message ?? 'Failed to load channel data.',
      graphQLErrors: currentError.graphQLErrors ?? [],
      networkError: currentError.networkError ?? null,
    };
  }, [channelError, allChannelsError]);

  /* ------------------------------------------------------------------------ */
  /* Actions                                                                  */
  /* ------------------------------------------------------------------------ */

  /**
   * Switch to a different channel by slug
   */
  const switchChannel = useCallback((slug) => {
    if (slug && slug !== currentSlug) {
      setCurrentSlug(slug);
    }
  }, [currentSlug]);

  /**
   * Set channel directly (alias for switchChannel)
   */
  const setChannel = useCallback((slug) => {
    switchChannel(slug);
  }, [switchChannel]);

  /**
   * Refresh current channel data
   */
  const refreshChannel = useCallback(async () => {
    try {
      const result = await refetchChannel();
      return result.data?.channelBySlug ?? null;
    } catch (err) {
      console.warn('Channel refresh failed:', err);
      return null;
    }
  }, [refetchChannel]);

  /**
   * Refresh all channels list
   */
  const refreshChannels = useCallback(async () => {
    try {
      const result = await refetchAllChannels();
      return result.data?.allChannels?.edges?.map(edge => edge.node) ?? [];
    } catch (err) {
      console.warn('Channels refresh failed:', err);
      return [];
    }
  }, [refetchAllChannels]);

  /* ------------------------------------------------------------------------ */
  /* Admin Actions                                                            */
  /* ------------------------------------------------------------------------ */

  /**
   * Create a new channel (admin only)
   */
  const createChannel = useCallback(async (input) => {
    try {
      const { data } = await createChannelMutation({
        variables: { input },
        refetchQueries: [{ query: GET_ALL_CHANNELS }],
      });

      const newChannel = data?.createChannel?.channel;
      return {
        success: !!newChannel,
        channel: newChannel,
        error: null,
      };
    } catch (error) {
      return {
        success: false,
        channel: null,
        error: error.message || 'Failed to create channel',
      };
    }
  }, [createChannelMutation]);

  /**
   * Update an existing channel (admin only)
   */
  const updateChannel = useCallback(async (id, input) => {
    try {
      const { data } = await updateChannelMutation({
        variables: { input: { id, ...input } },
        refetchQueries: [
          { query: GET_CHANNEL_BY_SLUG, variables: { slug: currentSlug } },
          { query: GET_ALL_CHANNELS },
        ],
      });

      const updatedChannel = data?.updateChannel?.channel;
      return {
        success: !!updatedChannel,
        channel: updatedChannel,
        error: null,
      };
    } catch (error) {
      return {
        success: false,
        channel: null,
        error: error.message || 'Failed to update channel',
      };
    }
  }, [updateChannelMutation, currentSlug]);

  /**
   * Delete a channel (admin only)
   */
  const deleteChannel = useCallback(async (id) => {
    try {
      const { data } = await deleteChannelMutation({
        variables: { input: { id } },
        refetchQueries: [{ query: GET_ALL_CHANNELS }],
      });

      const success = data?.deleteChannel?.ok ?? false;
      return {
        success,
        error: null,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to delete channel',
      };
    }
  }, [deleteChannelMutation]);

  /* ------------------------------------------------------------------------ */
  /* Context Value                                                            */
  /* ------------------------------------------------------------------------ */

  const value = useMemo(() => ({
    // Current channel
    channel,
    currency,
    country,
    isActive,

    // All channels
    allChannels,
    activeChannels,

    // Loading & Error
    loading,
    error,

    // Actions
    setChannel,
    switchChannel,
    refetch: refreshChannel,
    refreshChannels,

    // Admin actions
    createChannel,
    updateChannel,
    deleteChannel,
  }), [
    channel,
    currency,
    country,
    isActive,
    allChannels,
    activeChannels,
    loading,
    error,
    setChannel,
    switchChannel,
    refreshChannel,
    refreshChannels,
    createChannel,
    updateChannel,
    deleteChannel,
  ]);

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return (
    <ChannelContext.Provider value={value}>
      {children}
    </ChannelContext.Provider>
  );
};

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

/**
 * useChannel - Hook to access channel context
 *
 * @returns {ChannelContextValue} Channel context value
 * @throws {Error} If used outside of ChannelProvider
 *
 * @example
 * const { currency, country, channel } = useChannel();
 *
 * @example
 * const { switchChannel, allChannels } = useChannel();
 *
 * @example
 * const { createChannel, updateChannel } = useChannel(); // Admin only
 */
export const useChannel = () => {
  const context = useContext(ChannelContext);
  if (!context) {
    throw new Error('useChannel must be used within ChannelProvider');
  }
  return context;
};

/* -------------------------------------------------------------------------- */
/* Default Export                                                             */
/* -------------------------------------------------------------------------- */

export default ChannelProvider;