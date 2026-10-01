/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductOffersCard.jsx                                                      */
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
/* Offer Shape (Reusable)                                                     */
/* -------------------------------------------------------------------------- */

const offerShape = PropTypes.shape({
  id: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  type: PropTypes.string,

  icon: PropTypes.string,

  title: PropTypes.string.isRequired,

  subtitle: PropTypes.string,

  badge: PropTypes.string,

  code: PropTypes.string,
});

/* -------------------------------------------------------------------------- */
/* Offer Item                                                                 */
/* -------------------------------------------------------------------------- */

const OfferItem = memo(
  ({
    offer,
    colors,
    onPress,
  }) => (
    <Pressable
      onPress={() =>
        onPress?.(offer)
      }
      style={styles.offerItem}
    >
      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor:
              colors.primary +
              "15",
          },
        ]}
      >
        <MaterialCommunityIcons
          name={
            offer.icon ??
            "tag-outline"
          }
          size={20}
          color={
            colors.primary
          }
        />
      </View>

      <View
        style={styles.offerContent}
      >
        <Text
          numberOfLines={1}
          style={[
            styles.offerTitle,
            {
              color:
                colors.text,
            },
          ]}
        >
          {offer.title}
        </Text>

        {!!offer.subtitle && (
          <Text
            numberOfLines={2}
            style={[
              styles.offerSubtitle,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            {offer.subtitle}
          </Text>
        )}
      </View>

      {!!offer.badge && (
        <View
          style={styles.badge}
        >
          <Text
            style={[
              styles.badgeText,
              {
                color: "#FFFFFF",
              },
            ]}
          >
            {offer.badge}
          </Text>
        </View>
      )}
    </Pressable>
  )
);

OfferItem.displayName =
  "OfferItem";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductOffersCard = memo(
  ({
    offers = [],

    showCoupons = true,

    showCashback = true,

    showShippingOffer = true,

    showFlashSale = true,

    showViewAll = true,

    onOfferPress,

    onViewAll,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Filtered Offers                                                        */
    /* ---------------------------------------------------------------------- */

    const visibleOffers =
      useMemo(() => {
        return offers.filter(
          (offer) => {
            switch (
              offer.type
            ) {
              case "coupon":
                return showCoupons;

              case "cashback":
                return showCashback;

              case "shipping":
                return showShippingOffer;

              case "flash":
                return showFlashSale;

              default:
                return true;
            }
          }
        );
      }, [
        offers,
        showCoupons,
        showCashback,
        showShippingOffer,
        showFlashSale,
      ]);

    const handleViewAll =
      useCallback(() => {
        onViewAll?.(
          visibleOffers
        );
      }, [
        onViewAll,
        visibleOffers,
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
          style={styles.header}
        >
          <View
            style={
              styles.headerLeft
            }
          >
            <MaterialCommunityIcons
              name="gift-outline"
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
              Offers &
              Promotions
            </Text>
          </View>

          {/* -------------------------------------------------------------- */}
          {/* View All                                                       */}
          {/* -------------------------------------------------------------- */}

          {showViewAll &&
            visibleOffers.length >
              0 && (
              <Pressable
                onPress={
                  handleViewAll
                }
                style={
                  styles.viewAllButton
                }
              >
                <Text
                  style={[
                    styles.viewAllText,
                    {
                      color:
                        colors.primary,
                    },
                  ]}
                >
                  View All
                </Text>

                <MaterialCommunityIcons
                  name="chevron-right"
                  size={20}
                  color={
                    colors.primary
                  }
                />
              </Pressable>
            )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Offers List                                                    */}
        {/* -------------------------------------------------------------- */}

        {visibleOffers.length >
        0 ? (
          visibleOffers.map(
            (
              offer,
              index
            ) => (
              <OfferItem
                key={
                  offer.id ??
                  offer.code ??
                  index
                }
                offer={offer}
                colors={colors}
                onPress={
                  onOfferPress
                }
              />
            )
          )
        ) : (
          /* ---------------------------------------------------------- */
          /* Empty State                                                */
          /* ---------------------------------------------------------- */

          <View
            style={
              styles.emptyContainer
            }
          >
            <MaterialCommunityIcons
              name="ticket-percent-outline"
              size={48}
              color={
                colors.border
              }
            />

            <Text
              style={[
                styles.emptyTitle,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              No Active Offers
            </Text>

            <Text
              style={[
                styles.emptyDescription,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              There are currently
              no promotions
              available for this
              product.
            </Text>
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Promotional Disclaimer                                         */}
        {/* -------------------------------------------------------------- */}

        {visibleOffers.length >
          0 && (
          <View
            style={[
              styles.footer,
              {
                borderTopColor:
                  colors.border,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="information-outline"
              size={16}
              color={
                colors.textSecondary
              }
            />

            <Text
              style={[
                styles.footerText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Promotions are subject
              to availability and
              may change without
              prior notice. Terms
              and conditions apply.
            </Text>
          </View>
        )}
      </View>
    );
  }
);

ProductOffersCard.displayName =
  "ProductOffersCard";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

OfferItem.propTypes = {
  offer: offerShape.isRequired,

  colors: PropTypes.object.isRequired,

  onPress: PropTypes.func,
};

ProductOffersCard.propTypes = {
  offers: PropTypes.arrayOf(
    offerShape
  ),

  showCoupons: PropTypes.bool,

  showCashback: PropTypes.bool,

  showShippingOffer: PropTypes.bool,

  showFlashSale: PropTypes.bool,

  showViewAll: PropTypes.bool,

  onOfferPress: PropTypes.func,

  onViewAll: PropTypes.func,

  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

OfferItem.defaultProps = {
  onPress: null,
};

ProductOffersCard.defaultProps = {
  offers: [],

  showCoupons: true,

  showCashback: true,

  showShippingOffer: true,

  showFlashSale: true,

  showViewAll: true,

  onOfferPress: null,

  onViewAll: null,

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

      justifyContent:
        "space-between",

      marginBottom: 18,
    },

    headerLeft: {
      flexDirection: "row",

      alignItems: "center",

      flex: 1,
    },

    title: {
      marginLeft: 10,

      fontSize: 18,

      fontWeight: "700",
    },

    viewAllButton: {
      flexDirection: "row",

      alignItems: "center",
    },

    viewAllText: {
      fontSize: 14,

      fontWeight: "600",

      marginRight: 2,
    },

    /* ------------------------------------------------------------------ */
    /* Offer Item                                                         */
    /* ------------------------------------------------------------------ */

    offerItem: {
      flexDirection: "row",

      alignItems: "center",

      paddingVertical: 14,
    },

    iconContainer: {
      width: 44,

      height: 44,

      borderRadius: 22,

      justifyContent:
        "center",

      alignItems:
        "center",
    },

    offerContent: {
      flex: 1,

      marginLeft: 14,
    },

    offerTitle: {
      fontSize: 15,

      fontWeight: "700",
    },

    offerSubtitle: {
      marginTop: 4,

      fontSize: 13,

      lineHeight: 18,
    },

    badge: {
      backgroundColor:
        "#EF4444",

      paddingHorizontal: 10,

      paddingVertical: 4,

      borderRadius: 999,
    },

    badgeText: {
      fontSize: 11,

      fontWeight: "700",
    },

    /* ------------------------------------------------------------------ */
    /* Empty State                                                        */
    /* ------------------------------------------------------------------ */

    emptyContainer: {
      alignItems: "center",

      justifyContent:
        "center",

      paddingVertical: 36,
    },

    emptyTitle: {
      marginTop: 16,

      fontSize: 16,

      fontWeight: "700",
    },

    emptyDescription: {
      marginTop: 8,

      textAlign: "center",

      fontSize: 14,

      lineHeight: 20,

      maxWidth: 260,
    },

    /* ------------------------------------------------------------------ */
    /* Footer                                                             */
    /* ------------------------------------------------------------------ */

    footer: {
      flexDirection: "row",

      alignItems: "flex-start",

      borderTopWidth: 1,

      marginTop: 18,

      paddingTop: 16,
    },

    footerText: {
      flex: 1,

      marginLeft: 8,

      fontSize: 12,

      lineHeight: 18,
    },
  });

export default ProductOffersCard;