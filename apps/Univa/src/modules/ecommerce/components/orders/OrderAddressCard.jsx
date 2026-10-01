/* -------------------------------------------------------------------------- */
/*                           OrderAddressCard.jsx                             */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
} from 'react';

import PropTypes from 'prop-types';

import {
  View,
  Text,
  StyleSheet,
} from 'react-native';

import {
  MaterialCommunityIcons,
} from '@expo/vector-icons';

import {
  colors,
  spacing,
  radius,
  typography,
} from '../../../theme';

import Divider from '../common/Divider';
import IconLabel from '../common/IconLabel';

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

function OrderAddressCard({
  title,
  address,
  showEmail,
  showPhone,
  showDivider,
}) {
  /* ---------------------------------------------------------------------- */
  /* Derived Values                                                         */
  /* ---------------------------------------------------------------------- */

  const fullAddress = useMemo(() => {
    if (!address) {
      return '';
    }

    // Get country string from various possible formats
    const country =
      address.country?.country ||
      address.country?.name ||
      address.country?.code ||
      address.country;

    // Get state/area from various possible formats
    const state = address.state || address.countryArea;

    return [
      address.streetAddress1,
      address.streetAddress2,
      address.city,
      state,
      address.postalCode,
      country,
    ]
      .filter(Boolean)
      .join(', ');
  }, [address]);

  const recipientName = useMemo(() => {
    if (!address) {
      return 'Recipient';
    }

    return (
      address.fullName ||
      [address.firstName, address.lastName]
        .filter(Boolean)
        .join(' ') ||
      'Recipient'
    );
  }, [address]);

  const deliveryInstructions = useMemo(() => {
    return (
      address?.deliveryInstructions ||
      address?.note ||
      address?.notes ||
      null
    );
  }, [address]);

  if (!address) {
    return null;
  }

  return (
    <View style={styles.card}>
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                             */}
      {/* ------------------------------------------------------------------ */}

      <View
        accessibilityRole="header"
        accessibilityLabel={title}
        style={styles.header}
      >
        <MaterialCommunityIcons
          name="map-marker-outline"
          size={22}
          color={colors.primary}
        />

        <Text style={styles.title}>
          {title}
        </Text>
      </View>

      {showDivider && <Divider />}

      {/* ------------------------------------------------------------------ */}
      {/* Recipient                                                          */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.section}>
        <View style={styles.nameRow}>
          <MaterialCommunityIcons
            name="account-circle-outline"
            size={20}
            color={colors.textSecondary}
          />

          <Text style={styles.recipientName}>
            {recipientName}
          </Text>
        </View>

        {address?.companyName && (
          <View style={styles.infoRow}>
            <MaterialCommunityIcons
              name="office-building-outline"
              size={18}
              color={colors.textSecondary}
            />

            <Text style={styles.infoText}>
              {address.companyName}
            </Text>
          </View>
        )}
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Address                                                            */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.section}>
        <IconLabel
          icon="map-marker"
          label="Delivery Address"
          value={fullAddress}
          valueProps={{
            numberOfLines: undefined,
            style: styles.addressValue,
          }}
        />
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Delivery Instructions                                              */}
      {/* ------------------------------------------------------------------ */}

      {deliveryInstructions && (
        <View style={styles.section}>
          <View style={styles.instructionsHeader}>
            <MaterialCommunityIcons
              name="clipboard-text-outline"
              size={18}
              color={colors.primary}
            />

            <Text style={styles.instructionsTitle}>
              Delivery Instructions
            </Text>
          </View>

          <Text style={styles.instructionsText}>
            {deliveryInstructions}
          </Text>
        </View>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Contact Information                                                */}
      {/* ------------------------------------------------------------------ */}

      {(showPhone || showEmail) && (
        <>
          <Divider />

          <View style={styles.section}>
            {showPhone && address?.phone && (
              <IconLabel
                icon="phone-outline"
                label="Phone"
                value={address.phone}
                style={styles.contactItem}
              />
            )}

            {showEmail && address?.email && (
              <IconLabel
                icon="email-outline"
                label="Email"
                value={address.email}
                style={styles.contactItem}
              />
            )}
          </View>
        </>
      )}
    </View>
  );
}

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.lg,

    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border || '#E5E7EB',
  },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
  },

  title: {
    marginLeft: spacing.sm,

    color: colors.text,

    fontSize: typography.fontSize.lg,

    fontWeight: typography.fontWeight.bold,
  },

  section: {
    marginTop: spacing.md,
  },

  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },

  recipientName: {
    flex: 1,

    marginLeft: spacing.sm,

    color: colors.text,

    fontSize: typography.fontSize.md,

    fontWeight: typography.fontWeight.semibold,
  },

  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',

    marginTop: spacing.xs,
  },

  infoText: {
    flex: 1,

    marginLeft: spacing.sm,

    color: colors.textSecondary,

    fontSize: typography.fontSize.sm,
  },

  addressValue: {
    flex: 1,
    flexWrap: 'wrap',
  },

  instructionsHeader: {
    flexDirection: 'row',
    alignItems: 'center',

    marginBottom: spacing.sm,
  },

  instructionsTitle: {
    marginLeft: spacing.sm,

    color: colors.primary,

    fontSize: typography.fontSize.md,

    fontWeight: typography.fontWeight.semibold,
  },

  instructionsText: {
    color: colors.textSecondary,

    fontSize: typography.fontSize.sm,

    lineHeight: 22,
  },

  contactItem: {
    marginBottom: spacing.sm,
  },
});

/* -------------------------------------------------------------------------- */
/*                         PropTypes & Default Props                          */
/* -------------------------------------------------------------------------- */

OrderAddressCard.propTypes = {
  /* ---------------------------------------------------------------------- */
  /* Content                                                                */
  /* ---------------------------------------------------------------------- */

  title: PropTypes.string,

  address: PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    firstName: PropTypes.string,

    lastName: PropTypes.string,

    fullName: PropTypes.string,

    companyName: PropTypes.string,

    phone: PropTypes.string,

    email: PropTypes.string,

    streetAddress1: PropTypes.string,

    streetAddress2: PropTypes.string,

    city: PropTypes.string,

    state: PropTypes.string,

    countryArea: PropTypes.string,

    postalCode: PropTypes.string,

    country: PropTypes.oneOfType([
      PropTypes.string,

      PropTypes.shape({
        code: PropTypes.string,

        country: PropTypes.string,

        name: PropTypes.string,
      }),
    ]),

    deliveryInstructions: PropTypes.string,

    note: PropTypes.string,

    notes: PropTypes.string,

    metadata: PropTypes.array,
  }),

  /* ---------------------------------------------------------------------- */
  /* Display Options                                                        */
  /* ---------------------------------------------------------------------- */

  showEmail: PropTypes.bool,

  showPhone: PropTypes.bool,

  showDivider: PropTypes.bool,
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

OrderAddressCard.defaultProps = {
  title: 'Shipping Address',

  address: null,

  showEmail: true,

  showPhone: true,

  showDivider: true,
};

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default memo(OrderAddressCard);