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
/* Recent Property Card */
/* -------------------------------------------------------------------------- */

function RecentPropertyCard({
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
    title = "Untitled Property",

    address = "Unknown Location",

    city,

    state,

    price = 0,

    currency = "NGN",

    bedrooms = 0,

    bathrooms = 0,

    area = 0,

    featuredImage,

    images = [],

    status = "AVAILABLE",

    listedAt,

    isFavorite = false,
  } = property ?? {};

  const image =
    featuredImage ??
    images?.[0]?.url ??
    "https://via.placeholder.com/600x400";

  /* ---------------------------------------------------------------------- */
  /* Money */
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
    }, [scale]);

  const pressOut =
    useCallback(() => {
      Animated.spring(scale, {
        toValue: 1,
        friction: 8,
        useNativeDriver: true,
      }).start();
    }, [scale]);

  /* ---------------------------------------------------------------------- */
  /* Status */
  /* ---------------------------------------------------------------------- */

  const statusColor =
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
              styles.statusBadge,
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
              color={
                isFavorite
                  ? "#EF4444"
                  : "#FFFFFF"
              }
              size={22}
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
        {/* Property Info */}
        {/* -------------------------------------------------- */}

        <View
          style={styles.infoRow}
        >
          <View
            style={styles.info}
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
                styles.infoText,
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
            style={styles.info}
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
                styles.infoText,
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
            style={styles.info}
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
                styles.infoText,
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
          <View
            style={styles.footerRow}
          >
            <Ionicons
              name="time-outline"
              size={14}
              color={
                colors.textSecondary
              }
            />

            <Text
              style={[
                styles.footerText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {listedAt
                ? new Date(
                    listedAt
                  ).toLocaleDateString()
                : "Recently Added"}
            </Text>
          </View>

          <Ionicons
            name="chevron-forward"
            size={18}
            color={colors.primary}
          />
        </View>
      </Pressable>
    </Animated.View>
  );
}

const styles =
  StyleSheet.create({
    card: {
      width: 290,

      borderRadius: 20,

      overflow: "hidden",

      elevation: 3,

      shadowColor: "#000",

      shadowOpacity: 0.08,

      shadowRadius: 8,

      shadowOffset: {
        width: 0,
        height: 3,
      },
    },

    imageWrapper: {
      position: "relative",
    },

    image: {
      width: "100%",

      height: 180,
    },

    favoriteButton: {
      position: "absolute",

      top: 12,

      right: 12,

      width: 40,

      height: 40,

      borderRadius: 20,

      backgroundColor:
        "rgba(0,0,0,0.35)",

      justifyContent:
        "center",

      alignItems: "center",
    },

    statusBadge: {
      position: "absolute",

      left: 12,

      top: 12,

      borderRadius: 8,

      paddingHorizontal: 10,

      paddingVertical: 4,
    },

    statusText: {
      color: "#FFFFFF",

      fontSize: 11,

      fontWeight: "700",
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
      marginLeft: 6,

      flex: 1,

      fontSize: 13,
    },

    infoRow: {
      marginTop: 18,

      marginHorizontal: 16,

      flexDirection: "row",

      justifyContent:
        "space-between",
    },

    info: {
      flexDirection: "row",

      alignItems: "center",
    },

    infoText: {
      marginLeft: 6,

      fontWeight: "600",
    },

    footer: {
      marginTop: 18,

      marginBottom: 16,

      marginHorizontal: 16,

      flexDirection: "row",

      justifyContent:
        "space-between",

      alignItems: "center",
    },

    footerRow: {
      flexDirection: "row",

      alignItems: "center",
    },

    footerText: {
      marginLeft: 6,

      fontSize: 12,
    },
  });

export default memo(
  RecentPropertyCard
);
