/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/DiscountedProducts.jsx  */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const DiscountedProducts = memo((props) => (
    <ProductCollectionSection
        title="Discounted Products"
        subtitle="Great savings"
        banner="Save big on these products."
        showBanner
        loadingMessage="Loading discounted products..."
        emptyTitle="No Discounted Products"
        emptyDescription="Discounted products will appear here."
        horizontal
        {...props}
    />
));

DiscountedProducts.displayName = "DiscountedProducts";
DiscountedProducts.propTypes = ProductCollectionSection.propTypes;

export default DiscountedProducts;