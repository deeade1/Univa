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

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Nearby Property Card */
/* -------------------------------------------------------------------------- */

function NearbyPropertyCard({
  property,
  onPress,
  onFavoritePress,
}) {
  const { colors } = useTheme();

  const scale =
    useRef(
      new Animated.Value(1)
    ).current;

  /* ---------------------------------------------------------------------- */
  /* Property */
  /* ---------------------------------------------------------------------- */

  const {
    id,

    slug,

    title = "Untitled Property",

    address = "Unknown Address",

    city,

    state,

    featuredImage,

    images = [],

    currency = "NGN",

    price = 0,

    bedrooms = 0,

    bathrooms = 0,

    area = 0,

    status = "AVAILABLE",

    distance = 0,

    estimatedTravelTime = "5 min",

    rating = 4.8,

    isFavorite = false,
  } = property ?? {};

  const image =
    featuredImage ??
    images?.[0]?.url ??
    "https://via.placeholder.com/800x600";

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
        friction: 8,
        useNativeDriver: true,
      }).start();
    }, []);

  const pressOut =
    useCallback(() => {
      Animated.spring(scale, {
        toValue: 1,
        friction: 8,
        useNativeDriver: true,
      }).start();
    }, []);

  const badgeColor =
    status === "SOLD"
      ? "#EF4444"
      : status === "RENTED"
      ? "#F59E0B"
      : "#22C55E";

  /* ---------------------------------------------------------------------- */
  /* UI */
  /* ---------------------------------------------------------------------- */

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
          onPress?.(
            property
          )
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
        {/* Image */}
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

          <View
            style={[
              styles.badge,
              {
                backgroundColor:
                  badgeColor,
              },
            ]}
          >
            <Text
              style={styles.badgeText}
            >
              {status}
            </Text>
          </View>

          <Pressable
            style={
              styles.favoriteButton
            }
            onPress={() =>
              onFavoritePress?.(
                property
              )
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

        {/* -------------------------------------------------- */}
        {/* Price */}
        {/* -------------------------------------------------- */}

        <Text
          style={[
            styles.price,
            {
              color:
                colors.primary,
            },
          ]}
        >
          {formattedPrice}
        </Text>

        {/* -------------------------------------------------- */}
        {/* Title */}
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
        {/* Location */}
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
            numberOfLines={1}
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
        {/* Nearby Info */}
        {/* -------------------------------------------------- */}

        <View
          style={styles.nearbyRow}
        >
          <View
            style={
              styles.nearbyChip
            }
          >
            <Ionicons
              name="walk-outline"
              size={15}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.nearbyText,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {distance} km
            </Text>
          </View>

          <View
            style={
              styles.nearbyChip
            }
          >
            <Ionicons
              name="car-outline"
              size={15}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.nearbyText,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {estimatedTravelTime}
            </Text>
          </View>

          <View
            style={
              styles.nearbyChip
            }
          >
            <Ionicons
              name="star"
              size={15}
              color="#FACC15"
            />

            <Text
              style={[
                styles.nearbyText,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {rating}
            </Text>
          </View>
        </View>

        {/* -------------------------------------------------- */}
        {/* Features */}
        {/* -------------------------------------------------- */}

        <View
          style={styles.features}
        >
          <View
            style={styles.feature}
          >
            <Ionicons
              name="bed-outline"
              size={16}
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
              {bedrooms}
            </Text>
          </View>

          <View
            style={styles.feature}
          >
            <Ionicons
              name="water-outline"
              size={16}
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
              {bathrooms}
            </Text>
          </View>

          <View
            style={styles.feature}
          >
            <Ionicons
              name="resize-outline"
              size={16}
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

        <View
          style={styles.footer}
        >
          <Text
            style={[
              styles.footerText,
              {
                color:
                  colors.primary,
              },
            ]}
          >
            View Details
          </Text>

          <Ionicons
            name="chevron-forward"
            size={18}
            color={
              colors.primary
            }
          />
        </View>
      </Pressable>
    </Animated.View>
  );
}

const styles =
  StyleSheet.create({
    card: {
      width: 300,

      borderRadius: 22,

      overflow: "hidden",

      elevation: 4,

      shadowColor: "#000",

      shadowOpacity: 0.08,

      shadowRadius: 10,

      shadowOffset: {
        width: 0,
        height: 4,
      },
    },

    imageWrapper: {
      position: "relative",
    },

    image: {
      width: "100%",

      height: 190,
    },

    badge: {
      position: "absolute",

      left: 12,

      top: 12,

      borderRadius: 8,

      paddingHorizontal: 10,

      paddingVertical: 5,
    },

    badgeText: {
      color: "#FFF",

      fontSize: 11,

      fontWeight: "700",
    },

    favoriteButton: {
      position: "absolute",

      right: 12,

      top: 12,

      width: 40,

      height: 40,

      borderRadius: 20,

      justifyContent:
        "center",

      alignItems: "center",

      backgroundColor:
        "rgba(0,0,0,0.35)",
    },

    price: {
      marginTop: 16,

      marginHorizontal: 16,

      fontSize: 22,

      fontWeight: "700",
    },

    title: {
      marginTop: 8,

      marginHorizontal: 16,

      fontSize: 17,

      fontWeight: "700",

      lineHeight: 24,
    },

    locationRow: {
      marginTop: 10,

      marginHorizontal: 16,

      flexDirection: "row",

      alignItems: "center",
    },

    location: {
      flex: 1,

      marginLeft: 6,

      fontSize: 13,
    },

    nearbyRow: {
      marginTop: 18,

      marginHorizontal: 16,

      flexDirection: "row",

      justifyContent:
        "space-between",
    },

    nearbyChip: {
      flexDirection: "row",

      alignItems: "center",
    },

    nearbyText: {
      marginLeft: 4,

      fontSize: 12,

      fontWeight: "600",
    },

    features: {
      marginTop: 18,

      marginHorizontal: 16,

      flexDirection: "row",

      justifyContent:
        "space-between",
    },

    feature: {
      flexDirection: "row",

      alignItems: "center",
    },

    featureText: {
      marginLeft: 6,

      fontWeight: "600",
    },

    footer: {
      marginTop: 22,

      marginHorizontal: 16,

      marginBottom: 18,

      flexDirection: "row",

      justifyContent:
        "space-between",

      alignItems: "center",
    },

    footerText: {
      fontWeight: "700",
    },
  });

export default memo(
  NearbyPropertyCard
);