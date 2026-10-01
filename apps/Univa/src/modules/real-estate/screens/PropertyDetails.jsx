import React, {
  memo,
  useCallback,
} from "react";

import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { useLocalSearchParams, useRouter } from "expo-router";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTheme } from "@/theme";

/* -------------------------------------------------------------------------- */
/* Hooks */
/* -------------------------------------------------------------------------- */

import usePropertyDetails from "../hooks/usePropertyDetails";
import useSavedProperties from "../hooks/useSavedProperties";

/* -------------------------------------------------------------------------- */
/* Components */
/* -------------------------------------------------------------------------- */

import PropertyGallery from "../components/property-details/PropertyGallery";
import PropertyOverview from "../components/property-details/PropertyOverview";
import PropertyFeatures from "../components/property-details/PropertyFeatures";
import PropertyAmenities from "../components/property-details/PropertyAmenities";
import PropertyMapPreview from "../components/property-details/PropertyMapPreview";
import AgentContactCard from "../components/property-details/AgentContactCard";
import MortgageCalculator from "../components/property-details/MortgageCalculator";
import SimilarProperties from "../components/property-details/SimilarProperties";
import ScheduleVisitCard from "../components/property-details/ScheduleVisitCard";
import PropertyActions from "../components/property-details/PropertyActions";

import DashboardSkeleton from "../components/skeleton/DashboardSkeleton";
import DashboardEmpty from "../components/empty/DashboardEmpty";

/* -------------------------------------------------------------------------- */
/* Property Details */
/* -------------------------------------------------------------------------- */

const PropertyDetails = memo(() => {
  const router = useRouter();

  const { colors } = useTheme();

  const { id } = useLocalSearchParams();

  /* ---------------------------------------------------------------------- */
  /* Property */
  /* ---------------------------------------------------------------------- */

  const {
    property,

    similarProperties,

    loading,

    refreshing,

    error,

    refresh,
  } = usePropertyDetails({
    id,
  });

  /* ---------------------------------------------------------------------- */
  /* Saved */
  /* ---------------------------------------------------------------------- */

  const {
    toggleSaved,

    isSaved,
  } = useSavedProperties();

  /* ---------------------------------------------------------------------- */
  /* Navigation */
  /* ---------------------------------------------------------------------- */

  const goBack =
    useCallback(() => {
      router.back();
    }, [router]);

  const openProperty =
    useCallback(
      (item) => {
        router.push({
          pathname:
            "/real-estate/property/[id]",

          params: {
            id: item.id,
          },
        });
      },
      [router]
    );

  const openAgent =
    useCallback(() => {
      if (!property?.agent) return;

      router.push({
        pathname:
          "/real-estate/agent/[id]",

        params: {
          id: property.agent.id,
        },
      });
    }, [router, property]);

  /* ---------------------------------------------------------------------- */
  /* Actions */
  /* ---------------------------------------------------------------------- */

  const handleSave =
    useCallback(() => {
      if (!property) return;

      toggleSaved(property.id);
    }, [
      property,
      toggleSaved,
    ]);

  const handleShare =
    useCallback(() => {
      console.log(
        "Share property"
      );
    }, []);

  const handleCall =
    useCallback(() => {
      console.log(
        "Call agent"
      );
    }, []);

  const handleMessage =
    useCallback(() => {
      console.log(
        "Message agent"
      );
    }, []);

  const handleSchedule =
    useCallback(() => {
      console.log(
        "Schedule visit"
      );
    }, []);

  /* ---------------------------------------------------------------------- */
  /* Loading */
  /* ---------------------------------------------------------------------- */

  if (loading) {
    return <DashboardSkeleton />;
  }

  /* ---------------------------------------------------------------------- */
  /* Error */
  /* ---------------------------------------------------------------------- */

  if (error || !property) {
    return (
      <DashboardEmpty
        title="Property not found"
        description={
          error?.message ??
          "Unable to load this property."
        }
        onRetry={refresh}
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
          onRefresh={refresh}
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
      {/* Property Gallery */}
      {/* ------------------------------------------------------------------ */}

      <PropertyGallery
        images={property.images}
        thumbnail={property.thumbnail}
        title={property.title}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Floating Actions */}
      {/* ------------------------------------------------------------------ */}

      <PropertyActions
        saved={isSaved(property.id)}
        onBack={goBack}
        onSave={handleSave}
        onShare={handleShare}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Property Status */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.badgesContainer}>
        {property.featured && (
          <View
            style={[
              styles.badge,
              styles.featuredBadge,
            ]}
          >
            <MaterialCommunityIcons
              name="star"
              size={14}
              color="#FFFFFF"
            />

            <Text
              style={
                styles.badgeText
              }
            >
              Featured
            </Text>
          </View>
        )}

        {property.verified && (
          <View
            style={[
              styles.badge,
              styles.verifiedBadge,
            ]}
          >
            <MaterialCommunityIcons
              name="check-decagram"
              size={14}
              color="#FFFFFF"
            />

            <Text
              style={
                styles.badgeText
              }
            >
              Verified
            </Text>
          </View>
        )}

        <View
          style={[
            styles.badge,
            property.listingType ===
            "RENT"
              ? styles.rentBadge
              : styles.saleBadge,
          ]}
        >
          <MaterialCommunityIcons
            name="home-city"
            size={14}
            color="#FFFFFF"
          />

          <Text
            style={
              styles.badgeText
            }
          >
            {property.listingType ===
            "RENT"
              ? "For Rent"
              : "For Sale"}
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Image Counter */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.imageCounter,
          {
            backgroundColor:
              colors.card,
            borderColor:
              colors.border,
          },
        ]}
      >
        <MaterialCommunityIcons
          name="image-multiple"
          size={18}
          color={colors.primary}
        />

        <Text
          style={[
            styles.imageCounterText,
            {
              color: colors.text,
            },
          ]}
        >
          {(property.images
            ?.length ??
            0) + " Photos"}
        </Text>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Property Overview */}
      {/* ------------------------------------------------------------------ */}

      <PropertyOverview
        property={property}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Property Price */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.priceCard,
          {
            backgroundColor:
              colors.card,
            borderColor:
              colors.border,
          },
        ]}
      >
        <Text
          style={[
            styles.priceLabel,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          Price
        </Text>

        <Text
          style={[
            styles.price,
            {
              color:
                colors.primary,
            },
          ]}
        >
          ₦
          {Number(
            property.price ?? 0
          ).toLocaleString()}
        </Text>

        {property.listingType ===
          "RENT" && (
          <Text
            style={[
              styles.perMonth,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            per month
          </Text>
        )}

        <View
          style={
            styles.addressRow
          }
        >
          <MaterialCommunityIcons
            name="map-marker"
            size={18}
            color={
              colors.primary
            }
          />

          <Text
            style={[
              styles.address,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {property.address}
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Property Statistics */}
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
            name="bed-outline"
            size={24}
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
            {property.bedrooms ??
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
            Bedrooms
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
            name="shower"
            size={24}
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
            {property.bathrooms ??
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
            Bathrooms
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
            name="ruler-square"
            size={24}
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
            {property.area ??
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
            m²
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Property Features */}
      {/* ------------------------------------------------------------------ */}

      <PropertyFeatures
        property={property}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Property Description */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor:
              colors.card,
            borderColor:
              colors.border,
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
          Description
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
          {property.description ||
            "No description has been provided for this property."}
        </Text>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Property Amenities */}
      {/* ------------------------------------------------------------------ */}

      <PropertyAmenities
        amenities={
          property.amenities ??
          []
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Additional Information */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor:
              colors.card,
            borderColor:
              colors.border,
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
          Additional Information
        </Text>

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Property Type
          </Text>

          <Text
            style={[
              styles.infoValue,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {property.propertyType ??
              "-"}
          </Text>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Category
          </Text>

          <Text
            style={[
              styles.infoValue,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {property.category
              ?.name ??
              "-"}
          </Text>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Year Built
          </Text>

          <Text
            style={[
              styles.infoValue,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {property.yearBuilt ??
              "-"}
          </Text>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Parking Spaces
          </Text>

          <Text
            style={[
              styles.infoValue,
              {
                color:
                  colors.text,
              },
            ]}
          >
            {property.parking ??
              0}
          </Text>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Furnished
          </Text>

          <Text
            style={[
              styles.infoValue,
              {
                color:
                  property.furnished
                    ? "#22C55E"
                    : colors.text,
              },
            ]}
          >
            {property.furnished
              ? "Yes"
              : "No"}
          </Text>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Pets Allowed
          </Text>

          <Text
            style={[
              styles.infoValue,
              {
                color:
                  property.petsAllowed
                    ? "#22C55E"
                    : colors.text,
              },
            ]}
          >
            {property.petsAllowed
              ? "Yes"
              : "No"}
          </Text>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Status
          </Text>

          <Text
            style={[
              styles.infoValue,
              {
                color:
                  property.available
                    ? "#22C55E"
                    : "#EF4444",
              },
            ]}
          >
            {property.available
              ? "Available"
              : "Unavailable"}
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Listing Agent */}
      {/* ------------------------------------------------------------------ */}

      <AgentContactCard
        agent={property.agent}
        onPress={openAgent}
        onCall={handleCall}
        onMessage={handleMessage}
        onEmail={() => {
          console.log("Email agent");
        }}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Schedule Property Visit */}
      {/* ------------------------------------------------------------------ */}

      <ScheduleVisitCard
        property={property}
        agent={property.agent}
        onSchedule={handleSchedule}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Quick Contact */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor:
              colors.card,
            borderColor:
              colors.border,
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

        <Text
          style={[
            styles.sectionSubtitle,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          Reach out to the listing agent for more
          information, schedule a viewing, or ask
          questions about this property.
        </Text>

        <View style={styles.contactActions}>
          <PropertyActions.Action
            icon="phone"
            label="Call"
            color="#22C55E"
            onPress={handleCall}
          />

          <PropertyActions.Action
            icon="message-text"
            label="Message"
            color="#3B82F6"
            onPress={handleMessage}
          />

          <PropertyActions.Action
            icon="email-outline"
            label="Email"
            color="#F59E0B"
            onPress={() =>
              console.log(
                "Email agent"
              )
            }
          />

          <PropertyActions.Action
            icon="account"
            label="Profile"
            color="#8B5CF6"
            onPress={openAgent}
          />
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Agent Statistics */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.section,
          {
            backgroundColor:
              colors.card,
            borderColor:
              colors.border,
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
          Agent Statistics
        </Text>

        <View style={styles.statsGrid}>
          <View style={styles.gridItem}>
            <MaterialCommunityIcons
              name="home-city"
              size={26}
              color={colors.primary}
            />

            <Text
              style={[
                styles.gridValue,
                {
                  color: colors.text,
                },
              ]}
            >
              {property.agent
                ?.propertiesCount ??
                0}
            </Text>

            <Text
              style={[
                styles.gridLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Listings
            </Text>
          </View>

          <View style={styles.gridItem}>
            <MaterialCommunityIcons
              name="star"
              size={26}
              color="#F59E0B"
            />

            <Text
              style={[
                styles.gridValue,
                {
                  color: colors.text,
                },
              ]}
            >
              {property.agent
                ?.rating ??
                "0.0"}
            </Text>

            <Text
              style={[
                styles.gridLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Rating
            </Text>
          </View>

          <View style={styles.gridItem}>
            <MaterialCommunityIcons
              name="account-group"
              size={26}
              color="#3B82F6"
            />

            <Text
              style={[
                styles.gridValue,
                {
                  color: colors.text,
                },
              ]}
            >
              {property.agent
                ?.reviews ??
                0}
            </Text>

            <Text
              style={[
                styles.gridLabel,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Reviews
            </Text>
          </View>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Property Location */}
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
          Property Location
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
          {property.address}
        </Text>

        <View style={styles.mapContainer}>
          <PropertyMapPreview
            property={property}
            height={260}
            onPress={() =>
              router.push({
                pathname:
                  "/real-estate/map",

                params: {
                  id: property.id,
                },
              })
            }
          />
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Mortgage Calculator */}
      {/* ------------------------------------------------------------------ */}

      <MortgageCalculator
        property={property}
        price={property.price}
      />

      {/* ------------------------------------------------------------------ */}
      {/* Financing Summary */}
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
          Financing Summary
        </Text>

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Property Price
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
            ₦
            {Number(
              property.price ?? 0
            ).toLocaleString()}
          </Text>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Estimated Down Payment
          </Text>

          <Text
            style={[
              styles.infoValue,
              {
                color: colors.text,
              },
            ]}
          >
            ₦
            {Math.round(
              (property.price ?? 0) *
                0.2
            ).toLocaleString()}
          </Text>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Estimated Loan Amount
          </Text>

          <Text
            style={[
              styles.infoValue,
              {
                color: colors.text,
              },
            ]}
          >
            ₦
            {Math.round(
              (property.price ?? 0) *
                0.8
            ).toLocaleString()}
          </Text>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Estimated Monthly Payment
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
            ₦
            {Math.round(
              (property.price ?? 0) /
                240
            ).toLocaleString()}
          </Text>
        </View>

        <View style={styles.infoDivider} />

        <View style={styles.infoRow}>
          <Text
            style={[
              styles.infoLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Estimated Loan Term
          </Text>

          <Text
            style={[
              styles.infoValue,
              {
                color: colors.text,
              },
            ]}
          >
            20 Years
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Investment Highlights */}
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
          Investment Highlights
        </Text>

        <View style={styles.highlightRow}>
          <MaterialCommunityIcons
            name="check-circle"
            size={20}
            color="#22C55E"
          />

          <Text
            style={[
              styles.highlightText,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Prime location with excellent road
            access.
          </Text>
        </View>

        <View style={styles.highlightRow}>
          <MaterialCommunityIcons
            name="check-circle"
            size={20}
            color="#22C55E"
          />

          <Text
            style={[
              styles.highlightText,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Strong rental and resale potential.
          </Text>
        </View>

        <View style={styles.highlightRow}>
          <MaterialCommunityIcons
            name="check-circle"
            size={20}
            color="#22C55E"
          />

          <Text
            style={[
              styles.highlightText,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Suitable for both personal residence
            and long-term investment.
          </Text>
        </View>

        <View style={styles.highlightRow}>
          <MaterialCommunityIcons
            name="check-circle"
            size={20}
            color="#22C55E"
          />

          <Text
            style={[
              styles.highlightText,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Located close to schools,
            hospitals, shopping centres and
            public transport.
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Similar Properties */}
      {/* ------------------------------------------------------------------ */}

      <SimilarProperties
        properties={similarProperties}
        onPropertyPress={openProperty}
        onFavoritePress={(item) =>
          toggleSaved(item.id)
        }
        isSaved={isSaved}
        onSeeAll={() =>
          router.push(
            "/real-estate/properties/similar"
          )
        }
      />

      {/* ------------------------------------------------------------------ */}
      {/* Bottom Action Bar */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.bottomActionBar,
          {
            backgroundColor:
              colors.card,
            borderTopColor:
              colors.border,
          },
        ]}
      >
        <PropertyActions.Action
          icon={
            isSaved(property.id)
              ? "heart"
              : "heart-outline"
          }
          label={
            isSaved(property.id)
              ? "Saved"
              : "Save"
          }
          color="#EF4444"
          onPress={handleSave}
        />

        <PropertyActions.Action
          icon="share-variant"
          label="Share"
          color="#3B82F6"
          onPress={handleShare}
        />

        <PropertyActions.Action
          icon="calendar-check"
          label="Visit"
          color="#22C55E"
          onPress={handleSchedule}
        />

        <PropertyActions.Action
          icon="phone"
          label="Call"
          color="#8B5CF6"
          onPress={handleCall}
        />
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Bottom Safe Area */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={styles.bottomSpacing}
      />
    </ScrollView>
  );
});

PropertyDetails.displayName =
  "PropertyDetails";

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
  /* Gallery */
  /* ---------------------------------------------------------------------- */

  badgesContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    paddingHorizontal: 20,
    marginTop: 18,
    gap: 10,
  },

  badge: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },

  badgeText: {
    marginLeft: 6,
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 12,
  },

  featuredBadge: {
    backgroundColor: "#F59E0B",
  },

  verifiedBadge: {
    backgroundColor: "#22C55E",
  },

  saleBadge: {
    backgroundColor: "#3B82F6",
  },

  rentBadge: {
    backgroundColor: "#8B5CF6",
  },

  imageCounter: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    marginHorizontal: 20,
    marginTop: 16,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 14,
    borderWidth: 1,
  },

  imageCounterText: {
    marginLeft: 8,
    fontSize: 14,
    fontWeight: "600",
  },

  /* ---------------------------------------------------------------------- */
  /* Generic Section */
  /* ---------------------------------------------------------------------- */

  section: {
    marginHorizontal: 20,
    marginTop: 24,
    borderRadius: 18,
    borderWidth: 1,
    padding: 18,
  },

  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
  },

  sectionSubtitle: {
    marginTop: 8,
    fontSize: 14,
    lineHeight: 22,
  },

  /* ---------------------------------------------------------------------- */
  /* Price */
  /* ---------------------------------------------------------------------- */

  priceCard: {
    marginHorizontal: 20,
    marginTop: 20,
    borderRadius: 18,
    borderWidth: 1,
    padding: 20,
  },

  priceLabel: {
    fontSize: 13,
  },

  price: {
    marginTop: 6,
    fontSize: 30,
    fontWeight: "800",
  },

  perMonth: {
    marginTop: 4,
    fontSize: 14,
  },

  addressRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 18,
  },

  address: {
    marginLeft: 10,
    flex: 1,
    fontSize: 15,
    lineHeight: 22,
  },

  /* ---------------------------------------------------------------------- */
  /* Statistics */
  /* ---------------------------------------------------------------------- */

  statsCard: {
    flexDirection: "row",
    marginHorizontal: 20,
    marginTop: 20,
    borderRadius: 18,
    borderWidth: 1,
    paddingVertical: 20,
  },

  statItem: {
    flex: 1,
    alignItems: "center",
  },

  statDivider: {
    width: 1,
    backgroundColor: "#E5E7EB",
  },

  statValue: {
    marginTop: 10,
    fontSize: 22,
    fontWeight: "700",
  },

  statLabel: {
    marginTop: 6,
    fontSize: 13,
  },

  /* ---------------------------------------------------------------------- */
  /* Description */
  /* ---------------------------------------------------------------------- */

  description: {
    marginTop: 12,
    fontSize: 15,
    lineHeight: 26,
  },

  /* ---------------------------------------------------------------------- */
  /* Information */
  /* ---------------------------------------------------------------------- */

  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 14,
  },

  infoLabel: {
    flex: 1,
    fontSize: 14,
  },

  infoValue: {
    fontSize: 15,
    fontWeight: "600",
    textAlign: "right",
    flex: 1,
  },

  infoDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: "#E5E7EB",
  },

  /* ---------------------------------------------------------------------- */
  /* Contact */
  /* ---------------------------------------------------------------------- */

  contactActions: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 20,
  },

  /* ---------------------------------------------------------------------- */
  /* Agent Stats */
  /* ---------------------------------------------------------------------- */

  statsGrid: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 20,
  },

  gridItem: {
    flex: 1,
    alignItems: "center",
  },

  gridValue: {
    marginTop: 10,
    fontSize: 22,
    fontWeight: "700",
  },

  gridLabel: {
    marginTop: 6,
    fontSize: 13,
  },

  /* ---------------------------------------------------------------------- */
  /* Map */
  /* ---------------------------------------------------------------------- */

  mapContainer: {
    marginTop: 18,
    overflow: "hidden",
    borderRadius: 18,
  },

  /* ---------------------------------------------------------------------- */
  /* Investment */
  /* ---------------------------------------------------------------------- */

  highlightRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginTop: 16,
  },

  highlightText: {
    flex: 1,
    marginLeft: 12,
    fontSize: 14,
    lineHeight: 22,
  },

  /* ---------------------------------------------------------------------- */
  /* Bottom Action Bar */
  /* ---------------------------------------------------------------------- */

  bottomActionBar: {
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
    marginTop: 30,
    paddingHorizontal: 12,
    paddingVertical: 16,
    borderTopWidth: 1,
  },

  /* ---------------------------------------------------------------------- */
  /* Bottom */
  /* ---------------------------------------------------------------------- */

  bottomSpacing: {
    height: 40,
  },
});

/* -------------------------------------------------------------------------- */
/* Export */
/* -------------------------------------------------------------------------- */

export default PropertyDetails;