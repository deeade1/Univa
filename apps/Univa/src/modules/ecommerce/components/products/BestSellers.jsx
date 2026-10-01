/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/BestSellers.jsx        */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const BestSellers = memo((props) => (
    <ProductCollectionSection
        title="Best Sellers"
        subtitle="Customer favorites"
        banner="Our most popular products."
        showBanner
        loadingMessage="Loading best sellers..."
        emptyTitle="No Best Sellers"
        emptyDescription="Best sellers will appear here."
        horizontal
        {...props}
    />
));

BestSellers.displayName = "BestSellers";
BestSellers.propTypes = ProductCollectionSection.propTypes;

export default BestSellers;