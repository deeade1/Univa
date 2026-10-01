/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/ProductGrid.jsx        */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useCallback,
    useMemo,
} from "react";

import {
    StyleSheet,
    View,
} from "react-native";

import {
    FlashList,
} from "@shopify/flash-list";

import PropTypes
    from "prop-types";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Components                                                                 */
/* -------------------------------------------------------------------------- */

import ProductCard
    from "./ProductCard";

import EmptyState
    from "../common/EmptyState";

import ErrorState
    from "../common/ErrorState";

import LoadingOverlay
    from "../common/LoadingOverlay";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductGrid = memo(({

    products = [],

    loading = false,

    refreshing = false,

    error = null,

    numColumns = 2,

    estimatedItemSize = 280,

    contentContainerStyle,

    columnWrapperStyle,

    ListHeaderComponent,

    ListFooterComponent,

    ListEmptyComponent,

    keyExtractor,

    renderItem,

    onRefresh,

    onLoadMore,

    onEndReachedThreshold = 0.5,

    onProductPress,

    onFavorite,

    onAddToCart,

    style,

}) => {

    const {
        spacing,
    } = theme;

    /* ---------------------------------------------------------------------- */
    /* Key Extractor                                                          */
    /* ---------------------------------------------------------------------- */

    const extractKey =
        useCallback(

            (item, index) => {

                if (keyExtractor) {
                    return keyExtractor(
                        item,
                        index
                    );
                }

                return (
                    item?.id?.toString?.() ??
                    index.toString()
                );

            },

            [keyExtractor]

        );

    /* ---------------------------------------------------------------------- */
    /* Product Renderer                                                       */
    /* ---------------------------------------------------------------------- */

    const renderProduct =
        useCallback(

            ({ item, index }) => {

                if (renderItem) {

                    return renderItem({
                        item,
                        index,
                    });

                }

                return (

                    <ProductCard

                        product={item}

                        onPress={
                            onProductPress
                        }

                        onFavorite={
                            onFavorite
                        }

                        onAddToCart={
                            onAddToCart
                        }

                        style={
                            styles.card
                        }

                    />

                );

            },

            [

                renderItem,

                onProductPress,

                onFavorite,

                onAddToCart,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Data                                                                    */
    /* ---------------------------------------------------------------------- */

    const data =
        useMemo(
            () => products,
            [products]
        );
            /* ---------------------------------------------------------------------- */
    /* Empty Component                                                        */
    /* ---------------------------------------------------------------------- */

    const renderEmpty =
        useCallback(() => {

            if (loading) {
                return null;
            }

            if (ListEmptyComponent) {
                return ListEmptyComponent;
            }

            return (

                <EmptyState

                    icon="package-variant"

                    title="No Products Found"

                    description={
                        "There are currently no products to display."
                    }

                />

            );

        }, [

            loading,

            ListEmptyComponent,

        ]);

    /* ---------------------------------------------------------------------- */
    /* Error State                                                            */
    /* ---------------------------------------------------------------------- */

    if (error) {

        return (

            <ErrorState

                title="Unable to load products"

                description={
                    error?.message ??
                    "Please check your connection and try again."
                }

                onRetry={
                    onRefresh
                }

            />

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Footer Loader                                                          */
    /* ---------------------------------------------------------------------- */

    const renderFooter =
        useCallback(() => {

            if (!loading) {
                return (
                    ListFooterComponent ??
                    null
                );
            }

            return (

                <View
                    style={
                        styles.footerLoader
                    }
                >

                    <LoadingOverlay

                        visible

                        fullscreen={false}

                        transparent

                        message="Loading products..."

                    />

                    {ListFooterComponent}

                </View>

            );

        }, [

            loading,

            ListFooterComponent,

        ]);

    /* ---------------------------------------------------------------------- */
    /* Header                                                                 */
    /* ---------------------------------------------------------------------- */

    const renderHeader =
        useMemo(
            () =>
                ListHeaderComponent ??
                null,
            [
                ListHeaderComponent,
            ]
        );

    /* ---------------------------------------------------------------------- */
    /* Pull-to-Refresh                                                        */
    /* ---------------------------------------------------------------------- */

    const handleRefresh =
        useCallback(() => {

            onRefresh?.();

        }, [

            onRefresh,

        ]);

    /* ---------------------------------------------------------------------- */
    /* Load More                                                              */
    /* ---------------------------------------------------------------------- */

    const handleEndReached =
        useCallback(() => {

            if (
                loading
            ) {
                return;
            }

            onLoadMore?.();

        }, [

            loading,

            onLoadMore,

        ]);
            /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (

        <View
            style={[

                styles.container,

                style,

            ]}
        >

            <FlashList

                /* ---------------------------------------------------------- */
                /* Data                                                       */
                /* ---------------------------------------------------------- */

                data={
                    data
                }

                renderItem={
                    renderProduct
                }

                keyExtractor={
                    extractKey
                }

                /* ---------------------------------------------------------- */
                /* Grid                                                       */
                /* ---------------------------------------------------------- */

                numColumns={
                    numColumns
                }

                columnWrapperStyle={
                    numColumns > 1
                        ? [

                            styles.column,

                            columnWrapperStyle,

                        ]
                        : undefined
                }

                /* ---------------------------------------------------------- */
                /* Header / Footer                                            */
                /* ---------------------------------------------------------- */

                ListHeaderComponent={
                    renderHeader
                }

                ListFooterComponent={
                    renderFooter
                }

                ListEmptyComponent={
                    renderEmpty
                }

                /* ---------------------------------------------------------- */
                /* Refresh                                                    */
                /* ---------------------------------------------------------- */

                refreshing={
                    refreshing
                }

                onRefresh={
                    handleRefresh
                }

                /* ---------------------------------------------------------- */
                /* Infinite Scroll                                            */
                /* ---------------------------------------------------------- */

                onEndReached={
                    handleEndReached
                }

                onEndReachedThreshold={
                    onEndReachedThreshold
                }

                /* ---------------------------------------------------------- */
                /* Layout                                                     */
                /* ---------------------------------------------------------- */

                contentContainerStyle={[

                    styles.content,

                    products.length === 0 &&
                        styles.emptyContent,

                    contentContainerStyle,

                ]}

                showsVerticalScrollIndicator={
                    false
                }

                keyboardShouldPersistTaps="handled"

                /* ---------------------------------------------------------- */
                /* Performance                                                */
                /* ---------------------------------------------------------- */

                removeClippedSubviews

                initialNumToRender={
                    8
                }

                maxToRenderPerBatch={
                    8
                }

                updateCellsBatchingPeriod={
                    50
                }

                windowSize={
                    11
                }

                estimatedItemSize={
                    estimatedItemSize
                }

            />

        </View>

    );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ProductGrid.displayName =
    "ProductGrid";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductGrid.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    products:
        PropTypes.array,

    loading:
        PropTypes.bool,

    refreshing:
        PropTypes.bool,

    error:
        PropTypes.object,

    /* ---------------------------------------------------------------------- */
    /* Grid                                                                   */
    /* ---------------------------------------------------------------------- */

    numColumns:
        PropTypes.number,

    estimatedItemSize:
        PropTypes.number,

    /* ---------------------------------------------------------------------- */
    /* Custom Rendering                                                       */
    /* ---------------------------------------------------------------------- */

    renderItem:
        PropTypes.func,

    keyExtractor:
        PropTypes.func,

    ListHeaderComponent:
        PropTypes.oneOfType([
            PropTypes.element,
            PropTypes.func,
        ]),

    ListFooterComponent:
        PropTypes.oneOfType([
            PropTypes.element,
            PropTypes.func,
        ]),

    ListEmptyComponent:
        PropTypes.oneOfType([
            PropTypes.element,
            PropTypes.func,
        ]),

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onRefresh:
        PropTypes.func,

    onLoadMore:
        PropTypes.func,

    onEndReachedThreshold:
        PropTypes.number,

    onProductPress:
        PropTypes.func,

    onFavorite:
        PropTypes.func,

    onAddToCart:
        PropTypes.func,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

    contentContainerStyle:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

    columnWrapperStyle:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
    StyleSheet.create({

        container: {

            flex: 1,

        },

        content: {

            padding: 16,

            paddingBottom: 32,

        },

        emptyContent: {

            flexGrow: 1,

            justifyContent:
                "center",

        },

        column: {

            justifyContent:
                "space-between",

            marginBottom: 16,

        },

        card: {

            flex: 1,

            marginHorizontal: 4,

        },

        footerLoader: {

            paddingVertical: 24,

            alignItems:
                "center",

            justifyContent:
                "center",

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    ProductGrid;