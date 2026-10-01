/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useThumbnail.js                     */
/* -------------------------------------------------------------------------- */

import { useCallback, useMemo } from "react";
import { useQuery, useMutation } from "@apollo/client/react";

import {
  GET_THUMBNAIL,
  GET_ALL_THUMBNAILS,
  GET_THUMBNAILS_BY_CATEGORY,
  GET_THUMBNAILS_BY_COLLECTION,
  GET_THUMBNAILS_BY_PRODUCT_MEDIA,
  GET_THUMBNAILS_BY_USER,
} from "@/modules/ecommerce/api/productQuery/queries/thumbnail";

import {
  CREATE_THUMBNAIL,
  UPDATE_THUMBNAIL,
  DELETE_THUMBNAIL,
} from "@/modules/ecommerce/api/productQuery/mutations/thumbnail";

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

export const useThumbnail = ({ id, skip = false } = {}) => {
  /* ------------------------------------------------------------------------ */
  /* Get Single Thumbnail                                                     */
  /* ------------------------------------------------------------------------ */

  const {
    data: thumbnailData,
    loading: thumbnailLoading,
    error: thumbnailError,
    refetch: refetchThumbnail,
  } = useQuery(GET_THUMBNAIL, {
    variables: { id },
    skip: skip || !id,
    fetchPolicy: "cache-and-network",
  });

  /* ------------------------------------------------------------------------ */
  /* Get All Thumbnails                                                       */
  /* ------------------------------------------------------------------------ */

  const {
    data: allThumbnailsData,
    loading: allThumbnailsLoading,
    error: allThumbnailsError,
    refetch: refetchAllThumbnails,
  } = useQuery(GET_ALL_THUMBNAILS, {
    skip: skip,
    fetchPolicy: "cache-and-network",
  });

  /* ------------------------------------------------------------------------ */
  /* Mutations                                                                */
  /* ------------------------------------------------------------------------ */

  const [createThumbnailMutation] = useMutation(CREATE_THUMBNAIL);
  const [updateThumbnailMutation] = useMutation(UPDATE_THUMBNAIL);
  const [deleteThumbnailMutation] = useMutation(DELETE_THUMBNAIL);

  /* ------------------------------------------------------------------------ */
  /* Memoized Data                                                            */
  /* ------------------------------------------------------------------------ */

  const thumbnail = thumbnailData?.thumbnail ?? null;
  const allThumbnails = allThumbnailsData?.allThumbnails?.edges?.map(edge => edge.node) ?? [];

  /* ------------------------------------------------------------------------ */
  /* Actions                                                                  */
  /* ------------------------------------------------------------------------ */

  const createThumbnail = useCallback(async (input) => {
    try {
      const { data } = await createThumbnailMutation({
        variables: { input },
      });
      await refetchAllThumbnails();
      return {
        success: true,
        thumbnail: data?.createThumbnail?.thumbnail,
      };
    } catch (error) {
      return { success: false, error };
    }
  }, [createThumbnailMutation, refetchAllThumbnails]);

  const updateThumbnail = useCallback(async (input) => {
    try {
      const { data } = await updateThumbnailMutation({
        variables: { input },
      });
      await refetchAllThumbnails();
      if (id) await refetchThumbnail();
      return {
        success: true,
        thumbnail: data?.updateThumbnail?.thumbnail,
      };
    } catch (error) {
      return { success: false, error };
    }
  }, [updateThumbnailMutation, refetchAllThumbnails, refetchThumbnail, id]);

  const deleteThumbnail = useCallback(async (id) => {
    try {
      const { data } = await deleteThumbnailMutation({
        variables: { input: { id } },
      });
      await refetchAllThumbnails();
      return {
        success: data?.deleteThumbnail?.ok ?? false,
      };
    } catch (error) {
      return { success: false, error };
    }
  }, [deleteThumbnailMutation, refetchAllThumbnails]);

  /* ------------------------------------------------------------------------ */
  /* Get Thumbnails by Category                                               */
  /* ------------------------------------------------------------------------ */

  const getByCategory = useCallback(async (categoryId) => {
    try {
      const { data } = await useQuery(GET_THUMBNAILS_BY_CATEGORY, {
        variables: { categoryId },
        fetchPolicy: "cache-and-network",
      });
      return data?.allThumbnails?.edges?.map(edge => edge.node) ?? [];
    } catch (error) {
      return [];
    }
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Get Thumbnails by Collection                                             */
  /* ------------------------------------------------------------------------ */

  const getByCollection = useCallback(async (collectionId) => {
    try {
      const { data } = await useQuery(GET_THUMBNAILS_BY_COLLECTION, {
        variables: { collectionId },
        fetchPolicy: "cache-and-network",
      });
      return data?.allThumbnails?.edges?.map(edge => edge.node) ?? [];
    } catch (error) {
      return [];
    }
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Get Thumbnails by Product Media                                          */
  /* ------------------------------------------------------------------------ */

  const getByProductMedia = useCallback(async (productMediaId) => {
    try {
      const { data } = await useQuery(GET_THUMBNAILS_BY_PRODUCT_MEDIA, {
        variables: { productMediaId },
        fetchPolicy: "cache-and-network",
      });
      return data?.allThumbnails?.edges?.map(edge => edge.node) ?? [];
    } catch (error) {
      return [];
    }
  }, []);

  /* ------------------------------------------------------------------------ */
  /* Error Normalization                                                      */
  /* ------------------------------------------------------------------------ */

  const error = useMemo(() => {
    const currentError = thumbnailError || allThumbnailsError;
    if (!currentError) return null;
    return {
      message: currentError.message ?? "Failed to load thumbnails.",
      graphQLErrors: currentError.graphQLErrors ?? [],
      networkError: currentError.networkError ?? null,
    };
  }, [thumbnailError, allThumbnailsError]);

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Data
    thumbnail,
    allThumbnails,

    // Loading
    loading: thumbnailLoading || allThumbnailsLoading,

    // Error
    error,

    // Actions
    createThumbnail,
    updateThumbnail,
    deleteThumbnail,
    getByCategory,
    getByCollection,
    getByProductMedia,
    refetchThumbnail,
    refetchAllThumbnails,
  };
};

export default useThumbnail;