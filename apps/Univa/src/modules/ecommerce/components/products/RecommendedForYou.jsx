/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/RecommendedForYou.jsx   */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const RecommendedForYou = memo((props) => (
    <ProductCollectionSection
        title="Recommended For You"
        subtitle="Personalized picks"
        banner="Based on your preferences."
        showBanner
        loadingMessage="Loading recommendations..."
        emptyTitle="No Recommendations"
        emptyDescription="Recommendations will appear here."
        horizontal
        {...props}
    />
));

RecommendedForYou.displayName = "RecommendedForYou";
RecommendedForYou.propTypes = ProductCollectionSection.propTypes;

export default RecommendedForYou;