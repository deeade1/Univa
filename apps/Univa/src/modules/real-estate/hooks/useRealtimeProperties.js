import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useApolloClient,
  useQuery,
  useSubscription,
} from "@apollo/client";

import { useAuth } from "@/context/AuthContext";

/* -------------------------------------------------------------------------- */
/* Queries */
/* -------------------------------------------------------------------------- */


import {
  GET_PROPERTIES,
  GET_FEATURED_PROPERTIES,
  GET_SAVED_PROPERTIES,
  GET_PROPERTY_CATEGORIES,
} from "@/modules/real-estate/api/queries";

/* -------------------------------------------------------------------------- */
/* Subscriptions */
/* -------------------------------------------------------------------------- */


import {
  REALTIME_PROPERTY_UPDATES,
} from "@/modules/real-estate/api/subscriptions";
/* -------------------------------------------------------------------------- */
/* Hook */
/* -------------------------------------------------------------------------- */

export default function useRealtimeProperties() {
  const client = useApolloClient();

  const { user } = useAuth();

  const userId = user?.id;
  /* -------------------------------------------------------------------------- */
/* Initial Queries */
/* -------------------------------------------------------------------------- */

const propertiesQuery = useQuery(
  GET_PROPERTIES,
  {
    fetchPolicy: "cache-and-network",

    notifyOnNetworkStatusChange: true,
  }
);

const featuredQuery = useQuery(
  GET_FEATURED_PROPERTIES,
  {
    fetchPolicy: "cache-and-network",
  }
);

const savedQuery = useQuery(
  GET_SAVED_PROPERTIES,
  {
    skip: !userId,

    fetchPolicy: "cache-and-network",
  }
);

const categoriesQuery = useQuery(
  GET_PROPERTY_CATEGORIES,
  {
    fetchPolicy: "cache-and-network",
  }
);
/* -------------------------------------------------------------------------- */
/* Local State */
/* -------------------------------------------------------------------------- */

const [properties, setProperties] =
  useState([]);

const [
  featuredProperties,
  setFeaturedProperties,
] = useState([]);

const [
  savedProperties,
  setSavedProperties,
] = useState([]);

const [
  categories,
  setCategories,
] = useState([]);

const [
  recentProperties,
  setRecentProperties,
] = useState([]);

const [
  notifications,
  setNotifications,
] = useState([]);
/* -------------------------------------------------------------------------- */
/* Hydrate Query Data */
/* -------------------------------------------------------------------------- */

useEffect(() => {
  const edges =
    propertiesQuery.data?.properties
      ?.edges ?? [];

  setProperties(
    edges.map(
      ({ node }) => node
    )
  );
}, [propertiesQuery.data]);

useEffect(() => {
  const edges =
    featuredQuery.data
      ?.featuredProperties
      ?.edges ?? [];

  setFeaturedProperties(
    edges.map(
      ({ node }) => node
    )
  );
}, [featuredQuery.data]);

useEffect(() => {
  const edges =
    savedQuery.data
      ?.savedProperties
      ?.edges ?? [];

  setSavedProperties(
    edges.map(
      ({ node }) => node
    )
  );
}, [savedQuery.data]);

useEffect(() => {
  const edges =
    categoriesQuery.data
      ?.propertyCategories
      ?.edges ?? [];

  setCategories(
    edges.map(
      ({ node }) => node
    )
  );
}, [categoriesQuery.data]);
/* -------------------------------------------------------------------------- */
/* Real-time Property Subscription */
/* -------------------------------------------------------------------------- */

useSubscription(
  REALTIME_PROPERTY_UPDATES,
  {
    shouldResubscribe: true,

    onData: ({ data }) => {
      const payload = data?.data;

      if (!payload) {
        return;
      }

      /* ------------------------------------------------------ */
      /* New Property */
      /* ------------------------------------------------------ */

      if (payload.propertyCreated?.property) {
        const property =
          payload.propertyCreated.property;

        setProperties((previous) => {
          const exists = previous.some(
            (item) => item.id === property.id
          );

          if (exists) {
            return previous;
          }

          return [property, ...previous];
        });
      }

      /* ------------------------------------------------------ */
      /* Updated Property */
      /* ------------------------------------------------------ */

      if (payload.propertyUpdated?.property) {
        const property =
          payload.propertyUpdated.property;

        setProperties((previous) =>
          previous.map((item) =>
            item.id === property.id
              ? property
              : item
          )
        );

        setFeaturedProperties((previous) =>
          previous.map((item) =>
            item.id === property.id
              ? property
              : item
          )
        );

        setSavedProperties((previous) =>
          previous.map((item) =>
            item.id === property.id
              ? property
              : item
          )
        );
      }

      /* ------------------------------------------------------ */
      /* Deleted Property */
      /* ------------------------------------------------------ */

      if (payload.propertyDeleted?.propertyId) {
        const propertyId =
          payload.propertyDeleted.propertyId;

        setProperties((previous) =>
          previous.filter(
            (item) => item.id !== propertyId
          )
        );

        setFeaturedProperties((previous) =>
          previous.filter(
            (item) => item.id !== propertyId
          )
        );

        setSavedProperties((previous) =>
          previous.filter(
            (item) => item.id !== propertyId
          )
        );
      }

      /* ------------------------------------------------------ */
      /* Saved Property */
      /* ------------------------------------------------------ */

      if (payload.savedProperty?.property) {
        const property =
          payload.savedProperty.property;

        setSavedProperties((previous) => {
          const exists = previous.some(
            (item) => item.id === property.id
          );

          if (exists) {
            return previous;
          }

          return [property, ...previous];
        });
      }

      /* ------------------------------------------------------ */
      /* Notification */
      /* ------------------------------------------------------ */

      if (payload.notification) {
        setNotifications((previous) => [
          payload.notification,
          ...previous,
        ]);
      }
    },

    onError: (error) => {
      console.warn(
        "[Real Estate Subscription]",
        error
      );
    },
  }
);
/* -------------------------------------------------------------------------- */
/* Loading */
/* -------------------------------------------------------------------------- */

const loading =
  propertiesQuery.loading ||
  featuredQuery.loading ||
  savedQuery.loading ||
  categoriesQuery.loading;

/* -------------------------------------------------------------------------- */
/* Error */
/* -------------------------------------------------------------------------- */

const error =
  propertiesQuery.error ||
  featuredQuery.error ||
  savedQuery.error ||
  categoriesQuery.error;

  /* -------------------------------------------------------------------------- */
/* Refresh */
/* -------------------------------------------------------------------------- */

const refresh = useCallback(async () => {
  try {
    await Promise.all([
      propertiesQuery.refetch(),
      featuredQuery.refetch(),
      savedQuery.refetch(),
      categoriesQuery.refetch(),
    ]);
  } catch (error) {
    console.error(
      "[Real Estate Refresh]",
      error
    );
  }
}, [
  propertiesQuery,
  featuredQuery,
  savedQuery,
  categoriesQuery,
]);
/* -------------------------------------------------------------------------- */
/* Apollo Cache Reset */
/* -------------------------------------------------------------------------- */

const resetCache = useCallback(async () => {
  try {
    await client.resetStore();
  } catch (error) {
    console.error(
      "[Real Estate Cache Reset]",
      error
    );
  }
}, [client]);
/* -------------------------------------------------------------------------- */
/* Derived State */
/* -------------------------------------------------------------------------- */

const recommendedProperties =
  useMemo(() => {
    return properties
      .filter(
        (property) =>
          property.isRecommended
      )
      .slice(0, 10);
  }, [properties]);

const nearbyProperties =
  useMemo(() => {
    return properties.filter(
      (property) =>
        property.isNearby
    );
  }, [properties]);

const latestProperties =
  useMemo(() => {
    return [...properties]
      .sort(
        (a, b) =>
          new Date(
            b.createdAt
          ) -
          new Date(a.createdAt)
      )
      .slice(0, 10);
  }, [properties]);

const featuredCount =
  featuredProperties.length;

const savedCount =
  savedProperties.length;

const unreadNotifications =
  notifications.filter(
    (item) => !item.isRead
  ).length;
  /* -------------------------------------------------------------------------- */
/* Memoized Dashboard */
/* -------------------------------------------------------------------------- */

const dashboard = useMemo(
  () => ({
    /* Properties */

    properties,

    featuredProperties,

    savedProperties,

    categories,

    recommendedProperties,

    nearbyProperties,

    latestProperties,

    recentProperties,

    /* Notifications */

    notifications,

    unreadNotifications,

    /* Counts */

    featuredCount,

    savedCount,

    /* State */

    loading,

    error,

    /* Actions */

    refresh,

    resetCache,
  }),
  [
    properties,
    featuredProperties,
    savedProperties,
    categories,
    recommendedProperties,
    nearbyProperties,
    latestProperties,
    recentProperties,
    notifications,
    unreadNotifications,
    featuredCount,
    savedCount,
    loading,
    error,
    refresh,
    resetCache,
  ]
);

return dashboard;
}