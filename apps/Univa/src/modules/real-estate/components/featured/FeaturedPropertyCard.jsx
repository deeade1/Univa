import React, {
  memo,
  useMemo,
} from "react";

import {
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { LinearGradient } from "expo-linear-gradient";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Featured Property Card */
/* -------------------------------------------------------------------------- */

function FeaturedPropertyCard({
  property,
  onPress,
  onFavoritePress,
}) {
  const { colors } = useTheme();

  /* -------------------------------------------------------------------------- */
  /* Property Data */
  /* -------------------------------------------------------------------------- */

  const {
    id,

    slug,

    title,

    description,

    image,

    images = [],

    price = 0,

    currency = "NGN",

    propertyType,

    listingType,

    city,

    state,

    country,

    bedrooms = 0,

    bathrooms = 0,

    parkingSpaces = 0,

    area,

    areaUnit = "sqm",

    isFeatured = false,

    isVerified = false,

    isFavorite = false,

    available = true,
  } = property ?? {};

  /* -------------------------------------------------------------------------- */
  /* Cover Image */
  /* -------------------------------------------------------------------------- */

  const coverImage =
    useMemo(() => {
      if (image) {
        return image;
      }

      if (images.length > 0) {
        return images[0];
      }

      return null;
    }, [image, images]);

  /* -------------------------------------------------------------------------- */
  /* Formatted Price */
  /* -------------------------------------------------------------------------- */

  const formattedPrice =
    useMemo(() => {
      try {
        return new Intl.NumberFormat(
          "en-NG",
          {
            style: "currency",
            currency,
            maximumFractionDigits: 0,
          }
        ).format(price);
      } catch {
        return `₦${Number(
          price
        ).toLocaleString()}`;
      }
    }, [price, currency]);

  /* -------------------------------------------------------------------------- */
  /* Location */
  /* -------------------------------------------------------------------------- */

  const location =
    useMemo(() => {
      return [city, state, country]
        .filter(Boolean)
        .join(", ");
    }, [city, state, country]);
      /* -------------------------------------------------------------------------- */
  /* Image Section */
  /* -------------------------------------------------------------------------- */

  return (
    <Pressable
      onPress={onPress}
      style={[
        styles.container,
        {
          backgroundColor: colors.card,
        },
      ]}
    >
      <View style={styles.imageContainer}>
        {coverImage ? (
          <Image
            source={{
              uri: coverImage,
            }}
            style={styles.image}
            resizeMode="cover"
          />
        ) : (
          <View
            style={[
              styles.placeholder,
              {
                backgroundColor:
                  colors.border,
              },
            ]}
          >
            <Ionicons
              name="home-outline"
              size={48}
              color={
                colors.textSecondary
              }
            />
          </View>
        )}

        {/* ------------------------------------------------------ */}
        {/* Image Overlay */}
        {/* ------------------------------------------------------ */}

        <LinearGradient
          colors={[
            "transparent",
            "rgba(0,0,0,0.65)",
          ]}
          style={styles.overlay}
        />

        {/* ------------------------------------------------------ */}
        {/* Featured Badge */}
        {/* ------------------------------------------------------ */}

        {isFeatured && (
          <LinearGradient
            colors={[
              "#FBBF24",
              "#F59E0B",
            ]}
            style={
              styles.featuredBadge
            }
          >
            <Ionicons
              name="star"
              size={12}
              color="#FFFFFF"
            />

            <Text
              style={
                styles.featuredText
              }
            >
              FEATURED
            </Text>
          </LinearGradient>
        )}

        {/* ------------------------------------------------------ */}
        {/* Verified Badge */}
        {/* ------------------------------------------------------ */}

        {isVerified && (
          <View
            style={
              styles.verifiedBadge
            }
          >
            <Ionicons
              name="checkmark-circle"
              size={24}
              color="#22C55E"
            />
          </View>
        )}

        {/* ------------------------------------------------------ */}
        {/* Availability */}
        {/* ------------------------------------------------------ */}

        <View
          style={[
            styles.statusBadge,
            {
              backgroundColor:
                available
                  ? "#16A34A"
                  : "#DC2626",
            },
          ]}
        >
          <Text
            style={
              styles.statusText
            }
          >
            {available
              ? "Available"
              : "Sold"}
          </Text>
        </View>

        {/* ------------------------------------------------------ */}
        {/* Favorite Button */}
        {/* ------------------------------------------------------ */}

        <Pressable
          onPress={() =>
            onFavoritePress?.(
              property
            )
          }
          style={
            styles.favoriteButton
          }
        >
          <Ionicons
            name={
              isFavorite
                ? "heart"
                : "heart-outline"
            }
            size={22}
            color={
              isFavorite
                ? "#EF4444"
                : "#FFFFFF"
            }
          />
        </Pressable>
      </View>

            {/* ---------------------------------------------------------------------- */}
      {/* Property Details */}
      {/* ---------------------------------------------------------------------- */}

      <View style={styles.content}>
        {/* ------------------------------------------------------ */}
        {/* Price */}
        {/* ------------------------------------------------------ */}

        <Text
          style={[
            styles.price,
            {
              color: colors.primary,
            },
          ]}
        >
          {formattedPrice}
        </Text>

        {/* ------------------------------------------------------ */}
        {/* Title */}
        {/* ------------------------------------------------------ */}

        <Text
          numberOfLines={2}
          style={[
            styles.title,
            {
              color: colors.text,
            },
          ]}
        >
          {title || "Untitled Property"}
        </Text>

        {/* ------------------------------------------------------ */}
        {/* Description */}
        {/* ------------------------------------------------------ */}

        {!!description && (
          <Text
            numberOfLines={2}
            style={[
              styles.description,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            {description}
          </Text>
        )}

        {/* ------------------------------------------------------ */}
        {/* Location */}
        {/* ------------------------------------------------------ */}

        <View
          style={styles.locationRow}
        >
          <Ionicons
            name="location-outline"
            size={15}
            color={
              colors.textSecondary
            }
          />

          <Text
            numberOfLines={1}
            style={[
              styles.location,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            {location}
          </Text>
        </View>

        {/* ------------------------------------------------------ */}
        {/* Property Type */}
        {/* ------------------------------------------------------ */}

        <View
          style={styles.badgesRow}
        >
          {!!propertyType && (
            <View
              style={[
                styles.typeBadge,
                {
                  backgroundColor:
                    colors.primary,
                },
              ]}
            >
              <Text
                style={
                  styles.typeBadgeText
                }
              >
                {propertyType}
              </Text>
            </View>
          )}

          {!!listingType && (
            <View
              style={[
                styles.listingBadge,
                {
                  borderColor:
                    colors.primary,
                },
              ]}
            >
              <Text
                style={[
                  styles.listingBadgeText,
                  {
                    color:
                      colors.primary,
                  },
                ]}
              >
                {listingType}
              </Text>
            </View>
          )}
        </View>

        {/* ------------------------------------------------------ */}
        {/* Property Stats */}
        {/* ------------------------------------------------------ */}

        <View
          style={styles.statsRow}
        >
          <View
            style={styles.statItem}
          >
            <Ionicons
              name="bed-outline"
              size={18}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.statText,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {bedrooms} Beds
            </Text>
          </View>

          <View
            style={styles.statItem}
          >
            <Ionicons
              name="water-outline"
              size={18}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.statText,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {bathrooms} Baths
            </Text>
          </View>

          <View
            style={styles.statItem}
          >
            <Ionicons
              name="car-outline"
              size={18}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.statText,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {parkingSpaces}
            </Text>
          </View>

          <View
            style={styles.statItem}
          >
            <Ionicons
              name="expand-outline"
              size={18}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.statText,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {area} {areaUnit}
            </Text>
          </View>
        </View>
      </View>
    </Pressable>
  );
}
const styles = StyleSheet.create({
  container: {
    width: 320,
    borderRadius: 22,
    overflow: "hidden",
    marginBottom: 8,
    elevation: 6,

    shadowColor: "#000",

    shadowOpacity: 0.12,

    shadowRadius: 10,

    shadowOffset: {
      width: 0,
      height: 5,
    },
  },

  /* -------------------------------------------------------------------------- */
  /* Image */
  /* -------------------------------------------------------------------------- */

  imageContainer: {
    height: 220,
    position: "relative",
  },

  image: {
    width: "100%",
    height: "100%",
  },

  placeholder: {
    flex: 1,

    justifyContent: "center",

    alignItems: "center",
  },

  overlay: {
    ...StyleSheet.absoluteFillObject,
  },

  /* -------------------------------------------------------------------------- */
  /* Badges */
  /* -------------------------------------------------------------------------- */

  featuredBadge: {
    position: "absolute",

    top: 14,

    left: 14,

    flexDirection: "row",

    alignItems: "center",

    paddingHorizontal: 12,

    paddingVertical: 6,

    borderRadius: 20,
  },

  featuredText: {
    color: "#FFFFFF",

    marginLeft: 4,

    fontWeight: "700",

    fontSize: 11,

    letterSpacing: 0.4,
  },

  verifiedBadge: {
    position: "absolute",

    top: 14,

    right: 14,
  },

  statusBadge: {
    position: "absolute",

    left: 14,

    bottom: 14,

    borderRadius: 16,

    paddingHorizontal: 12,

    paddingVertical: 6,
  },

  statusText: {
    color: "#FFFFFF",

    fontWeight: "700",

    fontSize: 12,
  },

  favoriteButton: {
    position: "absolute",

    bottom: 14,

    right: 14,

    width: 40,

    height: 40,

    borderRadius: 20,

    justifyContent: "center",

    alignItems: "center",

    backgroundColor:
      "rgba(0,0,0,0.35)",
  },

  /* -------------------------------------------------------------------------- */
  /* Content */
  /* -------------------------------------------------------------------------- */

  content: {
    padding: 18,
  },

  price: {
    fontSize: 26,

    fontWeight: "800",
  },

  title: {
    marginTop: 8,

    fontSize: 19,

    fontWeight: "700",

    lineHeight: 26,
  },

  description: {
    marginTop: 8,

    fontSize: 14,

    lineHeight: 22,
  },

  locationRow: {
    flexDirection: "row",

    alignItems: "center",

    marginTop: 12,
  },

  location: {
    flex: 1,

    marginLeft: 6,

    fontSize: 13,
  },

  /* -------------------------------------------------------------------------- */
  /* Property Type */
  /* -------------------------------------------------------------------------- */

  badgesRow: {
    flexDirection: "row",

    marginTop: 16,

    flexWrap: "wrap",
  },

  typeBadge: {
    borderRadius: 18,

    paddingHorizontal: 12,

    paddingVertical: 6,

    marginRight: 10,

    marginBottom: 8,
  },

  typeBadgeText: {
    color: "#FFFFFF",

    fontWeight: "700",

    fontSize: 12,

    textTransform: "capitalize",
  },

  listingBadge: {
    borderWidth: 1.5,

    borderRadius: 18,

    paddingHorizontal: 12,

    paddingVertical: 6,

    marginBottom: 8,
  },

  listingBadgeText: {
    fontWeight: "700",

    fontSize: 12,

    textTransform: "capitalize",
  },

  /* -------------------------------------------------------------------------- */
  /* Stats */
  /* -------------------------------------------------------------------------- */

  statsRow: {
    marginTop: 18,

    flexDirection: "row",

    justifyContent: "space-between",

    borderTopWidth:
      StyleSheet.hairlineWidth,

    borderTopColor: "#E5E7EB",

    paddingTop: 18,
  },

  statItem: {
    alignItems: "center",

    flex: 1,
  },

  statText: {
    marginTop: 6,

    fontSize: 12,

    fontWeight: "600",
  },
});

export default memo(
  FeaturedPropertyCard
);