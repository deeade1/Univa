import React, {
  memo,
  useCallback,
  useMemo,
  useRef,
} from "react";

import {
  Animated,
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
/* Recommended Property Card */
/* -------------------------------------------------------------------------- */

function RecommendedPropertyCard({
  property,
  onPress,
  onFavoritePress,
}) {
  const { colors } = useTheme();

  const scale = useRef(
    new Animated.Value(1)
  ).current;

  /* ---------------------------------------------------------------------- */
  /* Property */
  /* ---------------------------------------------------------------------- */

  const {
    title = "Luxury Apartment",

    address = "",

    city = "",

    state = "",

    featuredImage,

    images = [],

    currency = "NGN",

    price = 0,

    bedrooms = 0,

    bathrooms = 0,

    area = 0,

    status = "AVAILABLE",

    rating = 4.9,

    reviewCount = 0,

    isFavorite = false,

    recommendationScore = 96,

    recommendationReason =
      "Matches your preferred budget and location.",
  } = property ?? {};

  const image =
    featuredImage ??
    images?.[0]?.url ??
    "https://via.placeholder.com/900x600";

  /* ---------------------------------------------------------------------- */
  /* Price */
  /* ---------------------------------------------------------------------- */

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

  /* ---------------------------------------------------------------------- */
  /* Animation */
  /* ---------------------------------------------------------------------- */

  const pressIn =
    useCallback(() => {
      Animated.spring(scale, {
        toValue: 0.97,

        friction: 7,

        useNativeDriver: true,
      }).start();
    }, []);

  const pressOut =
    useCallback(() => {
      Animated.spring(scale, {
        toValue: 1,

        friction: 7,

        useNativeDriver: true,
      }).start();
    }, []);

  const statusColor =
    status === "SOLD"
      ? "#EF4444"
      : status === "RENTED"
      ? "#F59E0B"
      : "#22C55E";

  return (
    <Animated.View
      style={{
        transform: [
          {
            scale,
          },
        ],
      }}
    >
      <Pressable
        onPress={() =>
          onPress?.(property)
        }
        onPressIn={pressIn}
        onPressOut={pressOut}
        style={[
          styles.card,
          {
            backgroundColor:
              colors.card,
          },
        ]}
      >
        {/* -------------------------------------------------- */}
        {/* Hero Image */}
        {/* -------------------------------------------------- */}

        <View
          style={styles.imageWrapper}
        >
          <Image
            source={{
              uri: image,
            }}
            style={styles.image}
          />

          <LinearGradient
            colors={[
              "transparent",
              "rgba(0,0,0,0.75)",
            ]}
            style={
              styles.overlay
            }
          />

          {/* AI Badge */}

          <View
            style={
              styles.aiBadge
            }
          >
            <Ionicons
              name="sparkles"
              size={14}
              color="#FFFFFF"
            />

            <Text
              style={
                styles.aiBadgeText
              }
            >
              AI Recommended
            </Text>
          </View>

          {/* Match */}

          <View
            style={
              styles.matchBadge
            }
          >
            <Text
              style={
                styles.matchText
              }
            >
              {recommendationScore}% Match
            </Text>
          </View>

          {/* Favorite */}

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

          {/* Status */}

          <View
            style={[
              styles.status,
              {
                backgroundColor:
                  statusColor,
              },
            ]}
          >
            <Text
              style={
                styles.statusText
              }
            >
              {status}
            </Text>
          </View>
        </View>
                {/* -------------------------------------------------- */}
        {/* Property Info */}
        {/* -------------------------------------------------- */}

        <View style={styles.content}>
          <View style={styles.priceRow}>
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

            <View
              style={styles.ratingRow}
            >
              <Ionicons
                name="star"
                size={16}
                color="#FACC15"
              />

              <Text
                style={[
                  styles.rating,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                {rating}
              </Text>

              <Text
                style={[
                  styles.reviewCount,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                ({reviewCount})
              </Text>
            </View>
          </View>

          {/* -------------------------------------------------- */}
          {/* Property Title */}
          {/* -------------------------------------------------- */}

          <Text
            numberOfLines={2}
            style={[
              styles.title,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {title}
          </Text>

          {/* -------------------------------------------------- */}
          {/* Address */}
          {/* -------------------------------------------------- */}

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
              numberOfLines={2}
              style={[
                styles.location,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {address}
              {city
                ? `, ${city}`
                : ""}
              {state
                ? `, ${state}`
                : ""}
            </Text>
          </View>

          {/* -------------------------------------------------- */}
          {/* AI Recommendation */}
          {/* -------------------------------------------------- */}

          <View
            style={[
              styles.recommendationBox,
              {
                backgroundColor:
                  colors.primary +
                  "10",
              },
            ]}
          >
            <View
              style={
                styles.recommendationHeader
              }
            >
              <Ionicons
                name="sparkles"
                size={15}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.recommendationTitle,
                  {
                    color:
                      colors.primary,
                  },
                ]}
              >
                Why we recommend this
              </Text>
            </View>

            <Text
              style={[
                styles.recommendationText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {
                recommendationReason
              }
            </Text>
          </View>

          {/* -------------------------------------------------- */}
          {/* Property Features */}
          {/* -------------------------------------------------- */}

          <View
            style={styles.featuresRow}
          >
            <View
              style={styles.feature}
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
                  styles.featureText,
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
              style={styles.feature}
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
                  styles.featureText,
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
              style={styles.feature}
            >
              <Ionicons
                name="resize-outline"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.featureText,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                {area} sqm
              </Text>
            </View>
          </View>
                    {/* -------------------------------------------------- */}
          {/* Footer */}
          {/* -------------------------------------------------- */}

          <View style={styles.footer}>
            <Text
              style={[
                styles.footerText,
                {
                  color: colors.primary,
                },
              ]}
            >
              View Details
            </Text>

            <Ionicons
              name="chevron-forward"
              size={18}
              color={colors.primary}
            />
          </View>
        </View>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: 330,

    borderRadius: 24,

    overflow: "hidden",

    elevation: 5,

    shadowColor: "#000",

    shadowOpacity: 0.12,

    shadowRadius: 12,

    shadowOffset: {
      width: 0,
      height: 5,
    },
  },

  /* ---------------------------------------------------------------------- */
  /* Image */
  /* ---------------------------------------------------------------------- */

  imageWrapper: {
    position: "relative",
  },

  image: {
    width: "100%",

    height: 220,
  },

  overlay: {
    ...StyleSheet.absoluteFillObject,
  },

  aiBadge: {
    position: "absolute",

    top: 14,

    left: 14,

    flexDirection: "row",

    alignItems: "center",

    paddingHorizontal: 12,

    paddingVertical: 6,

    borderRadius: 20,

    backgroundColor:
      "rgba(37,99,235,0.95)",
  },

  aiBadgeText: {
    marginLeft: 6,

    color: "#FFFFFF",

    fontSize: 12,

    fontWeight: "700",
  },

  matchBadge: {
    position: "absolute",

    bottom: 14,

    left: 14,

    paddingHorizontal: 12,

    paddingVertical: 6,

    borderRadius: 18,

    backgroundColor:
      "rgba(34,197,94,0.95)",
  },

  matchText: {
    color: "#FFFFFF",

    fontWeight: "700",

    fontSize: 12,
  },

  favoriteButton: {
    position: "absolute",

    top: 14,

    right: 14,

    width: 42,

    height: 42,

    borderRadius: 21,

    alignItems: "center",

    justifyContent: "center",

    backgroundColor:
      "rgba(0,0,0,0.35)",
  },

  status: {
    position: "absolute",

    bottom: 14,

    right: 14,

    borderRadius: 16,

    paddingHorizontal: 12,

    paddingVertical: 5,
  },

  statusText: {
    color: "#FFFFFF",

    fontSize: 11,

    fontWeight: "700",
  },

  /* ---------------------------------------------------------------------- */
  /* Content */
  /* ---------------------------------------------------------------------- */

  content: {
    padding: 18,
  },

  priceRow: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  price: {
    fontSize: 24,

    fontWeight: "700",
  },

  ratingRow: {
    flexDirection: "row",

    alignItems: "center",
  },

  rating: {
    marginLeft: 4,

    fontWeight: "700",
  },

  reviewCount: {
    marginLeft: 4,

    fontSize: 12,
  },

  title: {
    marginTop: 14,

    fontSize: 18,

    fontWeight: "700",

    lineHeight: 26,
  },

  locationRow: {
    marginTop: 10,

    flexDirection: "row",

    alignItems: "flex-start",
  },

  location: {
    flex: 1,

    marginLeft: 6,

    fontSize: 14,

    lineHeight: 20,
  },

  recommendationBox: {
    marginTop: 18,

    borderRadius: 14,

    padding: 14,
  },

  recommendationHeader: {
    flexDirection: "row",

    alignItems: "center",
  },

  recommendationTitle: {
    marginLeft: 6,

    fontWeight: "700",

    fontSize: 13,
  },

  recommendationText: {
    marginTop: 8,

    fontSize: 13,

    lineHeight: 20,
  },

  featuresRow: {
    marginTop: 20,

    flexDirection: "row",

    justifyContent: "space-between",
  },

  feature: {
    flexDirection: "row",

    alignItems: "center",
  },

  featureText: {
    marginLeft: 6,

    fontSize: 13,

    fontWeight: "600",
  },

  footer: {
    marginTop: 22,

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    borderTopWidth:
      StyleSheet.hairlineWidth,

    borderTopColor:
      "rgba(0,0,0,0.08)",

    paddingTop: 18,
  },

  footerText: {
    fontSize: 15,

    fontWeight: "700",
  },
});

export default memo(
  RecommendedPropertyCard
);