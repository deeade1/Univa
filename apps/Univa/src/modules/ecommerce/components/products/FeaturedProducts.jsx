/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/FeaturedProducts.jsx    */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import ProductCollectionSection from "./ProductCollectionSection";

const FeaturedProducts = memo((props) => (
    <ProductCollectionSection
        title="Featured Products"
        banner="Hand-picked for you"
        showBanner
        loadingMessage="Loading featured products..."
        emptyTitle="No Featured Products"
        emptyDescription="Featured products will appear here."
        errorTitle="Unable to load featured products"
        {...props}
    />
));

FeaturedProducts.displayName = "FeaturedProducts";
export default FeaturedProducts;


