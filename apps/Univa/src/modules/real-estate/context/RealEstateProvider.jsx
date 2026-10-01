import React, {
  createContext,
  memo,
  useContext,
  useMemo,
} from "react";

import useRealtimeProperties from "../hooks/useRealtimeProperties";

/* -------------------------------------------------------------------------- */
/* Context */
/* -------------------------------------------------------------------------- */

const RealEstateContext =
  createContext(null);
  /* -------------------------------------------------------------------------- */
/* Provider */
/* -------------------------------------------------------------------------- */

function RealEstateProvider({
  children,
}) {
  const realEstate =
    useRealtimeProperties();

  const value = useMemo(
    () => realEstate,
    [realEstate]
  );

  return (
    <RealEstateContext.Provider
      value={value}
    >
      {children}
    </RealEstateContext.Provider>
  );
}
/* -------------------------------------------------------------------------- */
/* Hook */
/* -------------------------------------------------------------------------- */

export function useRealEstate() {
  const context =
    useContext(
      RealEstateContext
    );

  if (!context) {
    throw new Error(
      "useRealEstate must be used inside RealEstateProvider."
    );
  }

  return context;
}
/* -------------------------------------------------------------------------- */
/* Consumer */
/* -------------------------------------------------------------------------- */

export const RealEstateConsumer =
  RealEstateContext.Consumer;

/* -------------------------------------------------------------------------- */
/* Display Names */
/* -------------------------------------------------------------------------- */

RealEstateContext.displayName =
  "RealEstateContext";

RealEstateProvider.displayName =
  "RealEstateProvider";

/* -------------------------------------------------------------------------- */
/* Exports */
/* -------------------------------------------------------------------------- */

export {
  RealEstateContext,
};

export default memo(
  RealEstateProvider
);