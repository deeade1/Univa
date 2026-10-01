/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/seller/SellerContactCard.jsx   */
/* -------------------------------------------------------------------------- */

import React, { memo, useCallback, useMemo } from "react";
import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
  Linking,
  Platform,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Action Button Component                                                    */
/* -------------------------------------------------------------------------- */

const ActionButton = memo(({
  icon,
  label,
  onPress,
  color,
  disabled = false,
  loading = false,
  accessibilityLabel,
}) => {
  const { colors } = theme;

  return (
    <Pressable
      accessible
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel || label}
      accessibilityState={{ disabled, busy: loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={[
        styles.actionButton,
        {
          borderColor: colors.border,
          opacity: disabled ? 0.5 : 1,
        },
      ]}
    >
      <MaterialCommunityIcons
        name={icon}
        size={22}
        color={color}
      />

      <Text
        style={[
          styles.actionLabel,
          {
            color: disabled ? colors.textSecondary : colors.text,
          },
        ]}
      >
        {loading ? "Loading..." : label}
      </Text>
    </Pressable>
  );
});

ActionButton.displayName = "ActionButton";

ActionButton.propTypes = {
  icon: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  onPress: PropTypes.func,
  color: PropTypes.string.isRequired,
  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  accessibilityLabel: PropTypes.string,
};

ActionButton.defaultProps = {
  onPress: null,
  disabled: false,
  loading: false,
  accessibilityLabel: null,
};

/* -------------------------------------------------------------------------- */
/* Contact Info Item Component                                                */
/* -------------------------------------------------------------------------- */

const ContactInfoItem = memo(({
  icon,
  value,
  type,
  colors,
  onPress,
}) => {
  const handlePress = useCallback(() => {
    if (onPress && value) {
      onPress(value);
    }
  }, [onPress, value]);

  const isPressable = !!onPress && !!value;

  return (
    <Pressable
      accessible
      accessibilityRole={isPressable ? "button" : "text"}
      accessibilityLabel={`${type}: ${value}`}
      disabled={!isPressable}
      onPress={handlePress}
      style={styles.infoRow}
    >
      <MaterialCommunityIcons
        name={icon}
        size={20}
        color={colors.primary}
      />

      <Text
        style={[
          styles.infoText,
          {
            color: colors.text,
          },
        ]}
        numberOfLines={1}
      >
        {value}
      </Text>

      {isPressable && (
        <MaterialCommunityIcons
          name="chevron-right"
          size={20}
          color={colors.textSecondary}
        />
      )}
    </Pressable>
  );
});

ContactInfoItem.displayName = "ContactInfoItem";

ContactInfoItem.propTypes = {
  icon: PropTypes.string.isRequired,
  value: PropTypes.string,
  type: PropTypes.string.isRequired,
  colors: PropTypes.object.isRequired,
  onPress: PropTypes.func,
};

ContactInfoItem.defaultProps = {
  value: null,
  onPress: null,
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SellerContactCard = memo(({
  seller = {},
  loading = false,
  columns = 2,
  showPhone = true,
  showEmail = true,
  showChat = true,
  showCall = true,
  showWhatsApp = false,
  showWebsite = false,
  showTelegram = false,
  showInstagram = false,
  headerIcon = "account-box-outline",
  headerTitle = "Contact Seller",
  onChat,
  onCall,
  onEmail,
  onWhatsApp,
  onWebsite,
  onTelegram,
  onInstagram,
  style,
}) => {
  const { colors } = theme;

  /* ---------------------------------------------------------------------- */
  /* Contact Info Configuration                                             */
  /* ---------------------------------------------------------------------- */

  const contactInfo = useMemo(() => {
    const info = [];

    if (showPhone && seller?.phone) {
      info.push({
        key: "phone",
        icon: "phone-outline",
        value: seller.phone,
        type: "Phone",
        onPress: (value) => {
          const url = `tel:${value}`;
          Linking.openURL(url).catch(() => {});
        },
      });
    }

    if (showEmail && seller?.email) {
      info.push({
        key: "email",
        icon: "email-outline",
        value: seller.email,
        type: "Email",
        onPress: (value) => {
          const url = `mailto:${value}`;
          Linking.openURL(url).catch(() => {});
        },
      });
    }

    if (showWebsite && seller?.website) {
      info.push({
        key: "website",
        icon: "web",
        value: seller.website,
        type: "Website",
        onPress: (value) => {
          const url = value.startsWith('http') ? value : `https://${value}`;
          Linking.openURL(url).catch(() => {});
        },
      });
    }

    return info;
  }, [seller, showPhone, showEmail, showWebsite]);

  /* ---------------------------------------------------------------------- */
  /* Actions Configuration                                                  */
  /* ---------------------------------------------------------------------- */

  const actions = useMemo(() => {
    const actionsList = [];

    if (showChat && seller?.id) {
      actionsList.push({
        key: "chat",
        icon: "message-outline",
        label: "Chat",
        color: colors.primary,
        onPress: () => onChat?.(seller),
        accessibilityLabel: `Chat with ${seller?.name || "seller"}`,
        disabled: !onChat,
      });
    }

    if (showCall && seller?.phone) {
      actionsList.push({
        key: "call",
        icon: "phone",
        label: "Call",
        color: colors.success || "#10B981",
        onPress: () => {
          const url = `tel:${seller.phone}`;
          Linking.openURL(url).catch(() => {});
          onCall?.(seller);
        },
        accessibilityLabel: `Call ${seller?.name || "seller"}`,
        disabled: !onCall && !seller?.phone,
      });
    }

    if (showWhatsApp && seller?.phone) {
      actionsList.push({
        key: "whatsapp",
        icon: "whatsapp",
        label: "WhatsApp",
        color: "#25D366", // Brand color, keep as is
        onPress: () => {
          const phone = seller.phone.replace(/\D/g, '');
          const url = `https://wa.me/${phone}`;
          Linking.openURL(url).catch(() => {});
          onWhatsApp?.(seller);
        },
        accessibilityLabel: `WhatsApp ${seller?.name || "seller"}`,
        disabled: !onWhatsApp && !seller?.phone,
      });
    }

    if (showEmail && seller?.email) {
      actionsList.push({
        key: "email_action",
        icon: "email-outline",
        label: "Email",
        color: colors.warning || "#F59E0B",
        onPress: () => {
          const url = `mailto:${seller.email}`;
          Linking.openURL(url).catch(() => {});
          onEmail?.(seller);
        },
        accessibilityLabel: `Email ${seller?.name || "seller"}`,
        disabled: !onEmail && !seller?.email,
      });
    }

    if (showWebsite && seller?.website) {
      actionsList.push({
        key: "website_action",
        icon: "web",
        label: "Website",
        color: colors.info || "#3B82F6",
        onPress: () => {
          const url = seller.website.startsWith('http') ? seller.website : `https://${seller.website}`;
          Linking.openURL(url).catch(() => {});
          onWebsite?.(seller);
        },
        accessibilityLabel: `Visit ${seller?.name || "seller"}'s website`,
        disabled: !onWebsite && !seller?.website,
      });
    }

    if (showTelegram && seller?.telegram) {
      actionsList.push({
        key: "telegram",
        icon: "telegram",
        label: "Telegram",
        color: colors.info || "#0088CC",
        onPress: () => {
          const url = `https://t.me/${seller.telegram}`;
          Linking.openURL(url).catch(() => {});
          onTelegram?.(seller);
        },
        accessibilityLabel: `Telegram ${seller?.name || "seller"}`,
        disabled: !onTelegram && !seller?.telegram,
      });
    }

    if (showInstagram && seller?.instagram) {
      actionsList.push({
        key: "instagram",
        icon: "instagram",
        label: "Instagram",
        color: "#E4405F", // Brand color
        onPress: () => {
          const url = `https://instagram.com/${seller.instagram}`;
          Linking.openURL(url).catch(() => {});
          onInstagram?.(seller);
        },
        accessibilityLabel: `Instagram ${seller?.name || "seller"}`,
        disabled: !onInstagram && !seller?.instagram,
      });
    }

    return actionsList;
  }, [
    seller,
    showChat,
    showCall,
    showWhatsApp,
    showEmail,
    showWebsite,
    showTelegram,
    showInstagram,
    onChat,
    onCall,
    onWhatsApp,
    onEmail,
    onWebsite,
    onTelegram,
    onInstagram,
    colors,
  ]);

  /* ---------------------------------------------------------------------- */
  /* Memoized Styles                                                        */
  /* ---------------------------------------------------------------------- */

  const actionButtonWidth = useMemo(() => {
    if (columns === 1) return "98%";
    if (columns === 2) return "48%";
    if (columns === 3) return "31%";
    return "48%";
  }, [columns]);

  /* ---------------------------------------------------------------------- */
  /* Render                                                                 */
  /* ---------------------------------------------------------------------- */

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: colors.card,
          borderColor: colors.border,
        },
        style,
      ]}
    >
      {/* Header */}
      <View style={styles.header}>
        <MaterialCommunityIcons
          name={headerIcon}
          size={22}
          color={colors.primary}
        />

        <Text
          style={[
            styles.title,
            { color: colors.text },
          ]}
        >
          {headerTitle}
        </Text>
      </View>

      {/* Contact Info */}
      {!loading && contactInfo.length > 0 && (
        <View style={styles.infoContainer}>
          {contactInfo.map((info) => (
            <ContactInfoItem
              key={info.key}
              icon={info.icon}
              value={info.value}
              type={info.type}
              colors={colors}
              onPress={info.onPress}
            />
          ))}
        </View>
      )}

      {/* Loading Placeholders */}
      {loading && (
        <View style={styles.infoContainer}>
          {[1, 2].map((i) => (
            <View key={i} style={styles.infoRow}>
              <View style={[styles.placeholderIcon, { backgroundColor: colors.border }]} />
              <View style={[styles.placeholderText, { backgroundColor: colors.border }]} />
            </View>
          ))}
        </View>
      )}

      {/* Actions */}
      {!loading && actions.length > 0 && (
        <View style={styles.actions}>
          {actions.map((action) => (
            <ActionButton
              key={action.key}
              icon={action.icon}
              label={action.label}
              color={action.color}
              onPress={action.onPress}
              disabled={action.disabled}
              accessibilityLabel={action.accessibilityLabel}
              style={{ width: actionButtonWidth }}
            />
          ))}
        </View>
      )}
    </View>
  );
});

SellerContactCard.displayName = "SellerContactCard";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SellerContactCard.propTypes = {
  /**
   * Seller object containing contact information
   */
  seller: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    name: PropTypes.string,
    phone: PropTypes.string,
    email: PropTypes.string,
    website: PropTypes.string,
    telegram: PropTypes.string,
    instagram: PropTypes.string,
  }),

  /**
   * Loading state for skeleton/placeholders
   */
  loading: PropTypes.bool,

  /**
   * Number of action columns (1, 2, or 3)
   */
  columns: PropTypes.oneOf([1, 2, 3]),

  /**
   * Show phone number and call action
   */
  showPhone: PropTypes.bool,

  /**
   * Show email and email action
   */
  showEmail: PropTypes.bool,

  /**
   * Show chat action
   */
  showChat: PropTypes.bool,

  /**
   * Show call action
   */
  showCall: PropTypes.bool,

  /**
   * Show WhatsApp action
   */
  showWhatsApp: PropTypes.bool,

  /**
   * Show website link
   */
  showWebsite: PropTypes.bool,

  /**
   * Show Telegram action
   */
  showTelegram: PropTypes.bool,

  /**
   * Show Instagram action
   */
  showInstagram: PropTypes.bool,

  /**
   * Custom header icon
   */
  headerIcon: PropTypes.string,

  /**
   * Custom header title
   */
  headerTitle: PropTypes.string,

  /**
   * Chat action handler
   */
  onChat: PropTypes.func,

  /**
   * Call action handler
   */
  onCall: PropTypes.func,

  /**
   * Email action handler
   */
  onEmail: PropTypes.func,

  /**
   * WhatsApp action handler
   */
  onWhatsApp: PropTypes.func,

  /**
   * Website action handler
   */
  onWebsite: PropTypes.func,

  /**
   * Telegram action handler
   */
  onTelegram: PropTypes.func,

  /**
   * Instagram action handler
   */
  onInstagram: PropTypes.func,

  /**
   * Optional style overrides
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

SellerContactCard.defaultProps = {
  seller: {},
  loading: false,
  columns: 2,
  showPhone: true,
  showEmail: true,
  showChat: true,
  showCall: true,
  showWhatsApp: false,
  showWebsite: false,
  showTelegram: false,
  showInstagram: false,
  headerIcon: "account-box-outline",
  headerTitle: "Contact Seller",
  onChat: null,
  onCall: null,
  onEmail: null,
  onWhatsApp: null,
  onWebsite: null,
  onTelegram: null,
  onInstagram: null,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 18,
    marginVertical: 16,
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 18,
  },

  title: {
    marginLeft: 10,
    fontSize: 18,
    fontWeight: "700",
  },

  infoContainer: {
    marginBottom: 16,
  },

  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 14,
    paddingVertical: 4,
  },

  infoText: {
    marginLeft: 12,
    fontSize: 15,
    flex: 1,
  },

  actions: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 4,
    marginHorizontal: -4,
  },

  actionButton: {
    margin: 4,
    borderWidth: 1,
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: "center",
    justifyContent: "center",
  },

  actionLabel: {
    marginTop: 8,
    fontSize: 13,
    fontWeight: "600",
  },

  // Loading placeholders
  placeholderIcon: {
    width: 20,
    height: 20,
    borderRadius: 10,
    marginRight: 12,
  },

  placeholderText: {
    flex: 1,
    height: 16,
    borderRadius: 4,
  },
});

export default SellerContactCard;