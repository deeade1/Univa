/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/skeleton/DashboardSkeleton.jsx */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import { View, StyleSheet, ScrollView, Dimensions } from "react-native";

import ContentLoader, { Rect, Circle } from "react-content-loader/native";

import theme from "@/theme";

const { width } = Dimensions.get("window");

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const CARD_WIDTH = (width - 48) / 3;
const PRODUCT_WIDTH = (width - 48) / 2.2;

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const DashboardSkeleton = memo(({
  visible = true,
  showHeader = true,
  showSearchBar = true,
  showShortcuts = true,
  showCategories = true,
  showBanner = true,
  showProductSections = true,
  sectionsCount = 3,
  productsPerSection = 4,
  style,
}) => {
  const { colors } = theme;

  if (!visible) {
    return null;
  }

  const renderProductSection = (sectionIndex) => {
    const yOffset = 620 + (sectionIndex * 260);
    
    return (
      <React.Fragment key={sectionIndex}>
        {/* Section Header */}
        <Rect
          x="16"
          y={yOffset}
          width="200"
          height="22"
          rx="6"
        />
        <Rect
          x="340"
          y={yOffset}
          width="60"
          height="18"
          rx="6"
        />

        {/* Product Cards */}
        {Array.from({ length: Math.min(productsPerSection, 4) }).map((_, index) => {
          const xPos = 16 + (index * (PRODUCT_WIDTH + 12));
          return (
            <Rect
              key={index}
              x={xPos}
              y={yOffset + 36}
              width={PRODUCT_WIDTH}
              height={200}
              rx="12"
            />
          );
        })}
      </React.Fragment>
    );
  };

  const totalHeight = 1200 + (sectionsCount * 260);

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: colors.background,
        },
        style,
      ]}
    >
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        <ContentLoader
          speed={1.4}
          width="100%"
          height={totalHeight}
          viewBox={`0 0 400 ${totalHeight}`}
          backgroundColor={colors.border ?? "#E5E7EB"}
          foregroundColor={colors.card ?? "#F3F4F6"}
          style={{ width: '100%', height: totalHeight }}
        >
          {/* ------------------------------------------------------------------ */}
          {/* Header                                                             */}
          {/* ------------------------------------------------------------------ */}

          {showHeader && (
            <>
              <Rect
                x="16"
                y="16"
                width="200"
                height="28"
                rx="8"
              />
              <Rect
                x="16"
                y="50"
                width="160"
                height="16"
                rx="6"
              />
              {/* Avatar */}
              <Circle
                cx="370"
                cy="30"
                r="20"
              />
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Search Bar                                                         */}
          {/* ------------------------------------------------------------------ */}

          {showSearchBar && (
            <Rect
              x="16"
              y={showHeader ? 90 : 16}
              width="368"
              height="48"
              rx="12"
            />
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Shortcuts                                                          */}
          {/* ------------------------------------------------------------------ */}

          {showShortcuts && (
            <>
              <Rect
                x="16"
                y={showHeader ? 160 : 80}
                width="80"
                height="80"
                rx="12"
              />
              <Rect
                x="108"
                y={showHeader ? 160 : 80}
                width="80"
                height="80"
                rx="12"
              />
              <Rect
                x="200"
                y={showHeader ? 160 : 80}
                width="80"
                height="80"
                rx="12"
              />
              <Rect
                x="292"
                y={showHeader ? 160 : 80}
                width="80"
                height="80"
                rx="12"
              />
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Banner / Carousel                                                  */}
          {/* ------------------------------------------------------------------ */}

          {showBanner && (
            <Rect
              x="16"
              y={showHeader ? 270 : 190}
              width="368"
              height="160"
              rx="16"
            />
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Categories                                                         */}
          {/* ------------------------------------------------------------------ */}

          {showCategories && (
            <>
              <Rect
                x="16"
                y={showHeader ? 460 : 380}
                width="140"
                height="20"
                rx="6"
              />

              <Rect
                x="16"
                y={showHeader ? 490 : 410}
                width="80"
                height="100"
                rx="12"
              />
              <Rect
                x="106"
                y={showHeader ? 490 : 410}
                width="80"
                height="100"
                rx="12"
              />
              <Rect
                x="196"
                y={showHeader ? 490 : 410}
                width="80"
                height="100"
                rx="12"
              />
              <Rect
                x="286"
                y={showHeader ? 490 : 410}
                width="80"
                height="100"
                rx="12"
              />
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Product Sections                                                   */}
          {/* ------------------------------------------------------------------ */}

          {showProductSections && (
            <>
              {Array.from({ length: sectionsCount }).map((_, index) => 
                renderProductSection(index)
              )}
            </>
          )}
        </ContentLoader>
      </ScrollView>
    </View>
  );
});

DashboardSkeleton.displayName = "DashboardSkeleton";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

DashboardSkeleton.propTypes = {
  visible: PropTypes.bool,
  showHeader: PropTypes.bool,
  showSearchBar: PropTypes.bool,
  showShortcuts: PropTypes.bool,
  showCategories: PropTypes.bool,
  showBanner: PropTypes.bool,
  showProductSections: PropTypes.bool,
  sectionsCount: PropTypes.number,
  productsPerSection: PropTypes.number,
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

DashboardSkeleton.defaultProps = {
  visible: true,
  showHeader: true,
  showSearchBar: true,
  showShortcuts: true,
  showCategories: true,
  showBanner: true,
  showProductSections: true,
  sectionsCount: 3,
  productsPerSection: 4,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  scrollContent: {
    paddingBottom: 20,
  },
});

export default DashboardSkeleton;