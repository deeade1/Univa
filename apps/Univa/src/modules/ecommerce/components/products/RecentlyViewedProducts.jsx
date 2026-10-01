/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/RecentlyViewedProducts.jsx */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import ProductCollectionSection from "./ProductCollectionSection";

const RecentlyViewedProducts = memo(({ onClearHistory, ...props }) => (
    <ProductCollectionSection
        title="Recently Viewed"
        banner="Continue where you left off"
        showBanner
        actionLabel="Clear"
        showAction={!!onClearHistory}
        onAction={onClearHistory}
        loadingMessage="Loading recently viewed products..."
        emptyTitle="No Recently Viewed Products"
        emptyDescription="Products you view will appear here."
        errorTitle="Unable to load recently viewed products"
        {...props}
    />
));

RecentlyViewedProducts.displayName = "RecentlyViewedProducts";
export default RecentlyViewedProducts;