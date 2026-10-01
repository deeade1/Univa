/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/wishlist/WishlistActions.jsx   */
/* -------------------------------------------------------------------------- */

import React, { memo, useCallback, useMemo } from "react";
import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
  ActivityIndicator,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Action Button                                                              */
/* -------------------------------------------------------------------------- */

const ActionButton = memo(({
  icon,
  label,
  color,
  outlined = false,
  disabled = false,
  loading = false,
  onPress,
  accessibilityLabel,
}) => {
  const buttonStyle = [
    styles.button,
    {
      backgroundColor: outlined ? "transparent" : color,
      borderColor: color,
    },
    outlined && styles.outlinedButton,
    (disabled || loading) && styles.disabled,
  ];

  const textColor = outlined ? color : "#FFFFFF";
  const iconColor = outlined ? color : "#FFFFFF";

  return (
    <Pressable
      accessible
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel || label}
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={buttonStyle}
    >
      {loading ? (
        <ActivityIndicator size="small" color={textColor} />
      ) : (
        <>
          <MaterialCommunityIcons
            name={icon}
            size={18}
            color={iconColor}
          />
          <Text
            style={[
              styles.buttonText,
              { color: textColor },
            ]}
          >
            {label}
          </Text>
        </>
      )}
    </Pressable>
  );
});

ActionButton.displayName = "ActionButton";

ActionButton.propTypes = {
  icon: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  color: PropTypes.string.isRequired,
  outlined: PropTypes.bool,
  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  onPress: PropTypes.func,
  accessibilityLabel: PropTypes.string,
};

ActionButton.defaultProps = {
  outlined: false,
  disabled: false,
  loading: false,
  onPress: null,
  accessibilityLabel: null,
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const WishlistActions = memo(({
  product,
  showMoveToCart = true,
  showRemove = true,
  showShare = true,
  showCompare = false,
  moveToCartLabel = "Move to Cart",
  removeLabel = "Remove",
  shareLabel = "Share",
  compareLabel = "Compare",
  inStock,
  loading = false,
  onMoveToCart,
  onRemove,
  onShare,
  onCompare,
  style,
}) => {
  const { colors } = theme;

  /* ---------------------------------------------------------------------- */
  /* Memoized Values                                                        */
  /* ---------------------------------------------------------------------- */

  const isInStock = useMemo(
    () => inStock ?? product?.inStock ?? (product?.stock ?? 0) > 0,
    [inStock, product?.inStock, product?.stock]
  );

  const isDisabled = useMemo(
    () => loading || !isInStock,
    [loading, isInStock]
  );

  /* ---------------------------------------------------------------------- */
  /* Memoized Handlers                                                      */
  /* ---------------------------------------------------------------------- */

  const handleMoveToCart = useCallback(() => {
    onMoveToCart?.(product);
  }, [onMoveToCart, product]);

  const handleRemove = useCallback(() => {
    onRemove?.(product);
  }, [onRemove, product]);

  const handleShare = useCallback(() => {
    onShare?.(product);
  }, [onShare, product]);

  const handleCompare = useCallback(() => {
    onCompare?.(product);
  }, [onCompare, product]);

  /* ---------------------------------------------------------------------- */
  /* Action Configuration                                                    */
  /* ---------------------------------------------------------------------- */

  const actions = useMemo(() => {
    const actionList = [];

    if (showMoveToCart) {
      actionList.push({
        key: "moveToCart",
        icon: "cart-plus",
        label: moveToCartLabel,
        color: colors.primary,
        outlined: false,
        disabled: isDisabled,
        onPress: handleMoveToCart,
        accessibilityLabel: `Move ${product?.name || "product"} to cart`,
      });
    }

    if (showRemove) {
      actionList.push({
        key: "remove",
        icon: "heart-remove",
        label: removeLabel,
        color: colors.error || "#EF4444",
        outlined: true,
        disabled: loading,
        onPress: handleRemove,
        accessibilityLabel: `Remove ${product?.name || "product"} from wishlist`,
      });
    }

    if (showShare) {
      actionList.push({
        key: "share",
        icon: "share-variant",
        label: shareLabel,
        color: colors.info || "#3B82F6",
        outlined: true,
        disabled: loading,
        onPress: handleShare,
        accessibilityLabel: `Share ${product?.name || "product"}`,
      });
    }

    if (showCompare) {
      actionList.push({
        key: "compare",
        icon: "compare",
        label: compareLabel,
        color: colors.secondary || "#8B5CF6",
        outlined: true,
        disabled: loading,
        onPress: handleCompare,
        accessibilityLabel: `Compare ${product?.name || "product"}`,
      });
    }

    return actionList;
  }, [
    showMoveToCart,
    showRemove,
    showShare,
    showCompare,
    moveToCartLabel,
    removeLabel,
    shareLabel,
    compareLabel,
    colors,
    isDisabled,
    loading,
    product,
    handleMoveToCart,
    handleRemove,
    handleShare,
    handleCompare,
  ]);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  if (actions.length === 0) {
    return null;
  }

  return (
    <View style={[styles.container, style]}>
      {actions.map((action) => (
        <ActionButton
          key={action.key}
          icon={action.icon}
          label={action.label}
          color={action.color}
          outlined={action.outlined}
          disabled={action.disabled}
          loading={loading}
          onPress={action.onPress}
          accessibilityLabel={action.accessibilityLabel}
          style={styles.actionButton}
        />
      ))}
    </View>
  );
});

WishlistActions.displayName = "WishlistActions";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

WishlistActions.propTypes = {
  /**
   * Product object for the wishlist item
   */
  product: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    name: PropTypes.string,
    inStock: PropTypes.bool,
    stock: PropTypes.number,
  }),

  /**
   * Show move to cart action
   */
  showMoveToCart: PropTypes.bool,

  /**
   * Show remove action
   */
  showRemove: PropTypes.bool,

  /**
   * Show share action
   */
  showShare: PropTypes.bool,

  /**
   * Show compare action
   */
  showCompare: PropTypes.bool,

  /**
   * Custom label for move to cart button
   */
  moveToCartLabel: PropTypes.string,

  /**
   * Custom label for remove button
   */
  removeLabel: PropTypes.string,

  /**
   * Custom label for share button
   */
  shareLabel: PropTypes.string,

  /**
   * Custom label for compare button
   */
  compareLabel: PropTypes.string,

  /**
   * Override inStock status
   */
  inStock: PropTypes.bool,

  /**
   * Loading state for all actions
   */
  loading: PropTypes.bool,

  /**
   * Move to cart handler
   */
  onMoveToCart: PropTypes.func,

  /**
   * Remove handler
   */
  onRemove: PropTypes.func,

  /**
   * Share handler
   */
  onShare: PropTypes.func,

  /**
   * Compare handler
   */
  onCompare: PropTypes.func,

  /**
   * Optional style overrides
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

WishlistActions.defaultProps = {
  product: null,
  showMoveToCart: true,
  showRemove: true,
  showShare: true,
  showCompare: false,
  moveToCartLabel: "Move to Cart",
  removeLabel: "Remove",
  shareLabel: "Share",
  compareLabel: "Compare",
  inStock: null,
  loading: false,
  onMoveToCart: null,
  onRemove: null,
  onShare: null,
  onCompare: null,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginTop: 12,
    marginHorizontal: -4,
  },

  actionButton: {
    flex: 1,
    flexBasis: "48%",
    minWidth: "40%",
    marginHorizontal: 4,
  },

  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginBottom: 10,
    borderRadius: 12,
    minHeight: 48,
  },

  outlinedButton: {
    borderWidth: 1.5,
  },

  disabled: {
    opacity: 0.5,
  },

  buttonText: {
    marginLeft: 8,
    fontSize: 14,
    fontWeight: "700",
  },
});

export default WishlistActions;

 