/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/seller/SellerProducts.jsx       */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";

import ProductCollectionSection
    from "../products/ProductCollectionSection";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SellerProducts = memo(({
    seller,

    products = [],

    loading = false,

    error = null,

    horizontal = true,

    numColumns = 2,

    title,

    subtitle,

    showSeeAll = true,

    onSeeAll,

    onRetry,

    onProductPress,

    onWishlistPress,

    onAddToCart,

    ListHeaderComponent,

    ListFooterComponent,

    style,
}) => {

    return (

        <ProductCollectionSection

            title={
                title ??
                `${seller?.name ?? "Seller"} Products`
            }

            subtitle={subtitle}

            products={products}

            loading={loading}

            error={error}

            horizontal={horizontal}

            numColumns={numColumns}

            showSeeAll={showSeeAll}

            onSeeAll={onSeeAll}

            onRetry={onRetry}

            emptyIcon="storefront-outline"

            emptyTitle="No Products"

            emptyDescription="This seller hasn't listed any products yet."

            onProductPress={onProductPress}

            onFavorite={onWishlistPress}

            onAddToCart={onAddToCart}

            ListHeaderComponent={ListHeaderComponent}

            ListFooterComponent={ListFooterComponent}

            style={style}

        />

    );

});

SellerProducts.displayName =
    "SellerProducts";

export default SellerProducts;