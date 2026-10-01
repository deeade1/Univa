import React, {
  memo,
  useCallback,
  useRef,
} from "react";

import {
  Animated,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Category Card */
/* -------------------------------------------------------------------------- */

function CategoryCard({
  category,
  onPress,
}) {
  const { colors } = useTheme();

  const scale =
    useRef(
      new Animated.Value(1)
    ).current;

  /* -------------------------------------------------------------------------- */
  /* Data */
  /* -------------------------------------------------------------------------- */

  const {
    name = "Category",
    count = 0,
    icon = "home-outline",
    color = colors.primary,
  } = category ?? {};

  /* -------------------------------------------------------------------------- */
  /* Press Animation */
  /* -------------------------------------------------------------------------- */

  const handlePressIn =
    useCallback(() => {
      Animated.spring(scale, {
        toValue: 0.96,
        useNativeDriver: true,
        friction: 7,
      }).start();
    }, [scale]);

  const handlePressOut =
    useCallback(() => {
      Animated.spring(scale, {
        toValue: 1,
        useNativeDriver: true,
        friction: 7,
      }).start();
    }, [scale]);

  const handlePress =
    useCallback(() => {
      onPress?.(category);
    }, [
      category,
      onPress,
    ]);

  /* -------------------------------------------------------------------------- */
  /* UI */
  /* -------------------------------------------------------------------------- */

  return (
    <Animated.View
      style={[
        styles.wrapper,
        {
          transform: [
            {
              scale,
            },
          ],
        },
      ]}
    >
      <Pressable
        onPress={handlePress}
        onPressIn={
          handlePressIn
        }
        onPressOut={
          handlePressOut
        }
        style={[
          styles.card,
          {
            backgroundColor:
              colors.card,
          },
        ]}
      >
        {/* ------------------------------------------------------ */}
        {/* Icon */}
        {/* ------------------------------------------------------ */}

        <View
          style={[
            styles.iconContainer,
            {
              backgroundColor:
                `${color}18`,
            },
          ]}
        >
          <Ionicons
            name={icon}
            size={28}
            color={color}
          />
        </View>

        {/* ------------------------------------------------------ */}
        {/* Text */}
        {/* ------------------------------------------------------ */}

        <View
          style={styles.content}
        >
          <Text
            numberOfLines={1}
            style={[
              styles.name,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {name}
          </Text>

          <Text
            style={[
              styles.count,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            {count.toLocaleString()}{" "}
            {count === 1
              ? "Property"
              : "Properties"}
          </Text>
        </View>

        {/* ------------------------------------------------------ */}
        {/* Arrow */}
        {/* ------------------------------------------------------ */}

        <Ionicons
          name="chevron-forward"
          size={18}
          color={
            colors.textSecondary
          }
        />
      </Pressable>
    </Animated.View>
  );
}

const styles =
  StyleSheet.create({
    wrapper: {
      width: "48%",
    },

    card: {
      borderRadius: 18,

      padding: 18,

      minHeight: 120,

      justifyContent:
        "space-between",

      elevation: 2,

      shadowColor: "#000",

      shadowOpacity: 0.05,

      shadowRadius: 6,

      shadowOffset: {
        width: 0,
        height: 2,
      },
    },

    iconContainer: {
      width: 52,

      height: 52,

      borderRadius: 16,

      justifyContent:
        "center",

      alignItems: "center",
    },

    content: {
      marginTop: 18,

      flex: 1,
    },

    name: {
      fontSize: 16,

      fontWeight: "700",
    },

    count: {
      marginTop: 6,

      fontSize: 13,

      lineHeight: 18,
    },
  });

export default memo(
  CategoryCard
);