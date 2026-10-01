/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/RecentlyAddedProducts.jsx */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const RecentlyAddedProducts = memo((props) => (
    <ProductCollectionSection
        title="Recently Added"
        subtitle="Fresh inventory"
        banner="Check out what's new."
        showBanner
        loadingMessage="Loading recently added products..."
        emptyTitle="No Recently Added Products"
        emptyDescription="Recently added products will appear here."
        horizontal
        {...props}
    />
));

RecentlyAddedProducts.displayName = "RecentlyAddedProducts";
RecentlyAddedProducts.propTypes = ProductCollectionSection.propTypes;

export default RecentlyAddedProducts;