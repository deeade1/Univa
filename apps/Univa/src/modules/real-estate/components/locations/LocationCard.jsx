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
/* Location Card */
/* -------------------------------------------------------------------------- */

function LocationCard({
  location,
  onPress,
}) {
  const { colors } = useTheme();

  const scale = useRef(
    new Animated.Value(1)
  ).current;

  /* ---------------------------------------------------------------------- */
  /* Data */
  /* ---------------------------------------------------------------------- */

  const {
    name = "Lekki",

    state = "Lagos",

    country = "Nigeria",

    image,

    propertyCount = 0,

    averagePrice = 0,

    currency = "NGN",

    rating = 4.8,

    trending = true,
  } = location ?? {};

  /* ---------------------------------------------------------------------- */
  /* Format Price */
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
        ).format(
          averagePrice
        );
      } catch {
        return `₦${Number(
          averagePrice
        ).toLocaleString()}`;
      }
    }, [
      averagePrice,
      currency,
    ]);

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
            location
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
        {/* Hero Image */}
        {/* -------------------------------------------------- */}

        <View
          style={styles.imageWrapper}
        >
          <Image
            source={{
              uri:
                image ??
                "https://via.placeholder.com/800x600",
            }}
            style={styles.image}
          />

          <LinearGradient
            colors={[
              "transparent",
              "rgba(0,0,0,0.80)",
            ]}
            style={
              styles.overlay
            }
          />

          {trending && (
            <View
              style={
                styles.trendingBadge
              }
            >
              <Ionicons
                name="flame"
                size={14}
                color="#FFFFFF"
              />

              <Text
                style={
                  styles.trendingText
                }
              >
                Trending
              </Text>
            </View>
          )}

          <View
            style={
              styles.ratingBadge
            }
          >
            <Ionicons
              name="star"
              size={14}
              color="#FACC15"
            />

            <Text
              style={
                styles.ratingText
              }
            >
              {rating}
            </Text>
          </View>
        </View>

        {/* -------------------------------------------------- */}
        {/* Content */}
        {/* -------------------------------------------------- */}

        <View
          style={styles.content}
        >
          <Text
            numberOfLines={1}
            style={[
              styles.title,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {name}
          </Text>

          <View
            style={
              styles.locationRow
            }
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
              {state}, {country}
            </Text>
          </View>

          <View
            style={
              styles.infoRow
            }
          >
            <View
              style={
                styles.infoItem
              }
            >
              <Ionicons
                name="business-outline"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.infoValue,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                {propertyCount}
              </Text>

              <Text
                style={[
                  styles.infoLabel,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Properties
              </Text>
            </View>

            <View
              style={
                styles.infoItem
              }
            >
              <Ionicons
                name="cash-outline"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                numberOfLines={1}
                style={[
                  styles.infoValue,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                {formattedPrice}
              </Text>

              <Text
                style={[
                  styles.infoLabel,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Avg. Price
              </Text>
            </View>
          </View>

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
              Explore Area
            </Text>

            <Ionicons
              name="chevron-forward"
              size={18}
              color={
                colors.primary
              }
            />
          </View>
        </View>
      </Pressable>
    </Animated.View>
  );
}

const styles =
  StyleSheet.create({
    card: {
      width: 280,

      borderRadius: 22,

      overflow: "hidden",

      elevation: 5,

      shadowColor: "#000",

      shadowOpacity: 0.10,

      shadowRadius: 12,

      shadowOffset: {
        width: 0,
        height: 5,
      },
    },

    imageWrapper: {
      position: "relative",
    },

    image: {
      width: "100%",

      height: 180,
    },

    overlay: {
      ...StyleSheet.absoluteFillObject,
    },

    trendingBadge: {
      position: "absolute",

      top: 14,

      left: 14,

      flexDirection: "row",

      alignItems: "center",

      backgroundColor:
        "#EF4444",

      borderRadius: 18,

      paddingHorizontal: 10,

      paddingVertical: 5,
    },

    trendingText: {
      color: "#FFFFFF",

      marginLeft: 5,

      fontWeight: "700",

      fontSize: 12,
    },

    ratingBadge: {
      position: "absolute",

      bottom: 14,

      right: 14,

      flexDirection: "row",

      alignItems: "center",

      backgroundColor:
        "rgba(0,0,0,0.55)",

      borderRadius: 16,

      paddingHorizontal: 10,

      paddingVertical: 5,
    },

    ratingText: {
      color: "#FFFFFF",

      marginLeft: 4,

      fontWeight: "700",

      fontSize: 12,
    },

    content: {
      padding: 18,
    },

    title: {
      fontSize: 20,

      fontWeight: "700",
    },

    locationRow: {
      marginTop: 8,

      flexDirection: "row",

      alignItems: "center",
    },

    location: {
      marginLeft: 6,

      flex: 1,

      fontSize: 14,
    },

    infoRow: {
      marginTop: 22,

      flexDirection: "row",

      justifyContent:
        "space-between",
    },

    infoItem: {
      flex: 1,

      alignItems: "center",
    },

    infoValue: {
      marginTop: 8,

      fontSize: 16,

      fontWeight: "700",
    },

    infoLabel: {
      marginTop: 4,

      fontSize: 12,
    },

    footer: {
      marginTop: 24,

      paddingTop: 18,

      borderTopWidth:
        StyleSheet.hairlineWidth,

      borderTopColor:
        "rgba(0,0,0,0.08)",

      flexDirection: "row",

      justifyContent:
        "space-between",

      alignItems: "center",
    },

    footerText: {
      fontSize: 15,

      fontWeight: "700",
    },
  });

export default memo(
  LocationCard
);