/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/skeleton/                     */
/* ProductDetailsSkeleton.jsx                                                 */
/* -------------------------------------------------------------------------- */

import React, { memo } from "react";
import PropTypes from "prop-types";
import {
  View,
  StyleSheet,
  ScrollView,
  Dimensions,
} from "react-native";

import ContentLoader, { Rect, Circle } from "react-content-loader/native";

import theme from "@/theme";

const { width } = Dimensions.get("window");

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const THUMBNAIL_SIZE = 64;
const THUMBNAIL_GAP = 12;
const THUMBNAILS_PER_ROW = 5;
const THUMBNAIL_TOTAL_WIDTH = (THUMBNAIL_SIZE * THUMBNAILS_PER_ROW) + (THUMBNAIL_GAP * (THUMBNAILS_PER_ROW - 1));
const THUMBNAIL_START_X = (width - THUMBNAIL_TOTAL_WIDTH) / 2;

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductDetailsSkeleton = memo(({
  visible = true,
  showStickyFooter = true,
  showGallery = true,
  showThumbnails = true,
  showVariants = true,
  showQuantity = true,
  showActions = true,
  showSeller = true,
  showHighlights = true,
  showDescription = true,
  showSpecifications = true,
  showReviews = true,
  style,
}) => {
  const { colors } = theme;

  if (!visible) {
    return null;
  }

  /* ------------------------------------------------------------------------ */
  /* Render Footer Skeleton                                                    */
  /* ------------------------------------------------------------------------ */

  const renderFooterSkeleton = () => (
    <View style={styles.footer}>
      <View
        style={[
          styles.footerContent,
          {
            backgroundColor: colors.card || colors.background,
            borderColor: colors.border || "#E5E7EB",
          },
        ]}
      >
        <ContentLoader
          speed={1.4}
          width="100%"
          height={72}
          viewBox="0 0 400 72"
          backgroundColor={colors.border ?? "#E5E7EB"}
          foregroundColor={colors.card ?? "#F3F4F6"}
        >
          {/* Price */}
          <Rect
            x="16"
            y="16"
            width="120"
            height="40"
            rx="8"
          />

          {/* Add to Cart Button */}
          <Rect
            x="150"
            y="12"
            width="110"
            height="48"
            rx="12"
          />

          {/* Buy Now Button */}
          <Rect
            x="270"
            y="12"
            width="110"
            height="48"
            rx="12"
          />
        </ContentLoader>
      </View>
    </View>
  );

  /* ------------------------------------------------------------------------ */
  /* Render                                                                   */
  /* ------------------------------------------------------------------------ */

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
          height={1800}
          viewBox="0 0 400 1800"
          backgroundColor={colors.border ?? "#E5E7EB"}
          foregroundColor={colors.card ?? "#F3F4F6"}
          style={{ width: '100%', height: 1800 }}
        >
          {/* ------------------------------------------------------------------ */}
          {/* Product Gallery Skeleton                                           */}
          /* ------------------------------------------------------------------ *

          {showGallery && (
            <Rect
              x="0"
              y="0"
              width="400"
              height="320"
              rx="0"
            />
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Thumbnail Row                                                      */}
          /* ------------------------------------------------------------------ *

          {showThumbnails && showGallery && (
            <>
              {Array.from({ length: THUMBNAILS_PER_ROW }).map((_, index) => {
                const xPos = THUMBNAIL_START_X + (index * (THUMBNAIL_SIZE + THUMBNAIL_GAP));
                return (
                  <Rect
                    key={index}
                    x={xPos}
                    y="340"
                    width={THUMBNAIL_SIZE}
                    height={THUMBNAIL_SIZE}
                    rx="10"
                  />
                );
              })}
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Product Header                                                     */}
          /* ------------------------------------------------------------------ */

          {/* Brand */}
          <Rect
            x="16"
            y={showGallery ? 428 : 16}
            width="120"
            height="20"
            rx="6"
          />

          {/* Product Name */}
          <Rect
            x="16"
            y={showGallery ? 458 : 46}
            width="368"
            height="28"
            rx="8"
          />

          {/* Price */}
          <Rect
            x="16"
            y={showGallery ? 500 : 88}
            width="280"
            height="28"
            rx="8"
          />

          {/* Rating Row */}
          <Rect
            x="16"
            y={showGallery ? 542 : 130}
            width="90"
            height="18"
            rx="6"
          />
          <Rect
            x="116"
            y={showGallery ? 542 : 130}
            width="120"
            height="18"
            rx="6"
          />

          {/* ------------------------------------------------------------------ */}
          /* Variant Selector                                                   */
          /* ------------------------------------------------------------------ */

          {showVariants && (
            <>
              <Rect
                x="16"
                y={showGallery ? 680 : 168}
                width="110"
                height="20"
                rx="6"
              />

              <Rect
                x="16"
                y={showGallery ? 710 : 198}
                width="72"
                height="42"
                rx="20"
              />
              <Rect
                x="98"
                y={showGallery ? 710 : 198}
                width="72"
                height="42"
                rx="20"
              />
              <Rect
                x="180"
                y={showGallery ? 710 : 198}
                width="72"
                height="42"
                rx="20"
              />
              <Rect
                x="262"
                y={showGallery ? 710 : 198}
                width="72"
                height="42"
                rx="20"
              />
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Quantity Selector                                                  */}
          /* ------------------------------------------------------------------ */

          {showQuantity && (
            <>
              <Rect
                x="16"
                y={showVariants ? 772 : 260}
                width="100"
                height="20"
                rx="6"
              />

              <Rect
                x="16"
                y={showVariants ? 800 : 288}
                width="44"
                height="44"
                rx="10"
              />
              <Rect
                x="70"
                y={showVariants ? 800 : 288}
                width="60"
                height="44"
                rx="10"
              />
              <Rect
                x="140"
                y={showVariants ? 800 : 288}
                width="44"
                height="44"
                rx="10"
              />
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Action Buttons                                                     */}
          /* ------------------------------------------------------------------ */

          {showActions && (
            <>
              <Rect
                x="16"
                y={showQuantity ? 864 : 352}
                width="180"
                height="48"
                rx="12"
              />
              <Rect
                x="206"
                y={showQuantity ? 864 : 352}
                width="180"
                height="48"
                rx="12"
              />
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Seller Card                                                        */}
          /* ------------------------------------------------------------------ */

          {showSeller && (
            <Rect
              x="16"
              y={showActions ? 932 : 420}
              width="368"
              height="140"
              rx="16"
            />
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Highlights Section                                                 */}
          /* ------------------------------------------------------------------ */

          {showHighlights && (
            <>
              <Rect
                x="16"
                y={showSeller ? 1092 : 580}
                width="140"
                height="22"
                rx="6"
              />

              {Array.from({ length: 4 }).map((_, index) => {
                const yPos = showSeller ? 1124 + (index * 30) : 612 + (index * 30);
                const width = Math.random() > 0.5 ? 300 : 280;
                return (
                  <React.Fragment key={index}>
                    <Rect
                      x="16"
                      y={yPos}
                      width="18"
                      height="18"
                      rx="9"
                    />
                    <Rect
                      x="44"
                      y={yPos}
                      width={width}
                      height="16"
                      rx="6"
                    />
                  </React.Fragment>
                );
              })}
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Description Section                                                */}
          /* ------------------------------------------------------------------ */

          {showDescription && (
            <>
              <Rect
                x="16"
                y={showHighlights ? 1252 : 740}
                width="170"
                height="22"
                rx="6"
              />

              {Array.from({ length: 5 }).map((_, index) => {
                const yPos = showHighlights ? 1284 + (index * 26) : 772 + (index * 26);
                const width = index === 4 ? 240 : (index === 0 ? 368 : (index === 1 ? 350 : (index === 2 ? 368 : 340)));
                return (
                  <Rect
                    key={index}
                    x="16"
                    y={yPos}
                    width={width}
                    height="16"
                    rx="6"
                  />
                );
              })}
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Specifications Section                                             */}
          /* ------------------------------------------------------------------ */

          {showSpecifications && (
            <>
              <Rect
                x="16"
                y={showDescription ? 1424 : 912}
                width="150"
                height="22"
                rx="6"
              />

              {Array.from({ length: 6 }).map((_, index) => {
                const yPos = showDescription ? 1456 + (index * 26) : 944 + (index * 26);
                const labelWidth = [140, 120, 160, 100, 130, 150][index];
                const valueWidth = [130, 110, 140, 90, 120, 160][index];
                return (
                  <React.Fragment key={index}>
                    <Rect
                      x="16"
                      y={yPos}
                      width={labelWidth}
                      height="16"
                      rx="6"
                    />
                    <Rect
                      x="250"
                      y={yPos}
                      width={valueWidth}
                      height="16"
                      rx="6"
                    />
                  </React.Fragment>
                );
              })}
            </>
          )}

          {/* ------------------------------------------------------------------ */}
          {/* Reviews Section                                                    */}
          /* ------------------------------------------------------------------ */

          {showReviews && (
            <>
              <Rect
                x="16"
                y={showSpecifications ? 1622 : 1110}
                width="120"
                height="22"
                rx="6"
              />

              {Array.from({ length: 2 }).map((_, index) => {
                const yPos = showSpecifications ? 1654 + (index * 120) : 1142 + (index * 120);
                return (
                  <Rect
                    key={index}
                    x="16"
                    y={yPos}
                    width="368"
                    height="110"
                    rx="14"
                  />
                );
              })}
            </>
          )}
        </ContentLoader>
      </ScrollView>

      {/* ------------------------------------------------------------------ */}
      {/* Sticky Bottom Action Bar                                            */}
      /* ------------------------------------------------------------------ */

      {showStickyFooter && renderFooterSkeleton()}
    </View>
  );
});

ProductDetailsSkeleton.displayName = "ProductDetailsSkeleton";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductDetailsSkeleton.propTypes = {
  visible: PropTypes.bool,
  showStickyFooter: PropTypes.bool,
  showGallery: PropTypes.bool,
  showThumbnails: PropTypes.bool,
  showVariants: PropTypes.bool,
  showQuantity: PropTypes.bool,
  showActions: PropTypes.bool,
  showSeller: PropTypes.bool,
  showHighlights: PropTypes.bool,
  showDescription: PropTypes.bool,
  showSpecifications: PropTypes.bool,
  showReviews: PropTypes.bool,
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

ProductDetailsSkeleton.defaultProps = {
  visible: true,
  showStickyFooter: true,
  showGallery: true,
  showThumbnails: true,
  showVariants: true,
  showQuantity: true,
  showActions: true,
  showSeller: true,
  showHighlights: true,
  showDescription: true,
  showSpecifications: true,
  showReviews: true,
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
    paddingBottom: 100,
  },

  footer: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 16,
    paddingBottom: 16,
    paddingTop: 8,
  },

  footerContent: {
    borderRadius: 18,
    borderWidth: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    height: 72,
    overflow: "hidden",
  },
});

export default ProductDetailsSkeleton;