/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductWarrantyCard.jsx                                                    */
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
/* Coverage Item                                                              */
/* -------------------------------------------------------------------------- */

const CoverageItem = memo(
  ({
    label,
    available,
    colors,
  }) => (
    <View
      style={
        styles.coverageItem
      }
    >
      <MaterialCommunityIcons
        name={
          available
            ? "check-circle"
            : "close-circle"
        }
        size={18}
        color={
          available
            ? "#22C55E"
            : "#EF4444"
        }
      />

      <Text
        style={[
          styles.coverageText,
          {
            color:
              colors.text,
          },
        ]}
      >
        {label}
      </Text>
    </View>
  )
);

CoverageItem.displayName =
  "CoverageItem";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductWarrantyCard =
  memo(
    ({
      product,

      showProvider = true,

      showCoverage = true,

      showRegistration = true,

      showCertificate = true,

      showClaimProcess = true,

      showLearnMore = true,

      onWarrantyPress,

      onRegisterWarranty,

      style,
    }) => {
      const { colors } =
        theme;

      /* ------------------------------------------------------------------ */
      /* Warranty Data                                                      */
      /* ------------------------------------------------------------------ */

      const duration =
        useMemo(
          () =>
            product
              ?.warrantyDuration ??
            "12 Months",
          [product]
        );

      const provider =
        useMemo(
          () =>
            product
              ?.warrantyProvider ??
            "Manufacturer",
          [product]
        );

      const certificate =
        product
          ?.warrantyCertificate ??
        true;

      const registration =
        product
          ?.registrationRequired ??
        false;

      const handleLearnMore =
        useCallback(() => {
          onWarrantyPress?.(
            product
          );
        }, [
          product,
          onWarrantyPress,
        ]);

      const handleRegister =
        useCallback(() => {
          onRegisterWarranty?.(
            product
          );
        }, [
          product,
          onRegisterWarranty,
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
              name="shield-check-outline"
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
              Warranty
            </Text>
          </View>
                    {/* -------------------------------------------------------------- */}
          {/* Warranty Summary                                               */}
          {/* -------------------------------------------------------------- */}

          <View
            style={styles.summary}
          >
            <Text
              style={[
                styles.duration,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {duration}
            </Text>

            <Text
              style={[
                styles.summaryText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Manufacturer Warranty
            </Text>
          </View>

          {/* -------------------------------------------------------------- */}
          {/* Warranty Provider                                              */}
          {/* -------------------------------------------------------------- */}

          {showProvider && (
            <View
              style={[
                styles.infoRow,
                {
                  borderTopColor:
                    colors.border,
                },
              ]}
            >
              <View
                style={
                  styles.infoLeft
                }
              >
                <MaterialCommunityIcons
                  name="office-building-outline"
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
                  Provider
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
                {provider}
              </Text>
            </View>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Coverage                                                       */}
          {/* -------------------------------------------------------------- */}

          {showCoverage && (
            <View
              style={styles.coverageSection}
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
                Coverage
              </Text>

              <CoverageItem
                label="Parts Covered"
                available={
                  product
                    ?.coversParts ??
                  true
                }
                colors={colors}
              />

              <CoverageItem
                label="Labour Included"
                available={
                  product
                    ?.coversLabour ??
                  true
                }
                colors={colors}
              />

              <CoverageItem
                label="Official Service Centres"
                available={
                  product
                    ?.officialService ??
                  true
                }
                colors={colors}
              />

              <CoverageItem
                label="Accidental Damage"
                available={
                  product
                    ?.coversAccidental ??
                  false
                }
                colors={colors}
              />
            </View>
          )}
                    {/* -------------------------------------------------------------- */}
          {/* Warranty Certificate                                           */}
          {/* -------------------------------------------------------------- */}

          {showCertificate && (
            <View
              style={[
                styles.infoRow,
                {
                  borderTopColor:
                    colors.border,
                },
              ]}
            >
              <View
                style={
                  styles.infoLeft
                }
              >
                <MaterialCommunityIcons
                  name={
                    certificate
                      ? "file-certificate-outline"
                      : "file-remove-outline"
                  }
                  size={18}
                  color={
                    certificate
                      ? "#22C55E"
                      : "#EF4444"
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
                  Warranty Certificate
                </Text>
              </View>

              <Text
                style={[
                  styles.infoValue,
                  {
                    color:
                      certificate
                        ? "#22C55E"
                        : "#EF4444",
                  },
                ]}
              >
                {certificate
                  ? "Available"
                  : "Not Available"}
              </Text>
            </View>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Registration                                                   */}
          {/* -------------------------------------------------------------- */}

          {showRegistration && (
            <View
              style={[
                styles.infoRow,
                {
                  borderTopColor:
                    colors.border,
                },
              ]}
            >
              <View
                style={
                  styles.infoLeft
                }
              >
                <MaterialCommunityIcons
                  name="clipboard-check-outline"
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
                  Registration
                </Text>
              </View>

              <Text
                style={[
                  styles.infoValue,
                  {
                    color:
                      registration
                        ? "#F59E0B"
                        : "#22C55E",
                  },
                ]}
              >
                {registration
                  ? "Required"
                  : "Not Required"}
              </Text>
            </View>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Claim Process                                                  */}
          {/* -------------------------------------------------------------- */}

          {showClaimProcess && (
            <View
              style={[
                styles.claimContainer,
                {
                  backgroundColor:
                    colors.background,
                },
              ]}
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
                  styles.claimText,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Contact the seller
                or authorised service
                centre with your proof
                of purchase to submit
                a warranty claim.
              </Text>
            </View>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Actions                                                        */}
          {/* -------------------------------------------------------------- */}

          {(showLearnMore ||
            (showRegistration &&
              registration)) && (
            <View
              style={
                styles.actions
              }
            >
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
                    name="book-open-variant"
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
                    Learn More
                  </Text>
                </Pressable>
              )}

              {showRegistration &&
                registration && (
                  <Pressable
                    onPress={
                      handleRegister
                    }
                    style={[
                      styles.registerButton,
                      {
                        backgroundColor:
                          colors.primary,
                      },
                    ]}
                  >
                    <MaterialCommunityIcons
                      name="shield-check"
                      size={18}
                      color="#FFFFFF"
                    />

                    <Text
                      style={
                        styles.registerButtonText
                      }
                    >
                      Register
                    </Text>
                  </Pressable>
                )}
            </View>
          )}
        </View>
      );
    }
);

ProductWarrantyCard.displayName =
  "ProductWarrantyCard";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const productShape = PropTypes.shape({
  warrantyDuration:
    PropTypes.string,

  warrantyProvider:
    PropTypes.string,

  warrantyCertificate:
    PropTypes.bool,

  registrationRequired:
    PropTypes.bool,

  coversParts:
    PropTypes.bool,

  coversLabour:
    PropTypes.bool,

  officialService:
    PropTypes.bool,

  coversAccidental:
    PropTypes.bool,
});

CoverageItem.propTypes = {
  label:
    PropTypes.string
      .isRequired,

  available:
    PropTypes.bool,

  colors:
    PropTypes.object
      .isRequired,
};

CoverageItem.defaultProps = {
  available: false,
};

ProductWarrantyCard.propTypes =
  {
    product: productShape,

    showProvider:
      PropTypes.bool,

    showCoverage:
      PropTypes.bool,

    showRegistration:
      PropTypes.bool,

    showCertificate:
      PropTypes.bool,

    showClaimProcess:
      PropTypes.bool,

    showLearnMore:
      PropTypes.bool,

    onWarrantyPress:
      PropTypes.func,

    onRegisterWarranty:
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

ProductWarrantyCard.defaultProps =
  {
    product: null,

    showProvider: true,

    showCoverage: true,

    showRegistration:
      true,

    showCertificate:
      true,

    showClaimProcess:
      true,

    showLearnMore: true,

    onWarrantyPress:
      null,

    onRegisterWarranty:
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
    /* Summary                                                            */
    /* ------------------------------------------------------------------ */

    summary: {
      marginBottom: 20,
    },

    duration: {
      fontSize: 22,

      fontWeight: "700",
    },

    summaryText: {
      marginTop: 4,

      fontSize: 14,
    },

    /* ------------------------------------------------------------------ */
    /* Information Rows                                                   */
    /* ------------------------------------------------------------------ */

    infoRow: {
      flexDirection: "row",

      alignItems: "center",

      justifyContent:
        "space-between",

      borderTopWidth: 1,

      paddingVertical: 14,
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
      marginLeft: 12,

      flexShrink: 1,

      textAlign: "right",

      fontSize: 14,

      fontWeight: "500",
    },

    /* ------------------------------------------------------------------ */
    /* Coverage                                                           */
    /* ------------------------------------------------------------------ */

    coverageSection: {
      marginTop: 20,
    },

    sectionTitle: {
      fontSize: 16,

      fontWeight: "700",

      marginBottom: 14,
    },

    coverageItem: {
      flexDirection: "row",

      alignItems: "center",

      marginBottom: 12,
    },

    coverageText: {
      marginLeft: 10,

      fontSize: 14,
    },

    /* ------------------------------------------------------------------ */
    /* Claim                                                              */
    /* ------------------------------------------------------------------ */

    claimContainer: {
      flexDirection: "row",

      alignItems: "flex-start",

      borderRadius: 12,

      padding: 14,

      marginTop: 20,
    },

    claimText: {
      flex: 1,

      marginLeft: 10,

      fontSize: 13,

      lineHeight: 20,
    },

    /* ------------------------------------------------------------------ */
    /* Actions                                                            */
    /* ------------------------------------------------------------------ */

    actions: {
      flexDirection: "row",

      marginTop: 22,
    },

    learnButton: {
      flex: 1,

      flexDirection: "row",

      justifyContent:
        "center",

      alignItems: "center",

      borderWidth: 1,

      borderRadius: 12,

      paddingVertical: 12,

      marginRight: 8,
    },

    learnButtonText: {
      marginLeft: 8,

      fontSize: 14,

      fontWeight: "700",
    },

    registerButton: {
      flex: 1,

      flexDirection: "row",

      justifyContent:
        "center",

      alignItems: "center",

      borderRadius: 12,

      paddingVertical: 12,

      marginLeft: 8,
    },

    registerButtonText: {
      marginLeft: 8,

      color: "#FFFFFF",

      fontSize: 14,

      fontWeight: "700",
    },
  });

export default ProductWarrantyCard;