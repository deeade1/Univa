/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductFeatures.jsx                                                        */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import {
  colors,
  spacing,
  radius,
  typography,
} from "@/theme";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEFAULT_ICON = "check-circle-outline";

/* -------------------------------------------------------------------------- */
/* Feature Item                                                               */
/* -------------------------------------------------------------------------- */

const FeatureItem = memo(
  ({
    feature,
    themeColors,
    onPress,
    showSeparator = true,
  }) => {
    const handlePress = useCallback(() => {
      onPress?.(feature);
    }, [onPress, feature]);

    const Container = onPress ? Pressable : View;

    const isInteractive = !!onPress;

    return (
      <>
        <Container
          {...(isInteractive && {
            accessibilityRole: "button",
            accessibilityLabel: feature.title,
            onPress: handlePress,
          })}
          style={styles.featureItem}
        >
          <View
            style={[
              styles.iconContainer,
              {
                backgroundColor: `${themeColors.primary}15`,
              },
            ]}
          >
            <MaterialCommunityIcons
              name={feature.icon ?? DEFAULT_ICON}
              size={20}
              color={themeColors.primary}
            />
          </View>

          <View style={styles.featureContent}>
            <Text
              style={[
                styles.featureTitle,
                {
                  color: themeColors.text,
                },
              ]}
            >
              {feature.title}
            </Text>

            {feature.value != null && (
              <Text
                style={[
                  styles.featureValue,
                  {
                    color: themeColors.textSecondary,
                  },
                ]}
              >
                {typeof feature.value === 'number'
                  ? feature.value.toString()
                  : feature.value}
              </Text>
            )}

            {!!feature.description && (
              <Text
                style={[
                  styles.featureDescription,
                  {
                    color: themeColors.textSecondary,
                  },
                ]}
              >
                {Array.isArray(feature.description)
                  ? feature.description.join('\n')
                  : feature.description}
              </Text>
            )}
          </View>

          {isInteractive && feature.showChevron !== false && (
            <MaterialCommunityIcons
              name="chevron-right"
              size={20}
              color={themeColors.textSecondary}
            />
          )}
        </Container>

        {showSeparator && (
          <View
            style={[
              styles.separator,
              {
                backgroundColor: themeColors.border,
              },
            ]}
          />
        )}
      </>
    );
  }
);

FeatureItem.displayName = "FeatureItem";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductFeatures = memo(
  ({
    product,
    features = [],
    title = "Product Features",
    showHeader = true,
    showViewAll = true,
    showSummary = true,
    showFooter = true,
    onFeaturePress,
    onViewAll,
    style,
  }) => {
    const themeColors = colors;

    /* ---------------------------------------------------------------------- */
    /* Feature Data                                                           */
    /* ---------------------------------------------------------------------- */

    const items = useMemo(() => {
      if (features.length > 0) {
        return features;
      }

      return product?.features ?? [];
    }, [
      features,
      product?.features,
    ]);

    /* ---------------------------------------------------------------------- */
    /* Group features by category                                             */
    /* ---------------------------------------------------------------------- */

    const groupedItems = useMemo(() => {
      const groups = {};
      
      items.forEach((feature) => {
        const category = feature.category ?? null;
        if (!groups[category]) {
          groups[category] = [];
        }
        groups[category].push(feature);
      });

      return groups;
    }, [items]);

    const categories = useMemo(() => Object.keys(groupedItems), [groupedItems]);

    const handleViewAll = useCallback(() => {
      onViewAll?.({
        product,
        features: items,
      });
    }, [items, onViewAll, product]);

    /* ---------------------------------------------------------------------- */
    /* Render                                                                  */
    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,
          {
            backgroundColor: themeColors.card,
            borderColor: themeColors.border,
          },
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Header                                                         */}
        {/* -------------------------------------------------------------- */}

        {showHeader && (
          <View style={styles.header}>
            <View style={styles.headerLeft}>
              <MaterialCommunityIcons
                name="shape-outline"
                size={22}
                color={themeColors.primary}
              />

              <Text
                style={[
                  styles.headerTitle,
                  {
                    color: themeColors.text,
                  },
                ]}
              >
                {title}
              </Text>
            </View>

            {/* View All */}
            {showViewAll && items.length > 0 && (
              <Pressable
                onPress={handleViewAll}
                style={styles.viewAllButton}
                accessibilityRole="button"
                accessibilityLabel="View all features"
              >
                <Text
                  style={[
                    styles.viewAllText,
                    {
                      color: themeColors.primary,
                    },
                  ]}
                >
                  View All
                </Text>

                <MaterialCommunityIcons
                  name="chevron-right"
                  size={20}
                  color={themeColors.primary}
                />
              </Pressable>
            )}
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Features List                                                  */}
        {/* -------------------------------------------------------------- */}

        {items.length > 0 ? (
          categories.map((category, categoryIndex) => {
            const featuresInCategory = groupedItems[category];
            const isLastCategory = categoryIndex === categories.length - 1;

            return (
              <View key={category ?? 'uncategorized'}>
                {/* Category Label */}
                {category && (
                  <View
                    style={[
                      styles.categoryBadge,
                      {
                        backgroundColor: `${themeColors.primary}12`,
                      },
                    ]}
                  >
                    <Text
                      style={[
                        styles.categoryText,
                        {
                          color: themeColors.primary,
                        },
                      ]}
                    >
                      {category}
                    </Text>
                  </View>
                )}

                {/* Features in this category */}
                {featuresInCategory.map((feature, index) => (
                  <FeatureItem
                    key={String(feature.id ?? feature.title ?? index)}
                    feature={feature}
                    themeColors={themeColors}
                    onPress={onFeaturePress}
                    showSeparator={index !== featuresInCategory.length - 1 || !isLastCategory}
                  />
                ))}

                {/* Category separator */}
                {!isLastCategory && (
                  <View
                    style={[
                      styles.categorySeparator,
                      {
                        backgroundColor: themeColors.border,
                      },
                    ]}
                  />
                )}
              </View>
            );
          })
        ) : (
          /* Empty State */
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons
              name="shape-outline"
              size={54}
              color={themeColors.border}
            />

            <Text
              style={[
                styles.emptyTitle,
                {
                  color: themeColors.text,
                },
              ]}
            >
              No Features Available
            </Text>

            <Text
              style={[
                styles.emptyDescription,
                {
                  color: themeColors.textSecondary,
                },
              ]}
            >
              Product features have not been added for this item yet.
            </Text>
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Features Summary                                               */}
        {/* -------------------------------------------------------------- */}

        {showSummary && items.length > 0 && (
          <View
            style={[
              styles.summaryContainer,
              {
                borderTopColor: themeColors.border,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="check-decagram-outline"
              size={18}
              color={themeColors.primary}
            />

            <Text
              style={[
                styles.summaryText,
                {
                  color: themeColors.textSecondary,
                },
              ]}
            >
              This product includes{" "}
              <Text
                style={[
                  styles.summaryCount,
                  {
                    color: themeColors.text,
                  },
                ]}
              >
                {items.length}
              </Text>{" "}
              key feature
              {items.length !== 1 ? "s" : ""}
              designed to help you quickly understand its
              capabilities and benefits.
            </Text>
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Information Footer                                             */}
        {/* -------------------------------------------------------------- */}

        {showFooter && (
          <View
            style={[
              styles.footer,
              {
                borderTopColor: themeColors.border,
              },
            ]}
          >
            <MaterialCommunityIcons
              name="information-outline"
              size={16}
              color={themeColors.textSecondary}
            />

            <Text
              style={[
                styles.footerText,
                {
                  color: themeColors.textSecondary,
                },
              ]}
            >
              Features provide a high-level overview of the product.
              Refer to the specifications and description for
              complete technical details.
            </Text>
          </View>
        )}
      </View>
    );
  }
);

ProductFeatures.displayName = "ProductFeatures";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const featureShape = PropTypes.shape({
  id: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  icon: PropTypes.string,

  title: PropTypes.string.isRequired,

  value: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  description: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.arrayOf(PropTypes.string),
  ]),

  category: PropTypes.string,

  showChevron: PropTypes.bool,
});

const productShape = PropTypes.shape({
  features: PropTypes.arrayOf(featureShape),
});

FeatureItem.propTypes = {
  feature: featureShape.isRequired,

  themeColors: PropTypes.shape({
    primary: PropTypes.string,
    text: PropTypes.string,
    textSecondary: PropTypes.string,
    border: PropTypes.string,
  }).isRequired,

  onPress: PropTypes.func,

  showSeparator: PropTypes.bool,
};

FeatureItem.defaultProps = {
  onPress: null,
  showSeparator: true,
};

ProductFeatures.propTypes = {
  product: productShape,

  features: PropTypes.arrayOf(featureShape),

  title: PropTypes.string,

  showHeader: PropTypes.bool,

  showViewAll: PropTypes.bool,

  showSummary: PropTypes.bool,

  showFooter: PropTypes.bool,

  onFeaturePress: PropTypes.func,

  onViewAll: PropTypes.func,

  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ProductFeatures.defaultProps = {
  product: null,

  features: [],

  title: "Product Features",

  showHeader: true,

  showViewAll: true,

  showSummary: true,

  showFooter: true,

  onFeaturePress: null,

  onViewAll: null,

  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },

  /* ------------------------------------------------------------------ */
  /* Header                                                             */
  /* ------------------------------------------------------------------ */

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.lg,
  },

  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
  },

  headerTitle: {
    marginLeft: spacing.sm,
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.bold,
  },

  viewAllButton: {
    flexDirection: "row",
    alignItems: "center",
  },

  viewAllText: {
    marginRight: 2,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
  },

  /* ------------------------------------------------------------------ */
  /* Category                                                           */
  /* ------------------------------------------------------------------ */

  categoryBadge: {
    alignSelf: "flex-start",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radius.full,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },

  categoryText: {
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.bold,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },

  categorySeparator: {
    height: StyleSheet.hairlineWidth,
    marginVertical: spacing.md,
  },

  /* ------------------------------------------------------------------ */
  /* Feature Item                                                       */
  /* ------------------------------------------------------------------ */

  featureItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: spacing.md,
  },

  iconContainer: {
    width: 44,
    height: 44,
    borderRadius: radius.full,
    justifyContent: "center",
    alignItems: "center",
  },

  featureContent: {
    flex: 1,
    marginLeft: spacing.md,
    marginRight: spacing.sm,
  },

  featureTitle: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
  },

  featureValue: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.semibold,
  },

  featureDescription: {
    marginTop: spacing.xs,
    fontSize: typography.fontSize.sm,
    lineHeight: 20,
  },

  /* ------------------------------------------------------------------ */
  /* Separator                                                          */
  /* ------------------------------------------------------------------ */

  separator: {
    height: StyleSheet.hairlineWidth,
  },

  /* ------------------------------------------------------------------ */
  /* Empty State                                                        */
  /* ------------------------------------------------------------------ */

  emptyContainer: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.xl,
  },

  emptyTitle: {
    marginTop: spacing.md,
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
  },

  emptyDescription: {
    marginTop: spacing.sm,
    textAlign: "center",
    fontSize: typography.fontSize.sm,
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
    marginTop: spacing.lg,
    paddingTop: spacing.md,
  },

  summaryText: {
    flex: 1,
    marginLeft: spacing.sm,
    fontSize: typography.fontSize.sm,
    lineHeight: 20,
  },

  summaryCount: {
    fontWeight: typography.fontWeight.bold,
  },

  /* ------------------------------------------------------------------ */
  /* Footer                                                             */
  /* ------------------------------------------------------------------ */

  footer: {
    flexDirection: "row",
    alignItems: "flex-start",
    borderTopWidth: 1,
    marginTop: spacing.md,
    paddingTop: spacing.md,
  },

  footerText: {
    flex: 1,
    marginLeft: spacing.sm,
    fontSize: typography.fontSize.sm,
    lineHeight: 18,
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default ProductFeatures;