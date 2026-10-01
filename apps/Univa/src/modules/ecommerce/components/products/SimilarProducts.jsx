/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/SimilarProducts.jsx     */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const SimilarProducts = memo((props) => (
    <ProductCollectionSection
        title="Similar Products"
        subtitle="Compare alternatives"
        banner="Products with similar features."
        showBanner
        loadingMessage="Loading similar products..."
        emptyTitle="No Similar Products"
        emptyDescription="Similar products will appear here."
        horizontal
        {...props}
    />
));

SimilarProducts.displayName = "SimilarProducts";
SimilarProducts.propTypes = ProductCollectionSection.propTypes;

export default SimilarProducts;