/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductPurchaseCard.jsx                                                    */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useState,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from "react-native";

import {
  MaterialCommunityIcons,
} from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import ProductPrice from "../products/ProductPrice";
import QuantitySelector from "../cart/QuantitySelector";
import StockBadge from "../common/StockBadge";
import ShippingBadge from "../common/ShippingBadge";
import AvailabilityBadge from "../common/AvailabilityBadge";
import Button from "../common/Button";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductPurchaseCard = memo(
  ({
    product,

    quantity,

    defaultQuantity = 1,

    showPrice = true,

    showStock = true,

    showShipping = true,

    showAvailability = true,

    showQuantitySelector = true,

    showBuyNow = true,

    showAddToCart = true,

    showWishlist = false,

    loading = false,

    disabled = false,

    onQuantityChange,

    onAddToCart,

    onBuyNow,

    onWishlist,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    const [
      internalQuantity,
      setInternalQuantity,
    ] = useState(
      defaultQuantity
    );

    /* ---------------------------------------------------------------------- */
    /* Memoized Values                                                        */
    /* ---------------------------------------------------------------------- */

    const currentQuantity =
      quantity ??
      internalQuantity;

    const inStock =
      product?.inStock ??
      (product?.stock ?? 0) >
        0;

    const stockCount =
      product?.stock ?? 0;

    const shipping =
      product?.shipping;

    const availability =
      product?.availability;

    /* ---------------------------------------------------------------------- */
    /* Quantity                                                               */
    /* ---------------------------------------------------------------------- */

    const handleQuantityChange =
      useCallback(
        (value) => {
          setInternalQuantity(
            value
          );

          onQuantityChange?.(
            value
          );
        },
        [
          onQuantityChange,
        ]
      );

    /* ---------------------------------------------------------------------- */
    /* Purchase Actions                                                       */
    /* ---------------------------------------------------------------------- */

    const handleAddToCart =
      useCallback(() => {
        onAddToCart?.(
          product,
          currentQuantity
        );
      }, [
        product,
        currentQuantity,
        onAddToCart,
      ]);

    const handleBuyNow =
      useCallback(() => {
        onBuyNow?.(
          product,
          currentQuantity
        );
      }, [
        product,
        currentQuantity,
        onBuyNow,
      ]);

    const handleWishlist =
      useCallback(() => {
        onWishlist?.(
          product
        );
      }, [
        product,
        onWishlist,
      ]);

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,
          {
            backgroundColor:
              colors.card,

            borderColor:
              colors.border,
          },
          style,
        ]}
      >        {/* -------------------------------------------------------------- */}
        {/* Price                                                          */}
        {/* -------------------------------------------------------------- */}

        {showPrice && (
          <ProductPrice
            price={
              product?.price
            }
            salePrice={
              product?.salePrice
            }
            discount={
              product?.discount
            }
            currency={
              product?.currency
            }
            size="large"
            style={
              styles.price
            }
          />
        )}

        {/* -------------------------------------------------------------- */}
        {/* Stock Badge                                                    */}
        {/* -------------------------------------------------------------- */}

        {showStock && (
          <View
            style={
              styles.section
            }
          >
            <StockBadge
              inStock={
                inStock
              }
              quantity={
                stockCount
              }
            />
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Availability                                                   */}
        {/* -------------------------------------------------------------- */}

        {showAvailability &&
          availability && (
            <View
              style={
                styles.section
              }
            >
              <AvailabilityBadge
                status={
                  availability
                }
              />
            </View>
          )}

        {/* -------------------------------------------------------------- */}
        {/* Shipping Information                                           */}
        {/* -------------------------------------------------------------- */}

        {showShipping &&
          shipping && (
            <View
              style={
                styles.shippingContainer
              }
            >
              <ShippingBadge
                shipping={
                  shipping
                }
              />

              {!!shipping
                ?.estimatedDelivery && (
                <View
                  style={
                    styles.deliveryRow
                  }
                >
                  <MaterialCommunityIcons
                    name="truck-delivery-outline"
                    size={18}
                    color={
                      colors.primary
                    }
                  />

                  <Text
                    style={[
                      styles.deliveryText,
                      {
                        color:
                          colors.textSecondary,
                      },
                    ]}
                  >
                    Estimated delivery:{" "}
                    {
                      shipping.estimatedDelivery
                    }
                  </Text>
                </View>
              )}

              {!!shipping
                ?.freeShipping && (
                <View
                  style={
                    styles.deliveryRow
                  }
                >
                  <MaterialCommunityIcons
                    name="check-circle"
                    size={18}
                    color="#22C55E"
                  />

                  <Text
                    style={[
                      styles.freeShipping,
                    ]}
                  >
                    Free Shipping
                  </Text>
                </View>
              )}
            </View>
          )}

        {/* -------------------------------------------------------------- */}
        {/* Quantity Selector                                              */}
        {/* -------------------------------------------------------------- */}

        {showQuantitySelector && (
          <View
            style={
              styles.quantitySection
            }
          >
            <Text
              style={[
                styles.sectionTitle,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              Quantity
            </Text>

            <QuantitySelector
              value={
                currentQuantity
              }
              min={1}
              max={
                Math.max(
                  stockCount,
                  1
                )
              }
              disabled={
                !inStock ||
                disabled
              }
              onChange={
                handleQuantityChange
              }
            />
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Part 3                                                         */}
        {/* Purchase buttons, wishlist action and extra information        */}
        {/* -------------------------------------------------------------- */}
                {/* -------------------------------------------------------------- */}
        {/* Purchase Actions                                               */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.actions}>
          {showAddToCart && (
            <Button
              title="Add to Cart"
              icon="cart-plus"
              loading={loading}
              disabled={
                disabled || !inStock
              }
              onPress={
                handleAddToCart
              }
              style={styles.cartButton}
            />
          )}

          {showBuyNow && (
            <Button
              title="Buy Now"
              icon="lightning-bolt"
              variant="outline"
              loading={loading}
              disabled={
                disabled || !inStock
              }
              onPress={
                handleBuyNow
              }
              style={[
                styles.buyNowButton,
                showAddToCart &&
                  styles.buttonSpacing,
              ]}
            />
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Wishlist Button                                                */}
        {/* -------------------------------------------------------------- */}

        {showWishlist && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Add product to wishlist"
            disabled={loading}
            onPress={
              handleWishlist
            }
            style={[
              styles.wishlistButton,
              {
                borderColor:
                  colors.border,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="heart-outline"
              size={20}
              color={colors.primary}
            />

            <Text
              style={[
                styles.wishlistText,
                {
                  color:
                    colors.primary,
                },
              ]}
            >
              Add to Wishlist
            </Text>
          </Pressable>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Purchase Benefits                                              */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.benefits}>
          <View
            style={styles.benefitRow}
          >
            <MaterialCommunityIcons
              name="shield-check"
              size={18}
              color="#22C55E"
            />

            <Text
              style={[
                styles.benefitText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Secure checkout &
              encrypted payment
            </Text>
          </View>

          <View
            style={styles.benefitRow}
          >
            <MaterialCommunityIcons
              name="refresh"
              size={18}
              color="#3B82F6"
            />

            <Text
              style={[
                styles.benefitText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Easy returns where
              eligible
            </Text>
          </View>

          <View
            style={styles.benefitRow}
          >
            <MaterialCommunityIcons
              name="shield-star-outline"
              size={18}
              color="#F59E0B"
            />

            <Text
              style={[
                styles.benefitText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Quality assurance from
              verified sellers
            </Text>
          </View>
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Additional Information                                         */}
        {/* -------------------------------------------------------------- */}

        {(product?.warranty ||
          product?.returnPolicy) && (
          <View
            style={styles.infoSection}
          >
            {!!product?.warranty && (
              <View
                style={
                  styles.infoRow
                }
              >
                <MaterialCommunityIcons
                  name="shield-check-outline"
                  size={18}
                  color={
                    colors.primary
                  }
                />

                <Text
                  style={[
                    styles.infoText,
                    {
                      color:
                        colors.text,
                    },
                  ]}
                >
                  Warranty:{" "}
                  {
                    product.warranty
                  }
                </Text>
              </View>
            )}

            {!!product
              ?.returnPolicy && (
              <View
                style={
                  styles.infoRow
                }
              >
                <MaterialCommunityIcons
                  name="package-variant-closed"
                  size={18}
                  color={
                    colors.primary
                  }
                />

                <Text
                  style={[
                    styles.infoText,
                    {
                      color:
                        colors.text,
                    },
                  ]}
                >
                  Returns:{" "}
                  {
                    product.returnPolicy
                  }
                </Text>
              </View>
            )}
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Part 4                                                         */}
        {/* PropTypes, defaultProps, styles and export                     */}
        {/* -------------------------------------------------------------- */}
      </View>
    );
  }
);

ProductPurchaseCard.displayName =
  "ProductPurchaseCard";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductPurchaseCard.propTypes = {
  product: PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    price: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    salePrice:
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
      ]),

    discount:
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
      ]),

    currency:
      PropTypes.string,

    stock:
      PropTypes.number,

    inStock:
      PropTypes.bool,

    shipping:
      PropTypes.object,

    availability:
      PropTypes.string,

    warranty:
      PropTypes.string,

    returnPolicy:
      PropTypes.string,
  }),

  quantity:
    PropTypes.number,

  defaultQuantity:
    PropTypes.number,

  showPrice:
    PropTypes.bool,

  showStock:
    PropTypes.bool,

  showShipping:
    PropTypes.bool,

  showAvailability:
    PropTypes.bool,

  showQuantitySelector:
    PropTypes.bool,

  showBuyNow:
    PropTypes.bool,

  showAddToCart:
    PropTypes.bool,

  showWishlist:
    PropTypes.bool,

  loading:
    PropTypes.bool,

  disabled:
    PropTypes.bool,

  onQuantityChange:
    PropTypes.func,

  onAddToCart:
    PropTypes.func,

  onBuyNow:
    PropTypes.func,

  onWishlist:
    PropTypes.func,

  style:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ProductPurchaseCard.defaultProps = {
  product: null,

  quantity: undefined,

  defaultQuantity: 1,

  showPrice: true,

  showStock: true,

  showShipping: true,

  showAvailability: true,

  showQuantitySelector: true,

  showBuyNow: true,

  showAddToCart: true,

  showWishlist: false,

  loading: false,

  disabled: false,

  onQuantityChange: null,

  onAddToCart: null,

  onBuyNow: null,

  onWishlist: null,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      borderWidth: 1,

      borderRadius: 20,

      padding: 18,

      marginVertical: 16,
    },

    /* ------------------------------------------------------------------ */
    /* Price                                                              */
    /* ------------------------------------------------------------------ */

    price: {
      marginBottom: 18,
    },

    section: {
      marginBottom: 14,
    },

    sectionTitle: {
      fontSize: 15,

      fontWeight: "700",

      marginBottom: 10,
    },

    /* ------------------------------------------------------------------ */
    /* Shipping                                                           */
    /* ------------------------------------------------------------------ */

    shippingContainer: {
      marginBottom: 18,
    },

    deliveryRow: {
      flexDirection: "row",

      alignItems: "center",

      marginTop: 10,
    },

    deliveryText: {
      marginLeft: 8,

      fontSize: 13,

      flex: 1,
    },

    freeShipping: {
      marginLeft: 8,

      color: "#22C55E",

      fontWeight: "700",

      fontSize: 13,
    },

    /* ------------------------------------------------------------------ */
    /* Quantity                                                           */
    /* ------------------------------------------------------------------ */

    quantitySection: {
      marginBottom: 22,
    },

    /* ------------------------------------------------------------------ */
    /* Buttons                                                            */
    /* ------------------------------------------------------------------ */

    actions: {
      flexDirection: "row",

      marginBottom: 18,
    },

    cartButton: {
      flex: 1,
    },

    buyNowButton: {
      flex: 1,
    },

    buttonSpacing: {
      marginLeft: 12,
    },

    wishlistButton: {
      flexDirection: "row",

      alignItems: "center",

      justifyContent: "center",

      borderWidth: 1,

      borderRadius: 12,

      paddingVertical: 14,

      marginBottom: 22,
    },

    wishlistText: {
      marginLeft: 8,

      fontSize: 15,

      fontWeight: "700",
    },

    /* ------------------------------------------------------------------ */
    /* Benefits                                                           */
    /* ------------------------------------------------------------------ */

    benefits: {
      borderTopWidth:
        StyleSheet.hairlineWidth,

      borderColor: "#E5E7EB",

      paddingTop: 18,
    },

    benefitRow: {
      flexDirection: "row",

      alignItems: "center",

      marginBottom: 12,
    },

    benefitText: {
      marginLeft: 10,

      flex: 1,

      fontSize: 13,

      lineHeight: 18,
    },

    /* ------------------------------------------------------------------ */
    /* Warranty / Returns                                                 */
    /* ------------------------------------------------------------------ */

    infoSection: {
      marginTop: 10,

      paddingTop: 16,

      borderTopWidth:
        StyleSheet.hairlineWidth,

      borderColor: "#E5E7EB",
    },

    infoRow: {
      flexDirection: "row",

      alignItems: "center",

      marginBottom: 10,
    },

    infoText: {
      marginLeft: 10,

      flex: 1,

      fontSize: 13,

      lineHeight: 18,
    },
  });

export default ProductPurchaseCard;