/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/FlashSaleProducts.jsx   */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const FlashSaleProducts = memo((props) => (
    <ProductCollectionSection
        title="Flash Sale"
        subtitle="Limited time offers"
        banner="Hurry! These deals won't last."
        showBanner
        loadingMessage="Loading flash deals..."
        emptyTitle="No Flash Sales"
        emptyDescription="Flash sales will appear here."
        horizontal
        {...props}
    />
));

FlashSaleProducts.displayName = "FlashSaleProducts";
FlashSaleProducts.propTypes = ProductCollectionSection.propTypes;

export default FlashSaleProducts;