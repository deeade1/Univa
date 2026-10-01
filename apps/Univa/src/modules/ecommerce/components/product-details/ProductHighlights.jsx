/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductHighlights.jsx                                                      */
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

const DEFAULT_ICON = "check-decagram";

/* -------------------------------------------------------------------------- */
/* Highlight Item                                                             */
/* -------------------------------------------------------------------------- */

const HighlightItem = memo(
  ({
    highlight,
    themeColors,
    onPress,
  }) => {
    const handlePress = useCallback(() => {
      onPress?.(highlight);
    }, [onPress, highlight]);

    const Container = onPress ? Pressable : View;

    return (
      <Container
        {...(onPress && {
          accessibilityRole: "button",
          accessibilityLabel: highlight.title,
          onPress: handlePress,
        })}
        style={styles.item}
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
            name={highlight.icon ?? DEFAULT_ICON}
            size={20}
            color={themeColors.primary}
          />
        </View>

        <View style={styles.content}>
          <Text
            style={[
              styles.title,
              {
                color: themeColors.text,
              },
            ]}
          >
            {highlight.title}
          </Text>

          {!!highlight.description && (
            <Text
              style={[
                styles.description,
                {
                  color: themeColors.textSecondary,
                },
              ]}
            >
              {highlight.description}
            </Text>
          )}
        </View>

        {highlight.showChevron !== false && (
          <MaterialCommunityIcons
            name="chevron-right"
            size={20}
            color={themeColors.textSecondary}
          />
        )}
      </Container>
    );
  }
);

HighlightItem.displayName = "HighlightItem";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductHighlights = memo(
  ({
    product,
    highlights = [],
    showHeader = true,
    showViewAll = true,
    showFooter = true,
    showSummary = true,
    title = "Product Highlights",
    onHighlightPress,
    onViewAll,
    style,
  }) => {
    const themeColors = colors;

    /* ------------------------------------------------------------------ */
    /* Data                                                               */
    /* ------------------------------------------------------------------ */

    const items = useMemo(() => {
      if (highlights.length > 0) {
        return highlights;
      }

      return product?.highlights ?? [];
    }, [
      highlights,
      product?.highlights,
    ]);

    const handleViewAll = useCallback(() => {
      onViewAll?.({
        product,
        highlights: items,
      });
    }, [items, onViewAll, product]);

    /* ------------------------------------------------------------------ */
    /* Render                                                              */
    /* ------------------------------------------------------------------ */

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
                name="star-circle-outline"
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
                accessibilityLabel="View all highlights"
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
        {/* Highlights                                                     */}
        {/* -------------------------------------------------------------- */}

        {items.length > 0 ? (
          items.map((highlight, index) => (
            <React.Fragment key={String(highlight.id ?? highlight.title ?? index)}>
              <HighlightItem
                highlight={highlight}
                themeColors={themeColors}
                onPress={onHighlightPress}
              />

              {index !== items.length - 1 && (
                <View
                  style={[
                    styles.separator,
                    {
                      backgroundColor: themeColors.border,
                    },
                  ]}
                />
              )}
            </React.Fragment>
          ))
        ) : (
          /* Empty State */
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons
              name="star-outline"
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
              No Highlights
            </Text>

            <Text
              style={[
                styles.emptyDescription,
                {
                  color: themeColors.textSecondary,
                },
              ]}
            >
              Highlights for this product are not available yet.
            </Text>
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Highlights Summary                                             */}
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
              name="lightbulb-on-outline"
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
              {items.length} product highlight
              {items.length > 1 ? "s" : ""} available to help
              you quickly understand this product's key features
              and benefits.
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
              Product highlights provide a quick overview. Refer to
              the specifications and description for complete
              product information.
            </Text>
          </View>
        )}
      </View>
    );
  }
);

ProductHighlights.displayName = "ProductHighlights";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const highlightShape = PropTypes.shape({
  id: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  icon: PropTypes.string,

  title: PropTypes.string.isRequired,

  description: PropTypes.string,

  showChevron: PropTypes.bool,
});

const productShape = PropTypes.shape({
  highlights: PropTypes.arrayOf(highlightShape),
});

HighlightItem.propTypes = {
  highlight: highlightShape.isRequired,

  themeColors: PropTypes.shape({
    primary: PropTypes.string,
    text: PropTypes.string,
    textSecondary: PropTypes.string,
    border: PropTypes.string,
  }).isRequired,

  onPress: PropTypes.func,
};

HighlightItem.defaultProps = {
  onPress: null,
};

ProductHighlights.propTypes = {
  product: productShape,

  highlights: PropTypes.arrayOf(highlightShape),

  showHeader: PropTypes.bool,

  showViewAll: PropTypes.bool,

  showFooter: PropTypes.bool,

  showSummary: PropTypes.bool,

  title: PropTypes.string,

  onHighlightPress: PropTypes.func,

  onViewAll: PropTypes.func,

  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ProductHighlights.defaultProps = {
  product: null,

  highlights: [],

  showHeader: true,

  showViewAll: true,

  showFooter: true,

  showSummary: true,

  title: "Product Highlights",

  onHighlightPress: null,

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
    justifyContent: "space-between",
    alignItems: "center",
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
  /* Highlight Item                                                     */
  /* ------------------------------------------------------------------ */

  item: {
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

  content: {
    flex: 1,
    marginLeft: spacing.md,
    marginRight: spacing.sm,
  },

  title: {
    fontSize: typography.fontSize.md,
    fontWeight: typography.fontWeight.bold,
  },

  description: {
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
    fontSize: typography.fontSize.sm,
    textAlign: "center",
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

export default ProductHighlights;