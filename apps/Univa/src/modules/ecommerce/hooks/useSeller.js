/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useSeller.js                        */
/* -------------------------------------------------------------------------- */

import { useCallback, useMemo, useState } from "react";
import { useQuery, useMutation } from "@apollo/client/react";

import {
  GET_USER,
  GET_USERS,
  GET_USER_PROFILE,
} from "@/modules/auth/api/queries/user";


import {
  UPGRADE_ACCOUNT,
  UPDATE_USER_AND_PROFILE,
  ASSIGN_USER_ROLE,
  UNASSIGN_USER_ROLE,
} from "@/modules/auth/api/mutations/user";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const SELLER_ROLES = {
  AGENT: 'agent',
  DRIVER: 'driver',
  VENDOR: 'vendor',
  BANKER: 'banker',
  SELLER: 'seller',
};

const SELLER_ROLE_LABELS = {
  [SELLER_ROLES.AGENT]: 'Agent',
  [SELLER_ROLES.DRIVER]: 'Driver',
  [SELLER_ROLES.VENDOR]: 'Vendor',
  [SELLER_ROLES.BANKER]: 'Banker',
  [SELLER_ROLES.SELLER]: 'Seller',
};

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

const useSeller = ({
  sellerId,
  userId,
  skip = false,
  onCompleted,
  onError,
} = {}) => {

  /* ------------------------------------------------------------------------ */
  /* State                                                                    */
  /* ------------------------------------------------------------------------ */

  const [selectedSellerId, setSelectedSellerId] = useState(sellerId || userId);
  const [roleFilter, setRoleFilter] = useState(null);

  /* ------------------------------------------------------------------------ */
  /* Get Single Seller/User                                                   */
  /* ------------------------------------------------------------------------ */

  const {
    data: sellerData,
    loading: sellerLoading,
    error: sellerError,
    refetch: refetchSeller,
  } = useQuery(GET_USER, {
    variables: { id: selectedSellerId },
    skip: skip || !selectedSellerId,
    fetchPolicy: "cache-and-network",
  });

  /* ------------------------------------------------------------------------ */
  /* Get All Sellers (Users with seller roles)                                */
  /* ------------------------------------------------------------------------ */

  const {
    data: allSellersData,
    loading: allSellersLoading,
    error: allSellersError,
    refetch: refetchAllSellers,
  } = useQuery(GET_USERS, {
    variables: {
      first: 100,
      // You may need to add a role filter to your users query
      // or filter on the client side
    },
    skip: skip,
    fetchPolicy: "cache-and-network",
  });

  /* ------------------------------------------------------------------------ */
  /* Get Seller Profile                                                       */
  /* ------------------------------------------------------------------------ */

  const {
    data: profileData,
    loading: profileLoading,
    error: profileError,
    refetch: refetchProfile,
  } = useQuery(GET_USER_PROFILE, {
    variables: { userId: selectedSellerId },
    skip: skip || !selectedSellerId,
    fetchPolicy: "cache-and-network",
  });

  /* ------------------------------------------------------------------------ */
  /* Mutations                                                                */
  /* ------------------------------------------------------------------------ */

  const [upgradeAccount] = useMutation(UPGRADE_ACCOUNT);
  const [updateUser] = useMutation(UPDATE_USER_AND_PROFILE);
  const [assignRole] = useMutation(ASSIGN_USER_ROLE);
  const [unassignRole] = useMutation(UNASSIGN_USER_ROLE);

  /* ------------------------------------------------------------------------ */
  /* Memoized Data                                                            */
  /* ------------------------------------------------------------------------ */

  const seller = useMemo(() => {
    const user = sellerData?.user ?? null;
    if (!user) return null;

    // Check if user has seller-related roles
    const sellerRoles = user.userRoles?.filter(role =>
      Object.values(SELLER_ROLES).includes(role.roleName?.toLowerCase())
    ) ?? [];

    return {
      ...user,
      isSeller: sellerRoles.length > 0,
      sellerRoles: sellerRoles,
      primaryRole: sellerRoles[0]?.roleName || null,
      roleLabel: sellerRoles[0] ? SELLER_ROLE_LABELS[sellerRoles[0].roleName] : null,
    };
  }, [sellerData]);

  const profile = useMemo(() => {
    return profileData?.userProfile ?? null;
  }, [profileData]);

  const allSellers = useMemo(() => {
    const users = allSellersData?.allUsers?.edges?.map(edge => edge.node) ?? [];

    // Filter users with seller roles
    return users.filter(user => {
      const roles = user.userRoles?.map(r => r.roleName?.toLowerCase()) ?? [];
      return roles.some(role => Object.values(SELLER_ROLES).includes(role));
    });
  }, [allSellersData]);

  const filteredSellers = useMemo(() => {
    if (!roleFilter) return allSellers;
    return allSellers.filter(user => {
      const roles = user.userRoles?.map(r => r.roleName?.toLowerCase()) ?? [];
      return roles.includes(roleFilter.toLowerCase());
    });
  }, [allSellers, roleFilter]);

  /* ------------------------------------------------------------------------ */
  /* Actions                                                                  */
  /* ------------------------------------------------------------------------ */

  /**
   * Upgrade a user to a seller role
   */
  const upgradeToSeller = useCallback(async ({
    userId,
    roleName,
    licenseId,
    companyName,
    licenseNumber,
    vehicleType,
    vehiclePlate,
    vehicleMake,
    vehicleModel,
    vehicleYear,
    insuranceProvider,
    insuranceExpiry,
  }) => {
    try {
      const { data } = await upgradeAccount({
        variables: {
          input: {
            userId: userId || selectedSellerId,
            roleName: roleName || SELLER_ROLES.SELLER,
            licenseId,
            companyName,
            licenseNumber,
            vehicleType,
            vehiclePlate,
            vehicleMake,
            vehicleModel,
            vehicleYear,
            insuranceProvider,
            insuranceExpiry,
          },
        },
      });

      const result = data?.upgradeAccount;

      if (result?.success) {
        await refetchSeller();
        await refetchAllSellers();
        return {
          success: true,
          user: result.user,
          agentProfile: result.agentProfile,
          driverProfile: result.driverProfile,
          message: result.message,
        };
      }

      return {
        success: false,
        message: result?.message || "Failed to upgrade account",
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    }
  }, [selectedSellerId, upgradeAccount, refetchSeller, refetchAllSellers]);

  /**
   * Update seller profile
   */
  const updateSellerProfile = useCallback(async (input) => {
    try {
      const { data } = await updateUser({
        variables: {
          input: {
            userId: selectedSellerId,
            ...input,
          },
        },
      });

      const result = data?.updateUserAndProfile;

      if (result) {
        await refetchProfile();
        await refetchSeller();
        return {
          success: true,
          user: result.user,
          profile: result.profile,
        };
      }

      return {
        success: false,
        message: "Failed to update profile",
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    }
  }, [selectedSellerId, updateUser, refetchProfile, refetchSeller]);

  /**
   * Assign a role to a seller
   */
  const assignSellerRole = useCallback(async ({ userId, roleName, appName = 'ecommerce' }) => {
    try {
      const { data } = await assignRole({
        variables: {
          input: {
            userId: userId || selectedSellerId,
            appName: appName,
            roleName: roleName,
            isActive: true,
          },
        },
      });

      const result = data?.assignUserRole;

      if (result) {
        await refetchSeller();
        await refetchAllSellers();
        return {
          success: true,
          user: result.user,
        };
      }

      return {
        success: false,
        message: "Failed to assign role",
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    }
  }, [selectedSellerId, assignRole, refetchSeller, refetchAllSellers]);

  /**
   * Remove a role from a seller
   */
  const unassignSellerRole = useCallback(async ({ userId, roleName, appName = 'ecommerce' }) => {
    try {
      const { data } = await unassignRole({
        variables: {
          input: {
            userId: userId || selectedSellerId,
            appName: appName,
            roleName: roleName,
          },
        },
      });

      const result = data?.unassignUserRole;

      if (result?.success) {
        await refetchSeller();
        await refetchAllSellers();
        return {
          success: true,
          message: result.message,
        };
      }

      return {
        success: false,
        message: result?.message || "Failed to unassign role",
      };
    } catch (error) {
      return {
        success: false,
        error,
      };
    }
  }, [selectedSellerId, unassignRole, refetchSeller, refetchAllSellers]);

  /**
   * Set seller filter by role
   */
  const filterByRole = useCallback((role) => {
    setRoleFilter(role);
  }, []);

  /**
   * Clear seller filters
   */
  const clearFilters = useCallback(() => {
    setRoleFilter(null);
  }, []);

  /**
   * Select a seller
   */
  const selectSeller = useCallback((id) => {
    setSelectedSellerId(id);
  }, []);

  /**
   * Refresh all seller data
   */
  const refresh = useCallback(async () => {
    await Promise.all([
      refetchSeller(),
      refetchAllSellers(),
      refetchProfile(),
    ]);
  }, [refetchSeller, refetchAllSellers, refetchProfile]);

  /* ------------------------------------------------------------------------ */
  /* Error Normalization                                                      */
  /* ------------------------------------------------------------------------ */

  const error = useMemo(() => {
    const currentError = sellerError || allSellersError || profileError;
    if (!currentError) return null;
    return {
      message: currentError.message ?? "Failed to load seller data.",
      graphQLErrors: currentError.graphQLErrors ?? [],
      networkError: currentError.networkError ?? null,
    };
  }, [sellerError, allSellersError, profileError]);

  /* ------------------------------------------------------------------------ */
  /* Loading States                                                           */
  /* ------------------------------------------------------------------------ */

  const loading = sellerLoading || allSellersLoading || profileLoading;

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Data
    seller,
    profile,
    allSellers: filteredSellers,
    selectedSellerId,

    // Roles
    roles: SELLER_ROLES,
    roleLabels: SELLER_ROLE_LABELS,
    roleFilter,
    filterByRole,
    clearFilters,

    // Loading
    loading,
    sellerLoading,
    allSellersLoading,
    profileLoading,

    // Error
    error,

    // Actions
    selectSeller,
    upgradeToSeller,
    updateSellerProfile,
    assignSellerRole,
    unassignSellerRole,
    refresh,
    refetchSeller,
    refetchAllSellers,
    refetchProfile,

    // Helpers
    isSeller: seller?.isSeller ?? false,
    hasSellers: allSellers.length > 0,
  };
};

export default useSeller;