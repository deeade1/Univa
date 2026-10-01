/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/TopRatedProducts.jsx    */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const TopRatedProducts = memo((props) => (
    <ProductCollectionSection
        title="Top Rated Products"
        subtitle="Highest rated"
        banner="Products loved by our customers."
        showBanner
        loadingMessage="Loading top rated products..."
        emptyTitle="No Top Rated Products"
        emptyDescription="Top rated products will appear here."
        horizontal
        {...props}
    />
));

TopRatedProducts.displayName = "TopRatedProducts";
TopRatedProducts.propTypes = ProductCollectionSection.propTypes;

export default TopRatedProducts;