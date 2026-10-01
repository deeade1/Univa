/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductDeliveryCard.jsx                                                    */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductDeliveryCard = memo(
  ({
    product,

    address,

    showEstimate = true,

    showShippingCost = true,

    showCourier = true,

    showPickup = true,

    showChangeAddress = true,

    onChangeAddress,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Memoized Values                                                        */
    /* ---------------------------------------------------------------------- */

    const deliveryEstimate =
      useMemo(
        () =>
          product
            ?.deliveryEstimate ??
          "2–5 business days",
        [
          product?.deliveryEstimate,
        ]
      );

    const shippingCost =
      useMemo(
        () =>
          product?.shippingCost ??
          0,
        [
          product?.shippingCost,
        ]
      );

    const courier = useMemo(
      () =>
        product?.courier ??
        "Standard Delivery",
      [product?.courier]
    );

    const pickupAvailable =
      useMemo(
        () =>
          product?.pickupAvailable ??
          false,
        [
          product?.pickupAvailable,
        ]
      );

    const freeShipping =
      useMemo(
        () =>
          product?.freeShipping ??
          shippingCost === 0,
        [
          product?.freeShipping,
          shippingCost,
        ]
      );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleAddressPress =
      useCallback(() => {
        onChangeAddress?.();
      }, [onChangeAddress]);

    /* ---------------------------------------------------------------------- */
    /* Dynamic Colors                                                         */
    /* ---------------------------------------------------------------------- */

    const successColor = colors.success || "#22C55E";
    const errorColor = colors.error || "#EF4444";
    const successContainerColor = colors.successContainer || "#DCFCE7";
    const surfaceVariantColor = colors.surfaceVariant || "#F8FAFC";

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
      >
        {/* -------------------------------------------------------------- */}
        {/* Header                                                         */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.header}>
          <MaterialCommunityIcons
            name="truck-fast-outline"
            size={22}
            color={
              colors.primary
            }
          />

          <Text
            style={[
              styles.title,
              {
                color:
                  colors.text,
              },
            ]}
          >
            Delivery Information
          </Text>
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Delivery Address                                               */}
        {/* -------------------------------------------------------------- */}

        <View
          style={styles.section}
        >
          <View
            style={
              styles.sectionHeader
            }
          >
            <MaterialCommunityIcons
              name="map-marker-outline"
              size={18}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.sectionTitle,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              Deliver to
            </Text>
          </View>

          <Text
            numberOfLines={2}
            style={[
              styles.address,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            {address ??
              "Select a delivery address"}
          </Text>

          {showChangeAddress && (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Change delivery address"
              onPress={
                handleAddressPress
              }
              style={
                styles.changeAddress
              }
            >
              <MaterialCommunityIcons
                name="pencil-outline"
                size={16}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.changeAddressText,
                  {
                    color:
                      colors.primary,
                  },
                ]}
              >
                Change Address
              </Text>
            </Pressable>
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Delivery Estimate                                              */}
        {/* -------------------------------------------------------------- */}

        {showEstimate && (
          <View
            style={styles.infoRow}
          >
            <View
              style={
                styles.infoLeft
              }
            >
              <MaterialCommunityIcons
                name="clock-outline"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.infoLabel,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                Estimated Delivery
              </Text>
            </View>

            <Text
              style={[
                styles.infoValue,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {deliveryEstimate}
            </Text>
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Shipping Cost                                                  */}
        {/* -------------------------------------------------------------- */}

        {showShippingCost && (
          <View
            style={styles.infoRow}
          >
            <View
              style={
                styles.infoLeft
              }
            >
              <MaterialCommunityIcons
                name="cash"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.infoLabel,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                Shipping
              </Text>
            </View>

            {freeShipping ? (
              <View
                style={[
                  styles.freeShippingBadge,
                  {
                    backgroundColor:
                      successContainerColor,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name="tag-outline"
                  size={14}
                  color={successColor}
                />

                <Text
                  style={[
                    styles.freeShippingText,
                    {
                      color: successColor,
                    },
                  ]}
                >
                  FREE
                </Text>
              </View>
            ) : (
              <Text
                style={[
                  styles.infoValue,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                {product?.currency ??
                  "₦"}
                {shippingCost}
              </Text>
            )}
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Courier                                                        */}
        {/* -------------------------------------------------------------- */}

        {showCourier && (
          <View
            style={styles.infoRow}
          >
            <View
              style={
                styles.infoLeft
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
                  styles.infoLabel,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                Courier
              </Text>
            </View>

            <Text
              style={[
                styles.infoValue,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {courier}
            </Text>
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Pickup Availability                                            */}
        {/* -------------------------------------------------------------- */}

        {showPickup && (
          <View
            style={styles.infoRow}
          >
            <View
              style={
                styles.infoLeft
              }
            >
              <MaterialCommunityIcons
                name={
                  pickupAvailable
                    ? "store-outline"
                    : "store-off-outline"
                }
                size={18}
                color={
                  pickupAvailable
                    ? successColor
                    : errorColor
                }
              />

              <Text
                style={[
                  styles.infoLabel,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                Store Pickup
              </Text>
            </View>

            <Text
              style={[
                styles.infoValue,
                {
                  color:
                    pickupAvailable
                      ? successColor
                      : errorColor,
                },
              ]}
            >
              {pickupAvailable
                ? "Available"
                : "Unavailable"}
            </Text>
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Delivery Notes                                                 */}
        {/* -------------------------------------------------------------- */}

        {!!product
          ?.deliveryNotes && (
          <View
            style={[
              styles.notesContainer,
              {
                backgroundColor:
                  surfaceVariantColor,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="information-outline"
              size={18}
              color={
                colors.primary
              }
              style={
                styles.notesIcon
              }
            />

            <Text
              style={[
                styles.notesText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {
                product.deliveryNotes
              }
            </Text>
          </View>
        )}
      </View>
    );
  }
);

ProductDeliveryCard.displayName =
  "ProductDeliveryCard";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductDeliveryCard.propTypes = {
  /**
   * Product information
   */
  product: PropTypes.shape({
    deliveryEstimate:
      PropTypes.string,

    shippingCost:
      PropTypes.oneOfType([
        PropTypes.number,
        PropTypes.string,
      ]),

    courier:
      PropTypes.string,

    currency:
      PropTypes.string,

    freeShipping:
      PropTypes.bool,

    pickupAvailable:
      PropTypes.bool,

    deliveryNotes:
      PropTypes.string,
  }),

  /**
   * Delivery address
   */
  address: PropTypes.string,

  /**
   * Display options
   */
  showEstimate:
    PropTypes.bool,

  showShippingCost:
    PropTypes.bool,

  showCourier:
    PropTypes.bool,

  showPickup:
    PropTypes.bool,

  showChangeAddress:
    PropTypes.bool,

  /**
   * Callbacks
   */
  onChangeAddress:
    PropTypes.func,

  /**
   * Optional style
   */
  style:
    PropTypes.oneOfType([
      PropTypes.object,
      PropTypes.array,
    ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ProductDeliveryCard.defaultProps = {
  product: null,

  address: null,

  showEstimate: true,

  showShippingCost: true,

  showCourier: true,

  showPickup: true,

  showChangeAddress: true,

  onChangeAddress: null,

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
    /* Header                                                             */
    /* ------------------------------------------------------------------ */

    header: {
      flexDirection: "row",

      alignItems: "center",

      marginBottom: 20,
    },

    title: {
      marginLeft: 10,

      fontSize: 18,

      fontWeight: "700",
    },

    /* ------------------------------------------------------------------ */
    /* Sections                                                           */
    /* ------------------------------------------------------------------ */

    section: {
      marginBottom: 18,
    },

    sectionHeader: {
      flexDirection: "row",

      alignItems: "center",

      marginBottom: 8,
    },

    sectionTitle: {
      marginLeft: 8,

      fontSize: 15,

      fontWeight: "700",
    },

    address: {
      fontSize: 14,

      lineHeight: 20,
    },

    changeAddress: {
      flexDirection: "row",

      alignItems: "center",

      alignSelf: "flex-start",

      marginTop: 10,
    },

    changeAddressText: {
      marginLeft: 6,

      fontSize: 14,

      fontWeight: "600",
    },

    /* ------------------------------------------------------------------ */
    /* Information Rows                                                   */
    /* ------------------------------------------------------------------ */

    infoRow: {
      flexDirection: "row",

      alignItems: "center",

      justifyContent:
        "space-between",

      paddingVertical: 12,
    },

    infoLeft: {
      flexDirection: "row",

      alignItems: "center",

      flex: 1,
    },

    infoLabel: {
      marginLeft: 10,

      fontSize: 14,

      fontWeight: "600",
    },

    infoValue: {
      fontSize: 14,

      fontWeight: "500",

      textAlign: "right",

      marginLeft: 12,

      flexShrink: 1,
    },

    /* ------------------------------------------------------------------ */
    /* Free Shipping Badge                                                */
    /* ------------------------------------------------------------------ */

    freeShippingBadge: {
      flexDirection: "row",

      alignItems: "center",

      paddingHorizontal: 10,

      paddingVertical: 5,

      borderRadius: 999,
    },

    freeShippingText: {
      marginLeft: 4,

      fontSize: 12,

      fontWeight: "700",
    },

    /* ------------------------------------------------------------------ */
    /* Notes                                                              */
    /* ------------------------------------------------------------------ */

    notesContainer: {
      flexDirection: "row",

      alignItems: "flex-start",

      marginTop: 18,

      padding: 14,

      borderRadius: 12,
    },

    notesIcon: {
      marginTop: 2,
    },

    notesText: {
      flex: 1,

      marginLeft: 10,

      fontSize: 13,

      lineHeight: 20,
    },
  });

export default ProductDeliveryCard;

