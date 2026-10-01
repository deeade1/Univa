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

import { useRouter } from "expo-router";

import { useTheme } from "@/theme";


import { useAuth } from "@/context/AuthContext";

import { useRealEstate } from "../../context/RealEstateProvider";

function Header() {
  const router = useRouter();

  const { colors } = useTheme();

  const {
    user,
  } = useAuth();

  const {
    unreadNotifications,
  } = useRealEstate();
    const greeting =
    useMemo(() => {
      const hour =
        new Date().getHours();

      if (hour < 12) {
        return "Good Morning";
      }

      if (hour < 17) {
        return "Good Afternoon";
      }

      return "Good Evening";
    }, []);

  const fullName =
    [
      user?.firstName,
      user?.lastName,
    ]
      .filter(Boolean)
      .join(" ");

  const initials =
    fullName
      ?.split(" ")
      .map((name) => name[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "U";
        const openNotifications =
    () => {
      router.push(
        "/real-estate/messages"
      );
    };

  const openProfile =
    () => {
      router.push(
        "/profile"
      );
    };
      return (
    <View
      style={[
        styles.container,
        {
          backgroundColor:
            colors.background,
        },
      ]}
    >
      <View style={styles.left}>
        <Text
          style={[
            styles.greeting,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          {greeting}
        </Text>

        <Text
          style={[
            styles.name,
            {
              color:
                colors.text,
            },
          ]}
        >
          {fullName ||
            "Welcome"}
        </Text>

        <View
          style={styles.locationRow}
        >
          <Ionicons
            name="location"
            size={14}
            color={
              colors.primary
            }
          />

          <Text
            style={[
              styles.location,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Lagos, Nigeria
          </Text>
        </View>
      </View>

      <View
        style={styles.right}
      >
        <Pressable
          onPress={
            openNotifications
          }
          style={
            styles.notificationButton
          }
        >
          <Ionicons
            name="notifications-outline"
            size={24}
            color={
              colors.text
            }
          />

          {unreadNotifications >
            0 && (
            <View
              style={[
                styles.badge,
                {
                  backgroundColor:
                    colors.error,
                },
              ]}
            >
              <Text
                style={
                  styles.badgeText
                }
              >
                {unreadNotifications >
                99
                  ? "99+"
                  : unreadNotifications}
              </Text>
            </View>
          )}
        </Pressable>

        <Pressable
          onPress={
            openProfile
          }
          style={
            styles.avatarContainer
          }
        >
          {user?.profilePhoto ? (
            <Image
              source={{
                uri: user.profilePhoto,
              }}
              style={
                styles.avatar
              }
            />
          ) : (
            <View
              style={[
                styles.avatarFallback,
                {
                  backgroundColor:
                    colors.primary,
                },
              ]}
            >
              <Text
                style={
                  styles.avatarText
                }
              >
                {initials}
              </Text>
            </View>
          )}
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  left: {
    flex: 1,
  },

  greeting: {
    fontSize: 14,
    fontWeight: "500",
  },

  name: {
    fontSize: 24,
    fontWeight: "700",
    marginTop: 4,
  },

  locationRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 8,
  },

  location: {
    marginLeft: 4,
    fontSize: 13,
  },

  right: {
    flexDirection: "row",
    alignItems: "center",
  },

  notificationButton: {
    marginRight: 16,
    position: "relative",
  },

  badge: {
    position: "absolute",
    top: -4,
    right: -4,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 4,
  },

  badgeText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontWeight: "700",
  },

  avatarContainer: {
    overflow: "hidden",
    borderRadius: 22,
  },

  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
  },

  avatarFallback: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },

  avatarText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
});

export default memo(Header);