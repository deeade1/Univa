import React, {
  memo,
  useCallback,
  useMemo,
} from "react";

import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
  Text,
} from "react-native";

import { useLocalSearchParams } from "expo-router";
import { useRouter } from "expo-router";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Hooks */
/* -------------------------------------------------------------------------- */

import useFeaturedAgents from "../hooks/useFeaturedAgents";
import useSavedProperties from "../hooks/useSavedProperties";

/* -------------------------------------------------------------------------- */
/* Components */
/* -------------------------------------------------------------------------- */

import AgentCard from "../components/agents/AgentCard";
import PropertyCard from "../components/property/PropertyCard";

import DashboardSkeleton from "../components/skeleton/DashboardSkeleton";
import DashboardEmpty from "../components/empty/DashboardEmpty";

/* -------------------------------------------------------------------------- */
/* Agent Profile */
/* -------------------------------------------------------------------------- */

const AgentProfile = memo(() => {
  const router = useRouter();

  const { id } =
    useLocalSearchParams();

  const { colors } = useTheme();

  /* ---------------------------------------------------------------------- */
  /* Hooks */
  /* ---------------------------------------------------------------------- */

  const {
    agents,

    loading,

    refreshing,

    error,

    refresh,
  } = useFeaturedAgents();

  const {
    toggleSaved,

    isSaved,
  } = useSavedProperties();

  /* ---------------------------------------------------------------------- */
  /* Agent */
  /* ---------------------------------------------------------------------- */

  const agent = useMemo(
    () =>
      agents.find(
        (item) =>
          String(item.id) ===
          String(id)
      ),
    [agents, id]
  );

  const properties =
    useMemo(
      () =>
        agent?.properties ??
        [],
      [agent]
    );

  /* ---------------------------------------------------------------------- */
  /* Navigation */
  /* ---------------------------------------------------------------------- */

  const openProperty =
    useCallback(
      (property) => {
        router.push({
          pathname:
            "/real-estate/property/[id]",

          params: {
            id: property.id,
          },
        });
      },
      [router]
    );

  const goBack =
    useCallback(() => {
      router.back();
    }, [router]);

  /* ---------------------------------------------------------------------- */
  /* Refresh */
  /* ---------------------------------------------------------------------- */

  const handleRefresh =
    useCallback(async () => {
      await refresh();
    }, [refresh]);

  /* ---------------------------------------------------------------------- */
  /* Loading */
  /* ---------------------------------------------------------------------- */

  if (loading) {
    return (
      <DashboardSkeleton />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Agent Not Found */
  /* ---------------------------------------------------------------------- */

  if (!agent) {
    return (
      <DashboardEmpty
        title="Agent Not Found"
        description="The requested agent could not be found."
        onRetry={
          handleRefresh
        }
      />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Error */
  /* ---------------------------------------------------------------------- */

  if (error) {
    return (
      <DashboardEmpty
        title="Unable to load agent"
        description={
          error.message
        }
        onRetry={
          handleRefresh
        }
      />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Screen */
  /* ---------------------------------------------------------------------- */

  return (
    <ScrollView
      style={[
        styles.container,
        {
          backgroundColor:
            colors.background,
        },
      ]}
      contentContainerStyle={
        styles.content
      }
      showsVerticalScrollIndicator={
        false
      }
      refreshControl={
        <RefreshControl
          refreshing={
            refreshing
          }
          onRefresh={
            handleRefresh
          }
          tintColor={
            colors.primary
          }
          colors={[
            colors.primary,
          ]}
        />
      }
    >
          {/* ------------------------------------------------------------------ */}
      {/* Hero Section */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.heroContainer}>
        <Image
          source={{
            uri:
              agent.coverImage ||
              agent.banner ||
              "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=1200",
          }}
          style={styles.coverImage}
          resizeMode="cover"
        />

        <Pressable
          style={[
            styles.backButton,
            {
              backgroundColor:
                colors.card,
            },
          ]}
          onPress={goBack}
        >
          <MaterialCommunityIcons
            name="arrow-left"
            size={22}
            color={colors.text}
          />
        </Pressable>

        <View
          style={[
            styles.heroOverlay,
            {
              backgroundColor:
                "rgba(0,0,0,0.35)",
            },
          ]}
        />
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Profile Card */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.profileCard,
          {
            backgroundColor:
              colors.card,
            borderColor:
              colors.border,
          },
        ]}
      >
        <Image
          source={{
            uri:
              agent.avatar ||
              agent.image,
          }}
          style={styles.avatar}
        />

        {agent.verified && (
          <View
            style={
              styles.verifiedBadge
            }
          >
            <MaterialCommunityIcons
              name="check-decagram"
              size={20}
              color="#FFFFFF"
            />
          </View>
        )}

        <Text
          style={[
            styles.agentName,
            {
              color:
                colors.text,
            },
          ]}
        >
          {agent.name}
        </Text>

        <Text
          style={[
            styles.agentTitle,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          {agent.title ||
            "Licensed Real Estate Consultant"}
        </Text>

        <View
          style={
            styles.ratingRow
          }
        >
          <MaterialCommunityIcons
            name="star"
            size={18}
            color="#F59E0B"
          />

          <Text
            style={[
              styles.ratingText,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {agent.rating ??
              "5.0"}
          </Text>

          <Text
            style={[
              styles.reviewText,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            (
            {agent.reviewCount ??
              0}{" "}
            Reviews)
          </Text>
        </View>

        {agent.bio && (
          <Text
            style={[
              styles.bio,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            {agent.bio}
          </Text>
        )}
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Statistics */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.statsCard,
          {
            backgroundColor:
              colors.card,
            borderColor:
              colors.border,
          },
        ]}
      >
        <View
          style={
            styles.statItem
          }
        >
          <MaterialCommunityIcons
            name="home-city"
            size={26}
            color={
              colors.primary
            }
          />

          <Text
            style={[
              styles.statValue,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {properties.length}
          </Text>

          <Text
            style={[
              styles.statLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Listings
          </Text>
        </View>

        <View
          style={
            styles.statDivider
          }
        />

        <View
          style={
            styles.statItem
          }
        >
          <MaterialCommunityIcons
            name="briefcase"
            size={26}
            color="#22C55E"
          />

          <Text
            style={[
              styles.statValue,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {agent.experience ??
              0}
          </Text>

          <Text
            style={[
              styles.statLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Years
          </Text>
        </View>

        <View
          style={
            styles.statDivider
          }
        />

        <View
          style={
            styles.statItem
          }
        >
          <MaterialCommunityIcons
            name="account-group"
            size={26}
            color="#3B82F6"
          />

          <Text
            style={[
              styles.statValue,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {agent.clients ??
              "250+"}
          </Text>

          <Text
            style={[
              styles.statLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Clients
          </Text>
        </View>

        <View
          style={
            styles.statDivider
          }
        />

        <View
          style={
            styles.statItem
          }
        >
          <MaterialCommunityIcons
            name="trophy"
            size={26}
            color="#F59E0B"
          />

          <Text
            style={[
              styles.statValue,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {agent.awards ??
              0}
          </Text>

          <Text
            style={[
              styles.statLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Awards
          </Text>
        </View>
      </View>
            {/* ------------------------------------------------------------------ */}
      {/* Contact Actions */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <Text
          style={[
            styles.sectionTitle,
            {
              color: colors.text,
            },
          ]}
        >
          Contact Agent
        </Text>

        <View style={styles.actionGrid}>
          <Pressable
            style={[
              styles.actionButton,
              {
                backgroundColor: "#22C55E",
              },
            ]}
            onPress={() =>
              handleCall(agent.phone)
            }
          >
            <MaterialCommunityIcons
              name="phone"
              size={24}
              color="#FFFFFF"
            />

            <Text style={styles.actionText}>
              Call
            </Text>
          </Pressable>

          <Pressable
            style={[
              styles.actionButton,
              {
                backgroundColor: "#25D366",
              },
            ]}
            onPress={() =>
              handleWhatsApp(
                agent.phone
              )
            }
          >
            <MaterialCommunityIcons
              name="whatsapp"
              size={24}
              color="#FFFFFF"
            />

            <Text style={styles.actionText}>
              WhatsApp
            </Text>
          </Pressable>

          <Pressable
            style={[
              styles.actionButton,
              {
                backgroundColor: "#2563EB",
              },
            ]}
            onPress={() =>
              handleEmail(agent.email)
            }
          >
            <MaterialCommunityIcons
              name="email"
              size={24}
              color="#FFFFFF"
            />

            <Text style={styles.actionText}>
              Email
            </Text>
          </Pressable>

          <Pressable
            style={[
              styles.actionButton,
              {
                backgroundColor: "#7C3AED",
              },
            ]}
            onPress={handleShare}
          >
            <MaterialCommunityIcons
              name="share-variant"
              size={24}
              color="#FFFFFF"
            />

            <Text style={styles.actionText}>
              Share
            </Text>
          </Pressable>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Agency Information */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <Text
          style={[
            styles.sectionTitle,
            {
              color: colors.text,
            },
          ]}
        >
          Agency Information
        </Text>

        <View style={styles.infoRow}>
          <MaterialCommunityIcons
            name="office-building"
            size={22}
            color={colors.primary}
          />

          <View style={styles.infoContent}>
            <Text
              style={[
                styles.infoTitle,
                {
                  color: colors.text,
                },
              ]}
            >
              Agency
            </Text>

            <Text
              style={[
                styles.infoValue,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {agent.agency ??
                "Independent Realtor"}
            </Text>
          </View>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <MaterialCommunityIcons
            name="map-marker"
            size={22}
            color={colors.primary}
          />

          <View style={styles.infoContent}>
            <Text
              style={[
                styles.infoTitle,
                {
                  color: colors.text,
                },
              ]}
            >
              Office Address
            </Text>

            <Text
              style={[
                styles.infoValue,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {agent.address ??
                "Not Available"}
            </Text>
          </View>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <MaterialCommunityIcons
            name="web"
            size={22}
            color={colors.primary}
          />

          <View style={styles.infoContent}>
            <Text
              style={[
                styles.infoTitle,
                {
                  color: colors.text,
                },
              ]}
            >
              Website
            </Text>

            <Text
              style={[
                styles.infoValue,
                {
                  color:
                    colors.primary,
                },
              ]}
            >
              {agent.website ??
                "Not Available"}
            </Text>
          </View>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Professional Information */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <Text
          style={[
            styles.sectionTitle,
            {
              color: colors.text,
            },
          ]}
        >
          Professional Details
        </Text>

        <View style={styles.tagContainer}>
          {(agent.specialties ?? [
            "Residential",
            "Luxury Homes",
            "Apartments",
            "Commercial",
          ]).map((item) => (
            <View
              key={item}
              style={[
                styles.tag,
                {
                  backgroundColor:
                    colors.primary +
                    "15",
                },
              ]}
            >
              <Text
                style={[
                  styles.tagText,
                  {
                    color:
                      colors.primary,
                  },
                ]}
              >
                {item}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <MaterialCommunityIcons
            name="certificate"
            size={22}
            color="#F59E0B"
          />

          <View style={styles.infoContent}>
            <Text
              style={[
                styles.infoTitle,
                {
                  color: colors.text,
                },
              ]}
            >
              Certifications
            </Text>

            <Text
              style={[
                styles.infoValue,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {agent.certifications ??
                "Licensed Realtor • Certified Property Consultant"}
            </Text>
          </View>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <MaterialCommunityIcons
            name="translate"
            size={22}
            color="#10B981"
          />

          <View style={styles.infoContent}>
            <Text
              style={[
                styles.infoTitle,
                {
                  color: colors.text,
                },
              ]}
            >
              Languages
            </Text>

            <Text
              style={[
                styles.infoValue,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {(agent.languages ??
                [
                  "English",
                  "Yoruba",
                ]).join(", ")}
            </Text>
          </View>
        </View>
      </View>
            {/* ------------------------------------------------------------------ */}
      {/* About Agent */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <Text
          style={[
            styles.sectionTitle,
            {
              color: colors.text,
            },
          ]}
        >
          About {agent.name}
        </Text>

        <Text
          style={[
            styles.description,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          {agent.about ||
            agent.bio ||
            `${agent.name} is a trusted real estate professional specializing in residential, commercial and investment properties. With years of experience helping buyers, sellers and investors, ${agent.name.split(" ")[0]} is committed to delivering exceptional service, transparent communication and outstanding results throughout every stage of the property transaction.`}
        </Text>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Experience Timeline */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <Text
          style={[
            styles.sectionTitle,
            {
              color: colors.text,
            },
          ]}
        >
          Career Highlights
        </Text>

        {(agent.timeline ?? [
          {
            year: "2025",
            title:
              "Top Performing Property Consultant",
          },
          {
            year: "2023",
            title:
              "Joined Premium Partner Network",
          },
          {
            year: "2021",
            title:
              "Exceeded 100 Successful Sales",
          },
          {
            year: "2018",
            title:
              "Started Professional Real Estate Career",
          },
        ]).map((item, index) => (
          <View
            key={`${item.year}-${index}`}
            style={styles.timelineRow}
          >
            <View
              style={[
                styles.timelineDot,
                {
                  backgroundColor:
                    colors.primary,
                },
              ]}
            />

            <View
              style={
                styles.timelineContent
              }
            >
              <Text
                style={[
                  styles.timelineYear,
                  {
                    color:
                      colors.primary,
                  },
                ]}
              >
                {item.year}
              </Text>

              <Text
                style={[
                  styles.timelineTitle,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                {item.title}
              </Text>
            </View>
          </View>
        ))}
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Performance Metrics */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <Text
          style={[
            styles.sectionTitle,
            {
              color: colors.text,
            },
          ]}
        >
          Performance Metrics
        </Text>

        <View style={styles.metricsGrid}>
          <View style={styles.metricItem}>
            <MaterialCommunityIcons
              name="handshake"
              size={26}
              color="#22C55E"
            />

            <Text
              style={[
                styles.metricValue,
                {
                  color: colors.text,
                },
              ]}
            >
              {agent.closedDeals ??
                "150+"}
            </Text>

            <Text
              style={[
                styles.metricLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Deals Closed
            </Text>
          </View>

          <View style={styles.metricItem}>
            <MaterialCommunityIcons
              name="clock-check"
              size={26}
              color="#3B82F6"
            />

            <Text
              style={[
                styles.metricValue,
                {
                  color: colors.text,
                },
              ]}
            >
              {agent.responseTime ??
                "< 30m"}
            </Text>

            <Text
              style={[
                styles.metricLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Avg. Response
            </Text>
          </View>

          <View style={styles.metricItem}>
            <MaterialCommunityIcons
              name="account-heart"
              size={26}
              color="#EC4899"
            />

            <Text
              style={[
                styles.metricValue,
                {
                  color: colors.text,
                },
              ]}
            >
              {agent.satisfaction ??
                "98%"}
            </Text>

            <Text
              style={[
                styles.metricLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Satisfaction
            </Text>
          </View>

          <View style={styles.metricItem}>
            <MaterialCommunityIcons
              name="cash-multiple"
              size={26}
              color="#F59E0B"
            />

            <Text
              style={[
                styles.metricValue,
                {
                  color: colors.text,
                },
              ]}
            >
              {agent.salesVolume ??
                "₦2B+"}
            </Text>

            <Text
              style={[
                styles.metricLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Sales Volume
            </Text>
          </View>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Awards & Recognition */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <Text
          style={[
            styles.sectionTitle,
            {
              color: colors.text,
            },
          ]}
        >
          Awards & Recognition
        </Text>

        {(agent.achievements ?? [
          "Top 1% Real Estate Agent",
          "Excellence in Customer Service",
          "Highest Annual Sales Award",
          "Verified Premium Partner",
        ]).map((award, index) => (
          <View
            key={index}
            style={styles.achievementRow}
          >
            <MaterialCommunityIcons
              name="trophy-award"
              size={22}
              color="#F59E0B"
            />

            <Text
              style={[
                styles.achievementText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {award}
            </Text>
          </View>
        ))}
      </View>
            {/* ------------------------------------------------------------------ */}
      {/* Agent Listings */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor: colors.background,
          },
        ]}
      >
        <View style={styles.sectionHeader}>
          <View>
            <Text
              style={[
                styles.sectionTitle,
                {
                  color: colors.text,
                },
              ]}
            >
              Featured Listings
            </Text>

            <Text
              style={[
                styles.sectionSubtitle,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {properties.length} active
              {properties.length === 1
                ? " listing"
                : " listings"}
            </Text>
          </View>

          <Pressable
            style={[
              styles.viewAllButton,
              {
                borderColor:
                  colors.primary,
              },
            ]}
            onPress={() =>
              router.push({
                pathname:
                  "/real-estate/agent-properties/[id]",

                params: {
                  id: agent.id,
                },
              })
            }
          >
            <Text
              style={[
                styles.viewAllText,
                {
                  color:
                    colors.primary,
                },
              ]}
            >
              View All
            </Text>

            <MaterialCommunityIcons
              name="chevron-right"
              size={18}
              color={
                colors.primary
              }
            />
          </Pressable>
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Property Statistics */}
        {/* -------------------------------------------------------------- */}

        <View
          style={[
            styles.listingSummary,
            {
              backgroundColor:
                colors.card,
              borderColor:
                colors.border,
            },
          ]}
        >
          <View
            style={
              styles.summaryItem
            }
          >
            <MaterialCommunityIcons
              name="home-city"
              size={22}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.summaryValue,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {properties.length}
            </Text>

            <Text
              style={[
                styles.summaryLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Active
            </Text>
          </View>

          <View
            style={
              styles.summaryDivider
            }
          />

          <View
            style={
              styles.summaryItem
            }
          >
            <MaterialCommunityIcons
              name="currency-ngn"
              size={22}
              color="#22C55E"
            />

            <Text
              style={[
                styles.summaryValue,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              ₦
              {properties.length
                ? Math.max(
                    ...properties.map(
                      (p) =>
                        Number(
                          p.price ??
                            0
                        )
                    )
                  ).toLocaleString()
                : "0"}
            </Text>

            <Text
              style={[
                styles.summaryLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Highest
            </Text>
          </View>

          <View
            style={
              styles.summaryDivider
            }
          />

          <View
            style={
              styles.summaryItem
            }
          >
            <MaterialCommunityIcons
              name="star-circle"
              size={22}
              color="#F59E0B"
            />

            <Text
              style={[
                styles.summaryValue,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {agent.rating ??
                "5.0"}
            </Text>

            <Text
              style={[
                styles.summaryLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Rating
            </Text>
          </View>
        </View>

        {/* -------------------------------------------------------------- */}
        {/* Property List */}
        {/* -------------------------------------------------------------- */}

        {properties.length > 0 ? (
          properties.map(
            (property) => (
              <PropertyCard
                key={property.id}
                property={property}
                saved={isSaved(
                  property.id
                )}
                style={
                  styles.propertyCard
                }
                onPress={() =>
                  openProperty(
                    property
                  )
                }
                onFavoritePress={() =>
                  toggleSaved(
                    property.id
                  )
                }
              />
            )
          )
        ) : (
          <DashboardEmpty
            title="No Active Listings"
            description={`${agent.name} doesn't have any published properties yet.`}
          />
        )}
      </View>
            {/* ------------------------------------------------------------------ */}
      {/* Client Reviews */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <View style={styles.sectionHeader}>
          <Text
            style={[
              styles.sectionTitle,
              {
                color: colors.text,
              },
            ]}
          >
            Client Reviews
          </Text>

          <Text
            style={[
              styles.sectionSubtitle,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            {agent.reviewCount ?? 0} Reviews
          </Text>
        </View>

        {(agent.reviews ?? [
          {
            id: 1,
            name: "Michael A.",
            rating: 5,
            comment:
              "Excellent service from start to finish. The entire buying process was smooth and transparent.",
          },
          {
            id: 2,
            name: "Grace O.",
            rating: 5,
            comment:
              "Professional, responsive and knowledgeable. Highly recommended.",
          },
        ]).map((review) => (
          <View
            key={review.id}
            style={styles.reviewCard}
          >
            <View
              style={
                styles.reviewHeader
              }
            >
              <View
                style={
                  styles.reviewAvatar
                }
              >
                <Text
                  style={
                    styles.reviewInitial
                  }
                >
                  {review.name
                    .charAt(0)
                    .toUpperCase()}
                </Text>
              </View>

              <View
                style={
                  styles.reviewInfo
                }
              >
                <Text
                  style={[
                    styles.reviewName,
                    {
                      color:
                        colors.text,
                    },
                  ]}
                >
                  {review.name}
                </Text>

                <View
                  style={
                    styles.ratingRow
                  }
                >
                  {Array.from({
                    length: 5,
                  }).map(
                    (_, index) => (
                      <MaterialCommunityIcons
                        key={index}
                        name={
                          index <
                          review.rating
                            ? "star"
                            : "star-outline"
                        }
                        size={16}
                        color="#F59E0B"
                      />
                    )
                  )}
                </View>
              </View>
            </View>

            <Text
              style={[
                styles.reviewComment,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              {review.comment}
            </Text>
          </View>
        ))}
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Schedule Viewing */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
          },
        ]}
      >
        <MaterialCommunityIcons
          name="calendar-check"
          size={42}
          color={colors.primary}
        />

        <Text
          style={[
            styles.scheduleTitle,
            {
              color: colors.text,
            },
          ]}
        >
          Schedule a Property Viewing
        </Text>

        <Text
          style={[
            styles.scheduleDescription,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          Book an appointment with {agent.name}
          {" "}to tour available properties,
          discuss financing options and receive
          personalized recommendations.
        </Text>

        <Pressable
          style={[
            styles.scheduleButton,
            {
              backgroundColor:
                colors.primary,
            },
          ]}
          onPress={() =>
            router.push({
              pathname:
                "/real-estate/schedule-visit",

              params: {
                agentId: agent.id,
              },
            })
          }
        >
          <MaterialCommunityIcons
            name="calendar-plus"
            size={20}
            color="#FFFFFF"
          />

          <Text
            style={
              styles.scheduleButtonText
            }
          >
            Schedule Visit
          </Text>
        </Pressable>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Bottom Contact Bar */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.bottomBar,
          {
            backgroundColor:
              colors.card,
            borderTopColor:
              colors.border,
          },
        ]}
      >
        <Pressable
          style={[
            styles.bottomButton,
            {
              backgroundColor:
                "#22C55E",
            },
          ]}
          onPress={() =>
            handleCall(agent.phone)
          }
        >
          <MaterialCommunityIcons
            name="phone"
            size={20}
            color="#FFFFFF"
          />

          <Text
            style={
              styles.bottomButtonText
            }
          >
            Call
          </Text>
        </Pressable>

        <Pressable
          style={[
            styles.bottomButton,
            {
              backgroundColor:
                colors.primary,
            },
          ]}
          onPress={() =>
            router.push({
              pathname:
                "/real-estate/chat",

              params: {
                agentId: agent.id,
              },
            })
          }
        >
          <MaterialCommunityIcons
            name="message-text"
            size={20}
            color="#FFFFFF"
          />

          <Text
            style={
              styles.bottomButtonText
            }
          >
            Message
          </Text>
        </Pressable>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Bottom Spacer */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.bottomSpacing} />

    </ScrollView>
  );
});

AgentProfile.displayName =
  "AgentProfile";
  /* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  content: {
    paddingBottom: 40,
  },

  /* ---------------------------------------------------------------------- */
  /* Hero */
  /* ---------------------------------------------------------------------- */

  heroContainer: {
    height: 260,
    position: "relative",
  },

  coverImage: {
    width: "100%",
    height: "100%",
  },

  heroOverlay: {
    ...StyleSheet.absoluteFillObject,
  },

  backButton: {
    position: "absolute",
    top: 50,
    left: 20,
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: "center",
    alignItems: "center",
    elevation: 4,
    zIndex: 20,
  },

  /* ---------------------------------------------------------------------- */
  /* Profile */
  /* ---------------------------------------------------------------------- */

  profileCard: {
    marginHorizontal: 20,
    marginTop: -60,
    borderRadius: 22,
    borderWidth: 1,
    alignItems: "center",
    padding: 24,
    elevation: 2,
  },

  avatar: {
    width: 110,
    height: 110,
    borderRadius: 55,
  },

  verifiedBadge: {
    position: "absolute",
    top: 98,
    right: "34%",
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "#10B981",
    justifyContent: "center",
    alignItems: "center",
  },

  agentName: {
    marginTop: 16,
    fontSize: 26,
    fontWeight: "700",
    textAlign: "center",
  },

  agentTitle: {
    marginTop: 6,
    fontSize: 15,
    textAlign: "center",
  },

  ratingRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 10,
  },

  ratingText: {
    marginLeft: 6,
    fontWeight: "700",
    fontSize: 15,
  },

  reviewText: {
    marginLeft: 6,
    fontSize: 14,
  },

  bio: {
    marginTop: 16,
    textAlign: "center",
    lineHeight: 22,
    fontSize: 15,
  },

  /* ---------------------------------------------------------------------- */
  /* Statistics */
  /* ---------------------------------------------------------------------- */

  statsCard: {
    flexDirection: "row",
    marginHorizontal: 20,
    marginTop: 24,
    borderWidth: 1,
    borderRadius: 18,
    paddingVertical: 20,
  },

  statItem: {
    flex: 1,
    alignItems: "center",
  },

  statDivider: {
    width: StyleSheet.hairlineWidth,
    backgroundColor: "#D1D5DB",
  },

  statValue: {
    marginTop: 8,
    fontSize: 22,
    fontWeight: "700",
  },

  statLabel: {
    marginTop: 4,
    fontSize: 13,
  },

  /* ---------------------------------------------------------------------- */
  /* Sections */
  /* ---------------------------------------------------------------------- */

  section: {
    marginHorizontal: 20,
    marginTop: 24,
    padding: 20,
    borderRadius: 18,
    borderWidth: 1,
  },

  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 18,
  },

  sectionTitle: {
    fontSize: 20,
    fontWeight: "700",
  },

  sectionSubtitle: {
    marginTop: 4,
    fontSize: 14,
  },

  description: {
    lineHeight: 24,
    fontSize: 15,
  },

  /* ---------------------------------------------------------------------- */
  /* Contact */
  /* ---------------------------------------------------------------------- */

  actionGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
  },

  actionButton: {
    width: "48%",
    height: 72,
    borderRadius: 16,
    marginBottom: 14,
    justifyContent: "center",
    alignItems: "center",
  },

  actionText: {
    color: "#FFFFFF",
    marginTop: 6,
    fontWeight: "700",
  },

  /* ---------------------------------------------------------------------- */
  /* Information */
  /* ---------------------------------------------------------------------- */

  infoRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingVertical: 14,
  },

  infoContent: {
    flex: 1,
    marginLeft: 14,
  },

  infoTitle: {
    fontWeight: "700",
    fontSize: 15,
  },

  infoValue: {
    marginTop: 4,
    fontSize: 14,
    lineHeight: 21,
  },

  infoDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: "#E5E7EB",
  },

  /* ---------------------------------------------------------------------- */
  /* Tags */
  /* ---------------------------------------------------------------------- */

  tagContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 8,
  },

  tag: {
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    marginRight: 10,
    marginBottom: 10,
  },

  tagText: {
    fontWeight: "600",
    fontSize: 13,
  },

  /* ---------------------------------------------------------------------- */
  /* Timeline */
  /* ---------------------------------------------------------------------- */

  timelineRow: {
    flexDirection: "row",
    marginBottom: 18,
  },

  timelineDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginTop: 7,
    marginRight: 16,
  },

  timelineContent: {
    flex: 1,
  },

  timelineYear: {
    fontWeight: "700",
    marginBottom: 4,
  },

  timelineTitle: {
    fontSize: 15,
    lineHeight: 22,
  },

  /* ---------------------------------------------------------------------- */
  /* Metrics */
  /* ---------------------------------------------------------------------- */

  metricsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
  },

  metricItem: {
    width: "48%",
    alignItems: "center",
    marginBottom: 20,
  },

  metricValue: {
    marginTop: 8,
    fontSize: 20,
    fontWeight: "700",
  },

  metricLabel: {
    marginTop: 4,
    textAlign: "center",
    fontSize: 13,
  },

  achievementRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 14,
  },

  achievementText: {
    marginLeft: 12,
    flex: 1,
    lineHeight: 22,
  },

  /* ---------------------------------------------------------------------- */
  /* Listings */
  /* ---------------------------------------------------------------------- */

  listingSummary: {
    flexDirection: "row",
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 20,
    paddingVertical: 16,
  },

  summaryItem: {
    flex: 1,
    alignItems: "center",
  },

  summaryDivider: {
    width: StyleSheet.hairlineWidth,
    backgroundColor: "#D1D5DB",
  },

  summaryValue: {
    marginTop: 6,
    fontSize: 18,
    fontWeight: "700",
  },

  summaryLabel: {
    marginTop: 4,
    fontSize: 12,
  },

  propertyCard: {
    marginBottom: 18,
  },

  viewAllButton: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },

  viewAllText: {
    fontWeight: "700",
    marginRight: 4,
  },

  /* ---------------------------------------------------------------------- */
  /* Reviews */
  /* ---------------------------------------------------------------------- */

  reviewCard: {
    marginBottom: 18,
  },

  reviewHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
  },

  reviewAvatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: "#3B82F6",
    justifyContent: "center",
    alignItems: "center",
  },

  reviewInitial: {
    color: "#FFFFFF",
    fontWeight: "700",
  },

  reviewInfo: {
    marginLeft: 12,
    flex: 1,
  },

  reviewName: {
    fontWeight: "700",
    marginBottom: 4,
  },

  reviewComment: {
    lineHeight: 22,
    fontSize: 14,
  },

  /* ---------------------------------------------------------------------- */
  /* Schedule */
  /* ---------------------------------------------------------------------- */

  scheduleTitle: {
    marginTop: 16,
    fontSize: 22,
    fontWeight: "700",
    textAlign: "center",
  },

  scheduleDescription: {
    marginTop: 12,
    textAlign: "center",
    lineHeight: 24,
  },

  scheduleButton: {
    marginTop: 24,
    height: 54,
    borderRadius: 14,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },

  scheduleButtonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 16,
    marginLeft: 8,
  },

  /* ---------------------------------------------------------------------- */
  /* Bottom Bar */
  /* ---------------------------------------------------------------------- */

  bottomBar: {
    flexDirection: "row",
    padding: 20,
    borderTopWidth: 1,
    marginTop: 30,
  },

  bottomButton: {
    flex: 1,
    height: 52,
    borderRadius: 14,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
    marginHorizontal: 6,
  },

  bottomButtonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    marginLeft: 8,
    fontSize: 15,
  },

  bottomSpacing: {
    height: 40,
  },
});

/* -------------------------------------------------------------------------- */
/* Export */
/* -------------------------------------------------------------------------- */

export default AgentProfile;