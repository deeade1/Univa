/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/checkout/DeliveryMethodCard.jsx */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme"

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const DELIVERY_ICONS = {
  STANDARD: "truck-outline",
  EXPRESS: "truck-fast-outline",
  SAME_DAY: "clock-fast",
  PICKUP: "store-outline",
  DIGITAL: "download-outline",
};

const formatMoney = (money) => {
  if (!money) return "Free";

  if (typeof money === "number") {
    return `₦${money.toLocaleString()}`;
  }

  if (money.formatted) {
    return money.formatted;
  }

  return `₦${Number(
    money.amount ?? 0
  ).toLocaleString()}`;
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const DeliveryMethodCard = memo(
  ({
    method,

    selected = false,

    editable = true,

    showEstimatedDate = true,

    showCarrier = true,

    showDescription = true,

    compact = false,

    onPress,

    style,
  }) => {
    const { colors } = theme;


    const icon =
      DELIVERY_ICONS[
        method?.type
      ] ??
      "truck-delivery-outline";

    return (
      <Pressable
        disabled={!editable}
        onPress={() =>
          onPress?.(method)
        }
        style={[
          styles.container,
          {
            backgroundColor:
              colors.card,
            borderColor: selected
              ? colors.primary
              : colors.border,
          },
          compact &&
            styles.compactContainer,
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Header */}
        {/* -------------------------------------------------------------- */}

        <View
          style={styles.header}
        >
          <View
            style={
              styles.headerLeft
            }
          >
            <MaterialCommunityIcons
              name={icon}
              size={24}
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
              {method?.name ??
                "Delivery Method"}
            </Text>
          </View>

          {selected && (
            <View
              style={[
                styles.selected,
                {
                  backgroundColor:
                    colors.primary,
                },
              ]}
            >
              <MaterialCommunityIcons
                name="check"
                size={16}
                color="#FFFFFF"
              />
            </View>
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Description */}
        {/* -------------------------------------------------------------- */}

        {showDescription &&
          !!method?.description && (
            <Text
              style={[
                styles.description,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {
                method.description
              }
            </Text>
          )}

        {/* -------------------------------------------------------------- */}
        {/* Delivery Details */}
        {/* -------------------------------------------------------------- */}

        {showCarrier &&
          !!method?.carrier && (
            <View
              style={
                styles.infoRow
              }
            >
              <MaterialCommunityIcons
                name="package-variant-closed"
                size={16}
                color={
                  colors.textSecondary
                }
              />

              <Text
                style={[
                  styles.info,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Carrier:{" "}
                {
                  method.carrier
                }
              </Text>
            </View>
          )}

        {showEstimatedDate &&
          (method?.estimatedDelivery ||
            method?.estimatedDays) && (
            <View
              style={
                styles.infoRow
              }
            >
              <MaterialCommunityIcons
                name="calendar-clock"
                size={16}
                color={
                  colors.textSecondary
                }
              />

              <Text
                style={[
                  styles.info,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                {method?.estimatedDelivery ??
                  `${method?.estimatedDays} day(s)`}
              </Text>
            </View>
          )}

        {/* -------------------------------------------------------------- */}
        {/* Footer */}
        {/* -------------------------------------------------------------- */}

        <View
          style={styles.footer}
        >
          <Text
            style={[
              styles.price,
              {
                color:
                  colors.primary,
              },
            ]}
          >
            {formatMoney(
              method?.price
            )}
          </Text>

          {editable && (
            <MaterialCommunityIcons
              name="chevron-right"
              size={22}
              color={
                colors.textSecondary
              }
            />
          )}
        </View>
      </Pressable>
    );
  }
);

DeliveryMethodCard.displayName =
  "DeliveryMethodCard";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      borderWidth: 1,
      borderRadius: 18,
      padding: 18,
      marginBottom: 16,
    },

    compactContainer: {
      padding: 14,
    },

    header: {
      flexDirection: "row",
      justifyContent:
        "space-between",
      alignItems: "center",
      marginBottom: 12,
    },

    headerLeft: {
      flexDirection: "row",
      alignItems: "center",
      flex: 1,
    },

    title: {
      marginLeft: 10,
      fontSize: 17,
      fontWeight: "700",
      flex: 1,
    },

    description: {
      fontSize: 14,
      lineHeight: 22,
      marginBottom: 12,
    },

    infoRow: {
      flexDirection: "row",
      alignItems: "center",
      marginBottom: 8,
    },

    info: {
      marginLeft: 8,
      fontSize: 14,
    },

    footer: {
      marginTop: 12,
      flexDirection: "row",
      justifyContent:
        "space-between",
      alignItems: "center",
    },

    price: {
      fontSize: 18,
      fontWeight: "700",
    },

    selected: {
      width: 26,
      height: 26,
      borderRadius: 13,
      justifyContent:
        "center",
      alignItems: "center",
    },
  });

export default DeliveryMethodCard;