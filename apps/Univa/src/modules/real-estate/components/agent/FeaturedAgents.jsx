import React, {
  memo,
  useMemo,
} from "react";

import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

import AgentCard from "./AgentCard";
import FeaturedAgentsSkeleton from "./FeaturedAgentsSkeleton";
import FeaturedAgentsEmpty from "./FeaturedAgentsEmpty";

/* -------------------------------------------------------------------------- */
/* Featured Agents */
/* -------------------------------------------------------------------------- */

const FeaturedAgents = memo(
  ({
    agents = [],
    loading = false,
    error = null,
    onRetry,
    onPressAgent,
    onCallAgent,
    onMessageAgent,
    onSeeAll,
    title = "Featured Agents",
    subtitle = "Top-rated professionals near you",
    horizontal = false,
  }) => {
    const { colors } = useTheme();

    const list = useMemo(() => agents ?? [], [agents]);

    /* ---------------------------------------------------------------------- */
    /* Loading */
    /* ---------------------------------------------------------------------- */

    if (loading) {
      return <FeaturedAgentsSkeleton />;
    }

    /* ---------------------------------------------------------------------- */
    /* Error / Empty */
    /* ---------------------------------------------------------------------- */

    if (error || list.length === 0) {
      return (
        <FeaturedAgentsEmpty
          onRetry={onRetry}
        />
      );
    }

    /* ---------------------------------------------------------------------- */
    /* Render */
    /* ---------------------------------------------------------------------- */

    return (
      <View style={styles.container}>
        {/* -------------------------------------------------------------- */}
        {/* Header */}
        {/* -------------------------------------------------------------- */}

        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <View
              style={[
                styles.iconContainer,
                {
                  backgroundColor: colors.primary + "15",
                },
              ]}
            >
              <MaterialCommunityIcons
                name="account-tie-outline"
                size={20}
                color={colors.primary}
              />
            </View>

            <View>
              <Text
                style={[
                  styles.title,
                  {
                    color: colors.text,
                  },
                ]}
              >
                {title}
              </Text>

              {!!subtitle && (
                <Text
                  style={[
                    styles.subtitle,
                    {
                      color: colors.textSecondary,
                    },
                  ]}
                >
                  {subtitle}
                </Text>
              )}
            </View>
          </View>

          {onSeeAll && (
            <TouchableOpacity
              activeOpacity={0.8}
              onPress={onSeeAll}
            >
              <Text
                style={[
                  styles.seeAll,
                  {
                    color: colors.primary,
                  },
                ]}
              >
                See All
              </Text>
            </TouchableOpacity>
          )}
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Agent List */}
        {/* -------------------------------------------------------------- */}

        {horizontal ? (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.horizontalList}
          >
            {list.map((agent) => (
              <View
                key={agent.id}
                style={styles.horizontalCard}
              >
                <AgentCard
                  agent={agent}
                  onPress={onPressAgent}
                  onCall={onCallAgent}
                  onMessage={onMessageAgent}
                />
              </View>
            ))}
          </ScrollView>
        ) : (
          <View style={styles.verticalList}>
            {list.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onPress={onPressAgent}
                onCall={onCallAgent}
                onMessage={onMessageAgent}
              />
            ))}
          </View>
        )}
      </View>
    );
  }
);

FeaturedAgents.displayName = "FeaturedAgents";

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    marginTop: 28,
  },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 18,
    paddingHorizontal: 20,
  },

  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
  },

  iconContainer: {
    width: 42,
    height: 42,
    borderRadius: 21,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
  },

  title: {
    fontSize: 20,
    fontWeight: "700",
  },

  subtitle: {
    marginTop: 2,
    fontSize: 13,
  },

  seeAll: {
    fontSize: 15,
    fontWeight: "700",
  },

  verticalList: {
    paddingHorizontal: 20,
  },

  horizontalList: {
    paddingHorizontal: 20,
    paddingRight: 8,
  },

  horizontalCard: {
    width: 340,
    marginRight: 16,
  },
});

export default FeaturedAgents;