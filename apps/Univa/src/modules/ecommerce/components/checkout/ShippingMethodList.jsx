/* -------------------------------------------------------------------------- */
/*                               ShippingMethodList                           */
/* -------------------------------------------------------------------------- */

import React, { memo, useCallback } from 'react';
import PropTypes from 'prop-types';
import {
  View,
  FlatList,
  StyleSheet,
} from 'react-native';

import ShippingCard from './ShippingCard';
import EmptyState from '../../common/EmptyState';

import {
  colors,
  spacing,
} from '../../../theme';

/* -------------------------------------------------------------------------- */
/*                              Component                                     */
/* -------------------------------------------------------------------------- */

const ShippingMethodList = ({
  methods,
  selectedMethodId,
  onSelectMethod,
  currencySymbol,
  freeLabel,
  contentContainerStyle,
}) => {
  /* ---------------------------------------------------------------------- */
  /* Helpers                                                                */
  /* ---------------------------------------------------------------------- */

  const keyExtractor = useCallback(
    (item) => String(item.id),
    []
  );

  const handleSelect = useCallback(
    (method) => {
      if (!method?.disabled && onSelectMethod) {
        onSelectMethod(method);
      }
    },
    [onSelectMethod]
  );
    /* ---------------------------------------------------------------------- */
  /* Render Item                                                            */
  /* ---------------------------------------------------------------------- */

  const renderItem = useCallback(
    ({ item }) => (
      <ShippingCard
        method={item}
        selected={item.id === selectedMethodId}
        onPress={() => handleSelect(item)}
        currencySymbol={currencySymbol}
        freeLabel={freeLabel}
      />
    ),
    [
      selectedMethodId,
      handleSelect,
      currencySymbol,
      freeLabel,
    ]
  );

  /* ---------------------------------------------------------------------- */
  /* Empty State                                                            */
  /* ---------------------------------------------------------------------- */

  const renderEmptyComponent = useCallback(
    () => (
      <EmptyState
        title="No shipping methods"
        description="Shipping options are currently unavailable."
      />
    ),
    []
  );

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View style={styles.container}>
      <FlatList
        data={methods}
        keyExtractor={keyExtractor}
        renderItem={renderItem}
        ListEmptyComponent={renderEmptyComponent}
        contentContainerStyle={[
          styles.contentContainer,
          methods.length === 0 && styles.emptyContent,
          contentContainerStyle,
        ]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        removeClippedSubviews
        initialNumToRender={5}
        maxToRenderPerBatch={5}
        windowSize={7}
      />
    </View>
  );
}
/* -------------------------------------------------------------------------- */
/*                                    Styles                                  */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
    width: '100%',
  },

  contentContainer: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },

  emptyContent: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: spacing.xxl,
  },

  separator: {
    height: spacing.sm,
  },

  footerSpacing: {
    height: spacing.lg,
  },

  loadingContainer: {
    paddingVertical: spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },

  listWrapper: {
    flexGrow: 1,
  },

  cardWrapper: {
    marginBottom: spacing.sm,
  },

  disabledOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.transparent || 'transparent',
  },
});
/* -------------------------------------------------------------------------- */
/*                              PropTypes & Export                            */
/* -------------------------------------------------------------------------- */

ShippingMethodList.propTypes = {
  /**
   * Array of available shipping methods.
   */
  methods: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
      ]).isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string,
      price: PropTypes.number,
      estimatedDays: PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
      ]),
      badge: PropTypes.string,
      icon: PropTypes.elementType,
      disabled: PropTypes.bool,
    })
  ),

  /**
   * Currently selected shipping method ID.
   */
  selectedMethodId: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  /**
   * Callback fired when a shipping method is selected.
   */
  onSelectMethod: PropTypes.func,

  /**
   * Currency symbol displayed by ShippingCard.
   */
  currencySymbol: PropTypes.string,

  /**
   * Label displayed when shipping is free.
   */
  freeLabel: PropTypes.string,

  /**
   * Optional FlatList content container style.
   */
  contentContainerStyle: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

ShippingMethodList.defaultProps = {
  methods: [],
  selectedMethodId: null,
  onSelectMethod: () => {},
  currencySymbol: '$',
  freeLabel: 'Free',
  contentContainerStyle: null,
};

export default memo(ShippingMethodList);