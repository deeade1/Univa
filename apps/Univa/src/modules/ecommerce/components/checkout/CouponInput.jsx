/* -------------------------------------------------------------------------- */
/*                               CouponInput                                  */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useState,
  useCallback,
} from 'react';

import PropTypes from 'prop-types';

import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';

import { Ionicons } from '@expo/vector-icons';

import {
  colors,
  spacing,
  typography,
  radius,
} from '../../../theme';

/* -------------------------------------------------------------------------- */
/*                                Component                                   */
/* -------------------------------------------------------------------------- */

const CouponInput = ({
  coupon,
  onApplyCoupon,
  onRemoveCoupon,
  loading,
  error,
  placeholder,
}) => {
  /* ---------------------------------------------------------------------- */
  /* State                                                                  */
  /* ---------------------------------------------------------------------- */

  const [code, setCode] = useState('');

  /* ---------------------------------------------------------------------- */
  /* Derived Values                                                         */
  /* ---------------------------------------------------------------------- */

  const hasCoupon = useMemo(
    () => Boolean(coupon?.code),
    [coupon]
  );

  const trimmedCode = useMemo(
    () => code.trim().toUpperCase(),
    [code]
  );

  const canApply = useMemo(
    () =>
      trimmedCode.length > 0 &&
      !loading,
    [
      trimmedCode,
      loading,
    ]
  );

  /* ---------------------------------------------------------------------- */
  /* Handlers                                                               */
  /* ---------------------------------------------------------------------- */

  const handleApply = useCallback(() => {
    if (!canApply) {
      return;
    }

    onApplyCoupon(trimmedCode);
  }, [
    canApply,
    trimmedCode,
    onApplyCoupon,
  ]);

  const handleRemove = useCallback(() => {
    setCode('');
    onRemoveCoupon();
  }, [
    onRemoveCoupon,
  ]);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View style={styles.container}>
      {/* ------------------------------------------------------------------ */}
      {/* Title                                                              */}
      {/* ------------------------------------------------------------------ */}

      <Text style={styles.title}>
        Promo Code
      </Text>

      {/* ------------------------------------------------------------------ */}
      {/* Applied Coupon                                                     */}
      {/* ------------------------------------------------------------------ */}

      {hasCoupon ? (
        <View style={styles.appliedContainer}>
          <View style={styles.appliedHeader}>
            <View style={styles.appliedCodeWrapper}>
              <Ionicons
                name="checkmark-circle"
                size={22}
                color={colors.success}
              />

              <Text style={styles.appliedCode}>
                {coupon.code}
              </Text>
            </View>

            <Pressable
              onPress={handleRemove}
              style={styles.removeButton}
            >
              <Text style={styles.removeText}>
                Remove
              </Text>
            </Pressable>
          </View>

          {!!coupon.discountAmount && (
            <View style={styles.discountRow}>
              <Text style={styles.discountLabel}>
                Discount
              </Text>

              <Text style={styles.discountValue}>
                - ₦
                {coupon.discountAmount.toLocaleString()}
              </Text>
            </View>
          )}
        </View>
      ) : (
        <>
          {/* -------------------------------------------------------------- */}
          {/* Input Row                                                      */}
          {/* -------------------------------------------------------------- */}

          <View style={styles.inputRow}>
            <TextInput
              value={code}
              onChangeText={setCode}
              placeholder={placeholder}
              placeholderTextColor={
                colors.textSecondary
              }
              autoCapitalize="characters"
              autoCorrect={false}
              editable={!loading}
              style={styles.input}
            />

            <Pressable
              onPress={handleApply}
              disabled={!canApply}
              style={[
                styles.applyButton,
                !canApply &&
                  styles.disabledButton,
              ]}
            >
              {loading ? (
                <ActivityIndicator
                  size="small"
                  color={colors.white}
                />
              ) : (
                <Text style={styles.applyText}>
                  Apply
                </Text>
              )}
            </Pressable>
          </View>

          {/* -------------------------------------------------------------- */}
          {/* Error Message                                                  */}
          {/* -------------------------------------------------------------- */}

          {!!error && (
            <View style={styles.errorContainer}>
              <Ionicons
                name="alert-circle"
                size={18}
                color={colors.error}
              />

              <Text style={styles.errorText}>
                {error}
              </Text>
            </View>
          )}
        </>
      )}
    </View>
  );
};

/* -------------------------------------------------------------------------- */
/*                                    Styles                                  */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  /* ---------------------------------------------------------------------- */
  /* Container                                                              */
  /* ---------------------------------------------------------------------- */

  container: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
  },

  /* ---------------------------------------------------------------------- */
  /* Title                                                                  */
  /* ---------------------------------------------------------------------- */

  title: {
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
    color: colors.text,
    marginBottom: spacing.md,
  },

  /* ---------------------------------------------------------------------- */
  /* Input Row                                                              */
  /* ---------------------------------------------------------------------- */

  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },

  input: {
    flex: 1,
    height: 48,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    fontSize: typography.fontSize.md,
    color: colors.text,
    marginRight: spacing.sm,
  },

  /* ---------------------------------------------------------------------- */
  /* Apply Button                                                           */
  /* ---------------------------------------------------------------------- */

  applyButton: {
    height: 48,
    minWidth: 90,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
  },

  disabledButton: {
    opacity: 0.5,
  },

  applyText: {
    color: colors.white,
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.semibold,
  },

  /* ---------------------------------------------------------------------- */
  /* Applied Coupon                                                         */
  /* ---------------------------------------------------------------------- */

  appliedContainer: {
    backgroundColor:
      colors.successLight || '#ECFDF5',
    borderRadius: radius.md,
    padding: spacing.md,
  },

  appliedHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },

  appliedCodeWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
  },

  appliedCode: {
    marginLeft: spacing.sm,
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
    color: colors.text,
  },

  removeButton: {
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
  },

  removeText: {
    color: colors.error,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
  },

  /* ---------------------------------------------------------------------- */
  /* Discount Row                                                           */
  /* ---------------------------------------------------------------------- */

  discountRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },

  discountLabel: {
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
  },

  discountValue: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
    color: colors.success,
  },

  /* ---------------------------------------------------------------------- */
  /* Error                                                                  */
  /* ---------------------------------------------------------------------- */

  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.sm,
  },

  errorText: {
    marginLeft: spacing.xs,
    fontSize: typography.fontSize.sm,
    color: colors.error,
    flex: 1,
  },
});

/* -------------------------------------------------------------------------- */
/*                              PropTypes & Export                            */
/* -------------------------------------------------------------------------- */

CouponInput.propTypes = {
  /**
   * Currently applied coupon.
   */
  coupon: PropTypes.shape({
    code: PropTypes.string,

    discountType: PropTypes.string,

    discountValue: PropTypes.number,

    discountAmount: PropTypes.number,
  }),

  /**
   * Apply coupon callback.
   */
  onApplyCoupon: PropTypes.func,

  /**
   * Remove coupon callback.
   */
  onRemoveCoupon: PropTypes.func,

  /**
   * Coupon validation loading state.
   */
  loading: PropTypes.bool,

  /**
   * Coupon validation error.
   */
  error: PropTypes.string,

  /**
   * Input placeholder.
   */
  placeholder: PropTypes.string,
};

CouponInput.defaultProps = {
  coupon: null,

  onApplyCoupon: () => {},

  onRemoveCoupon: () => {},

  loading: false,

  error: null,

  placeholder: 'Enter promo code',
};

export default memo(CouponInput);