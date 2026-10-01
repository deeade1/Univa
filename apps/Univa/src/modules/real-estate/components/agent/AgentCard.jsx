import React, { memo } from "react";
import {
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Agent Card */
/* -------------------------------------------------------------------------- */

const AgentCard = memo(
  ({
    agent,
    onPress,
    onCall,
    onMessage,
    style,
  }) => {
    const { colors } = useTheme();

    if (!agent) return null;

    const {
      id,
      avatar,
      name,
      agency,
      rating,
      reviews,
      propertiesCount,
      verified,
      location,
    } = agent;

    return (
      <Pressable
        onPress={() => onPress?.(agent)}
        android_ripple={{ color: colors.border }}
        style={[
          styles.container,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
          style,
        ]}
      >
        {/* ---------------------------------------------------------------- */}
        {/* Avatar */}
        {/* ---------------------------------------------------------------- */}

        <View style={styles.avatarWrapper}>
          <Image
            source={{
              uri:
                avatar ||
                "https://via.placeholder.com/150x150.png?text=Agent",
            }}
            style={styles.avatar}
          />

          {verified && (
            <View
              style={[
                styles.verifiedBadge,
                { backgroundColor: colors.primary },
              ]}
            >
              <MaterialCommunityIcons
                name="check-decagram"
                size={14}
                color="#FFFFFF"
              />
            </View>
          )}
        </View>

        {/* ---------------------------------------------------------------- */}
        {/* Info */}
        {/* ---------------------------------------------------------------- */}

        <View style={styles.content}>
          <Text
            numberOfLines={1}
            style={[
              styles.name,
              { color: colors.text },
            ]}
          >
            {name}
          </Text>

          {!!agency && (
            <Text
              numberOfLines={1}
              style={[
                styles.agency,
                { color: colors.textSecondary },
              ]}
            >
              {agency}
            </Text>
          )}

          {!!location && (
            <View style={styles.row}>
              <MaterialCommunityIcons
                name="map-marker-outline"
                size={14}
                color={colors.textSecondary}
              />

              <Text
                numberOfLines={1}
                style={[
                  styles.location,
                  { color: colors.textSecondary },
                ]}
              >
                {location}
              </Text>
            </View>
          )}

          <View style={styles.statsRow}>
            <View style={styles.stat}>
              <MaterialCommunityIcons
                name="star"
                size={14}
                color="#F4B400"
              />

              <Text
                style={[
                  styles.statText,
                  { color: colors.text },
                ]}
              >
                {rating ?? "0.0"}
              </Text>
            </View>

            <View style={styles.stat}>
              <MaterialCommunityIcons
                name="home-city-outline"
                size={14}
                color={colors.primary}
              />

              <Text
                style={[
                  styles.statText,
                  { color: colors.text },
                ]}
              >
                {propertiesCount ?? 0}
              </Text>
            </View>

            <View style={styles.stat}>
              <MaterialCommunityIcons
                name="account-group-outline"
                size={14}
                color={colors.primary}
              />

              <Text
                style={[
                  styles.statText,
                  { color: colors.text },
                ]}
              >
                {reviews ?? 0}
              </Text>
            </View>
          </View>
        </View>

        {/* ---------------------------------------------------------------- */}
        {/* Actions */}
        {/* ---------------------------------------------------------------- */}

        <View style={styles.actions}>
          <Pressable
            hitSlop={8}
            onPress={() => onCall?.(agent)}
            style={[
              styles.iconButton,
              {
                backgroundColor: colors.background,
                borderColor: colors.border,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="phone-outline"
              size={20}
              color={colors.primary}
            />
          </Pressable>

          <Pressable
            hitSlop={8}
            onPress={() => onMessage?.(agent)}
            style={[
              styles.iconButton,
              {
                backgroundColor: colors.background,
                borderColor: colors.border,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="message-outline"
              size={20}
              color={colors.primary}
            />
          </Pressable>
        </View>
      </Pressable>
    );
  }
);

AgentCard.displayName = "AgentCard";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
    marginBottom: 14,
  },

  avatarWrapper: {
    position: "relative",
  },

  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
  },

  verifiedBadge: {
    position: "absolute",
    bottom: -2,
    right: -2,
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },

  content: {
    flex: 1,
    marginLeft: 16,
  },

  name: {
    fontSize: 17,
    fontWeight: "700",
  },

  agency: {
    marginTop: 3,
    fontSize: 14,
    fontWeight: "500",
  },

  row: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 6,
  },

  location: {
    marginLeft: 4,
    fontSize: 13,
  },

  statsRow: {
    flexDirection: "row",
    marginTop: 12,
  },

  stat: {
    flexDirection: "row",
    alignItems: "center",
    marginRight: 16,
  },

  statText: {
    marginLeft: 4,
    fontSize: 13,
    fontWeight: "600",
  },

  actions: {
    justifyContent: "space-between",
    marginLeft: 12,
    height: 72,
  },

  iconButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
});

export default AgentCard;