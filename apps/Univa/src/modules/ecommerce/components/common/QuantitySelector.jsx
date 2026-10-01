/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/QuantitySelector.jsx    */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
  useMemo,
  useState,
  useEffect,
  useRef,
} from "react";

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

// Optional - uncomment if you have haptics installed
// import * as Haptics from "expo-haptics";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEFAULT_MIN = 1;
const DEFAULT_MAX = 999;
const DEFAULT_STEP = 1;

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const QuantitySelector = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Value                                                                   */
    /* ---------------------------------------------------------------------- */

    value = 1,
    min = DEFAULT_MIN,
    max = DEFAULT_MAX,
    step = DEFAULT_STEP,
    stock = null,

    /* ---------------------------------------------------------------------- */
    /* Behaviour                                                               */
    /* ---------------------------------------------------------------------- */

    disabled = false,
    loading = false,
    showStock = true,
    showMax = true,
    showValidationMessages = true,
    enableLongPress = true,

    /* ---------------------------------------------------------------------- */
    /* Labels                                                                 */
    /* ---------------------------------------------------------------------- */

    title = null,
    stockLabel = "Available",
    maxLabel = "Maximum",

    /* ---------------------------------------------------------------------- */
    /* Appearance                                                              */
    /* ---------------------------------------------------------------------- */

    size = "md", // xs | sm | md | lg
    variant = "outlined", // outlined | filled | minimal
    showBorder = true,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onChange,
    onIncrease,
    onDecrease,
    onBlur,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,
    containerStyle: containerStyleProp, // Renamed to avoid conflict

    /* ---------------------------------------------------------------------- */
    /* Accessibility                                                          */
    /* ---------------------------------------------------------------------- */

    accessibilityLabel = "Quantity selector",
  }) => {
    const { colors, spacing, typography, radius } = theme;

    /* ---------------------------------------------------------------------- */
    /* Refs                                                                   */
    /* ---------------------------------------------------------------------- */

    const longPressTimer = useRef(null);
    const [isLongPressing, setIsLongPressing] = useState(false);

    /* ---------------------------------------------------------------------- */
    /* Computed Values                                                        */
    /* ---------------------------------------------------------------------- */

    const effectiveMax = useMemo(() => {
      if (stock !== null && stock > 0) {
        return Math.min(max, stock);
      }
      return max;
    }, [max, stock]);

    const canDecrease = useMemo(
      () => !disabled && !loading && value > min,
      [disabled, loading, value, min]
    );

    const canIncrease = useMemo(
      () => !disabled && !loading && value < effectiveMax,
      [disabled, loading, value, effectiveMax]
    );

    const isOutOfStock = useMemo(
      () => stock !== null && stock <= 0,
      [stock]
    );

    const isLowStock = useMemo(
      () => stock !== null && stock > 0 && stock <= 5,
      [stock]
    );

    const isAtMax = useMemo(
      () => value >= effectiveMax,
      [value, effectiveMax]
    );

    /* ---------------------------------------------------------------------- */
    /* Size Styles                                                            */
    /* ---------------------------------------------------------------------- */

    const metrics = useMemo(() => {
      switch (size) {
        case "xs":
          return {
            button: 28,
            icon: 14,
            text: 13,
            radius: 8,
            height: 32,
            spacing: 8,
          };
        case "sm":
          return {
            button: 34,
            icon: 16,
            text: 15,
            radius: 10,
            height: 36,
            spacing: 10,
          };
        case "lg":
          return {
            button: 48,
            icon: 24,
            text: 20,
            radius: 16,
            height: 52,
            spacing: 16,
          };
        case "md":
        default:
          return {
            button: 40,
            icon: 20,
            text: 17,
            radius: 12,
            height: 44,
            spacing: 12,
          };
      }
    }, [size]);

    /* ---------------------------------------------------------------------- */
    /* Variant Styles                                                         */
    /* ---------------------------------------------------------------------- */

    const variantStyles = useMemo(() => {
      switch (variant) {
        case "filled":
          return {
            backgroundColor: colors.surface ?? colors.card,
            borderWidth: showBorder ? 1 : 0,
            borderColor: colors.border,
          };
        case "minimal":
          return {
            backgroundColor: "transparent",
            borderWidth: 0,
          };
        case "outlined":
        default:
          return {
            backgroundColor: colors.background,
            borderWidth: showBorder ? 1 : 0,
            borderColor: colors.border,
          };
      }
    }, [variant, showBorder, colors]);

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleIncrease = useCallback(() => {
      if (!canIncrease) return;

      // Optional haptic feedback
      // if (Haptics) {
      //   Haptics.selectionAsync();
      // }

      const next = Math.min(value + step, effectiveMax);

      if (onIncrease) {
        onIncrease(next);
      }

      if (onChange) {
        onChange(next);
      }
    }, [canIncrease, value, step, effectiveMax, onIncrease, onChange]);

    const handleDecrease = useCallback(() => {
      if (!canDecrease) return;

      // Optional haptic feedback
      // if (Haptics) {
      //   Haptics.selectionAsync();
      // }

      const next = Math.max(value - step, min);

      if (onDecrease) {
        onDecrease(next);
      }

      if (onChange) {
        onChange(next);
      }
    }, [canDecrease, value, step, min, onDecrease, onChange]);

    /* ---------------------------------------------------------------------- */
    /* Long Press Handlers                                                    */
    /* ---------------------------------------------------------------------- */

    const startLongPress = useCallback(
      (direction) => {
        if (!enableLongPress) return;

        if (longPressTimer.current) {
          clearTimeout(longPressTimer.current);
        }

        setIsLongPressing(true);

        longPressTimer.current = setTimeout(() => {
          const jumpAmount = 5;

          if (direction === "increase") {
            const newValue = Math.min(effectiveMax, value + jumpAmount);
            if (onChange) {
              onChange(newValue);
            }
          } else {
            const newValue = Math.max(min, value - jumpAmount);
            if (onChange) {
              onChange(newValue);
            }
          }

          setIsLongPressing(false);
        }, 400);
      },
      [value, min, effectiveMax, onChange, enableLongPress]
    );

    const cancelLongPress = useCallback(() => {
      if (longPressTimer.current) {
        clearTimeout(longPressTimer.current);
        longPressTimer.current = null;
      }
      setIsLongPressing(false);
    }, []);

    /* ---------------------------------------------------------------------- */
    /* Cleanup Long Press Timer                                               */
    /* ---------------------------------------------------------------------- */

    useEffect(() => {
      return () => {
        if (longPressTimer.current) {
          clearTimeout(longPressTimer.current);
        }
      };
    }, []);

    /* ---------------------------------------------------------------------- */
    /* Render Helper: Button                                                  */
    /* ---------------------------------------------------------------------- */

    const renderButton = useCallback(
      (icon, onPress, enabled, label, hint) => (
        <Pressable
          disabled={!enabled || loading}
          onPress={onPress}
          onPressIn={() => {
            if (icon === "plus") {
              startLongPress("increase");
            } else {
              startLongPress("decrease");
            }
          }}
          onPressOut={cancelLongPress}
          onLongPress={() => {}}
          delayLongPress={400}
          accessibilityRole="button"
          accessibilityLabel={label}
          accessibilityHint={hint}
          accessibilityState={{
            disabled: !enabled || loading,
          }}
          style={[
            styles.button,
            {
              width: metrics.button,
              height: metrics.button,
              opacity: enabled && !loading ? 1 : 0.35,
            },
          ]}
        >
          <MaterialCommunityIcons
            name={icon}
            size={metrics.icon}
            color={enabled && !loading ? colors.text : colors.textSecondary}
          />
        </Pressable>
      ),
      [metrics, colors, loading, startLongPress, cancelLongPress]
    );

    /* ---------------------------------------------------------------------- */
    /* Render Helper: Validation Message                                      */
    /* ---------------------------------------------------------------------- */

    const renderValidationMessage = useCallback(() => {
      if (!showValidationMessages) return null;
      if (disabled || loading) return null;

      let message = null;
      let color = null;

      if (isOutOfStock) {
        message = "This product is currently out of stock.";
        color = colors.error;
      } else if (isLowStock) {
        message = `Only ${stock} item${stock > 1 ? "s" : ""} remaining.`;
        color = colors.warning ?? "#F59E0B";
      } else if (isAtMax && stock !== null) {
        message = "Maximum quantity reached.";
        color = colors.warning ?? "#F59E0B";
      }

      if (!message) return null;

      return (
        <Text
          style={[
            styles.validationText,
            {
              color: color,
              marginTop: spacing?.sm ?? 8,
            },
          ]}
        >
          {message}
        </Text>
      );
    }, [
      showValidationMessages,
      disabled,
      loading,
      isOutOfStock,
      isLowStock,
      isAtMax,
      stock,
      colors,
      spacing,
    ]);

    /* ---------------------------------------------------------------------- */
    /* Main Render                                                            */
    /* ---------------------------------------------------------------------- */

    return (
      <View
        accessible
        accessibilityRole="adjustable"
        accessibilityLabel={accessibilityLabel}
        accessibilityValue={{
          min: min,
          max: effectiveMax,
          now: value,
        }}
        style={[styles.wrapper, variantStyles, containerStyleProp]}
      >
        {/* ------------------------------------------------------------------ */}
        {/* Title                                                              */}
        {/* ------------------------------------------------------------------ */}

        {title && (
          <Text
            style={[
              styles.title,
              typography?.bodyMedium,
              {
                color: colors.text,
                marginBottom: spacing?.sm ?? 8,
              },
            ]}
          >
            {title}
          </Text>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* Controls                                                           */}
        {/* ------------------------------------------------------------------ */}

        <View
          style={[
            styles.container,
            {
              height: metrics.height,
              backgroundColor: disabled ? colors.surfaceDisabled ?? colors.surface : colors.surface,
              borderRadius: metrics.radius,
            },
            style,
          ]}
        >
          {/* Decrease Button */}
          {renderButton(
            "minus",
            handleDecrease,
            canDecrease,
            "Decrease quantity",
            "Tap to decrease by 1, hold to decrease by 5"
          )}

          {/* Value / Loading */}
          <View
            style={[
              styles.valueContainer,
              {
                paddingHorizontal: metrics.spacing,
                minWidth: 42,
              },
            ]}
          >
            {loading ? (
              <ActivityIndicator size="small" color={colors.primary} />
            ) : (
              <Text
                style={[
                  styles.value,
                  {
                    fontSize: metrics.text,
                    color: disabled ? colors.textSecondary : colors.text,
                    fontWeight: "700",
                  },
                ]}
              >
                {value}
              </Text>
            )}
          </View>

          {/* Increase Button */}
          {renderButton(
            "plus",
            handleIncrease,
            canIncrease,
            "Increase quantity",
            "Tap to increase by 1, hold to increase by 5"
          )}
        </View>

        {/* ------------------------------------------------------------------ */}
        {/* Stock Information                                                 */}
        {/* ------------------------------------------------------------------ */}

        {showStock && stock !== null && !loading && (
          <View
            style={[
              styles.infoRow,
              {
                marginTop: spacing?.sm ?? 8,
              },
            ]}
          >
            <Text
              style={[
                styles.infoLabel,
                typography?.bodySmall,
                {
                  color: colors.textSecondary,
                },
              ]}
            >
              {stockLabel}
            </Text>
            <Text
              style={[
                styles.infoValue,
                typography?.bodySmall,
                {
                  color: stock > 0 ? colors.success : colors.error,
                  fontWeight: "600",
                },
              ]}
            >
              {stock > 0 ? `${stock} in stock` : "Out of stock"}
            </Text>
          </View>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* Maximum Purchase                                                  */}
        {/* ------------------------------------------------------------------ */}

        {showMax && Number.isFinite(effectiveMax) && !loading && (
          <View
            style={[
              styles.infoRow,
              {
                marginTop: spacing?.xs ?? 4,
              },
            ]}
          >
            <Text
              style={[
                styles.infoLabel,
                typography?.bodySmall,
                {
                  color: colors.textSecondary,
                },
              ]}
            >
              {maxLabel}
            </Text>
            <Text
              style={[
                styles.infoValue,
                typography?.bodySmall,
                {
                  color: colors.text,
                  fontWeight: "600",
                },
              ]}
            >
              {effectiveMax}
            </Text>
          </View>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* Validation Messages                                               */}
        {/* ------------------------------------------------------------------ */}

        {renderValidationMessage()}
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

QuantitySelector.displayName = "QuantitySelector";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

QuantitySelector.propTypes = {
  /* ---------------------------------------------------------------------- */
  /* Value                                                                  */
  /* ---------------------------------------------------------------------- */

  value: PropTypes.number,
  min: PropTypes.number,
  max: PropTypes.number,
  step: PropTypes.number,
  stock: PropTypes.number,

  /* ---------------------------------------------------------------------- */
  /* Behaviour                                                              */
  /* ---------------------------------------------------------------------- */

  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  showStock: PropTypes.bool,
  showMax: PropTypes.bool,
  showValidationMessages: PropTypes.bool,
  enableLongPress: PropTypes.bool,

  /* ---------------------------------------------------------------------- */
  /* Labels                                                                 */
  /* ---------------------------------------------------------------------- */

  title: PropTypes.string,
  stockLabel: PropTypes.string,
  maxLabel: PropTypes.string,

  /* ---------------------------------------------------------------------- */
  /* Appearance                                                             */
  /* ---------------------------------------------------------------------- */

  size: PropTypes.oneOf(["xs", "sm", "md", "lg"]),
  variant: PropTypes.oneOf(["outlined", "filled", "minimal"]),
  showBorder: PropTypes.bool,

  /* ---------------------------------------------------------------------- */
  /* Events                                                                 */
  /* ---------------------------------------------------------------------- */

  onChange: PropTypes.func,
  onIncrease: PropTypes.func,
  onDecrease: PropTypes.func,
  onBlur: PropTypes.func,

  /* ---------------------------------------------------------------------- */
  /* Styling                                                                */
  /* ---------------------------------------------------------------------- */

  style: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
  containerStyle: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),

  /* ---------------------------------------------------------------------- */
  /* Accessibility                                                          */
  /* ---------------------------------------------------------------------- */

  accessibilityLabel: PropTypes.string,
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

QuantitySelector.defaultProps = {
  value: 1,
  min: DEFAULT_MIN,
  max: DEFAULT_MAX,
  step: DEFAULT_STEP,
  stock: null,

  disabled: false,
  loading: false,
  showStock: true,
  showMax: true,
  showValidationMessages: true,
  enableLongPress: true,

  title: null,
  stockLabel: "Available",
  maxLabel: "Maximum",

  size: "md",
  variant: "outlined",
  showBorder: true,

  onChange: null,
  onIncrease: null,
  onDecrease: null,
  onBlur: null,

  style: null,
  containerStyle: null,

  accessibilityLabel: "Quantity selector",
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  /* ------------------------------------------------------------------ */
  /* Wrapper                                                            */
  /* ------------------------------------------------------------------ */

  wrapper: {
    width: "100%",
  },

  /* ------------------------------------------------------------------ */
  /* Title                                                              */
  /* ------------------------------------------------------------------ */

  title: {
    fontWeight: "700",
  },

  /* ------------------------------------------------------------------ */
  /* Container                                                          */
  /* ------------------------------------------------------------------ */

  container: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    borderWidth: 1,
    overflow: "hidden",
  },

  /* ------------------------------------------------------------------ */
  /* Buttons                                                            */
  /* ------------------------------------------------------------------ */

  button: {
    justifyContent: "center",
    alignItems: "center",
  },

  /* ------------------------------------------------------------------ */
  /* Value                                                              */
  /* ------------------------------------------------------------------ */

  valueContainer: {
    alignItems: "center",
    justifyContent: "center",
  },

  value: {
    textAlign: "center",
  },

  /* ------------------------------------------------------------------ */
  /* Information                                                        */
  /* ------------------------------------------------------------------ */

  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  infoLabel: {
    fontWeight: "500",
  },

  infoValue: {
    fontWeight: "600",
  },

  /* ------------------------------------------------------------------ */
  /* Validation                                                         */
  /* ------------------------------------------------------------------ */

  validationText: {
    fontSize: 13,
    fontWeight: "500",
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default QuantitySelector;