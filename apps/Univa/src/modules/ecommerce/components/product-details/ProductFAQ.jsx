/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductFAQ.jsx                                                             */
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
  Platform.OS === "android" &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(
    true
  );
}

/* -------------------------------------------------------------------------- */
/* FAQ Item                                                                   */
/* -------------------------------------------------------------------------- */

const FAQItem = memo(
  ({
    item,
    expanded,
    colors,
    onToggle,
  }) => (
    <View
      style={[
        styles.faqItem,
        {
          borderBottomColor:
            colors.border,
        },
      ]}
    >
      <Pressable
        onPress={() =>
          onToggle(item.id)
        }
        style={
          styles.questionContainer
        }
      >
        <Text
          style={[
            styles.question,
            {
              color:
                colors.text,
            },
          ]}
        >
          {item.question}
        </Text>

        <MaterialCommunityIcons
          name={
            expanded
              ? "minus-circle-outline"
              : "plus-circle-outline"
          }
          size={22}
          color={
            colors.primary
          }
        />
      </Pressable>

      {expanded && (
        <View
          style={
            styles.answerContainer
          }
        >
          <Text
            style={[
              styles.answer,
              {
                color:
                  colors.textSecondary,
              },
            ]}
          >
            {item.answer}
          </Text>
        </View>
      )}
    </View>
  )
);

FAQItem.displayName =
  "FAQItem";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductFAQ = memo(
  ({
    product,

    faqs = [],

    title =
      "Frequently Asked Questions",

    showHeader = true,

    allowMultipleOpen = false,

    onViewAll,

    style,
  }) => {
    const { colors } =
      theme;

    /* ---------------------------------------------------------------------- */
    /* FAQ Data                                                               */
    /* ---------------------------------------------------------------------- */

    const items =
      useMemo(() => {
        if (
          faqs.length > 0
        ) {
          return faqs;
        }

        return (
          product?.faqs ??
          []
        );
      }, [
        faqs,
        product,
      ]);

    const [
      expandedItems,
      setExpandedItems,
    ] = useState({});

    const toggleFAQ =
      useCallback(
        (id) => {
          LayoutAnimation.configureNext(
            LayoutAnimation
              .Presets
              .easeInEaseOut
          );

          setExpandedItems(
            (previous) => {
              if (
                allowMultipleOpen
              ) {
                return {
                  ...previous,
                  [id]:
                    !previous[id],
                };
              }

              return previous[id]
                ? {}
                : {
                    [id]: true,
                  };
            }
          );
        },
        [allowMultipleOpen]
      );

    const handleViewAll =
      useCallback(() => {
        onViewAll?.(
          items
        );
      }, [
        items,
        onViewAll,
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
                name="frequently-asked-questions"
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

          {items.length > 0 && (
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
        {/* FAQ List                                                       */}
        {/* -------------------------------------------------------------- */}

        {items.length > 0 ? (
          items.map(
            (
              item,
              index
            ) => (
              <FAQItem
                key={
                  item.id ??
                  index
                }
                item={item}
                expanded={
                  !!expandedItems[
                    item.id
                  ]
                }
                colors={colors}
                onToggle={
                  toggleFAQ
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
              name="comment-question-outline"
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
              No Questions Yet
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
                Frequently asked
                questions have not
                been added for this
                product yet.
              </Text>
            </View>
          )}
                    {/* -------------------------------------------------------------- */}
          {/* FAQ Summary                                                    */}
          {/* -------------------------------------------------------------- */}

          {items.length > 0 && (
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
                {items.length} frequently
                asked question
                {items.length !== 1
                  ? "s"
                  : ""}{" "}
                answered to help
                you make an informed
                purchase decision.
              </Text>
            </View>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Need More Help?                                                */}
          {/* -------------------------------------------------------------- */}

          <View
            style={[
              styles.supportCard,
              {
                backgroundColor:
                  colors.background,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="headset"
              size={24}
              color={
                colors.primary
              }
            />

            <View
              style={
                styles.supportContent
              }
            >
              <Text
                style={[
                  styles.supportTitle,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                Didn't find your answer?
              </Text>

              <Text
                style={[
                  styles.supportDescription,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Contact the seller
                or customer support
                for additional
                product information
                before placing
                your order.
              </Text>

              <Pressable
                style={[
                  styles.supportButton,
                  {
                    backgroundColor:
                      colors.primary,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name="message-text-outline"
                  size={18}
                  color="#FFFFFF"
                />

                <Text
                  style={
                    styles.supportButtonText
                  }
                >
                  Contact Seller
                </Text>
              </Pressable>
            </View>
          </View>

          {/* -------------------------------------------------------------- */}
          {/* Information Footer                                             */}
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
              Answers are provided
              by the seller or
              manufacturer and may
              change as products
              are updated.
            </Text>
          </View>
        </View>
      );
    }
);

ProductFAQ.displayName =
  "ProductFAQ";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const faqShape = PropTypes.shape({
  id: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  question:
    PropTypes.string
      .isRequired,

  answer:
    PropTypes.string
      .isRequired,
});

const productShape =
  PropTypes.shape({
    faqs:
      PropTypes.arrayOf(
        faqShape
      ),
  });

FAQItem.propTypes = {
  item: faqShape.isRequired,

  expanded:
    PropTypes.bool,

  colors:
    PropTypes.object
      .isRequired,

  onToggle:
    PropTypes.func
      .isRequired,
};

FAQItem.defaultProps = {
  expanded: false,
};

ProductFAQ.propTypes = {
  product:
    productShape,

  faqs:
    PropTypes.arrayOf(
      faqShape
    ),

  title:
    PropTypes.string,

  showHeader:
    PropTypes.bool,

  allowMultipleOpen:
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

ProductFAQ.defaultProps = {
  product: null,

  faqs: [],

  title:
    "Frequently Asked Questions",

  showHeader: true,

  allowMultipleOpen: false,

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

      justifyContent:
        "space-between",

      alignItems: "center",

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
    /* FAQ Item                                                           */
    /* ------------------------------------------------------------------ */

    faqItem: {
      borderBottomWidth: 1,

      paddingVertical: 14,
    },

    questionContainer: {
      flexDirection: "row",

      justifyContent:
        "space-between",

      alignItems: "flex-start",
    },

    question: {
      flex: 1,

      marginRight: 12,

      fontSize: 15,

      fontWeight: "700",

      lineHeight: 22,
    },

    answerContainer: {
      marginTop: 14,

      paddingLeft: 4,
    },

    answer: {
      fontSize: 14,

      lineHeight: 22,
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

    /* ------------------------------------------------------------------ */
    /* Support Card                                                       */
    /* ------------------------------------------------------------------ */

    supportCard: {
      flexDirection: "row",

      alignItems: "flex-start",

      borderRadius: 16,

      padding: 16,

      marginTop: 18,
    },

    supportContent: {
      flex: 1,

      marginLeft: 14,
    },

    supportTitle: {
      fontSize: 16,

      fontWeight: "700",
    },

    supportDescription: {
      marginTop: 6,

      fontSize: 13,

      lineHeight: 20,
    },

    supportButton: {
      alignSelf: "flex-start",

      flexDirection: "row",

      alignItems: "center",

      borderRadius: 10,

      paddingHorizontal: 16,

      paddingVertical: 10,

      marginTop: 14,
    },

    supportButtonText: {
      color: "#FFFFFF",

      fontSize: 14,

      fontWeight: "700",

      marginLeft: 8,
    },

    /* ------------------------------------------------------------------ */
    /* Footer                                                             */
    /* ------------------------------------------------------------------ */

    footer: {
      flexDirection: "row",

      alignItems: "flex-start",

      borderTopWidth: 1,

      marginTop: 18,

      paddingTop: 16,
    },

    footerText: {
      flex: 1,

      marginLeft: 8,

      fontSize: 12,

      lineHeight: 18,
    },
  });

export default ProductFAQ;