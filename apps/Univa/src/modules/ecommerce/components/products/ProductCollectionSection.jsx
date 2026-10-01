/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/ProductCollectionSection.jsx */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useMemo,
    useCallback,
} from "react";

import {
    FlatList,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from "react-native";

import PropTypes
    from "prop-types";

import theme
    from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import SectionHeader
    from "../common/SectionHeader";

import LoadingOverlay
    from "../common/LoadingOverlay";

import EmptyState
    from "../common/EmptyState";

import ErrorState
    from "../common/ErrorState";

/* -------------------------------------------------------------------------- */
/* Product Components                                                         */
/* -------------------------------------------------------------------------- */

import ProductCard
    from "./ProductCard";

import ProductGrid
    from "./ProductGrid";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const productPropType =
    PropTypes.shape({

        id:
            PropTypes.oneOfType([
                PropTypes.string,
                PropTypes.number,
            ]),

        name:
            PropTypes.string,

        price:
            PropTypes.number,

        image:
            PropTypes.string,

    });

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductCollectionSection = memo(({

    /* ---------------------------------------------------------------------- */
    /* Header                                                                 */
    /* ---------------------------------------------------------------------- */

    title,

    subtitle,

    showSeeAll = true,

    seeAllLabel = "See All",

    onSeeAll,

    /* ---------------------------------------------------------------------- */
    /* Banner                                                                 */
    /* ---------------------------------------------------------------------- */

    banner,

    showBanner = false,

    /* ---------------------------------------------------------------------- */
    /* Optional Action                                                        */
    /* ---------------------------------------------------------------------- */

    actionLabel,

    onAction,

    showAction = false,

    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    products = [],

    horizontal = true,

    numColumns = 2,

    /* ---------------------------------------------------------------------- */
    /* States                                                                 */
    /* ---------------------------------------------------------------------- */

    loading = false,

    loadingMessage = "Loading...",

    error = null,

    errorTitle = "Unable to load products",

    onRetry,

    emptyIcon = "package-variant",

    emptyTitle = "No Products",

    emptyDescription = "Nothing to display.",

    /* ---------------------------------------------------------------------- */
    /* Product Events                                                         */
    /* ---------------------------------------------------------------------- */

    onProductPress,

    onFavorite,

    onAddToCart,

    /* ---------------------------------------------------------------------- */
    /* Custom Renderer                                                        */
    /* ---------------------------------------------------------------------- */

    /**
     * Custom product renderer function.
     * If provided, overrides the default ProductCard rendering.
     * 
     * @param {Object} params
     * @param {Object} params.item - The product item
     * @param {number} params.index - The index of the item
     * @returns {React.ReactNode}
     */
    renderItem,

    /* ---------------------------------------------------------------------- */
    /* Slots                                                                  */
    /* ---------------------------------------------------------------------- */

    ListHeaderComponent,

    ListFooterComponent,

    style,

}) => {

    const {
        colors,
    } = theme;

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    const data = useMemo(
        () => products,
        [products]
    );

    /* ---------------------------------------------------------------------- */
    /* Key Extractor                                                          */
    /* ---------------------------------------------------------------------- */

    const keyExtractor = useCallback(

        (item, index) =>

            item?.id?.toString?.() ??
            item?.pk?.toString?.() ??
            item?.uuid ??
            item?.slug ??
            `product-${index}`,

        []

    );

    /* ---------------------------------------------------------------------- */
    /* Product Renderer                                                       */
    /* ---------------------------------------------------------------------- */

    const renderProduct = useCallback(

        ({ item, index }) => {
            // If custom renderItem is provided, use it
            if (renderItem) {
                return renderItem({ item, index });
            }

            // Default ProductCard rendering
            return (

                <View
                    style={styles.cardWrapper}
                >

                    <ProductCard

                        product={item}

                        onPress={onProductPress}

                        onFavorite={onFavorite}

                        onAddToCart={onAddToCart}

                        style={
                            horizontal
                                ? styles.horizontalCard
                                : styles.gridCard
                        }

                    />

                </View>

            );
        },

        [

            renderItem,

            horizontal,

            onProductPress,

            onFavorite,

            onAddToCart,

        ]

    );

    /* ---------------------------------------------------------------------- */
    /* Header                                                                 */
    /* ---------------------------------------------------------------------- */

    const renderHeader = useMemo(

        () => (

            <>

                <SectionHeader

                    title={
                        title
                    }

                    subtitle={
                        subtitle
                    }

                    showAction={
                        showSeeAll
                    }

                    actionLabel={
                        seeAllLabel
                    }

                    onActionPress={
                        onSeeAll
                    }

                />

                {showBanner && !!banner && (

                    <View
                        style={[

                            styles.bannerContainer,

                            {

                                backgroundColor:
                                    colors.surfaceVariant ??
                                    colors.surface,

                            },

                        ]}
                    >

                        <Text
                            style={[

                                styles.bannerText,

                                {

                                    color:
                                        colors.textSecondary,

                                },

                            ]}
                        >

                            {banner}

                        </Text>

                    </View>

                )}

                {showAction &&
                    actionLabel &&
                    typeof onAction === "function" && (

                    <View
                        style={
                            styles.actionContainer
                        }
                    >

                        <TouchableOpacity

                            onPress={
                                onAction
                            }

                            activeOpacity={
                                0.7
                            }

                            accessibilityRole="button"

                            accessibilityLabel={
                                actionLabel
                            }

                        >

                            <Text
                                style={[

                                    styles.actionText,

                                    {

                                        color:
                                            colors.primary,

                                    },

                                ]}
                            >

                                {actionLabel}

                            </Text>

                        </TouchableOpacity>

                    </View>

                )}

                {typeof ListHeaderComponent === "function"
                    ? <ListHeaderComponent />
                    : ListHeaderComponent}

            </>

        ),

        [

            title,

            subtitle,

            showSeeAll,

            seeAllLabel,

            onSeeAll,

            showBanner,

            banner,

            showAction,

            actionLabel,

            onAction,

            ListHeaderComponent,

            colors,

        ]

    );

    /* ---------------------------------------------------------------------- */
    /* Loading State                                                          */
    /* ---------------------------------------------------------------------- */

    if (loading) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                {renderHeader}

                <LoadingOverlay

                    visible

                    fullscreen={false}

                    transparent

                    message={
                        loadingMessage
                    }

                />

            </View>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Error State                                                            */
    /* ---------------------------------------------------------------------- */
    
    if (error) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                {renderHeader}
                
                <ErrorState

                    title={
                        errorTitle
                    }

                    description={
                        error?.message ??
                        "Please try again."
                    }

                    onRetry={
                        onRetry
                    }

                />

            </View>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Empty State                                                            */
    /* ---------------------------------------------------------------------- */

    if (!data.length) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                {renderHeader}

                <EmptyState

                    icon={
                        emptyIcon
                    }

                    title={
                        emptyTitle
                    }

                    description={
                        emptyDescription
                    }

                />

            </View>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Horizontal Layout                                                      */
    /* ---------------------------------------------------------------------- */

    if (horizontal) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                {renderHeader}

                <FlatList

                    horizontal

                    data={
                        data
                    }

                    renderItem={
                        renderProduct
                    }

                    keyExtractor={
                        keyExtractor
                    }

                    showsHorizontalScrollIndicator={
                        false
                    }

                    contentContainerStyle={
                        styles.horizontalContent
                    }

                    ItemSeparatorComponent={() => (

                        <View
                            style={
                                styles.separator
                            }
                        />

                    )}

                    ListFooterComponent={
                        typeof ListFooterComponent === "function"
                            ? <ListFooterComponent />
                            : ListFooterComponent
                    }

                    initialNumToRender={
                        6
                    }

                    maxToRenderPerBatch={
                        6
                    }

                    updateCellsBatchingPeriod={
                        50
                    }

                    windowSize={
                        5
                    }

                    removeClippedSubviews

                    keyboardShouldPersistTaps="handled"

                />

            </View>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Grid Layout                                                            */
    /* ---------------------------------------------------------------------- */

    return (

        <View
            style={[

                styles.container,

                style,

            ]}
        >

            {renderHeader}

            <ProductGrid

                products={
                    data
                }

                loading={
                    loading
                }

                error={
                    error
                }

                numColumns={
                    numColumns
                }

                onProductPress={
                    onProductPress
                }

                onFavorite={
                    onFavorite
                }

                onAddToCart={
                    onAddToCart
                }

                renderItem={
                    renderItem // Pass through to ProductGrid if it supports it
                }

                ListFooterComponent={
                    typeof ListFooterComponent === "function"
                        ? <ListFooterComponent />
                        : ListFooterComponent
                }

            />

        </View>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ProductCollectionSection.displayName =
    "ProductCollectionSection";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductCollectionSection.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Header                                                                 */
    /* ---------------------------------------------------------------------- */

    title:
        PropTypes.string,

    subtitle:
        PropTypes.string,

    showSeeAll:
        PropTypes.bool,

    seeAllLabel:
        PropTypes.string,

    onSeeAll:
        PropTypes.func,

    /* ---------------------------------------------------------------------- */
    /* Banner                                                                 */
    /* ---------------------------------------------------------------------- */

    banner:
        PropTypes.string,

    showBanner:
        PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* Secondary Action                                                       */
    /* ---------------------------------------------------------------------- */

    actionLabel:
        PropTypes.string,

    showAction:
        PropTypes.bool,

    onAction:
        PropTypes.func,

    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    products:
        PropTypes.arrayOf(
            productPropType
        ),

    horizontal:
        PropTypes.bool,

    numColumns:
        PropTypes.number,

    /* ---------------------------------------------------------------------- */
    /* Loading / Error / Empty                                                */
    /* ---------------------------------------------------------------------- */

    loading:
        PropTypes.bool,

    loadingMessage:
        PropTypes.string,

    error:
        PropTypes.object,

    errorTitle:
        PropTypes.string,

    onRetry:
        PropTypes.func,

    emptyIcon:
        PropTypes.string,

    emptyTitle:
        PropTypes.string,

    emptyDescription:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Product Events                                                         */
    /* ---------------------------------------------------------------------- */

    onProductPress:
        PropTypes.func,

    onFavorite:
        PropTypes.func,

    onAddToCart:
        PropTypes.func,

    /* ---------------------------------------------------------------------- */
    /* Custom Renderer                                                        */
    /* ---------------------------------------------------------------------- */

    /**
     * Custom product renderer function.
     * If provided, overrides the default ProductCard rendering.
     * 
     * @param {Object} params
     * @param {Object} params.item - The product item
     * @param {number} params.index - The index of the item
     * @returns {React.ReactNode}
     */
    renderItem:
        PropTypes.func,

    /* ---------------------------------------------------------------------- */
    /* Slots                                                                  */
    /* ---------------------------------------------------------------------- */

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

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ProductCollectionSection.defaultProps = {

    title: null,
    subtitle: null,
    showSeeAll: true,
    seeAllLabel: "See All",
    onSeeAll: null,

    banner: null,
    showBanner: false,

    actionLabel: null,
    onAction: null,
    showAction: false,

    products: [],
    horizontal: true,
    numColumns: 2,

    loading: false,
    loadingMessage: "Loading...",
    error: null,
    errorTitle: "Unable to load products",
    onRetry: null,

    emptyIcon: "package-variant",
    emptyTitle: "No Products",
    emptyDescription: "Nothing to display.",

    onProductPress: null,
    onFavorite: null,
    onAddToCart: null,

    renderItem: null,

    ListHeaderComponent: null,
    ListFooterComponent: null,

    style: null,

};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
    StyleSheet.create({

        container: {

            marginBottom:
                24,

        },

        /* ------------------------------------------------------------------ */
        /* Banner                                                             */
        /* ------------------------------------------------------------------ */

        bannerContainer: {

            marginHorizontal:
                16,

            marginBottom:
                12,

            paddingHorizontal:
                12,

            paddingVertical:
                10,

            borderRadius:
                12,

        },

        bannerText: {

            fontSize:
                13,

            fontWeight:
                "500",

        },

        /* ------------------------------------------------------------------ */
        /* Secondary Action                                                   */
        /* ------------------------------------------------------------------ */

        actionContainer: {

            marginHorizontal:
                16,

            marginBottom:
                12,

        },

        actionText: {

            fontSize:
                14,

            fontWeight:
                "600",

            textAlign:
                "right",

        },

        /* ------------------------------------------------------------------ */
        /* Horizontal List                                                    */
        /* ------------------------------------------------------------------ */

        horizontalContent: {

            paddingHorizontal:
                16,

            paddingBottom:
                8,

        },

        cardWrapper: {

            width:
                220,

        },

        horizontalCard: {

            width:
                "100%",

        },

        separator: {

            width:
                16,

        },

        /* ------------------------------------------------------------------ */
        /* Grid                                                               */
        /* ------------------------------------------------------------------ */

        gridCard: {

            flex:
                1,

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    ProductCollectionSection;