/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/products/ShippingInformation.jsx */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import Divider from "../common/Divider";
import IconLabel from "../common/IconLabel";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ShippingInformation = memo(({

  /* ---------------------------------------------------------------------- */
  /* Shipping Origin & Destination                                          */
  /* ---------------------------------------------------------------------- */

  shipsFrom = "Warehouse",

  shipsTo = "Nationwide",

  /* ---------------------------------------------------------------------- */
  /* Carrier Information                                                    */
  /* ---------------------------------------------------------------------- */

  courier = null,

  shippingMethod = "Standard Shipping",

  dispatchTime = "Within 24 hours",

  /* ---------------------------------------------------------------------- */
  /* Package Information                                                    */
  /* ---------------------------------------------------------------------- */

  trackingAvailable = true,

  internationalShipping = false,

  weight = null,

  dimensions = null,

  /* ---------------------------------------------------------------------- */
  /* Additional Notes                                                       */
  /* ---------------------------------------------------------------------- */

  shippingNotes = null,

  /* ---------------------------------------------------------------------- */
  /* Visibility                                                             */
  /* ---------------------------------------------------------------------- */

  showCourier = true,

  showTracking = true,

  showWeight = true,

  showDimensions = true,

  showInternational = true,

  showNotes = true,

  /* ---------------------------------------------------------------------- */
  /* Styling                                                                */
  /* ---------------------------------------------------------------------- */

  style,

}) => {

  const {
    colors,
    spacing,
  } = theme;

  /* ---------------------------------------------------------------------- */
  /* Computed Values                                                        */
  /* ---------------------------------------------------------------------- */

  const hasPackageInfo = useMemo(
    () => Boolean(weight || dimensions),
    [weight, dimensions]
  );

  const hasNotes = useMemo(
    () => Boolean(shippingNotes?.trim()),
    [shippingNotes]
  );
    /* ---------------------------------------------------------------------- */
  /* Component                                                              */
  /* ---------------------------------------------------------------------- */

  return (
    <View
      style={[
        styles.container,
        style,
      ]}
    >
      {/* ------------------------------------------------------------------ */}
      {/* Section Title                                                      */}
      {/* ------------------------------------------------------------------ */}

      <Text
        style={[
          styles.title,
          {
            color: colors.text,
          },
        ]}
      >
        Shipping Information
      </Text>

      {/* ------------------------------------------------------------------ */}
      {/* Shipping Origin                                                    */}
      {/* ------------------------------------------------------------------ */}

      <IconLabel
        icon="warehouse"
        label={`Ships From: ${shipsFrom}`}
        iconColor={colors.primary}
        textStyle={[
          styles.infoText,
          {
            color: colors.text,
          },
        ]}
        style={styles.infoRow}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Shipping Destination                                               */}
      {/* ------------------------------------------------------------------ */}

      <IconLabel
        icon="map-marker-radius-outline"
        label={`Ships To: ${shipsTo}`}
        iconColor={colors.primary}
        textStyle={[
          styles.infoText,
          {
            color: colors.text,
          },
        ]}
        style={styles.infoRow}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Courier / Carrier                                                  */}
      {/* ------------------------------------------------------------------ */}

      {showCourier && !!courier && (
        <IconLabel
          icon="truck-fast-outline"
          label={`Courier: ${courier}`}
          iconColor={colors.primary}
          textStyle={[
            styles.infoText,
            {
              color: colors.text,
            },
          ]}
          style={styles.infoRow}
        />
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Shipping Method                                                    */}
      {/* ------------------------------------------------------------------ */}

      <IconLabel
        icon="truck-delivery-outline"
        label={`Shipping Method: ${shippingMethod}`}
        iconColor={colors.primary}
        textStyle={[
          styles.infoText,
          {
            color: colors.text,
          },
        ]}
        style={styles.infoRow}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Dispatch Time                                                      */}
      {/* ------------------------------------------------------------------ */}

      <IconLabel
        icon="clock-outline"
        label={`Dispatch Time: ${dispatchTime}`}
        iconColor={colors.primary}
        textStyle={[
          styles.infoText,
          {
            color: colors.text,
          },
        ]}
        style={styles.infoRow}
      />

      <Divider spacing={spacing.md} />
            {/* ------------------------------------------------------------------ */}
      {/* Additional Shipping Information                                    */}
      {/* ------------------------------------------------------------------ */}

      {showTracking && (
        <IconLabel
          icon={
            trackingAvailable
              ? "map-marker-path"
              : "map-marker-off-outline"
          }
          label={
            trackingAvailable
              ? "Order Tracking Available"
              : "Tracking Not Available"
          }
          iconColor={
            trackingAvailable
              ? colors.success ?? "#16A34A"
              : colors.warning ?? "#F59E0B"
          }
          textStyle={[
            styles.infoText,
            {
              color: colors.text,
            },
          ]}
          style={styles.infoRow}
        />
      )}

      {showInternational && (
        <IconLabel
          icon="earth"
          label={
            internationalShipping
              ? "International Shipping Available"
              : "Domestic Shipping Only"
          }
          iconColor={
            internationalShipping
              ? colors.success ?? "#16A34A"
              : colors.primary
          }
          textStyle={[
            styles.infoText,
            {
              color: colors.text,
            },
          ]}
          style={styles.infoRow}
        />
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Package Information                                                */}
      {/* ------------------------------------------------------------------ */}

      {hasPackageInfo && (
        <>
          <Divider spacing={spacing.md} />

          <View style={styles.packageContainer}>
            <Text
              style={[
                styles.packageTitle,
                {
                  color: colors.text,
                },
              ]}
            >
              Package Information
            </Text>

            {showWeight && !!weight && (
              <IconLabel
                icon="weight-kilogram"
                label={`Weight: ${weight}`}
                iconColor={colors.primary}
                textStyle={[
                  styles.featureText,
                  {
                    color: colors.text,
                  },
                ]}
                style={styles.featureItem}
              />
            )}

            {showDimensions && !!dimensions && (
              <IconLabel
                icon="resize"
                label={`Dimensions: ${dimensions}`}
                iconColor={colors.primary}
                textStyle={[
                  styles.featureText,
                  {
                    color: colors.text,
                  },
                ]}
                style={styles.featureItem}
              />
            )}
          </View>
        </>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Shipping Notes                                                     */}
      {/* ------------------------------------------------------------------ */}

      {showNotes && hasNotes && (
        <>
          <Divider spacing={spacing.md} />

          <View style={styles.notesContainer}>
            <Text
              style={[
                styles.notesTitle,
                {
                  color: colors.text,
                },
              ]}
            >
              Shipping Notes
            </Text>

            <Text
              style={[
                styles.notesText,
                {
                  color: colors.textSecondary,
                },
              ]}
            >
              {shippingNotes}
            </Text>
          </View>
        </>
      )}
    </View>
  );
});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ShippingInformation.displayName = "ShippingInformation";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ShippingInformation.propTypes = {
  /* ---------------------------------------------------------------------- */
  /* Shipping Origin & Destination                                          */
  /* ---------------------------------------------------------------------- */

  shipsFrom: PropTypes.string,

  shipsTo: PropTypes.string,

  /* ---------------------------------------------------------------------- */
  /* Carrier Information                                                    */
  /* ---------------------------------------------------------------------- */

  courier: PropTypes.string,

  shippingMethod: PropTypes.string,

  dispatchTime: PropTypes.string,

  /* ---------------------------------------------------------------------- */
  /* Package Information                                                    */
  /* ---------------------------------------------------------------------- */

  trackingAvailable: PropTypes.bool,

  internationalShipping: PropTypes.bool,

  weight: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  dimensions: PropTypes.string,

  /* ---------------------------------------------------------------------- */
  /* Additional Notes                                                       */
  /* ---------------------------------------------------------------------- */

  shippingNotes: PropTypes.string,

  /* ---------------------------------------------------------------------- */
  /* Visibility                                                             */
  /* ---------------------------------------------------------------------- */

  showCourier: PropTypes.bool,

  showTracking: PropTypes.bool,

  showWeight: PropTypes.bool,

  showDimensions: PropTypes.bool,

  showInternational: PropTypes.bool,

  showNotes: PropTypes.bool,

  /* ---------------------------------------------------------------------- */
  /* Styling                                                                */
  /* ---------------------------------------------------------------------- */

  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ShippingInformation.defaultProps = {
  shipsFrom: "Warehouse",

  shipsTo: "Nationwide",

  courier: null,

  shippingMethod: "Standard Shipping",

  dispatchTime: "Within 24 hours",

  trackingAvailable: true,

  internationalShipping: false,

  weight: null,

  dimensions: null,

  shippingNotes: null,

  showCourier: true,

  showTracking: true,

  showWeight: true,

  showDimensions: true,

  showInternational: true,

  showNotes: true,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  /* ---------------------------------------------------------------------- */
  /* Container                                                              */
  /* ---------------------------------------------------------------------- */

  container: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.md,
  },

  /* ---------------------------------------------------------------------- */
  /* Header                                                                 */
  /* ---------------------------------------------------------------------- */

  title: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: theme.spacing.md,
  },

  /* ---------------------------------------------------------------------- */
  /* Information Rows                                                       */
  /* ---------------------------------------------------------------------- */

  infoRow: {
    marginBottom: theme.spacing.sm,
  },

  infoText: {
    fontSize: 15,
    fontWeight: "500",
    lineHeight: 22,
  },

  /* ---------------------------------------------------------------------- */
  /* Package Information                                                    */
  /* ---------------------------------------------------------------------- */

  packageContainer: {
    marginTop: theme.spacing.xs,
  },

  packageTitle: {
    fontSize: 16,
    fontWeight: "700",
    marginBottom: theme.spacing.sm,
  },

  featureItem: {
    marginBottom: theme.spacing.sm,
  },

  featureText: {
    fontSize: 14,
    fontWeight: "500",
    lineHeight: 20,
  },

  /* ---------------------------------------------------------------------- */
  /* Shipping Notes                                                         */
  /* ---------------------------------------------------------------------- */

  notesContainer: {
    marginTop: theme.spacing.xs,
  },

  notesTitle: {
    fontSize: 16,
    fontWeight: "700",
    marginBottom: theme.spacing.sm,
  },

  notesText: {
    fontSize: 14,
    lineHeight: 22,
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default ShippingInformation;