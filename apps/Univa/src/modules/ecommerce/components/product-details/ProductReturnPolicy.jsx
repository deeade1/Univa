/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductReturnPolicy.jsx                                                    */
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
/* Policy Item                                                                */
/* -------------------------------------------------------------------------- */

const PolicyItem = memo(
  ({
    icon,
    title,
    value,
    color,
    colors,
  }) => (
    <View
      style={styles.policyItem}
    >
      <MaterialCommunityIcons
        name={icon}
        size={20}
        color={
          color ??
          colors.primary
        }
      />

      <View
        style={
          styles.policyContent
        }
      >
        <Text
          style={[
            styles.policyTitle,
            {
              color:
                colors.text,
            },
          ]}
        >
          {title}
        </Text>

        <Text
          style={[
            styles.policyValue,
            {
              color:
                colors
                  .textSecondary,
            },
          ]}
        >
          {value}
        </Text>
      </View>
    </View>
  )
);

PolicyItem.displayName =
  "PolicyItem";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductReturnPolicy =
  memo(
    ({
      product,

      showWindow = true,

      showCondition = true,

      showRefund = true,

      showExchange = true,

      showProcess = true,

      showLearnMore = true,

      onPolicyPress,

      style,
    }) => {
      const { colors } =
        theme;

      /* ------------------------------------------------------------------ */
      /* Memoized Data                                                      */
      /* ------------------------------------------------------------------ */

      const returnWindow =
        useMemo(
          () =>
            product
              ?.returnWindow ??
            "30 Days",
          [product]
        );

      const refundMethod =
        useMemo(
          () =>
            product
              ?.refundMethod ??
            "Original Payment Method",
          [product]
        );

      const exchangeAvailable =
        product?.exchange ??
        true;

      const returnCondition =
        product?.condition ??
        "Unused and in original packaging";

      const handleLearnMore =
        useCallback(() => {
          onPolicyPress?.(
            product
          );
        }, [
          product,
          onPolicyPress,
        ]);

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

          <View
            style={
              styles.header
            }
          >
            <MaterialCommunityIcons
              name="package-return"
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
              Return Policy
            </Text>
          </View>
                    {/* -------------------------------------------------------------- */}
          {/* Return Window                                                  */}
          {/* -------------------------------------------------------------- */}

          {showWindow && (
            <PolicyItem
              icon="calendar-refresh"
              title="Return Window"
              value={`Eligible for returns within ${returnWindow} of delivery.`}
              colors={colors}
            />
          )}

          {/* -------------------------------------------------------------- */}
          {/* Return Condition                                               */}
          {/* -------------------------------------------------------------- */}

          {showCondition && (
            <PolicyItem
              icon="package-variant-closed-check"
              title="Condition"
              value={
                returnCondition
              }
              colors={colors}
            />
          )}

          {/* -------------------------------------------------------------- */}
          {/* Refund Method                                                  */}
          {/* -------------------------------------------------------------- */}

          {showRefund && (
            <PolicyItem
              icon="cash-refund"
              title="Refund"
              value={
                refundMethod
              }
              colors={colors}
            />
          )}

          {/* -------------------------------------------------------------- */}
          {/* Exchange                                                       */}
          {/* -------------------------------------------------------------- */}

          {showExchange && (
            <PolicyItem
              icon={
                exchangeAvailable
                  ? "swap-horizontal"
                  : "close-circle-outline"
              }
              title="Exchange"

              value={
                exchangeAvailable
                  ? "Exchange available for eligible items."
                  : "Exchange is not available for this product."
              }

              color={
                exchangeAvailable
                  ? "#22C55E"
                  : "#EF4444"
              }

              colors={colors}
            />
          )}

          {/* -------------------------------------------------------------- */}
          {/* Return Process                                                 */}
          {/* -------------------------------------------------------------- */}

          {showProcess && (
            <View
              style={[
                styles.processCard,
                {
                  backgroundColor:
                    colors.background,
                },
              ]}
            >
              <Text
                style={[
                  styles.processTitle,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                Return Process
              </Text>

              <View
                style={
                  styles.stepRow
                }
              >
                <MaterialCommunityIcons
                  name="numeric-1-circle"
                  size={20}
                  color={
                    colors.primary
                  }
                />

                <Text
                  style={[
                    styles.stepText,
                    {
                      color:
                        colors.textSecondary,
                    },
                  ]}
                >
                  Request a return
                  from your order
                  history.
                </Text>
              </View>

              <View
                style={
                  styles.stepRow
                }
              >
                <MaterialCommunityIcons
                  name="numeric-2-circle"
                  size={20}
                  color={
                    colors.primary
                  }
                />

                <Text
                  style={[
                    styles.stepText,
                    {
                      color:
                        colors.textSecondary,
                    },
                  ]}
                >
                  Package the item
                  securely and attach
                  the return label.
                </Text>
              </View>

              <View
                style={
                  styles.stepRow
                }
              >
                <MaterialCommunityIcons
                  name="numeric-3-circle"
                  size={20}
                  color={
                    colors.primary
                  }
                />

                <Text
                  style={[
                    styles.stepText,
                    {
                      color:
                        colors.textSecondary,
                    },
                  ]}
                >
                  After inspection,
                  your refund or
                  exchange will be
                  processed.
                </Text>
              </View>
            </View>
          )}
                    {/* -------------------------------------------------------------- */}
          {/* Important Notes                                                */}
          {/* -------------------------------------------------------------- */}

          <View
            style={[
              styles.notesContainer,
              {
                borderTopColor:
                  colors.border,
              },
            ]}
          >
            <View
              style={styles.noteRow}
            >
              <MaterialCommunityIcons
                name="information-outline"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.noteText,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Items must be
                returned with all
                original accessories,
                manuals and packaging.
              </Text>
            </View>

            <View
              style={styles.noteRow}
            >
              <MaterialCommunityIcons
                name="shield-check-outline"
                size={18}
                color="#22C55E"
              />

              <Text
                style={[
                  styles.noteText,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Eligible refunds are
                processed after the
                returned item passes
                inspection.
              </Text>
            </View>
          </View>

          {/* -------------------------------------------------------------- */}
          {/* Non-returnable Items                                           */}
          {/* -------------------------------------------------------------- */}

          <View
            style={[
              styles.restrictedContainer,
              {
                backgroundColor:
                  colors.background,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="alert-circle-outline"
              size={20}
              color="#F59E0B"
            />

            <View
              style={
                styles.restrictedContent
              }
            >
              <Text
                style={[
                  styles.restrictedTitle,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                Non-returnable Items
              </Text>

              <Text
                style={[
                  styles.restrictedText,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Personal care items,
                digital products,
                customised products
                and opened consumables
                may not qualify for
                returns.
              </Text>
            </View>
          </View>

          {/* -------------------------------------------------------------- */}
          {/* Learn More                                                     */}
          {/* -------------------------------------------------------------- */}

          {showLearnMore && (
            <Pressable
              onPress={
                handleLearnMore
              }
              style={[
                styles.learnButton,
                {
                  borderColor:
                    colors.primary,
                },
              ]}
            >
              <MaterialCommunityIcons
                name="file-document-outline"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.learnButtonText,
                  {
                    color:
                      colors.primary,
                    },
                  ]}
              >
                View Full Return Policy
              </Text>

              <MaterialCommunityIcons
                name="chevron-right"
                size={18}
                color={
                  colors.primary
                }
              />
            </Pressable>
          )}
        </View>
      );
    }
);

ProductReturnPolicy.displayName =
  "ProductReturnPolicy";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const productShape = PropTypes.shape({
  returnWindow:
    PropTypes.string,

  refundMethod:
    PropTypes.string,

  exchange:
    PropTypes.bool,

  condition:
    PropTypes.string,
});

PolicyItem.propTypes = {
  icon:
    PropTypes.string
      .isRequired,

  title:
    PropTypes.string
      .isRequired,

  value:
    PropTypes.string
      .isRequired,

  color:
    PropTypes.string,

  colors:
    PropTypes.object
      .isRequired,
};

PolicyItem.defaultProps = {
  color: null,
};

ProductReturnPolicy.propTypes =
  {
    product:
      productShape,

    showWindow:
      PropTypes.bool,

    showCondition:
      PropTypes.bool,

    showRefund:
      PropTypes.bool,

    showExchange:
      PropTypes.bool,

    showProcess:
      PropTypes.bool,

    showLearnMore:
      PropTypes.bool,

    onPolicyPress:
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

ProductReturnPolicy.defaultProps =
  {
    product: null,

    showWindow: true,

    showCondition: true,

    showRefund: true,

    showExchange: true,

    showProcess: true,

    showLearnMore: true,

    onPolicyPress:
      null,

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

      marginBottom: 18,
    },

    title: {
      marginLeft: 10,

      fontSize: 18,

      fontWeight: "700",
    },

    /* ------------------------------------------------------------------ */
    /* Policy Item                                                        */
    /* ------------------------------------------------------------------ */

    policyItem: {
      flexDirection: "row",

      alignItems: "flex-start",

      marginBottom: 18,
    },

    policyContent: {
      flex: 1,

      marginLeft: 12,
    },

    policyTitle: {
      fontSize: 15,

      fontWeight: "700",
    },

    policyValue: {
      marginTop: 4,

      fontSize: 13,

      lineHeight: 20,
    },

    /* ------------------------------------------------------------------ */
    /* Process Card                                                       */
    /* ------------------------------------------------------------------ */

    processCard: {
      borderRadius: 14,

      padding: 16,

      marginTop: 20,
    },

    processTitle: {
      fontSize: 16,

      fontWeight: "700",

      marginBottom: 14,
    },

    stepRow: {
      flexDirection: "row",

      alignItems: "flex-start",

      marginBottom: 12,
    },

    stepText: {
      flex: 1,

      marginLeft: 10,

      fontSize: 13,

      lineHeight: 20,
    },

    /* ------------------------------------------------------------------ */
    /* Notes                                                              */
    /* ------------------------------------------------------------------ */

    notesContainer: {
      borderTopWidth: 1,

      marginTop: 22,

      paddingTop: 18,
    },

    noteRow: {
      flexDirection: "row",

      alignItems: "flex-start",

      marginBottom: 12,
    },

    noteText: {
      flex: 1,

      marginLeft: 10,

      fontSize: 13,

      lineHeight: 20,
    },

    /* ------------------------------------------------------------------ */
    /* Restricted Items                                                   */
    /* ------------------------------------------------------------------ */

    restrictedContainer: {
      flexDirection: "row",

      alignItems: "flex-start",

      borderRadius: 14,

      padding: 16,

      marginTop: 18,
    },

    restrictedContent: {
      flex: 1,

      marginLeft: 12,
    },

    restrictedTitle: {
      fontSize: 15,

      fontWeight: "700",

      marginBottom: 6,
    },

    restrictedText: {
      fontSize: 13,

      lineHeight: 20,
    },

    /* ------------------------------------------------------------------ */
    /* Learn Button                                                       */
    /* ------------------------------------------------------------------ */

    learnButton: {
      flexDirection: "row",

      alignItems: "center",

      justifyContent:
        "center",

      borderWidth: 1,

      borderRadius: 12,

      paddingVertical: 14,

      marginTop: 24,
    },

    learnButtonText: {
      flex: 1,

      textAlign: "center",

      fontSize: 14,

      fontWeight: "700",

      marginHorizontal: 10,
    },
  });

export default ProductReturnPolicy;