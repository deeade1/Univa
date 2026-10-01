/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductSpecifications.jsx                                                  */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useState,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
  LayoutAnimation,
  Platform,
  UIManager,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Enable Android Layout Animation                                            */
/* -------------------------------------------------------------------------- */

if (
  Platform.OS ===
    "android" &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(
    true
  );
}

/* -------------------------------------------------------------------------- */
/* Specification Row                                                          */
/* -------------------------------------------------------------------------- */

const SpecificationRow = memo(
  ({
    specification,
    colors,
  }) => (
    <View
      style={[
        styles.specRow,
        {
          borderBottomColor:
            colors.border,
        },
      ]}
    >
      <Text
        style={[
          styles.specLabel,
          {
            color:
              colors.textSecondary,
          },
        ]}
      >
        {specification.label}
      </Text>

      <Text
        style={[
          styles.specValue,
          {
            color:
              colors.text,
          },
        ]}
      >
        {specification.value}
      </Text>
    </View>
  )
);

SpecificationRow.displayName =
  "SpecificationRow";

/* -------------------------------------------------------------------------- */
/* Specification Section                                                      */
/* -------------------------------------------------------------------------- */

const SpecificationSection =
  memo(
    ({
      section,
      expanded,
      colors,
      onToggle,
    }) => (
      <View
        style={styles.section}
      >
        <Pressable
          onPress={() =>
            onToggle(
              section.title
            )
          }
          style={
            styles.sectionHeader
          }
        >
          <View
            style={
              styles.sectionLeft
            }
          >
            <MaterialCommunityIcons
              name={
                section.icon ??
                "format-list-bulleted"
              }
              size={20}
              color={
                colors.primary
              }
            />

            <Text
              style={[
                styles.sectionTitle,
                {
                  color:
                    colors.text,
                },
              ]}
            >
              {section.title}
            </Text>
          </View>

          <MaterialCommunityIcons
            name={
              expanded
                ? "chevron-up"
                : "chevron-down"
            }
            size={20}
            color={
              colors.textSecondary
            }
          />
        </Pressable>

        {expanded &&
          section.items?.map(
            (
              item,
              index
            ) => (
              <SpecificationRow
                key={
                  item.id ??
                  item.label ??
                  index
                }
                specification={
                  item
                }
                colors={colors}
              />
            )
          )}
      </View>
    )
  );

SpecificationSection.displayName =
  "SpecificationSection";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductSpecifications =
  memo(
    ({
      product,

      specifications = [],

      title =
        "Specifications",

      showHeader = true,

      defaultExpanded =
        true,

      onViewAll,

      style,
    }) => {
      const { colors } =
        theme;

      /* ------------------------------------------------------------------ */
      /* Data                                                               */
      /* ------------------------------------------------------------------ */

      const sections =
        useMemo(() => {
          if (
            specifications.length >
            0
          ) {
            return specifications;
          }

          return (
            product
              ?.specifications ??
            []
          );
        }, [
          specifications,
          product,
        ]);

      const [
        expandedSections,
        setExpandedSections,
      ] = useState(() => {
        if (
          !defaultExpanded
        ) {
          return {};
        }

        return sections.reduce(
          (
            acc,
            section
          ) => {
            acc[
              section.title
            ] = true;

            return acc;
          },
          {}
        );
      });

      const toggleSection =
        useCallback(
          (title) => {
            LayoutAnimation.configureNext(
              LayoutAnimation.Presets
                .easeInEaseOut
            );

            setExpandedSections(
              (
                previous
              ) => ({
                ...previous,
                [title]:
                  !previous[
                    title
                  ],
              })
            );
          },
          []
        );

      const handleViewAll =
        useCallback(() => {
          onViewAll?.(
            sections
          );
        }, [
          onViewAll,
          sections,
        ]);

      return (
        <View
          style={[
            styles.container,
            {
              backgroundColor:
                colors.card,

              borderColor:
                colors.border,
            },
            style,
          ]}
        >
          {/* -------------------------------------------------------------- */}
          {/* Header                                                         */}
          {/* -------------------------------------------------------------- */}

          {showHeader && (
            <View
              style={
                styles.header
              }
            >
              <View
                style={
                  styles.headerLeft
                }
              >
                <MaterialCommunityIcons
                  name="clipboard-text-outline"
                  size={22}
                  color={
                    colors.primary
                  }
                />

                <Text
                  style={[
                    styles.headerTitle,
                    {
                      color:
                        colors.text,
                    },
                  ]}
                >
                  {title}
                </Text>
              </View>
                        {/* -------------------------------------------------------------- */}
          {/* View All                                                       */}
          {/* -------------------------------------------------------------- */}

          {sections.length > 0 && (
            <Pressable
              onPress={
                handleViewAll
              }
              style={
                styles.viewAllButton
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
                size={20}
                color={
                  colors.primary
                }
              />
            </Pressable>
          )}
            </View>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Specification Sections                                         */}
          {/* -------------------------------------------------------------- */}

          {sections.length >
          0 ? (
            sections.map(
              (
                section,
                index
              ) => (
                <SpecificationSection
                  key={
                    section.id ??
                    section.title ??
                    index
                  }
                  section={
                    section
                  }
                  expanded={
                    expandedSections[
                      section
                        .title
                    ]
                  }
                  colors={colors}
                  onToggle={
                    toggleSection
                  }
                />
              )
            )
          ) : (
            /* ---------------------------------------------------------- */
            /* Empty State                                                */
            /* ---------------------------------------------------------- */

            <View
              style={
                styles.emptyContainer
              }
            >
              <MaterialCommunityIcons
                name="clipboard-remove-outline"
                size={56}
                color={
                  colors.border
                }
              />

              <Text
                style={[
                  styles.emptyTitle,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                No Specifications
              </Text>

              <Text
                style={[
                  styles.emptyDescription,
                  {
                    color:
                      colors
                        .textSecondary,
                  },
                ]}
              >
                Technical
                specifications
                haven't been
                provided for this
                product yet.
              </Text>
            </View>
          )}
                    {/* -------------------------------------------------------------- */}
          {/* Specifications Summary                                         */}
          {/* -------------------------------------------------------------- */}

          {sections.length > 0 && (
            <View
              style={[
                styles.summaryContainer,
                {
                  borderTopColor:
                    colors.border,
                },
              ]}
            >
              <MaterialCommunityIcons
                name="information-outline"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.summaryText,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                {sections.length} specification
                section
                {sections.length !== 1
                  ? "s"
                  : ""}{" "}
                containing{" "}
                <Text
                  style={[
                    styles.summaryCount,
                    {
                      color:
                        colors.text,
                      },
                    ]}
                >
                  {sections.reduce(
                    (
                      total,
                      section
                    ) =>
                      total +
                      (
                        section
                          .items
                          ?.length ??
                        0
                      ),
                    0
                  )}
                </Text>{" "}
                technical
                specification
                {sections.reduce(
                  (
                    total,
                    section
                  ) =>
                    total +
                    (
                      section
                        .items
                        ?.length ??
                      0
                    ),
                  0
                ) !== 1
                  ? "s"
                  : ""}.
              </Text>
            </View>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Technical Information Footer                                   */}
          {/* -------------------------------------------------------------- */}

          <View
            style={[
              styles.footer,
              {
                borderTopColor:
                  colors.border,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="shield-check-outline"
              size={16}
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
              Specifications are
              supplied by the
              manufacturer and may
              vary slightly between
              product revisions.
              Please verify critical
              requirements before
              purchasing.
            </Text>
          </View>
        </View>
      );
    }
);

ProductSpecifications.displayName =
  "ProductSpecifications";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const specificationItemShape =
  PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    label:
      PropTypes.string
        .isRequired,

    value:
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
        PropTypes.bool,
      ]).isRequired,
  });

const specificationSectionShape =
  PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    title:
      PropTypes.string
        .isRequired,

    icon:
      PropTypes.string,

    items:
      PropTypes.arrayOf(
        specificationItemShape
      ),
  });

const productShape =
  PropTypes.shape({
    specifications:
      PropTypes.arrayOf(
        specificationSectionShape
      ),
  });

SpecificationRow.propTypes = {
  specification:
    specificationItemShape
      .isRequired,

  colors:
    PropTypes.object
      .isRequired,
};

SpecificationSection.propTypes =
  {
    section:
      specificationSectionShape
        .isRequired,

    expanded:
      PropTypes.bool,

    colors:
      PropTypes.object
        .isRequired,

    onToggle:
      PropTypes.func
        .isRequired,
  };

SpecificationSection.defaultProps =
  {
    expanded: false,
  };

ProductSpecifications.propTypes =
  {
    product:
      productShape,

    specifications:
      PropTypes.arrayOf(
        specificationSectionShape
      ),

    title:
      PropTypes.string,

    showHeader:
      PropTypes.bool,

    defaultExpanded:
      PropTypes.bool,

    onViewAll:
      PropTypes.func,

    style:
      PropTypes.oneOfType([
        PropTypes.object,
        PropTypes.array,
      ]),
  };

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ProductSpecifications.defaultProps =
  {
    product: null,

    specifications: [],

    title:
      "Specifications",

    showHeader: true,

    defaultExpanded: true,

    onViewAll: null,

    style: null,
  };

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      borderWidth: 1,

      borderRadius: 20,

      padding: 18,

      marginVertical: 16,
    },

    /* ------------------------------------------------------------------ */
    /* Header                                                             */
    /* ------------------------------------------------------------------ */

    header: {
      flexDirection: "row",

      alignItems: "center",

      justifyContent:
        "space-between",

      marginBottom: 18,
    },

    headerLeft: {
      flexDirection: "row",

      alignItems: "center",

      flex: 1,
    },

    headerTitle: {
      marginLeft: 10,

      fontSize: 18,

      fontWeight: "700",
    },

    viewAllButton: {
      flexDirection: "row",

      alignItems: "center",
    },

    viewAllText: {
      marginRight: 4,

      fontSize: 14,

      fontWeight: "600",
    },

    /* ------------------------------------------------------------------ */
    /* Sections                                                           */
    /* ------------------------------------------------------------------ */

    section: {
      marginBottom: 14,

      borderRadius: 14,

      overflow: "hidden",
    },

    sectionHeader: {
      flexDirection: "row",

      justifyContent:
        "space-between",

      alignItems: "center",

      paddingVertical: 14,
    },

    sectionLeft: {
      flexDirection: "row",

      alignItems: "center",

      flex: 1,
    },

    sectionTitle: {
      marginLeft: 10,

      fontSize: 16,

      fontWeight: "700",
    },

    /* ------------------------------------------------------------------ */
    /* Specification Row                                                  */
    /* ------------------------------------------------------------------ */

    specRow: {
      flexDirection: "row",

      justifyContent:
        "space-between",

      alignItems:
        "flex-start",

      borderBottomWidth: 1,

      paddingVertical: 12,
    },

    specLabel: {
      flex: 1,

      marginRight: 16,

      fontSize: 14,
    },

    specValue: {
      flex: 1,

      textAlign: "right",

      fontSize: 14,

      fontWeight: "600",
    },

    /* ------------------------------------------------------------------ */
    /* Empty State                                                        */
    /* ------------------------------------------------------------------ */

    emptyContainer: {
      alignItems: "center",

      justifyContent:
        "center",

      paddingVertical: 40,
    },

    emptyTitle: {
      marginTop: 16,

      fontSize: 16,

      fontWeight: "700",
    },

    emptyDescription: {
      marginTop: 8,

      textAlign: "center",

      fontSize: 14,

      lineHeight: 22,

      maxWidth: 280,
    },

    /* ------------------------------------------------------------------ */
    /* Summary                                                            */
    /* ------------------------------------------------------------------ */

    summaryContainer: {
      flexDirection: "row",

      alignItems: "flex-start",

      borderTopWidth: 1,

      marginTop: 20,

      paddingTop: 16,
    },

    summaryText: {
      flex: 1,

      marginLeft: 10,

      fontSize: 13,

      lineHeight: 20,
    },

    summaryCount: {
      fontWeight: "700",
    },

    /* ------------------------------------------------------------------ */
    /* Footer                                                             */
    /* ------------------------------------------------------------------ */

    footer: {
      flexDirection: "row",

      alignItems: "flex-start",

      borderTopWidth: 1,

      marginTop: 16,

      paddingTop: 16,
    },

    footerText: {
      flex: 1,

      marginLeft: 8,

      fontSize: 12,

      lineHeight: 18,
    },
  });

export default ProductSpecifications;