/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/CustomersAlsoViewed.jsx */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const CustomersAlsoViewed = memo((props) => (
    <ProductCollectionSection
        title="Customers Also Viewed"
        subtitle="Popular alternatives"
        banner="Products other shoppers explored."
        showBanner
        loadingMessage="Loading similar products..."
        emptyTitle="No Similar Products"
        emptyDescription="Similar products will appear here."
        horizontal
        {...props}
    />
));

CustomersAlsoViewed.displayName = "CustomersAlsoViewed";
CustomersAlsoViewed.propTypes = ProductCollectionSection.propTypes;

export default CustomersAlsoViewed;