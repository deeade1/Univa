/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/RelatedProducts.jsx     */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import ProductCollectionSection from "./ProductCollectionSection";

const RelatedProducts = memo((props) => (
    <ProductCollectionSection
        title="Related Products"
        subtitle="You might also like"
        banner="Products similar to this item."
        showBanner
        loadingMessage="Loading related products..."
        emptyTitle="No Related Products"
        emptyDescription="We couldn't find similar products."
        horizontal
        {...props}
    />
));

RelatedProducts.displayName = "RelatedProducts";
RelatedProducts.propTypes = ProductCollectionSection.propTypes;

export default RelatedProducts;