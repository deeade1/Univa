/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/ProductPrice.jsx */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  StyleSheet,
} from "react-native";

import theme from "@/theme";

import Price from "@/modules/ecommerce/components/common/Price";

/* -------------------------------------------------------------------------- */

const ProductPrice = memo(({
  /* ---------------------------------------------------------------------- */
  /* Product                                                                */
  /* ---------------------------------------------------------------------- */

  product,
  selectedVariant,

  /* ---------------------------------------------------------------------- */
  /* Appearance                                                             */
  /* ---------------------------------------------------------------------- */

  size = "xl",
  showDiscount = true,
  showCurrency = true,
  align = "left",
  style,
}) => {
  const { colors } = theme;

  /* ---------------------------------------------------------------------- */
  /* Active Pricing                                                         */
  /* ---------------------------------------------------------------------- */

  const activePrice = useMemo(
    () => selectedVariant?.price ?? product?.price,
    [selectedVariant, product]
  );

  const activeSalePrice = useMemo(
    () => selectedVariant?.salePrice ?? product?.salePrice,
    [selectedVariant, product]
  );

  const currency = useMemo(
    () => selectedVariant?.currency ??
      product?.currency ??
      "₦",
    [selectedVariant, product]
  );

  /* ---------------------------------------------------------------------- */
  /* Discount                                                               */
  /* ---------------------------------------------------------------------- */

  const hasDiscount = useMemo(() => {
    if (
      activePrice == null ||
      activeSalePrice == null
    ) {
      return false;
    }

    return Number(activeSalePrice) < Number(activePrice);
  }, [
    activePrice,
    activeSalePrice,
  ]);

  const discountPercentage = useMemo(() => {
    if (
      selectedVariant?.discountPercentage != null
    ) {
      return selectedVariant.discountPercentage;
    }

    if (
      product?.discountPercentage != null
    ) {
      return product.discountPercentage;
    }

    if (!hasDiscount) {
      return null;
    }

    return Math.round(
      (
        (Number(activePrice) -
          Number(activeSalePrice)) /
        Number(activePrice)
      ) * 100
    );
  }, [
    selectedVariant,
    product,
    activePrice,
    activeSalePrice,
    hasDiscount,
  ]);

  /* ---------------------------------------------------------------------- */

  return (
    <View style={[styles.container, style]}>
      <Price
        price={activePrice}
        salePrice={activeSalePrice}
        currency={currency}
        hasDiscount={hasDiscount}
        discountPercentage={discountPercentage}
        size={size}
        showDiscount={showDiscount}
        showCurrency={showCurrency}
        align={align}
        color={colors.primary}
      />
    </View>
  );
});

/* -------------------------------------------------------------------------- */

ProductPrice.displayName = "ProductPrice";

/* -------------------------------------------------------------------------- */

ProductPrice.propTypes = {
  product: PropTypes.object,
  selectedVariant: PropTypes.object,

  size: PropTypes.oneOf([
    "xs",
    "sm",
    "md",
    "lg",
    "xl",
  ]),

  showDiscount: PropTypes.bool,
  showCurrency: PropTypes.bool,

  align: PropTypes.oneOf([
    "left",
    "center",
    "right",
  ]),

  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

/* -------------------------------------------------------------------------- */

ProductPrice.defaultProps = {
  product: null,
  selectedVariant: null,

  size: "xl",
  showDiscount: true,
  showCurrency: true,

  align: "left",

  style: null,
};

/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    width: "100%",
  },
});

/* -------------------------------------------------------------------------- */

export default ProductPrice;