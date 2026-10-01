/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/RecommendedProducts.jsx */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import ProductCollectionSection from "./ProductCollectionSection";

const RecommendedProducts = memo((props) => (
    <ProductCollectionSection
        title="Recommended for You"
        banner="Based on your interests"
        showBanner
        loadingMessage="Loading recommendations..."
        emptyTitle="No Recommendations"
        emptyDescription="We'll recommend products as you browse."
        errorTitle="Unable to load recommendations"
        {...props}
    />
));

RecommendedProducts.displayName = "RecommendedProducts";
export default RecommendedProducts;