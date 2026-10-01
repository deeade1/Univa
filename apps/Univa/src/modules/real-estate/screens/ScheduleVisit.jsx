import React, {
  memo,
  useCallback,
  useMemo,
  useState,
} from "react";

import {
  ScrollView,
  RefreshControl,
  StyleSheet,
  View,
  Text,
  Pressable,
  TextInput,
  Alert,
} from "react-native";

import {
  useLocalSearchParams,
  useRouter,
} from "expo-router";

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

import DashboardSkeleton from "../components/skeleton/DashboardSkeleton";
import DashboardEmpty from "../components/empty/DashboardEmpty";

import AgentCard from "../components/agents/AgentCard";
import PropertyCard from "../components/property/PropertyCard";

/* -------------------------------------------------------------------------- */
/* Schedule Visit */
/* -------------------------------------------------------------------------- */

const ScheduleVisit = memo(() => {
  const router = useRouter();

  const {
    propertyId,
    agentId,
  } = useLocalSearchParams();

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
    savedProperties,
  } = useSavedProperties();

  /* ---------------------------------------------------------------------- */
  /* Lookups */
  /* ---------------------------------------------------------------------- */

  const agent = useMemo(
    () =>
      agents.find(
        (item) =>
          String(item.id) ===
          String(agentId)
      ),
    [agents, agentId]
  );

  const property =
    useMemo(
      () =>
        savedProperties.find(
          (item) =>
            String(item.id) ===
            String(propertyId)
        ),
      [
        savedProperties,
        propertyId,
      ]
    );

  /* ---------------------------------------------------------------------- */
  /* Form State */
  /* ---------------------------------------------------------------------- */

  const [selectedDate, setSelectedDate] =
    useState(null);

  const [selectedTime, setSelectedTime] =
    useState(null);

  const [visitType, setVisitType] =
    useState("physical");

  const [attendees, setAttendees] =
    useState(1);

  const [fullName, setFullName] =
    useState("");

  const [phone, setPhone] =
    useState("");

  const [email, setEmail] =
    useState("");

  const [notes, setNotes] =
    useState("");

  const [submitting, setSubmitting] =
    useState(false);

  /* ---------------------------------------------------------------------- */
  /* Refresh */
  /* ---------------------------------------------------------------------- */

  const handleRefresh =
    useCallback(async () => {
      await refresh();
    }, [refresh]);

  /* ---------------------------------------------------------------------- */
  /* Available Time Slots */
  /* ---------------------------------------------------------------------- */

  const availableTimes =
    useMemo(
      () => [
        "09:00 AM",
        "10:00 AM",
        "11:00 AM",
        "12:00 PM",
        "01:00 PM",
        "02:00 PM",
        "03:00 PM",
        "04:00 PM",
        "05:00 PM",
      ],
      []
    );

  /* ---------------------------------------------------------------------- */
  /* Loading */
  /* ---------------------------------------------------------------------- */

  if (loading) {
    return (
      <DashboardSkeleton />
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Error */
  /* ---------------------------------------------------------------------- */

  if (error) {
    return (
      <DashboardEmpty
        title="Unable to load appointment details"
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
  /* Validation */
  /* ---------------------------------------------------------------------- */

  if (!agent) {
    return (
      <DashboardEmpty
        title="Agent Not Found"
        description="The selected agent could not be found."
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
      keyboardShouldPersistTaps="handled"
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
    >      {/* ------------------------------------------------------------------ */}
      {/* Header */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.header}>
        <Pressable
          style={[
            styles.backButton,
            {
              backgroundColor: colors.card,
              borderColor: colors.border,
            },
          ]}
          onPress={() => router.back()}
        >
          <MaterialCommunityIcons
            name="arrow-left"
            size={22}
            color={colors.text}
          />
        </Pressable>

        <View style={styles.headerContent}>
          <Text
            style={[
              styles.title,
              {
                color: colors.text,
              },
            ]}
          >
            Schedule Visit
          </Text>

          <Text
            style={[
              styles.subtitle,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Book a convenient time to
            inspect this property.
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Property Summary */}
      {/* ------------------------------------------------------------------ */}

      {property && (
        <View
          style={styles.section}
        >
          <Text
            style={[
              styles.sectionTitle,
              {
                color: colors.text,
              },
            ]}
          >
            Property
          </Text>

          <PropertyCard
            property={property}
            compact
            onPress={() =>
              router.push({
                pathname:
                  "/real-estate/property/[id]",
                params: {
                  id: property.id,
                },
              })
            }
          />
        </View>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Agent Summary */}
      {/* ------------------------------------------------------------------ */}

      <View style={styles.section}>
        <Text
          style={[
            styles.sectionTitle,
            {
              color: colors.text,
            },
          ]}
        >
          Your Agent
        </Text>

        <AgentCard
          agent={agent}
          onPress={() =>
            router.push({
              pathname:
                "/real-estate/agent/[id]",
              params: {
                id: agent.id,
              },
            })
          }
        />
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Appointment Overview */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={[
          styles.summaryCard,
          {
            backgroundColor:
              colors.card,
            borderColor:
              colors.border,
          },
        ]}
      >
        <View
          style={styles.summaryRow}
        >
          <MaterialCommunityIcons
            name="calendar-check"
            size={22}
            color={colors.primary}
          />

          <Text
            style={[
              styles.summaryLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Appointment Status
          </Text>

          <Text
            style={[
              styles.summaryValue,
              {
                color:
                  colors.primary,
              },
            ]}
          >
            Pending
          </Text>
        </View>

        <View
          style={
            styles.summaryDivider
          }
        />

        <View
          style={styles.summaryRow}
        >
          <MaterialCommunityIcons
            name="account-tie"
            size={22}
            color="#22C55E"
          />

          <Text
            style={[
              styles.summaryLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Agent
          </Text>

          <Text
            style={[
              styles.summaryValue,
              {
                color:
                  colors.text,
              },
            ]}
            numberOfLines={1}
          >
            {agent.name}
          </Text>
        </View>

        {property && (
          <>
            <View
              style={
                styles.summaryDivider
              }
            />

            <View
              style={
                styles.summaryRow
              }
            >
              <MaterialCommunityIcons
                name="home-city"
                size={22}
                color="#3B82F6"
              />

              <Text
                style={[
                  styles.summaryLabel,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Property
              </Text>

              <Text
                style={[
                  styles.summaryValue,
                  {
                    color:
                      colors.text,
                  },
                ]}
                numberOfLines={1}
              >
                {property.title}
              </Text>
            </View>

            <View
              style={
                styles.summaryDivider
              }
            />

            <View
              style={
                styles.summaryRow
              }
            >
              <MaterialCommunityIcons
                name="currency-ngn"
                size={22}
                color="#F59E0B"
              />

              <Text
                style={[
                  styles.summaryLabel,
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
                  styles.summaryValue,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                ₦
                {Number(
                  property.price ?? 0
                ).toLocaleString()}
              </Text>
            </View>

            <View
              style={
                styles.summaryDivider
              }
            />

            <View
              style={
                styles.summaryRow
              }
            >
              <MaterialCommunityIcons
                name="map-marker"
                size={22}
                color="#EF4444"
              />

              <Text
                style={[
                  styles.summaryLabel,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Location
              </Text>

              <Text
                style={[
                  styles.summaryValue,
                  {
                    color:
                      colors.text,
                  },
                ]}
                numberOfLines={1}
              >
                {property.city ||
                  property.address ||
                  "N/A"}
              </Text>
            </View>

            <View
              style={
                styles.summaryDivider
              }
            />

            <View
              style={
                styles.summaryRow
              }
            >
              <MaterialCommunityIcons
                name="office-building"
                size={22}
                color="#8B5CF6"
              />

              <Text
                style={[
                  styles.summaryLabel,
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
                  styles.summaryValue,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                {property.type ??
                  "Residential"}
              </Text>
            </View>
          </>
        )}
      </View>
            {/* ------------------------------------------------------------------ */}
      {/* Visit Date */}
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
          Select Visit Date
        </Text>

        <Text
          style={[
            styles.sectionDescription,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          Choose your preferred day for the
          property inspection.
        </Text>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={
            false
          }
          contentContainerStyle={
            styles.dateContainer
          }
        >
          {Array.from({ length: 14 }).map(
            (_, index) => {
              const date = new Date();

              date.setDate(
                date.getDate() + index
              );

              const value =
                date.toISOString();

              const selected =
                selectedDate === value;

              return (
                <Pressable
                  key={value}
                  style={[
                    styles.dateCard,
                    {
                      backgroundColor:
                        selected
                          ? colors.primary
                          : colors.card,

                      borderColor:
                        selected
                          ? colors.primary
                          : colors.border,
                    },
                  ]}
                  onPress={() =>
                    setSelectedDate(
                      value
                    )
                  }
                >
                  <Text
                    style={[
                      styles.dateWeekday,
                      {
                        color: selected
                          ? "#FFFFFF"
                          : colors.textSecondary,
                      },
                    ]}
                  >
                    {date.toLocaleDateString(
                      "en-US",
                      {
                        weekday:
                          "short",
                      }
                    )}
                  </Text>

                  <Text
                    style={[
                      styles.dateNumber,
                      {
                        color: selected
                          ? "#FFFFFF"
                          : colors.text,
                      },
                    ]}
                  >
                    {date.getDate()}
                  </Text>

                  <Text
                    style={[
                      styles.dateMonth,
                      {
                        color: selected
                          ? "#FFFFFF"
                          : colors.textSecondary,
                      },
                    ]}
                  >
                    {date.toLocaleDateString(
                      "en-US",
                      {
                        month:
                          "short",
                      }
                    )}
                  </Text>
                </Pressable>
              );
            }
          )}
        </ScrollView>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Available Time Slots */}
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
          Available Time Slots
        </Text>

        <Text
          style={[
            styles.sectionDescription,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          Select a convenient appointment
          time.
        </Text>

        <View style={styles.timeGrid}>
          {availableTimes.map(
            (time, index) => {
              const unavailable =
                index === 2 ||
                index === 6;

              const selected =
                selectedTime === time;

              return (
                <Pressable
                  key={time}
                  disabled={
                    unavailable
                  }
                  style={[
                    styles.timeCard,
                    {
                      backgroundColor:
                        unavailable
                          ? "#F3F4F6"
                          : selected
                          ? colors.primary
                          : colors.card,

                      borderColor:
                        unavailable
                          ? "#E5E7EB"
                          : selected
                          ? colors.primary
                          : colors.border,

                      opacity:
                        unavailable
                          ? 0.55
                          : 1,
                    },
                  ]}
                  onPress={() =>
                    setSelectedTime(
                      time
                    )
                  }
                >
                  <MaterialCommunityIcons
                    name={
                      unavailable
                        ? "clock-remove-outline"
                        : "clock-outline"
                    }
                    size={18}
                    color={
                      unavailable
                        ? "#9CA3AF"
                        : selected
                        ? "#FFFFFF"
                        : colors.primary
                    }
                  />

                  <Text
                    style={[
                      styles.timeText,
                      {
                        color:
                          unavailable
                            ? "#9CA3AF"
                            : selected
                            ? "#FFFFFF"
                            : colors.text,
                      },
                    ]}
                  >
                    {time}
                  </Text>
                </Pressable>
              );
            }
          )}
        </View>

        <View
          style={
            styles.legendContainer
          }
        >
          <View
            style={
              styles.legendItem
            }
          >
            <View
              style={[
                styles.legendDot,
                {
                  backgroundColor:
                    colors.primary,
                },
              ]}
            />

            <Text
              style={[
                styles.legendText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Available
            </Text>
          </View>

          <View
            style={
              styles.legendItem
            }
          >
            <View
              style={[
                styles.legendDot,
                {
                  backgroundColor:
                    "#D1D5DB",
                },
              ]}
            />

            <Text
              style={[
                styles.legendText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Unavailable
            </Text>
          </View>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Appointment Preview */}
      {/* ------------------------------------------------------------------ */}

      {selectedDate &&
        selectedTime && (
          <View
            style={[
              styles.previewCard,
              {
                backgroundColor:
                  colors.primary +
                  "10",
                borderColor:
                  colors.primary,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="calendar-check"
              size={28}
              color={
                colors.primary
              }
            />

            <View
              style={
                styles.previewContent
              }
            >
              <Text
                style={[
                  styles.previewTitle,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                Appointment Preview
              </Text>

              <Text
                style={[
                  styles.previewText,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                {new Date(
                  selectedDate
                ).toLocaleDateString(
                  "en-US",
                  {
                    weekday:
                      "long",
                    day: "numeric",
                    month:
                      "long",
                    year: "numeric",
                  }
                )}
              </Text>

              <Text
                style={[
                  styles.previewTime,
                  {
                    color:
                      colors.primary,
                  },
                ]}
              >
                {selectedTime}
              </Text>
            </View>
          </View>
        )}
              {/* ------------------------------------------------------------------ */}
      {/* Visit Type */}
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
          Visit Type
        </Text>

        <Text
          style={[
            styles.sectionDescription,
            {
              color: colors.textSecondary,
            },
          ]}
        >
          Select how you would like to inspect the
          property.
        </Text>

        <View style={styles.optionGrid}>
          <Pressable
            style={[
              styles.optionCard,
              {
                backgroundColor:
                  visitType === "physical"
                    ? colors.primary
                    : colors.card,

                borderColor:
                  visitType === "physical"
                    ? colors.primary
                    : colors.border,
              },
            ]}
            onPress={() =>
              setVisitType("physical")
            }
          >
            <MaterialCommunityIcons
              name="home-city"
              size={28}
              color={
                visitType === "physical"
                  ? "#FFFFFF"
                  : colors.primary
              }
            />

            <Text
              style={[
                styles.optionTitle,
                {
                  color:
                    visitType === "physical"
                      ? "#FFFFFF"
                      : colors.text,
                },
              ]}
            >
              Physical Visit
            </Text>

            <Text
              style={[
                styles.optionDescription,
                {
                  color:
                    visitType === "physical"
                      ? "#FFFFFF"
                      : colors.textSecondary,
                },
              ]}
            >
              Visit the property with the agent.
            </Text>
          </Pressable>

          <Pressable
            style={[
              styles.optionCard,
              {
                backgroundColor:
                  visitType === "virtual"
                    ? colors.primary
                    : colors.card,

                borderColor:
                  visitType === "virtual"
                    ? colors.primary
                    : colors.border,
              },
            ]}
            onPress={() =>
              setVisitType("virtual")
            }
          >
            <MaterialCommunityIcons
              name="video"
              size={28}
              color={
                visitType === "virtual"
                  ? "#FFFFFF"
                  : colors.primary
              }
            />

            <Text
              style={[
                styles.optionTitle,
                {
                  color:
                    visitType === "virtual"
                      ? "#FFFFFF"
                      : colors.text,
                },
              ]}
            >
              Virtual Tour
            </Text>

            <Text
              style={[
                styles.optionDescription,
                {
                  color:
                    visitType === "virtual"
                      ? "#FFFFFF"
                      : colors.textSecondary,
                },
              ]}
            >
              Join an online video walkthrough.
            </Text>
          </Pressable>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Number of Attendees */}
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
          Number of Attendees
        </Text>

        <View style={styles.attendeeRow}>
          <Pressable
            style={[
              styles.counterButton,
              {
                borderColor: colors.border,
              },
            ]}
            onPress={() =>
              setAttendees((prev) =>
                Math.max(1, prev - 1)
              )
            }
          >
            <MaterialCommunityIcons
              name="minus"
              size={22}
              color={colors.text}
            />
          </Pressable>

          <View style={styles.counterValue}>
            <Text
              style={[
                styles.counterText,
                {
                  color: colors.text,
                },
              ]}
            >
              {attendees}
            </Text>
          </View>

          <Pressable
            style={[
              styles.counterButton,
              {
                borderColor: colors.border,
              },
            ]}
            onPress={() =>
              setAttendees((prev) =>
                prev + 1
              )
            }
          >
            <MaterialCommunityIcons
              name="plus"
              size={22}
              color={colors.text}
            />
          </Pressable>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Contact Information */}
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
          Contact Information
        </Text>

        <TextInput
          style={[
            styles.input,
            {
              borderColor: colors.border,
              color: colors.text,
            },
          ]}
          placeholder="Full Name"
          placeholderTextColor={
            colors.textSecondary
          }
          value={fullName}
          onChangeText={setFullName}
        />

        <TextInput
          style={[
            styles.input,
            {
              borderColor: colors.border,
              color: colors.text,
            },
          ]}
          placeholder="Phone Number"
          placeholderTextColor={
            colors.textSecondary
          }
          keyboardType="phone-pad"
          value={phone}
          onChangeText={setPhone}
        />

        <TextInput
          style={[
            styles.input,
            {
              borderColor: colors.border,
              color: colors.text,
            },
          ]}
          placeholder="Email Address"
          placeholderTextColor={
            colors.textSecondary
          }
          keyboardType="email-address"
          autoCapitalize="none"
          value={email}
          onChangeText={setEmail}
        />

        {(fullName.trim() === "" ||
          phone.trim() === "" ||
          email.trim() === "") && (
          <View
            style={styles.validationRow}
          >
            <MaterialCommunityIcons
              name="alert-circle-outline"
              size={18}
              color="#F59E0B"
            />

            <Text
              style={[
                styles.validationText,
                {
                  color:
                    colors.textSecondary,
                },
              ]}
            >
              Please complete all contact
              information before submitting your
              appointment request.
            </Text>
          </View>
        )}
      </View>
            {/* ------------------------------------------------------------------ */}
      {/* Additional Notes */}
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
          Additional Notes
        </Text>

        <Text
          style={[
            styles.sectionDescription,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          Include any special requests or
          questions for the agent before your
          appointment.
        </Text>

        <TextInput
          style={[
            styles.notesInput,
            {
              color: colors.text,
              borderColor:
                colors.border,
            },
          ]}
          multiline
          numberOfLines={6}
          textAlignVertical="top"
          value={notes}
          onChangeText={setNotes}
          placeholder="Example: I'd like to inspect the parking area, verify the title documents, and discuss mortgage options..."
          placeholderTextColor={
            colors.textSecondary
          }
        />

        <Text
          style={[
            styles.characterCount,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          {notes.length}/500
        </Text>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Appointment Summary */}
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
          Appointment Summary
        </Text>

        <View style={styles.summaryRow}>
          <Text
            style={[
              styles.summaryLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Agent
          </Text>

          <Text
            style={[
              styles.summaryValue,
              {
                color: colors.text,
              },
            ]}
          >
            {agent.name}
          </Text>
        </View>

        <View
          style={
            styles.summaryDivider
          }
        />

        <View style={styles.summaryRow}>
          <Text
            style={[
              styles.summaryLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Visit Type
          </Text>

          <Text
            style={[
              styles.summaryValue,
              {
                color: colors.text,
              },
            ]}
          >
            {visitType ===
            "physical"
              ? "Physical Visit"
              : "Virtual Tour"}
          </Text>
        </View>

        <View
          style={
            styles.summaryDivider
          }
        />

        <View style={styles.summaryRow}>
          <Text
            style={[
              styles.summaryLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Date
          </Text>

          <Text
            style={[
              styles.summaryValue,
              {
                color: colors.text,
              },
            ]}
          >
            {selectedDate
              ? new Date(
                  selectedDate
                ).toLocaleDateString()
              : "Not Selected"}
          </Text>
        </View>

        <View
          style={
            styles.summaryDivider
          }
        />

        <View style={styles.summaryRow}>
          <Text
            style={[
              styles.summaryLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Time
          </Text>

          <Text
            style={[
              styles.summaryValue,
              {
                color: colors.text,
              },
            ]}
          >
            {selectedTime ??
              "Not Selected"}
          </Text>
        </View>

        <View
          style={
            styles.summaryDivider
          }
        />

        <View style={styles.summaryRow}>
          <Text
            style={[
              styles.summaryLabel,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Attendees
          </Text>

          <Text
            style={[
              styles.summaryValue,
              {
                color: colors.text,
              },
            ]}
          >
            {attendees}
          </Text>
        </View>

        {property && (
          <>
            <View
              style={
                styles.summaryDivider
              }
            />

            <View
              style={
                styles.summaryRow
              }
            >
              <Text
                style={[
                  styles.summaryLabel,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Property
              </Text>

              <Text
                style={[
                  styles.summaryValue,
                  {
                    color:
                      colors.text,
                    flex: 1,
                    textAlign:
                      "right",
                  },
                ]}
                numberOfLines={2}
              >
                {property.title}
              </Text>
            </View>
          </>
        )}

        <View
          style={[
            styles.noticeCard,
            {
              backgroundColor:
                colors.primary +
                "10",
            },
          ]}
        >
          <MaterialCommunityIcons
            name="information-outline"
            size={22}
            color={colors.primary}
          />

          <Text
            style={[
              styles.noticeText,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            Your appointment request will be sent
            to the agent for confirmation. You'll
            receive a notification once it has
            been accepted or rescheduled.
          </Text>
        </View>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Booking Checklist */}
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
          Before You Submit
        </Text>

        {[
          "Selected a preferred date",
          "Selected a preferred time",
          "Provided your contact details",
          "Reviewed the appointment summary",
        ].map((item) => (
          <View
            key={item}
            style={
              styles.checklistRow
            }
          >
            <MaterialCommunityIcons
              name="check-circle"
              size={20}
              color="#22C55E"
            />

            <Text
              style={[
                styles.checklistText,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {item}
            </Text>
          </View>
        ))}
      </View>
            {/* ------------------------------------------------------------------ */}
      {/* Submit Appointment */}
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
        <Pressable
          style={[
            styles.submitButton,
            {
              backgroundColor:
                submitting
                  ? colors.border
                  : colors.primary,
            },
          ]}
          disabled={submitting}
          onPress={async () => {
            /* ------------------------------------------------------------ */
            /* Validation */
            /* ------------------------------------------------------------ */

            if (!selectedDate) {
              Alert.alert(
                "Select Date",
                "Please choose a preferred visit date."
              );

              return;
            }

            if (!selectedTime) {
              Alert.alert(
                "Select Time",
                "Please choose an available time slot."
              );

              return;
            }

            if (!fullName.trim()) {
              Alert.alert(
                "Full Name Required",
                "Please enter your full name."
              );

              return;
            }

            if (!phone.trim()) {
              Alert.alert(
                "Phone Number Required",
                "Please enter your phone number."
              );

              return;
            }

            if (!email.trim()) {
              Alert.alert(
                "Email Required",
                "Please enter your email address."
              );

              return;
            }

            try {
              setSubmitting(true);

              /* ---------------------------------------------------------- */
              /* TODO:
               *
               * Replace this timeout with your GraphQL mutation.
               *
               * await schedulePropertyVisit({
               *   propertyId,
               *   agentId,
               *   date: selectedDate,
               *   time: selectedTime,
               *   visitType,
               *   attendees,
               *   fullName,
               *   phone,
               *   email,
               *   notes,
               * });
               * ---------------------------------------------------------- */

              await new Promise(
                (resolve) =>
                  setTimeout(
                    resolve,
                    1800
                  )
              );

              Alert.alert(
                "Visit Scheduled",
                "Your appointment request has been sent successfully. The agent will contact you after confirming availability.",
                [
                  {
                    text: "OK",
                    onPress: () => {
                      router.replace(
                        "/real-estate"
                      );
                    },
                  },
                ]
              );
            } catch (err) {
              Alert.alert(
                "Booking Failed",
                err?.message ||
                  "Unable to schedule your visit. Please try again."
              );
            } finally {
              setSubmitting(false);
            }
          }}
        >
          <MaterialCommunityIcons
            name={
              submitting
                ? "loading"
                : "calendar-check"
            }
            size={22}
            color="#FFFFFF"
          />

          <Text
            style={
              styles.submitButtonText
            }
          >
            {submitting
              ? "Submitting..."
              : "Schedule Visit"}
          </Text>
        </Pressable>

        <Text
          style={[
            styles.submitHint,
            {
              color:
                colors.textSecondary,
            },
          ]}
        >
          By submitting this request you agree
          that the agent may contact you via
          phone, SMS or email regarding this
          appointment.
        </Text>
      </View>

      {/* ------------------------------------------------------------------ */}
      {/* Bottom Spacer */}
      {/* ------------------------------------------------------------------ */}

      <View
        style={{
          height: 48,
        }}
      />
    </ScrollView>
  );
});

ScheduleVisit.displayName =
  "ScheduleVisit";

/* -------------------------------------------------------------------------- */
/* Export */
/* -------------------------------------------------------------------------- */

export default ScheduleVisit;

/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  content: {
    padding: 20,
    paddingBottom: 60,
  },

  /* ---------------------------------------------------------------------- */
  /* Header */
  /* ---------------------------------------------------------------------- */

  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 24,
  },

  backButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 1,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 16,
  },

  headerContent: {
    flex: 1,
  },

  title: {
    fontSize: 28,
    fontWeight: "700",
  },

  subtitle: {
    marginTop: 4,
    fontSize: 15,
    lineHeight: 22,
  },

  /* ---------------------------------------------------------------------- */
  /* Sections */
  /* ---------------------------------------------------------------------- */

  section: {
    marginBottom: 24,
    padding: 20,
    borderRadius: 18,
    borderWidth: 1,
  },

  sectionTitle: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 8,
  },

  sectionDescription: {
    fontSize: 14,
    lineHeight: 22,
    marginBottom: 18,
  },

  /* ---------------------------------------------------------------------- */
  /* Summary */
  /* ---------------------------------------------------------------------- */

  summaryCard: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 20,
    marginBottom: 24,
  },

  summaryRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
  },

  summaryLabel: {
    flex: 1,
    marginLeft: 12,
    fontSize: 15,
  },

  summaryValue: {
    fontWeight: "700",
    fontSize: 15,
    maxWidth: "55%",
  },

  summaryDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: "#E5E7EB",
  },

  /* ---------------------------------------------------------------------- */
  /* Date Picker */
  /* ---------------------------------------------------------------------- */

  dateContainer: {
    paddingVertical: 6,
    paddingRight: 12,
  },

  dateCard: {
    width: 72,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: "center",
    paddingVertical: 14,
    marginRight: 12,
  },

  dateWeekday: {
    fontSize: 13,
  },

  dateNumber: {
    fontSize: 26,
    fontWeight: "700",
    marginVertical: 6,
  },

  dateMonth: {
    fontSize: 13,
  },

  /* ---------------------------------------------------------------------- */
  /* Time Slots */
  /* ---------------------------------------------------------------------- */

  timeGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
  },

  timeCard: {
    width: "48%",
    borderRadius: 14,
    borderWidth: 1,
    paddingVertical: 14,
    alignItems: "center",
    marginBottom: 14,
    flexDirection: "row",
    justifyContent: "center",
  },

  timeText: {
    marginLeft: 8,
    fontWeight: "600",
    fontSize: 14,
  },

  legendContainer: {
    flexDirection: "row",
    marginTop: 8,
  },

  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    marginRight: 20,
  },

  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 8,
  },

  legendText: {
    fontSize: 13,
  },

  /* ---------------------------------------------------------------------- */
  /* Preview */
  /* ---------------------------------------------------------------------- */

  previewCard: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 16,
    borderWidth: 1,
    padding: 18,
    marginBottom: 24,
  },

  previewContent: {
    flex: 1,
    marginLeft: 16,
  },

  previewTitle: {
    fontSize: 17,
    fontWeight: "700",
  },

  previewText: {
    marginTop: 6,
    fontSize: 14,
  },

  previewTime: {
    marginTop: 6,
    fontWeight: "700",
    fontSize: 16,
  },

  /* ---------------------------------------------------------------------- */
  /* Visit Type */
  /* ---------------------------------------------------------------------- */

  optionGrid: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  optionCard: {
    width: "48%",
    borderRadius: 16,
    borderWidth: 1,
    padding: 18,
    alignItems: "center",
  },

  optionTitle: {
    marginTop: 12,
    fontSize: 16,
    fontWeight: "700",
    textAlign: "center",
  },

  optionDescription: {
    marginTop: 8,
    fontSize: 13,
    textAlign: "center",
    lineHeight: 20,
  },

  /* ---------------------------------------------------------------------- */
  /* Attendees */
  /* ---------------------------------------------------------------------- */

  attendeeRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },

  counterButton: {
    width: 52,
    height: 52,
    borderWidth: 1,
    borderRadius: 14,
    justifyContent: "center",
    alignItems: "center",
  },

  counterValue: {
    width: 90,
    alignItems: "center",
  },

  counterText: {
    fontSize: 28,
    fontWeight: "700",
  },

  /* ---------------------------------------------------------------------- */
  /* Inputs */
  /* ---------------------------------------------------------------------- */

  input: {
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 16,
    height: 54,
    marginBottom: 16,
    fontSize: 15,
  },

  notesInput: {
    borderWidth: 1,
    borderRadius: 16,
    minHeight: 140,
    padding: 16,
    fontSize: 15,
  },

  characterCount: {
    marginTop: 10,
    textAlign: "right",
    fontSize: 12,
  },

  validationRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 8,
  },

  validationText: {
    flex: 1,
    marginLeft: 8,
    fontSize: 13,
    lineHeight: 20,
  },

  /* ---------------------------------------------------------------------- */
  /* Notice */
  /* ---------------------------------------------------------------------- */

  noticeCard: {
    flexDirection: "row",
    padding: 16,
    borderRadius: 14,
    marginTop: 20,
  },

  noticeText: {
    flex: 1,
    marginLeft: 12,
    lineHeight: 22,
    fontSize: 14,
  },

  /* ---------------------------------------------------------------------- */
  /* Checklist */
  /* ---------------------------------------------------------------------- */

  checklistRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 14,
  },

  checklistText: {
    marginLeft: 10,
    fontSize: 15,
  },

  /* ---------------------------------------------------------------------- */
  /* Submit */
  /* ---------------------------------------------------------------------- */

  submitButton: {
    height: 58,
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
  },

  submitButtonText: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "700",
    marginLeft: 10,
  },

  submitHint: {
    textAlign: "center",
    marginTop: 16,
    lineHeight: 22,
    fontSize: 13,
  },
});

/* -------------------------------------------------------------------------- */
/* Export */
/* -------------------------------------------------------------------------- */

export default ScheduleVisit;