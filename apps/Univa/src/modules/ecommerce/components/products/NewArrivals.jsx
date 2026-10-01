/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/NewArrivals.jsx        */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const NewArrivals = memo((props) => (
    <ProductCollectionSection
        title="New Arrivals"
        subtitle="Fresh from our collection"
        banner="Check out our latest products."
        showBanner
        loadingMessage="Loading new arrivals..."
        emptyTitle="No New Arrivals"
        emptyDescription="New arrivals will appear here."
        horizontal
        {...props}
    />
));

NewArrivals.displayName = "NewArrivals";
NewArrivals.propTypes = ProductCollectionSection.propTypes;

export default NewArrivals;