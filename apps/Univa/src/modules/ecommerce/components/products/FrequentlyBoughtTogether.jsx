/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/FrequentlyBoughtTogether.jsx */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const FrequentlyBoughtTogether = memo((props) => (
    <ProductCollectionSection
        title="Frequently Bought Together"
        subtitle="Complete your purchase"
        banner="Customers often purchase these items together."
        showBanner
        loadingMessage="Loading recommendations..."
        emptyTitle="No Bundle Recommendations"
        emptyDescription="Bundle recommendations will appear here."
        horizontal
        {...props}
    />
));

FrequentlyBoughtTogether.displayName = "FrequentlyBoughtTogether";
FrequentlyBoughtTogether.propTypes = ProductCollectionSection.propTypes;

export default FrequentlyBoughtTogether;