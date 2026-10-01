/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/seller/SellerProfile.jsx       */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from "react";

import {
  View,
  StyleSheet,
} from "react-native";

import PropTypes from "prop-types";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import ErrorState from "../common/ErrorState";
import EmptyState from "../common/EmptyState";

/* -------------------------------------------------------------------------- */
/* Seller Components                                                          */
/* -------------------------------------------------------------------------- */

import SellerCard from "./SellerCard";
import SellerStats from "./SellerStats";
import SellerPolicies from "./SellerPolicies";
import SellerContactCard from "./SellerContactCard";
import SellerProducts from "./SellerProducts";
import SellerSkeleton from "./SellerSkeleton";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SellerProfile = memo(({
  seller = null,

  products = [],

  loading = false,

  error = null,

  productsLoading = false,

  showCard = true,

  showStats = true,

  showPolicies = true,

  showContact = true,

  showProducts = true,

  showFollow = true,

  onSellerPress,

  onFollow,

  onContact,

  onProductPress,

  onWishlistPress,

  onAddToCart,

  onPolicyPress,

  onRetry,

  style,
}) => {

  const { colors } = theme;

  /* ---------------------------------------------------------------------- */
  /* Memoized Data                                                          */
  /* ---------------------------------------------------------------------- */

  const sellerProducts = useMemo(
    () => products ?? [],
    [products]
  );

  /* ---------------------------------------------------------------------- */
  /* Loading                                                                */
  /* ---------------------------------------------------------------------- */

  if (loading) {
    return (
      <SellerSkeleton
        style={style}
      />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Error                                                                  */
  /* ---------------------------------------------------------------------- */

  if (error) {
    return (
      <ErrorState
        title="Unable to load seller"
        description={
          error?.message ??
          "Please try again."
        }
        onRetry={onRetry}
      />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Empty                                                                  */
  /* ---------------------------------------------------------------------- */

  if (!seller) {
    return (
      <EmptyState
        icon="store-off"
        title="Seller not found"
        description="This seller is unavailable."
      />
    );
  }

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
              {/* -------------------------------------------------------------- */}
      {/* Seller Card                                                    */}
      {/* -------------------------------------------------------------- */}

      {showCard && (
        <SellerCard
          seller={seller}
          showStats={false}
          showFollow={showFollow}
          showContact={false}
          onPress={onSellerPress}
          onFollow={onFollow}
        />
      )}

      {/* -------------------------------------------------------------- */}
      {/* Seller Statistics                                              */}
      {/* -------------------------------------------------------------- */}

      {showStats && (
        <SellerStats
          seller={seller}
          style={styles.section}
        />
      )}

      {/* -------------------------------------------------------------- */}
      {/* Seller Policies                                                */}
      {/* -------------------------------------------------------------- */}

      {showPolicies && (
        <SellerPolicies
          seller={seller}
          onPolicyPress={onPolicyPress}
          style={styles.section}
        />
      )}

      {/* -------------------------------------------------------------- */}
      {/* Contact Seller                                                 */}
      {/* -------------------------------------------------------------- */}

      {showContact && (
        <SellerContactCard
          seller={seller}
          onChat={onContact}
          onCall={onContact}
          onEmail={onContact}
          onWhatsApp={onContact}
          onWebsite={onContact}
          style={styles.section}
        />
      )}

      {/* -------------------------------------------------------------- */}
      {/* Seller Products                                                */}
      {/* -------------------------------------------------------------- */}

      {showProducts && (
        <SellerProducts
          title="Products"

          products={sellerProducts}

          loading={productsLoading}

          horizontal

          showHeader

          showSeeAll

          onProductPress={onProductPress}

          onWishlistPress={onWishlistPress}

          onAddToCart={onAddToCart}
        />
      )}
    </View>
  );
});

SellerProfile.displayName =
  "SellerProfile";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SellerProfile.propTypes = {
  /**
   * Seller information
   */
  seller: PropTypes.object,

  /**
   * Seller products
   */
  products: PropTypes.array,

  /**
   * States
   */
  loading: PropTypes.bool,
  error: PropTypes.object,
  productsLoading: PropTypes.bool,

  /**
   * Visibility
   */
  showCard: PropTypes.bool,
  showStats: PropTypes.bool,
  showPolicies: PropTypes.bool,
  showContact: PropTypes.bool,
  showProducts: PropTypes.bool,
  showFollow: PropTypes.bool,

  /**
   * Events
   */
  onSellerPress: PropTypes.func,
  onFollow: PropTypes.func,
  onContact: PropTypes.func,
  onProductPress: PropTypes.func,
  onWishlistPress: PropTypes.func,
  onAddToCart: PropTypes.func,
  onPolicyPress: PropTypes.func,
  onRetry: PropTypes.func,

  /**
   * Styling
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

SellerProfile.defaultProps = {
  seller: null,
  products: [],

  loading: false,
  error: null,
  productsLoading: false,

  showCard: true,
  showStats: true,
  showPolicies: true,
  showContact: true,
  showProducts: true,
  showFollow: true,

  onSellerPress: null,
  onFollow: null,
  onContact: null,
  onProductPress: null,
  onWishlistPress: null,
  onAddToCart: null,
  onPolicyPress: null,
  onRetry: null,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    paddingVertical: 16,
  },

  section: {
    marginBottom: 16,
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default SellerProfile;