/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductTabs.jsx                                                            */
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
  ScrollView,
  StyleSheet,
} from "react-native";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Product Detail Components                                                  */
/* -------------------------------------------------------------------------- */

import ProductDescription from "../products/ProductDescription";
import SpecificationTable from "../products/SpecificationTable";
import ReviewsPreview from "../products/ReviewsPreview";
import QuestionsAndAnswers from "../products/QuestionsAndAnswers";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductTabs = memo(
  ({
    product,

    initialTab = "description",

    showDescription = true,

    showSpecifications = true,

    showReviews = true,

    showQuestions = true,

    onTabChange,

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Active Tab                                                             */
    /* ---------------------------------------------------------------------- */

    const [
      activeTab,
      setActiveTab,
    ] = useState(
      initialTab
    );

    /* ---------------------------------------------------------------------- */
    /* Tabs                                                                   */
    /* ---------------------------------------------------------------------- */

    const tabs = useMemo(() => {
      const items = [];

      if (showDescription) {
        items.push({
          key: "description",
          label:
            "Description",
        });
      }

      if (
        showSpecifications
      ) {
        items.push({
          key:
            "specifications",
          label:
            "Specifications",
        });
      }

      if (showReviews) {
        items.push({
          key: "reviews",
          label: `Reviews (${
            product
              ?.reviewCount ??
            0
          })`,
        });
      }

      if (
        showQuestions
      ) {
        items.push({
          key: "questions",
          label: `Q&A (${
            product
              ?.questionCount ??
            0
          })`,
        });
      }

      return items;
    }, [
      showDescription,
      showSpecifications,
      showReviews,
      showQuestions,
      product,
    ]);

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleTabPress =
      useCallback(
        (tabKey) => {
          setActiveTab(
            tabKey
          );

          onTabChange?.(
            tabKey
          );
        },
        [onTabChange]
      );

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

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
        {/* Tab Navigation                                                 */}
        {/* -------------------------------------------------------------- */}

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={
            styles.tabsContainer
          }
        >
          {tabs.map((tab) => {
            const isActive =
              activeTab === tab.key;

            return (
              <Pressable
                key={tab.key}
                accessibilityRole="button"
                accessibilityState={{
                  selected:
                    isActive,
                }}
                accessibilityLabel={
                  tab.label
                }
                onPress={() =>
                  handleTabPress(
                    tab.key
                  )
                }
                style={[
                  styles.tab,
                  {
                    borderBottomColor:
                      isActive
                        ? colors.primary
                        : "transparent",
                  },
                ]}
              >
                <Text
                  style={[
                    styles.tabLabel,
                    {
                      color:
                        isActive
                          ? colors.primary
                          : colors.textSecondary,

                      fontWeight:
                        isActive
                          ? "700"
                          : "500",
                    },
                  ]}
                >
                  {tab.label}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>

        {/* -------------------------------------------------------------- */}
        {/* Divider                                                        */}
        {/* -------------------------------------------------------------- */}

        <View
          style={[
            styles.divider,
            {
              backgroundColor:
                colors.border,
            },
          ]}
        />

        {/* -------------------------------------------------------------- */}
        {/* Tab Content                                                    */}
        {/* -------------------------------------------------------------- */}

        <View
          style={styles.content}
        >
          {/* ---------------------------------------------------------- */}
          {/* Description                                                */}
          {/* ---------------------------------------------------------- */}

          {activeTab ===
            "description" && (
            <ProductDescription
              description={
                product?.description
              }
              features={
                product?.features
              }
              highlights={
                product?.highlights
              }
              specifications={
                product?.specifications
              }
            />
          )}

          {/* ---------------------------------------------------------- */}
          {/* Specifications                                             */}
          {/* ---------------------------------------------------------- */}

          {activeTab ===
            "specifications" && (
            <SpecificationTable
              specifications={
                product?.specifications ??
                []
              }
              attributes={
                product?.attributes
              }
            />
          )}

          {/* ---------------------------------------------------------- */}
          {/* Reviews                                                    */}
          {/* ---------------------------------------------------------- */}

          {activeTab ===
            "reviews" && (
            <ReviewsPreview
              productId={
                product?.id
              }
              reviews={
                product?.reviews ??
                []
              }
              averageRating={
                product?.rating
              }
              reviewCount={
                product?.reviewCount
              }
              showViewAll
            />
          )}

          {/* ---------------------------------------------------------- */}
          {/* Questions & Answers                                        */}
          {/* ---------------------------------------------------------- */}

          {activeTab ===
            "questions" && (
            <QuestionsAndAnswers
              productId={
                product?.id
              }
              questions={
                product?.questions ??
                []
              }
              questionCount={
                product?.questionCount
              }
              showAskQuestion
            />
          )}
        </View>
      </View>
    );
  }
);

ProductTabs.displayName =
  "ProductTabs";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductTabs.propTypes = {
  /**
   * Product object
   */
  product: PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    description:
      PropTypes.string,

    features:
      PropTypes.array,

    highlights:
      PropTypes.array,

    specifications:
      PropTypes.array,

    attributes:
      PropTypes.object,

    reviews:
      PropTypes.array,

    reviewCount:
      PropTypes.number,

    rating:
      PropTypes.number,

    questions:
      PropTypes.array,

    questionCount:
      PropTypes.number,
  }),

  /**
   * Default selected tab
   */
  initialTab:
    PropTypes.oneOf([
      "description",
      "specifications",
      "reviews",
      "questions",
    ]),

  showDescription:
    PropTypes.bool,

  showSpecifications:
    PropTypes.bool,

  showReviews:
    PropTypes.bool,

  showQuestions:
    PropTypes.bool,

  /**
   * Called whenever a tab changes
   */
  onTabChange:
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

ProductTabs.defaultProps = {
  product: null,

  initialTab:
    "description",

  showDescription: true,

  showSpecifications: true,

  showReviews: true,

  showQuestions: true,

  onTabChange: null,

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

      overflow: "hidden",

      marginVertical: 16,
    },

    /* ------------------------------------------------------------------ */
    /* Tabs                                                               */
    /* ------------------------------------------------------------------ */

    tabsContainer: {
      paddingHorizontal: 16,

      minHeight: 56,

      alignItems: "center",
    },

    tab: {
      justifyContent:
        "center",

      alignItems:
        "center",

      paddingHorizontal: 18,

      paddingVertical: 16,

      marginRight: 8,

      borderBottomWidth: 3,
    },

    tabLabel: {
      fontSize: 14,

      textAlign: "center",
    },

    divider: {
      height:
        StyleSheet.hairlineWidth,
    },

    /* ------------------------------------------------------------------ */
    /* Content                                                            */
    /* ------------------------------------------------------------------ */

    content: {
      padding: 18,
    },
  });

export default ProductTabs;