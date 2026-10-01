/* -------------------------------------------------------------------------- */
/*                            OrderSkeleton.jsx                               */
/* -------------------------------------------------------------------------- */

import React, { memo } from 'react';
import PropTypes from 'prop-types';

import {
  View,
  StyleSheet,
} from 'react-native';

import SkeletonPlaceholder from 'react-native-skeleton-placeholder';

import {
  colors,
  spacing,
  radius,
} from '../../../theme';

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

function OrderSkeleton({
  count,
  showHeader,
}) {
  const placeholders = Array.from(
    { length: count ?? 6 },
    (_, index) => index
  );

  const actionButtons = [0, 1, 2, 3];

  return (
    <View style={styles.container}>
      <SkeletonPlaceholder>
        {showHeader && (
          <SkeletonPlaceholder.Item
            width={180}
            height={28}
            borderRadius={8}
            marginBottom={spacing.lg}
          />
        )}

        {placeholders.map((item) => (
          <View
            key={item}
            style={styles.cardWrapper}
          >
            {/* Card Container */}
            <SkeletonPlaceholder.Item
              backgroundColor={colors.white}
              borderRadius={radius.lg}
              padding={spacing.lg}
              borderWidth={StyleSheet.hairlineWidth}
              borderColor={colors.border || '#E5E7EB'}
              marginBottom={spacing.lg}
            >
              {/* -------------------------------------------------------- */}
              {/* Header                                                   */}
              {/* -------------------------------------------------------- */}

              <SkeletonPlaceholder.Item
                flexDirection="row"
                justifyContent="space-between"
                alignItems="center"
                marginBottom={spacing.lg}
              >
                <SkeletonPlaceholder.Item>
                  {/* Order Number */}
                  <SkeletonPlaceholder.Item
                    width={140}
                    height={18}
                    borderRadius={6}
                    marginBottom={spacing.sm}
                  />

                  {/* Order Date */}
                  <SkeletonPlaceholder.Item
                    width={90}
                    height={12}
                    borderRadius={6}
                  />
                </SkeletonPlaceholder.Item>

                {/* Status Badge */}
                <SkeletonPlaceholder.Item
                  width={80}
                  height={28}
                  borderRadius={20}
                />
              </SkeletonPlaceholder.Item>

              {/* -------------------------------------------------------- */}
              {/* Items Preview                                            */}
              {/* -------------------------------------------------------- */}

              <SkeletonPlaceholder.Item marginBottom={spacing.lg}>
                {[0, 1].map((index) => (
                  <SkeletonPlaceholder.Item
                    key={index}
                    flexDirection="row"
                    alignItems="center"
                    marginBottom={index === 1 ? 0 : spacing.md}
                  >
                    {/* Product Image */}
                    <SkeletonPlaceholder.Item
                      width={56}
                      height={56}
                      borderRadius={10}
                    />

                    <SkeletonPlaceholder.Item
                      marginLeft={spacing.md}
                      flex={1}
                    >
                      {/* Product Name */}
                      <SkeletonPlaceholder.Item
                        width="75%"
                        height={14}
                        borderRadius={6}
                        marginBottom={spacing.sm}
                      />

                      {/* Quantity */}
                      <SkeletonPlaceholder.Item
                        width="35%"
                        height={12}
                        borderRadius={6}
                      />
                    </SkeletonPlaceholder.Item>
                  </SkeletonPlaceholder.Item>
                ))}
              </SkeletonPlaceholder.Item>

              {/* -------------------------------------------------------- */}
              {/* Summary                                                  */}
              {/* -------------------------------------------------------- */}

              <SkeletonPlaceholder.Item
                flexDirection="row"
                justifyContent="space-between"
                alignItems="center"
                marginBottom={spacing.lg}
              >
                {/* Total Label */}
                <SkeletonPlaceholder.Item
                  width={70}
                  height={14}
                  borderRadius={6}
                />

                {/* Total Price */}
                <SkeletonPlaceholder.Item
                  width={110}
                  height={20}
                  borderRadius={6}
                />
              </SkeletonPlaceholder.Item>

              {/* -------------------------------------------------------- */}
              {/* Action Buttons                                           */}
              {/* -------------------------------------------------------- */}

              <SkeletonPlaceholder.Item
                flexDirection="row"
                justifyContent="space-between"
              >
                {actionButtons.map((button) => (
                  <SkeletonPlaceholder.Item
                    key={button}
                    width={82}
                    height={38}
                    borderRadius={radius.full}
                  />
                ))}
              </SkeletonPlaceholder.Item>
            </SkeletonPlaceholder.Item>
          </View>
        ))}
      </SkeletonPlaceholder>
    </View>
  );
}

/* -------------------------------------------------------------------------- */
/*                                   Display Name                             */
/* -------------------------------------------------------------------------- */

OrderSkeleton.displayName = 'OrderSkeleton';

/* -------------------------------------------------------------------------- */
/*                                   Styles                                   */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  /* ---------------------------------------------------------------------- */
  /* Container                                                              */
  /* ---------------------------------------------------------------------- */

  container: {
    flex: 1,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.xl,
    backgroundColor: colors.surface || '#F8FAFC',
  },

  /* ---------------------------------------------------------------------- */
  /* Card Wrapper                                                           */
  /* ---------------------------------------------------------------------- */

  cardWrapper: {
    marginBottom: spacing.lg,
  },
});

/* -------------------------------------------------------------------------- */
/*                         PropTypes & Default Props                          */
/* -------------------------------------------------------------------------- */

OrderSkeleton.propTypes = {
  /**
   * Number of skeleton cards to render.
   */
  count: PropTypes.number,

  /**
   * Whether to render the page header skeleton.
   */
  showHeader: PropTypes.bool,
};

OrderSkeleton.defaultProps = {
  count: 6,
  showHeader: true,
};

/* -------------------------------------------------------------------------- */
/*                                   Export                                   */
/* -------------------------------------------------------------------------- */

export default memo(OrderSkeleton);