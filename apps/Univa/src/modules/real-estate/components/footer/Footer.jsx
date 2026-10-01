import React, { memo } from "react";
import {
  Linking,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Footer Links */
/* -------------------------------------------------------------------------- */

const LINKS = [
  {
    id: "browse",
    title: "Browse Properties",
    icon: "home-city-outline",
  },
  {
    id: "map",
    title: "Explore Map",
    icon: "map-search-outline",
  },
  {
    id: "agent",
    title: "Become an Agent",
    icon: "account-tie-outline",
  },
  {
    id: "saved",
    title: "Saved Properties",
    icon: "heart-outline",
  },
  {
    id: "support",
    title: "Support",
    icon: "lifebuoy",
  },
];

/* -------------------------------------------------------------------------- */
/* Footer */
/* -------------------------------------------------------------------------- */

const Footer = memo(
  ({
    onBrowseProperties,
    onExploreMap,
    onBecomeAgent,
    onSavedProperties,
    onSupport,
    onPrivacyPolicy,
    onTerms,
    version = "v1.0.0",
  }) => {
    const { colors } = useTheme();

    const handlePress = (id) => {
      switch (id) {
        case "browse":
          onBrowseProperties?.();
          break;

        case "map":
          onExploreMap?.();
          break;

        case "agent":
          onBecomeAgent?.();
          break;

        case "saved":
          onSavedProperties?.();
          break;

        case "support":
          onSupport?.();
          break;

        default:
          break;
      }
    };

    return (
      <View
        style={[
          styles.container,
          {
            borderTopColor: colors.border,
          },
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Quick Links */}
        {/* -------------------------------------------------------------- */}

        <Text
          style={[
            styles.heading,
            {
              color: colors.text,
            },
          ]}
        >
          Quick Links
        </Text>

        <View style={styles.links}>
          {LINKS.map((item) => (
            <Pressable
              key={item.id}
              onPress={() => handlePress(item.id)}
              android_ripple={{
                color: colors.border,
              }}
              style={styles.link}
            >
              <MaterialCommunityIcons
                name={item.icon}
                size={20}
                color={colors.primary}
              />

              <Text
                style={[
                  styles.linkText,
                  {
                    color: colors.text,
                  },
                ]}
              >
                {item.title}
              </Text>

              <MaterialCommunityIcons
                name="chevron-right"
                size={20}
                color={colors.textSecondary}
              />
            </Pressable>
          ))}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Policies */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.policyRow}>
          <Pressable onPress={onPrivacyPolicy}>
            <Text
              style={[
                styles.policyText,
                {
                  color: colors.primary,
                },
              ]}
            >
              Privacy Policy
            </Text>
          </Pressable>

          <Text
            style={{
              color: colors.textSecondary,
            }}
          >
            •
          </Text>

          <Pressable onPress={onTerms}>
            <Text
              style={[
                styles.policyText,
                {
                  color: colors.primary,
                },
              ]}
            >
              Terms of Service
            </Text>
          </Pressable>
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Contact */}
        {/* -------------------------------------------------------------- */}

        <Pressable
          style={styles.emailRow}
          onPress={() =>
            Linking.openURL("mailto:support@univa.app")
          }
        >
          <MaterialCommunityIcons
            name="email-outline"
            size={18}
            color={colors.textSecondary}
          />

          <Text
            style={[
              styles.email,
              {
                color: colors.textSecondary,
              },
            ]}
          >
            support@univa.app
          </Text>
        </Pressable>

        {/* -------------------------------------------------------------- */}
        {/* Copyright */}
        {/* -------------------------------------------------------------- */}

        <Text
          style={[
            styles.version,
            {
              color: colors.textSecondary,
            },
          ]}
        >
          Univa Real Estate {version}
        </Text>

        <Text
          style={[
            styles.copyright,
            {
              color: colors.textSecondary,
            },
          ]}
        >
          © {new Date().getFullYear()} Univa. All rights reserved.
        </Text>
      </View>
    );
  }
);

Footer.displayName = "Footer";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    marginTop: 36,
    paddingTop: 28,
    paddingHorizontal: 20,
    paddingBottom: 40,
    borderTopWidth: 1,
  },

  heading: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 20,
  },

  links: {
    marginBottom: 24,
  },

  link: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 14,
  },

  linkText: {
    flex: 1,
    marginLeft: 14,
    fontSize: 15,
    fontWeight: "600",
  },

  policyRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 12,
    marginBottom: 18,
  },

  policyText: {
    fontSize: 14,
    fontWeight: "600",
  },

  emailRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 18,
  },

  email: {
    marginLeft: 8,
    fontSize: 14,
  },

  version: {
    textAlign: "center",
    fontSize: 13,
    fontWeight: "600",
  },

  copyright: {
    marginTop: 6,
    textAlign: "center",
    fontSize: 12,
  },
});

export default Footer;