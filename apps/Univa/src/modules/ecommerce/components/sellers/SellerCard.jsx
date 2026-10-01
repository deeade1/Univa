/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/SellerCard.jsx          */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  Image,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import SellerBadge, {
  SellerBadgeTypes,
} from "@/modules/ecommerce/components/common/SellerBadge";
import Rating from "@/modules/ecommerce/components/common/Rating";
import Button from "@/modules/ecommerce/components/common/Button";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SellerCard = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    seller,
    product,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showContact = true,
    showStats = true,
    showFollow = false,
    showTagline = true,
    showRating = true,
    showVerified = true,
    showLocation = true,
    showViewStore = false,
    compact = false,

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    following = false,

    /* ---------------------------------------------------------------------- */
    /* Custom Actions                                                         */
    /* ---------------------------------------------------------------------- */

    actions = null,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onPress,
    onContact,
    onFollow,
    onViewStore,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Memoized Values                                                        */
    /* ---------------------------------------------------------------------- */

    const sellerName = useMemo(
      () => seller?.name ?? seller?.storeName ?? "Seller",
      [seller]
    );

    const avatar = useMemo(
      () => seller?.avatar ?? seller?.profilePicture ?? null,
      [seller]
    );

    const displayLocation = useMemo(
      () => seller?.location ?? seller?.city ?? "Location unavailable",
      [seller]
    );

    const rating = useMemo(
      () => Number(seller?.rating || 0),
      [seller?.rating]
    );

    const reviewCount = useMemo(
      () => seller?.reviewCount ?? 0,
      [seller?.reviewCount]
    );

    const isVerified = useMemo(
      () => seller?.verified ?? false,
      [seller?.verified]
    );

    const productCount = useMemo(
      () => seller?.productCount ?? seller?.products ?? 0,
      [seller]
    );

    const followers = useMemo(
      () => seller?.followers ?? 0,
      [seller?.followers]
    );

    const responseTime = useMemo(
      () => seller?.responseTime ?? "<1 hr",
      [seller?.responseTime]
    );

    const salesCount = useMemo(
      () => seller?.sales ?? 0,
      [seller?.sales]
    );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handlePress = useCallback(() => {
      onPress?.(seller, product);
    }, [onPress, seller, product]);

    const handleContact = useCallback(() => {
      onContact?.(seller, product);
    }, [onContact, seller, product]);

    const handleFollow = useCallback(() => {
      onFollow?.(seller, product);
    }, [onFollow, seller, product]);

    const handleViewStore = useCallback(() => {
      onViewStore?.(seller, product);
    }, [onViewStore, seller, product]);

    /* ---------------------------------------------------------------------- */
    /* Default Actions                                                        */
    /* ---------------------------------------------------------------------- */

    const defaultActions = useMemo(() => {
      const actionList = [];

      if (showContact) {
        actionList.push({
          key: "contact",
          icon: "message-outline",
          label: "Contact",
          onPress: handleContact,
          type: "primary",
        });
      }

      if (showFollow) {
        actionList.push({
          key: "follow",
          icon: following ? "account-check-outline" : "account-plus-outline",
          label: following ? "Following" : "Follow",
          onPress: handleFollow,
          type: "outline",
        });
      }

      if (showViewStore) {
        actionList.push({
          key: "viewstore",
          icon: "storefront-outline",
          label: "View Store",
          onPress: handleViewStore,
          type: "outline",
        });
      }

      return actionList;
    }, [
      showContact,
      showFollow,
      showViewStore,
      following,
      handleContact,
      handleFollow,
      handleViewStore,
    ]);

    const displayActions = actions || defaultActions;

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <Pressable
        accessible
        accessibilityRole="button"
        accessibilityLabel={`Seller: ${sellerName}`}
        onPress={handlePress}
        style={[
          styles.container,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
          compact && styles.compactContainer,
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Header: Avatar + Info                                          */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.header}>
          {/* Avatar */}
          <Image
            source={
              avatar
                ? { uri: avatar }
                : { uri: 'https://ui-avatars.com/api/?name=User&background=random' }
            }
            style={[
              styles.avatar,
              compact && styles.compactAvatar,
            ]}
          />

          {/* Info */}
          <View style={styles.info}>
            <View style={styles.nameRow}>
              <Text
                numberOfLines={1}
                style={[
                  styles.name,
                  { color: colors.text },
                  compact && styles.compactName,
                ]}
              >
                {sellerName}
              </Text>

              {showVerified && isVerified && (
                <SellerBadge
                  type={SellerBadgeTypes.VERIFIED}
                  size="small"
                  iconOnly
                  style={styles.badgeSpacing}
                />
              )}
            </View>

            {/* Location */}
            {showLocation && (
              <Text
                numberOfLines={1}
                style={[
                  styles.location,
                  { color: colors.textSecondary },
                  compact && styles.compactLocation,
                ]}
              >
                {displayLocation}
              </Text>
            )}

            {/* Rating */}
            {showRating && (
              <View style={styles.ratingRow}>
                <Rating
                  rating={rating}
                  size={compact ? "sm" : "md"}
                  readonly
                  showReviewCount={false}
                />

                <Text
                  style={[
                    styles.rating,
                    { color: colors.text },
                    compact && styles.compactRating,
                  ]}
                >
                  {rating.toFixed(1)}
                </Text>

                {!compact && reviewCount > 0 && (
                  <Text
                    style={[
                      styles.reviewCount,
                      { color: colors.textSecondary },
                    ]}
                  >
                    ({reviewCount} reviews)
                  </Text>
                )}
              </View>
            )}

            {/* Tagline */}
            {showTagline && seller?.tagline && !compact && (
              <Text
                numberOfLines={2}
                style={[
                  styles.tagline,
                  { color: colors.textSecondary },
                ]}
              >
                {seller.tagline}
              </Text>
            )}
          </View>
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Stats                                                          */}
        {/* -------------------------------------------------------------- */}

        {showStats && !compact && (
          <View
            style={[
              styles.statsContainer,
              {
                borderTopColor: colors.border,
              },
            ]}
          >
            {/* Products */}
            <View style={styles.statItem}>
              <Text
                style={[
                  styles.statValue,
                  { color: colors.text },
                ]}
              >
                {productCount}
              </Text>
              <Text
                style={[
                  styles.statLabel,
                  { color: colors.textSecondary },
                ]}
              >
                Products
              </Text>
            </View>

            {/* Followers */}
            <View style={styles.statItem}>
              <Text
                style={[
                  styles.statValue,
                  { color: colors.text },
                ]}
              >
                {followers}
              </Text>
              <Text
                style={[
                  styles.statLabel,
                  { color: colors.textSecondary },
                ]}
              >
                Followers
              </Text>
            </View>

            {/* Response Time or Sales */}
            <View style={styles.statItem}>
              <Text
                style={[
                  styles.statValue,
                  { color: colors.text },
                ]}
              >
                {salesCount > 0 ? salesCount : responseTime}
              </Text>
              <Text
                style={[
                  styles.statLabel,
                  { color: colors.textSecondary },
                ]}
              >
                {salesCount > 0 ? "Sales" : "Response"}
              </Text>
            </View>
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Actions - Configurable                                         */}
        {/* -------------------------------------------------------------- */}

        {displayActions.length > 0 && !compact && (
          <View style={styles.actions}>
            {displayActions.map((action) => {
              const isPrimary = action.type === "primary";
              const isSingle = displayActions.length === 1;

              return (
                <Pressable
                  key={action.key}
                  accessible
                  accessibilityRole="button"
                  accessibilityLabel={action.label}
                  onPress={action.onPress}
                  style={[
                    styles.button,
                    isPrimary
                      ? {
                          backgroundColor: colors.primary,
                        }
                      : {
                          borderColor: colors.primary,
                          backgroundColor: "transparent",
                          borderWidth: 1.5,
                        },
                    isSingle && styles.fullButton,
                  ]}
                >
                  <MaterialCommunityIcons
                    name={action.icon}
                    size={18}
                    color={
                      isPrimary
                        ? colors.white
                        : colors.primary
                    }
                  />

                  <Text
                    style={[
                      styles.buttonText,
                      {
                        color: isPrimary
                          ? colors.white
                          : colors.primary,
                      },
                    ]}
                  >
                    {action.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Alternative: Button-based Actions (for product detail context) */}
        {/* -------------------------------------------------------------- */}

        {!compact && (showContact || showViewStore) && displayActions.length === 0 && (
          <View style={styles.buttonActions}>
            {showContact && (
              <Button
                title="Contact Seller"
                icon="message-text-outline"
                variant="outline"
                fullWidth
                onPress={handleContact}
                style={showViewStore ? styles.contactButton : styles.fullButton}
              />
            )}

            {showViewStore && (
              <Button
                title="View Store"
                icon="storefront-outline"
                fullWidth
                onPress={handleViewStore}
                style={showContact ? styles.storeButton : styles.fullButton}
              />
            )}
          </View>
        )}
      </Pressable>
    );
  }
);

SellerCard.displayName = "SellerCard";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SellerCard.propTypes = {
  /**
   * Seller object containing profile information
   */
  seller: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    name: PropTypes.string,
    storeName: PropTypes.string,
    avatar: PropTypes.string,
    profilePicture: PropTypes.string,
    tagline: PropTypes.string,
    location: PropTypes.string,
    city: PropTypes.string,
    rating: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    reviewCount: PropTypes.number,
    products: PropTypes.number,
    productCount: PropTypes.number,
    followers: PropTypes.number,
    sales: PropTypes.number,
    verified: PropTypes.bool,
    badge: PropTypes.string,
    badges: PropTypes.arrayOf(PropTypes.string),
    responseTime: PropTypes.string,
  }),

  /**
   * Optional product object (for context)
   */
  product: PropTypes.object,

  /**
   * Show contact button
   */
  showContact: PropTypes.bool,

  /**
   * Show seller statistics
   */
  showStats: PropTypes.bool,

  /**
   * Show follow button
   */
  showFollow: PropTypes.bool,

  /**
   * Show tagline
   */
  showTagline: PropTypes.bool,

  /**
   * Show rating
   */
  showRating: PropTypes.bool,

  /**
   * Show verified badge
   */
  showVerified: PropTypes.bool,

  /**
   * Show location
   */
  showLocation: PropTypes.bool,

  /**
   * Show view store button
   */
  showViewStore: PropTypes.bool,

  /**
   * Compact mode (hides stats, actions, review count)
   */
  compact: PropTypes.bool,

  /**
   * Whether the current user is following this seller
   */
  following: PropTypes.bool,

  /**
   * Custom actions configuration
   */
  actions: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      icon: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      onPress: PropTypes.func.isRequired,
      type: PropTypes.oneOf(["primary", "outline"]),
    })
  ),

  /**
   * Called when the card is pressed
   */
  onPress: PropTypes.func,

  /**
   * Called when the contact button is pressed
   */
  onContact: PropTypes.func,

  /**
   * Called when the follow button is pressed
   */
  onFollow: PropTypes.func,

  /**
   * Called when the view store button is pressed
   */
  onViewStore: PropTypes.func,

  /**
   * Optional style overrides
   */
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

SellerCard.defaultProps = {
  seller: null,
  product: null,
  showContact: true,
  showStats: true,
  showFollow: false,
  showTagline: true,
  showRating: true,
  showVerified: true,
  showLocation: true,
  showViewStore: false,
  compact: false,
  following: false,
  actions: null,
  onPress: null,
  onContact: null,
  onFollow: null,
  onViewStore: null,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderRadius: 20,
    padding: 18,
    marginBottom: 16,
  },

  compactContainer: {
    padding: 14,
  },

  /* ------------------------------------------------------------------ */
  /* Header                                                             */
  /* ------------------------------------------------------------------ */

  header: {
    flexDirection: "row",
    alignItems: "center",
  },

  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "#E5E7EB",
  },

  compactAvatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
  },

  info: {
    flex: 1,
    marginLeft: 16,
  },

  nameRow: {
    flexDirection: "row",
    alignItems: "center",
  },

  name: {
    fontSize: 18,
    fontWeight: "700",
    flex: 1,
  },

  compactName: {
    fontSize: 16,
  },

  badgeSpacing: {
    marginLeft: 6,
  },

  location: {
    marginTop: 4,
    fontSize: 14,
  },

  compactLocation: {
    fontSize: 12,
    marginTop: 2,
  },

  tagline: {
    marginTop: 6,
    fontSize: 14,
    lineHeight: 20,
  },

  /* ------------------------------------------------------------------ */
  /* Rating                                                             */
  /* ------------------------------------------------------------------ */

  ratingRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 8,
  },

  rating: {
    marginLeft: 4,
    fontWeight: "700",
    fontSize: 15,
  },

  compactRating: {
    fontSize: 13,
  },

  reviewCount: {
    marginLeft: 6,
    fontSize: 13,
  },

  /* ------------------------------------------------------------------ */
  /* Stats                                                              */
  /* ------------------------------------------------------------------ */

  statsContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    borderTopWidth: 1,
    marginTop: 18,
    paddingTop: 18,
  },

  statItem: {
    flex: 1,
    alignItems: "center",
  },

  statValue: {
    fontSize: 16,
    fontWeight: "700",
  },

  statLabel: {
    marginTop: 6,
    fontSize: 12,
    textAlign: "center",
  },

  /* ------------------------------------------------------------------ */
  /* Actions                                                            */
  /* ------------------------------------------------------------------ */

  actions: {
    flexDirection: "row",
    marginTop: 4,
  },

  button: {
    flex: 1,
    height: 46,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
    marginHorizontal: 4,
  },

  fullButton: {
    marginHorizontal: 0,
  },

  buttonText: {
    marginLeft: 8,
    fontWeight: "700",
    fontSize: 15,
  },

  /* ------------------------------------------------------------------ */
  /* Button Actions (Alternative)                                       */
  /* ------------------------------------------------------------------ */

  buttonActions: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 24,
  },

  contactButton: {
    flex: 1,
    marginRight: 8,
  },

  storeButton: {
    flex: 1,
    marginLeft: 8,
  },
});

export default SellerCard;