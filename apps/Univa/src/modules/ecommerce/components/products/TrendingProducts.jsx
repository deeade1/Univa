/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/TrendingProducts.jsx    */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const TrendingProducts = memo((props) => (
    <ProductCollectionSection
        title="Trending Now"
        subtitle="What's hot right now"
        banner="Trending products you shouldn't miss."
        showBanner
        loadingMessage="Loading trending products..."
        emptyTitle="No Trending Products"
        emptyDescription="Trending products will appear here."
        horizontal
        {...props}
    />
));

TrendingProducts.displayName = "TrendingProducts";
TrendingProducts.propTypes = ProductCollectionSection.propTypes;

export default TrendingProducts;