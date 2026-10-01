/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ProductGallery.jsx      */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useState,
  useCallback,
  useRef,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  FlatList,
  Pressable,
  Image,
  Text,
  Dimensions,
  StyleSheet,
} from "react-native";
import theme from "@/theme";
import {
  colors,
  spacing,
  radius,
  typography,
} from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import ZoomableImage from "@/modules/ecommerce/components/common/ZoomableImage";
import DiscountBadge from "@/modules/ecommerce/components/common/DiscountBadge";
import StockBadge from "@/modules/ecommerce/components/common/StockBadge";
import FavoriteButton from "@/modules/ecommerce/components/common/FavoriteButton";
import LoadingOverlay from "@/modules/ecommerce/components/common/LoadingOverlay";
import EmptyState from "@/modules/ecommerce/components/common/EmptyState";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const IMAGE_WIDTH = SCREEN_WIDTH;
const IMAGE_HEIGHT = SCREEN_WIDTH * 0.9;

/* -------------------------------------------------------------------------- */
/* Image Source Normalizer                                                    */
/* -------------------------------------------------------------------------- */

const normalizeImageSource = (source) => {
  if (typeof source === "number") return source;
  if (typeof source === "string") return { uri: source };
  if (source && typeof source === "object" && source.uri) return source;
  if (source && typeof source === "object" && source.url) return { uri: source.url };
  return null;
};

/* -------------------------------------------------------------------------- */
/* Image Placeholder                                                          */
/* -------------------------------------------------------------------------- */

const ImagePlaceholder = memo(({ style }) => (
  <View
    style={[
      styles.imagePlaceholder,
      style,
    ]}
  >
    <Text style={styles.placeholderText}>No Image</Text>
  </View>
));

ImagePlaceholder.displayName = "ImagePlaceholder";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductGallery = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    product,
    images = [],
    initialIndex = 0,

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    loading = false,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    showThumbnails = true,
    showIndicators = true,
    showDiscount = true,
    showStock = true,
    showFavorite = false,
    showCounter = true,
    loop = false,

    /* ---------------------------------------------------------------------- */
    /* State Props                                                            */
    /* ---------------------------------------------------------------------- */

    favorite = false,
    imageHeight = IMAGE_HEIGHT,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onImagePress,
    onImageChange,
    onFavoritePress,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,
  }) => {
    const themeColors = colors;

    /* ---------------------------------------------------------------------- */
    /* Refs                                                                   */
    /* ---------------------------------------------------------------------- */

    const flatListRef = useRef(null);
    const thumbnailListRef = useRef(null);

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    const [activeIndex, setActiveIndex] = useState(initialIndex);

    /* ---------------------------------------------------------------------- */
    /* Memoized Values                                                        */
    /* ---------------------------------------------------------------------- */

    const galleryImages = useMemo(() => {
      if (images?.length > 0) return images;
      if (product?.images?.length > 0) return product.images;
      if (product?.image) return [product.image];
      return [];
    }, [images, product]);

    const discount = useMemo(
      () => product?.discount ?? null,
      [product]
    );

    const inStock = useMemo(
      () =>
        product?.inStock ??
        (product?.stock ?? 0) > 0,
      [product]
    );

    const safeInitialIndex = useMemo(() => {
      const maxIndex = Math.max(galleryImages.length - 1, 0);
      return Math.min(Math.max(initialIndex, 0), maxIndex);
    }, [initialIndex, galleryImages.length]);

    /* ---------------------------------------------------------------------- */
    /* Loop Data - Simplified for now                                          */
    /* ---------------------------------------------------------------------- */

    const loopData = useMemo(() => {
      if (!loop || galleryImages.length === 0) return galleryImages;
      // Simplified: just duplicate once for basic infinite feel
      return [...galleryImages, ...galleryImages];
    }, [galleryImages, loop]);

    const loopOffset = useMemo(() => {
      return loop ? galleryImages.length : 0;
    }, [loop, galleryImages.length]);

    /* ---------------------------------------------------------------------- */
    /* Key Extractor                                                          */
    /* ---------------------------------------------------------------------- */

    const keyExtractor = useCallback(
      (item, index) =>
        String(
          item?.id ??
          item?.url ??
          item?.uri ??
          index
        ),
      []
    );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleImagePress = useCallback(
      (image, index) => {
        const actualIndex = loop ? index % galleryImages.length : index;
        onImagePress?.(image, actualIndex, galleryImages);
      },
      [onImagePress, galleryImages, loop]
    );

    const handleFavorite = useCallback(() => {
      onFavoritePress?.(product);
    }, [onFavoritePress, product]);

    const handleScrollToIndex = useCallback(
      (index) => {
        const actualIndex = loop ? index + loopOffset : index;
        flatListRef.current?.scrollToIndex({
          index: actualIndex,
          animated: true,
        });
        setActiveIndex(index);
        onImageChange?.(index);
      },
      [loop, loopOffset, onImageChange]
    );

    const handleThumbnailPress = useCallback(
      (index) => {
        handleScrollToIndex(index);
        try {
          thumbnailListRef.current?.scrollToIndex({
            index,
            animated: true,
            viewPosition: 0.5,
          });
        } catch {
          // Fallback: scroll to index after a delay
          setTimeout(() => {
            try {
              thumbnailListRef.current?.scrollToIndex({
                index,
                animated: true,
                viewPosition: 0.5,
              });
            } catch {
              // Ignore
            }
          }, 100);
        }
      },
      [handleScrollToIndex]
    );

    /* ---------------------------------------------------------------------- */
    /* Viewability                                                            */
    /* ---------------------------------------------------------------------- */

    const onViewableItemsChanged = useRef(({ viewableItems }) => {
      if (!viewableItems?.length) return;

      const index = viewableItems[0]?.index ?? 0;
      const actualIndex = loop ? index % galleryImages.length : index;

      setActiveIndex(actualIndex);

      try {
        thumbnailListRef.current?.scrollToIndex({
          index: actualIndex,
          animated: true,
          viewPosition: 0.5,
        });
      } catch {
        // Ignore thumbnail scroll errors
      }

      onImageChange?.(actualIndex);
    }).current;

    const viewabilityConfig = useRef({
      itemVisiblePercentThreshold: 60,
    }).current;

    /* ---------------------------------------------------------------------- */
    /* Render Image                                                           */
    /* ---------------------------------------------------------------------- */

    const renderItem = useCallback(
      ({ item, index }) => {
        const imageSource = normalizeImageSource(item);
        const actualIndex = loop ? index % galleryImages.length : index;

        return (
          <Pressable
            accessibilityRole="image"
            accessibilityLabel={`Product image ${actualIndex + 1}`}
            onPress={() => handleImagePress(item, actualIndex)}
            style={[
              styles.imageContainer,
              {
                width: IMAGE_WIDTH,
                height: imageHeight,
                backgroundColor: themeColors.surface,
              },
            ]}
          >
            {imageSource ? (
              <ZoomableImage
                source={imageSource}
                resizeMode="contain"
                style={[
                  styles.image,
                  {
                    width: IMAGE_WIDTH,
                    height: imageHeight,
                  },
                ]}
              />
            ) : (
              <ImagePlaceholder
                style={{
                  width: IMAGE_WIDTH,
                  height: imageHeight,
                }}
              />
            )}
          </Pressable>
        );
      },
      [imageHeight, handleImagePress, loop, galleryImages.length, themeColors.surface]
    );

    /* ---------------------------------------------------------------------- */
    /* Render Thumbnail                                                       */
    /* ---------------------------------------------------------------------- */

    const renderThumbnail = useCallback(
      ({ item, index }) => {
        const isActive = index === activeIndex;
        const imageSource = normalizeImageSource(item);

        return (
          <Pressable
            onPress={() => handleThumbnailPress(index)}
            style={[
              styles.thumbnailWrapper,
              isActive && [
                styles.activeThumbnail,
                { borderColor: themeColors.primary },
              ],
            ]}
          >
            {imageSource ? (
              <Image
                source={imageSource}
                resizeMode="cover"
                style={styles.thumbnail}
              />
            ) : (
              <View style={[styles.thumbnail, styles.thumbnailPlaceholder]} />
            )}
          </Pressable>
        );
      },
      [activeIndex, themeColors.primary, handleThumbnailPress]
    );

    /* ---------------------------------------------------------------------- */
    /* Loading State                                                          */
    /* ---------------------------------------------------------------------- */

    if (loading) {
      return (
        <View style={[styles.container, style]}>
          <LoadingOverlay
            visible
            fullscreen={false}
            transparent
            message="Loading images..."
          />
        </View>
      );
    }

    /* ---------------------------------------------------------------------- */
    /* Empty State                                                            */
    /* ---------------------------------------------------------------------- */

    if (galleryImages.length === 0) {
      return (
        <View
          style={[
            styles.container,
            {
              height: imageHeight,
              backgroundColor: themeColors.card,
            },
            style,
          ]}
        >
          <EmptyState
            icon="image-off"
            title="No Images"
            description="Product images are unavailable."
          />
        </View>
      );
    }

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    const showCounterBadge = showCounter && galleryImages.length > 1;

    return (
      <View style={[styles.container, style]}>
        {/* -------------------------------------------------------------- */}
        {/* Image Carousel                                                */}
        {/* -------------------------------------------------------------- */}

        <FlatList
          ref={flatListRef}
          data={loop ? loopData : galleryImages}
          horizontal
          pagingEnabled
          bounces={false}
          showsHorizontalScrollIndicator={false}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          initialScrollIndex={loop ? loopOffset + safeInitialIndex : safeInitialIndex}
          getItemLayout={(_, index) => ({
            length: IMAGE_WIDTH,
            offset: IMAGE_WIDTH * index,
            index,
          })}
          onViewableItemsChanged={onViewableItemsChanged}
          viewabilityConfig={viewabilityConfig}
          windowSize={3}
          initialNumToRender={1}
          maxToRenderPerBatch={2}
          scrollEventThrottle={16}
          updateCellsBatchingPeriod={50}
          disableIntervalMomentum={true}
          onScrollToIndexFailed={(info) => {
            const wait = new Promise((resolve) => setTimeout(resolve, 500));
            wait.then(() => {
              flatListRef.current?.scrollToIndex({
                index: info.index,
                animated: true,
              });
            });
          }}
        />

        {/* -------------------------------------------------------------- */}
        {/* Discount Badge                                                */}
        {/* -------------------------------------------------------------- */}

        {showDiscount && !!discount && (
          <View style={styles.discountBadge}>
            <DiscountBadge discount={discount} />
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Stock Badge                                                   */}
        {/* -------------------------------------------------------------- */}

        {showStock && (
          <View style={styles.stockBadge}>
            <StockBadge inStock={inStock} quantity={product?.stock} />
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Favorite Button                                               */}
        {/* -------------------------------------------------------------- */}

        {showFavorite && (
          <View style={styles.favoriteButton}>
            <FavoriteButton active={favorite} onPress={handleFavorite} />
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Image Counter                                                 */}
        {/* -------------------------------------------------------------- */}

        {showCounterBadge && (
          <View
            style={[
              styles.counterContainer,
              {
                backgroundColor: themeColors.backdrop ?? "rgba(0,0,0,0.6)",
              },
            ]}
          >
            <Text
              style={[
                styles.counterText,
                {
                  color: themeColors.onPrimary ?? "#FFFFFF",
                },
              ]}
            >
              {activeIndex + 1} / {galleryImages.length}
            </Text>
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Pagination Indicators                                         */}
        {/* -------------------------------------------------------------- */}

        {showIndicators && galleryImages.length > 1 && (
          <View style={styles.indicators}>
            {galleryImages.map((_, index) => {
              const active = index === activeIndex;
              return (
                <Pressable
                  key={index}
                  onPress={() => handleThumbnailPress(index)}
                  hitSlop={10}
                  style={[
                    styles.dot,
                    {
                      backgroundColor: active ? themeColors.primary : themeColors.border,
                    },
                    active && styles.activeDot,
                  ]}
                />
              );
            })}
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Thumbnail Strip                                               */}
        {/* -------------------------------------------------------------- */}

        {showThumbnails && galleryImages.length > 1 && (
          <View style={styles.thumbnailContainer}>
            <FlatList
              ref={thumbnailListRef}
              horizontal
              data={galleryImages}
              keyExtractor={keyExtractor}
              renderItem={renderThumbnail}
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.thumbnailContent}
              getItemLayout={(_, index) => ({
                length: 74,
                offset: 74 * index,
                index,
              })}
              initialNumToRender={8}
              maxToRenderPerBatch={8}
              windowSize={3}
              scrollEventThrottle={16}
              onScrollToIndexFailed={() => {
                // Fallback for thumbnail scrolling
              }}
            />
          </View>
        )}
      </View>
    );
  }
);

ProductGallery.displayName = "ProductGallery";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const imagePropType = PropTypes.oneOfType([
  PropTypes.string,
  PropTypes.number,
  PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    uri: PropTypes.string,
    url: PropTypes.string,
  }),
]);

ProductGallery.propTypes = {
  // Data
  product: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    image: PropTypes.string,
    images: PropTypes.array,
    discount: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    stock: PropTypes.number,
    inStock: PropTypes.bool,
  }),
  images: PropTypes.arrayOf(imagePropType),
  initialIndex: PropTypes.number,

  // State
  loading: PropTypes.bool,

  // Display
  showThumbnails: PropTypes.bool,
  showIndicators: PropTypes.bool,
  showDiscount: PropTypes.bool,
  showStock: PropTypes.bool,
  showFavorite: PropTypes.bool,
  showCounter: PropTypes.bool,
  loop: PropTypes.bool,

  // State Props
  favorite: PropTypes.bool,
  imageHeight: PropTypes.number,

  // Events
  onImagePress: PropTypes.func,
  onImageChange: PropTypes.func,
  onFavoritePress: PropTypes.func,

  // Styling
  style: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ProductGallery.defaultProps = {
  product: null,
  images: [],
  initialIndex: 0,
  loading: false,
  showThumbnails: true,
  showIndicators: true,
  showDiscount: true,
  showStock: true,
  showFavorite: false,
  showCounter: true,
  loop: false,
  favorite: false,
  imageHeight: IMAGE_HEIGHT,
  onImagePress: null,
  onImageChange: null,
  onFavoritePress: null,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    position: "relative",
    width: "100%",
  },

  /* ------------------------------------------------------------------ */
  /* Image                                                              */
  /* ------------------------------------------------------------------ */

  imageContainer: {
    justifyContent: "center",
    alignItems: "center",
    overflow: "hidden",
  },

  image: {
    width: "100%",
  },

  imagePlaceholder: {
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.surface || "#F3F4F6",
  },

  placeholderText: {
    color: colors.textSecondary || "#9CA3AF",
    fontSize: typography.small.fontSize,
    fontWeight: typography.small.fontWeight,
  },

  /* ------------------------------------------------------------------ */
  /* Badges                                                             */
  /* ------------------------------------------------------------------ */

  discountBadge: {
    position: "absolute",
    top: 16,
    left: 16,
    zIndex: 20,
  },

  stockBadge: {
    position: "absolute",
    top: 16,
    right: 16,
    zIndex: 20,
  },

  favoriteButton: {
    position: "absolute",
    bottom: 22,
    right: 18,
    zIndex: 25,
  },

  /* ------------------------------------------------------------------ */
  /* Counter                                                            */
  /* ------------------------------------------------------------------ */

  counterContainer: {
    position: "absolute",
    top: 60,
    right: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },

  counterText: {
    fontSize: 12,
    fontWeight: "600",
  },

  /* ------------------------------------------------------------------ */
  /* Pagination                                                         */
  /* ------------------------------------------------------------------ */

  indicators: {
    position: "absolute",
    bottom: 20,
    alignSelf: "center",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
  },

  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginHorizontal: 4,
  },

  activeDot: {
    width: 24,
    borderRadius: 12,
  },

  /* ------------------------------------------------------------------ */
  /* Thumbnails                                                         */
  /* ------------------------------------------------------------------ */

  thumbnailContainer: {
    position: "absolute",
    bottom: 80,
    left: 0,
    right: 0,
  },

  thumbnailContent: {
    paddingHorizontal: 16,
  },

  thumbnailWrapper: {
    width: 64,
    height: 64,
    borderRadius: 10,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "transparent",
    marginRight: 10,
  },

  activeThumbnail: {
    borderWidth: 2,
  },

  thumbnail: {
    width: "100%",
    height: "100%",
  },

  thumbnailPlaceholder: {
    backgroundColor: colors.surface || "#F3F4F6",
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default ProductGallery;