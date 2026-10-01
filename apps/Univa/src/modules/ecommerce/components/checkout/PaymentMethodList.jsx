/* -------------------------------------------------------------------------- */
/*                             PaymentMethodList                              */
/* -------------------------------------------------------------------------- */

import React, { memo, useCallback } from 'react';
import PropTypes from 'prop-types';
import {
  View,
  FlatList,
  StyleSheet,
} from 'react-native';

import PaymentMethodCard from './PaymentMethodCard';
import EmptyState from '../../common/EmptyState';

import {
  colors,
  spacing,
} from '../../../theme';

/* -------------------------------------------------------------------------- */
/*                                Component                                   */
/* -------------------------------------------------------------------------- */

const PaymentMethodList = ({
  methods,
  selectedMethodId,
  onSelectMethod,
  showDefaultBadge,
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
      <PaymentMethodCard
        method={item}
        selected={item.id === selectedMethodId}
        onPress={handleSelect}
        showDefaultBadge={showDefaultBadge}
      />
    ),
    [
      selectedMethodId,
      handleSelect,
      showDefaultBadge,
    ]
  );

  /* ---------------------------------------------------------------------- */
  /* Empty State                                                            */
  /* ---------------------------------------------------------------------- */

  const renderEmptyComponent = useCallback(
    () => (
      <EmptyState
        title="No payment methods"
        description="No payment methods are currently available. Please add or enable one to continue."
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
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
        removeClippedSubviews
        initialNumToRender={6}
        maxToRenderPerBatch={6}
        windowSize={7}
        ItemSeparatorComponent={() => (
          <View style={styles.separator} />
        )}
        ListFooterComponent={() => (
          <View style={styles.footerSpacing} />
        )}
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

  /* ---------------------------------------------------------------------- */
  /* FlatList                                                               */
  /* ---------------------------------------------------------------------- */

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

  /* ---------------------------------------------------------------------- */
  /* List Spacing                                                           */
  /* ---------------------------------------------------------------------- */

  separator: {
    height: spacing.sm,
  },

  footerSpacing: {
    height: spacing.lg,
  },

  /* ---------------------------------------------------------------------- */
  /* Optional Utility Styles                                                */
  /* ---------------------------------------------------------------------- */

  listWrapper: {
    flexGrow: 1,
  },

  loadingContainer: {
    paddingVertical: spacing.lg,
    justifyContent: 'center',
    alignItems: 'center',
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

PaymentMethodList.propTypes = {
  /**
   * Available payment methods.
   */
  methods: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
      ]).isRequired,

      type: PropTypes.oneOf([
        'card',
        'wallet',
        'bank',
        'paypal',
        'cash',
      ]).isRequired,

      name: PropTypes.string,
      brand: PropTypes.string,
      last4: PropTypes.string,
      holderName: PropTypes.string,
      expiry: PropTypes.string,
      icon: PropTypes.elementType,
      isDefault: PropTypes.bool,
      disabled: PropTypes.bool,
    })
  ),

  /**
   * Currently selected payment method ID.
   */
  selectedMethodId: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  /**
   * Invoked when a payment method is selected.
   */
  onSelectMethod: PropTypes.func,

  /**
   * Whether to display the DEFAULT badge.
   */
  showDefaultBadge: PropTypes.bool,

  /**
   * Optional FlatList content container style.
   */
  contentContainerStyle: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

PaymentMethodList.defaultProps = {
  methods: [],
  selectedMethodId: null,
  onSelectMethod: () => {},
  showDefaultBadge: true,
  contentContainerStyle: null,
};

export default memo(PaymentMethodList);