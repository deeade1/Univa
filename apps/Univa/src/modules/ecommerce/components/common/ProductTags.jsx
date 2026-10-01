/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ProductTags.jsx         */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import {
  StyleSheet,
  Text,
  View,
  Pressable,
} from "react-native";

import PropTypes
  from "prop-types";

import DiscountBadge
  from "./DiscountBadge";

import StockIndicator
  from "./StockIndicator";

import ShippingBadge, {
  SHIPPING_TYPE,
} from "./ShippingBadge";

import AvailabilityBadge, {
  AVAILABILITY_STATUS,
} from "./AvailabilityBadge";

import SellerBadge, {
  SELLER_BADGE,
} from "./SellerBadge";

import VerifiedBadge, {
  VERIFIED_TYPE,
} from "./VerifiedBadge";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Supported Tag Types                                                        */
/* -------------------------------------------------------------------------- */

export const PRODUCT_TAG_TYPE = {

  DISCOUNT:
    "discount",

  SHIPPING:
    "shipping",

  STOCK:
    "stock",

  AVAILABILITY:
    "availability",

  VERIFIED:
    "verified",

  SELLER:
    "seller",

  CUSTOM:
    "custom",

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductTags =
memo(({

  tags = [],

  spacing = 8,

  maxVisible,

  size = "small",

  variant = "soft",

  showIcons = true,

  onTagPress,

  style,

}) => {

  const {
    colors,
  } = theme;

  /* ---------------------------------------------------------------------- */
  /* Remove duplicates                                                      */
  /* ---------------------------------------------------------------------- */

  const uniqueTags =
    useMemo(() => {

      const seen =
        new Set();

      return tags.filter(
        (tag) => {

          const key =
            JSON.stringify(
              tag
            );

          if (
            seen.has(key)
          ) {
            return false;
          }

          seen.add(key);

          return true;

        }
      );

    }, [tags]);

  /* ---------------------------------------------------------------------- */
  /* Visible Tags                                                           */
  /* ---------------------------------------------------------------------- */

  const visibleTags =
    useMemo(() => {

      if (
        maxVisible ==
        null
      ) {
        return uniqueTags;
      }

      return uniqueTags.slice(
        0,
        maxVisible
      );

    }, [
      uniqueTags,
      maxVisible,
    ]);

  const hiddenCount =
    uniqueTags.length -
    visibleTags.length;
    /* ---------------------------------------------------------------------- */
/* Render Tag                                                             */
/* ---------------------------------------------------------------------- */

const renderTag = (
  tag,
  index
) => {

  let badge = null;

  switch (tag.type) {

    /* -------------------------------------------------------------- */
    /* Discount                                                       */
    /* -------------------------------------------------------------- */

    case PRODUCT_TAG_TYPE.DISCOUNT:

      badge = (

        <DiscountBadge
          percentage={
            tag.value ??
            tag.percentage ??
            0
          }
          size={size}
          variant={variant}
        />

      );

      break;

    /* -------------------------------------------------------------- */
    /* Shipping                                                       */
    /* -------------------------------------------------------------- */

    case PRODUCT_TAG_TYPE.SHIPPING:

      badge = (

        <ShippingBadge
          type={
            tag.shippingType ??
            SHIPPING_TYPE.FREE
          }
          size={size}
          variant={variant}
          showIcon={showIcons}
        />

      );

      break;

    /* -------------------------------------------------------------- */
    /* Availability                                                   */
    /* -------------------------------------------------------------- */

    case PRODUCT_TAG_TYPE.AVAILABILITY:

      badge = (

        <AvailabilityBadge
          status={
            tag.status ??
            AVAILABILITY_STATUS.AVAILABLE
          }
          size={size}
          variant={variant}
          showIcon={showIcons}
        />

      );

      break;

    /* -------------------------------------------------------------- */
    /* Seller                                                         */
    /* -------------------------------------------------------------- */

    case PRODUCT_TAG_TYPE.SELLER:

      badge = (

        <SellerBadge
          type={
            tag.sellerType ??
            SELLER_BADGE.VERIFIED
          }
          size={size}
          variant={variant}
          showIcon={showIcons}
        />

      );

      break;

    /* -------------------------------------------------------------- */
    /* Verified                                                      */
    /* -------------------------------------------------------------- */

    case PRODUCT_TAG_TYPE.VERIFIED:

      badge = (

        <VerifiedBadge
          type={
            tag.verifiedType ??
            VERIFIED_TYPE.VERIFIED
          }
          size={size}
          variant={variant}
          showIcon={showIcons}
          label={tag.label}
        />

      );

      break;

    /* -------------------------------------------------------------- */
    /* Stock                                                          */
    /* -------------------------------------------------------------- */

    case PRODUCT_TAG_TYPE.STOCK:

      badge = (

        <StockIndicator
          quantity={
            tag.quantity
          }
          maxQuantity={
            tag.maxQuantity
          }
          size={size}
          variant={variant}
          showIcon={showIcons}
          showProgress={
            tag.showProgress
          }
          showQuantity={
            tag.showQuantity
          }
        />

      );

      break;

    /* -------------------------------------------------------------- */
    /* Custom                                                         */
    /* -------------------------------------------------------------- */

    case PRODUCT_TAG_TYPE.CUSTOM:

      badge = (

        <View
          style={[
            styles.customBadge,
            {
              backgroundColor:
                tag.backgroundColor ??
                colors.primary,

              borderColor:
                tag.backgroundColor ??
                colors.primary,
            },
          ]}
        >

          <Text
            style={[
              styles.customText,
              {
                color:
                  tag.color ??
                  "#FFFFFF",
              },
            ]}
          >
            {tag.label}
          </Text>

        </View>

      );

      break;

    default:

      return null;

  }

  if (!badge) {
    return null;
  }

  return (

    <Pressable
      key={
        tag.id ??
        `${tag.type}-${index}`
      }
      disabled={!onTagPress}
      onPress={() =>
        onTagPress?.(
          tag,
          index
        )
      }
      style={{
        marginRight: spacing,
        marginBottom: spacing,
      }}
    >
      {badge}
    </Pressable>

  );

};
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

      {visibleTags.map(
        renderTag
      )}

      {hiddenCount >
        0 && (

        <View
          style={[
            styles.moreBadge,
            {
              borderColor:
                colors.border,

              backgroundColor:
                colors.surface ??
                colors.background,
            },
          ]}
        >

          <Text
            style={[
              styles.moreText,
              {
                color:
                  colors.textSecondary ??
                  colors.text,
              },
            ]}
          >
            +{hiddenCount} more
          </Text>

        </View>

      )}

    </View>

  );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ProductTags.displayName =
  "ProductTags";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductTags.propTypes = {

  tags:
    PropTypes.arrayOf(
      PropTypes.object
    ),

  spacing:
    PropTypes.number,

  maxVisible:
    PropTypes.number,

  size:
    PropTypes.oneOf([
      "small",
      "medium",
      "large",
    ]),

  variant:
    PropTypes.oneOf([
      "filled",
      "outline",
      "soft",
    ]),

  showIcons:
    PropTypes.bool,

  onTagPress:
    PropTypes.func,

  style:
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

    flexDirection:
      "row",

    flexWrap:
      "wrap",

    alignItems:
      "center",

  },

  /* ---------------------------------------------------------------------- */
  /* Custom Badge                                                           */
  /* ---------------------------------------------------------------------- */

  customBadge: {

    paddingHorizontal:
      10,

    paddingVertical:
      5,

    borderRadius:
      999,

    borderWidth:
      1,

    justifyContent:
      "center",

    alignItems:
      "center",

  },

  customText: {

    fontSize:
      12,

    fontWeight:
      "600",

  },

  /* ---------------------------------------------------------------------- */
  /* Overflow Badge                                                         */
  /* ---------------------------------------------------------------------- */

  moreBadge: {

    paddingHorizontal:
      10,

    paddingVertical:
      5,

    borderRadius:
      999,

    borderWidth:
      1,

    justifyContent:
      "center",

    alignItems:
      "center",

  },

  moreText: {

    fontSize:
      12,

    fontWeight:
      "600",

  },

});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
ProductTags;