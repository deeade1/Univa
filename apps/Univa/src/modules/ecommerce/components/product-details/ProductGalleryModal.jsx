/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductGalleryModal.jsx                                                    */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";

import PropTypes from "prop-types";

import {
  Modal,
  View,
  Text,
  Pressable,
  FlatList,
  Image,
  StyleSheet,
  Dimensions,
  StatusBar,
  ActivityIndicator,
  Alert,
  Animated,
  Platform,
} from "react-native";

import {
  MaterialCommunityIcons,
} from "@expo/vector-icons";

import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';

// Conditionally import MediaLibrary only on native platforms
let MediaLibrary = null;
if (Platform.OS !== 'web') {
  try {
    MediaLibrary = require('expo-media-library');
  } catch (e) {
    console.warn('expo-media-library not available:', e.message);
  }
}

import {
  VideoView,
  useVideoPlayer,
} from "expo-video";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const {
  width: SCREEN_WIDTH,
  height: SCREEN_HEIGHT,
} = Dimensions.get("window");

/* -------------------------------------------------------------------------- */
/* ZoomableImage Component                                                    */
/* -------------------------------------------------------------------------- */

import ZoomableImage from "../common/ZoomableImage";

/* -------------------------------------------------------------------------- */
/* Video Player Component                                                     */
/* -------------------------------------------------------------------------- */

const VideoPlayer = memo(({ source, style, onLoad, onError }) => {
  const videoSource = typeof source === 'string' ? source : source?.uri || source;

  // Create video player instance
  const player = useVideoPlayer(videoSource, (playerInstance) => {
    playerInstance.loop = false;
    playerInstance.play();
  });

  const [isPlaying, setIsPlaying] = useState(true);
  const [isLoaded, setIsLoaded] = useState(false);

  // Handle play/pause toggle
  const togglePlayback = useCallback(() => {
    if (isPlaying) {
      player.pause();
    } else {
      player.play();
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying, player]);

  // Handle load event
  useEffect(() => {
    if (player && !isLoaded) {
      setIsLoaded(true);
      onLoad?.();
    }
  }, [player, isLoaded, onLoad]);

  // Handle error
  useEffect(() => {
    const subscription = player.addListener('statusChange', (status) => {
      if (status.error) {
        console.error('Video error:', status.error);
        onError?.(status.error);
      }
    });
    return () => {
      subscription.remove();
    };
  }, [player, onError]);

  return (
    <View style={[styles.mediaPage, { position: 'relative' }]}>
      <VideoView
        player={player}
        style={[styles.video, style]}
        allowsFullscreen
        allowsPictureInPicture
        nativeControls
        contentFit="contain"
      />
      {/* Play/Pause overlay button */}
      <Pressable
        onPress={togglePlayback}
        style={styles.videoOverlay}
        accessibilityRole="button"
        accessibilityLabel={isPlaying ? "Pause video" : "Play video"}
      >
        <View style={styles.videoControlButton}>
          <MaterialCommunityIcons
            name={isPlaying ? "pause" : "play"}
            size={40}
            color="#FFFFFF"
          />
        </View>
      </Pressable>
    </View>
  );
});

VideoPlayer.displayName = "VideoPlayer";

/* -------------------------------------------------------------------------- */
/* Main Component                                                             */
/* -------------------------------------------------------------------------- */

const ProductGalleryModal = memo(
  ({
    visible,
    images = [],
    initialIndex = 0,
    productName,
    productId,
    onClose,
    onImageChange,
    enableDownload = true,
    enableShare = true,
    enableWishlist = true,
    enableZoom = true,
    showThumbnails = true,
    showPagination = true,
    showHint = true,
    style,
    isWishlisted: propIsWishlisted = false,
    onWishlistToggle,
  }) => {
    const { colors } = theme;

    const flatListRef = useRef(null);
    const [currentIndex, setCurrentIndex] = useState(initialIndex);
    const [isLoading, setIsLoading] = useState(true);
    const [imageLoaded, setImageLoaded] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const [isWishlisted, setIsWishlisted] = useState(propIsWishlisted);
    const [permissionStatus, setPermissionStatus] = useState(null);

    // Animated transitions
    const [fadeAnim] = useState(new Animated.Value(0));
    const [scaleAnim] = useState(new Animated.Value(0.95));

    // Check if download is available on this platform
    const isDownloadAvailable = Platform.OS !== 'web' && MediaLibrary !== null;

    /* ---------------------------------------------------------------------- */
    /* Effects                                                                */
    /* ---------------------------------------------------------------------- */

    useEffect(() => {
      if (visible) {
        setCurrentIndex(initialIndex);
        setImageLoaded(false);
        setIsLoading(true);

        // Animate in
        Animated.parallel([
          Animated.timing(fadeAnim, {
            toValue: 1,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.spring(scaleAnim, {
            toValue: 1,
            friction: 8,
            tension: 40,
            useNativeDriver: true,
          }),
        ]).start();

        // Scroll to initial index
        if (flatListRef.current && initialIndex > 0) {
          setTimeout(() => {
            flatListRef.current?.scrollToIndex({
              index: initialIndex,
              animated: false,
            });
          }, 100);
        }
      } else {
        // Animate out
        Animated.parallel([
          Animated.timing(fadeAnim, {
            toValue: 0,
            duration: 200,
            useNativeDriver: true,
          }),
          Animated.spring(scaleAnim, {
            toValue: 0.95,
            friction: 8,
            tension: 40,
            useNativeDriver: true,
          }),
        ]).start();
      }
    }, [visible, initialIndex]);

    /* ---------------------------------------------------------------------- */
    /* Permission Checks                                                      */
    /* ---------------------------------------------------------------------- */

    useEffect(() => {
      if (enableDownload && isDownloadAvailable) {
        (async () => {
          try {
            const { status } = await MediaLibrary.requestPermissionsAsync();
            setPermissionStatus(status);
          } catch (error) {
            console.warn('Failed to request media library permission:', error);
          }
        })();
      }
    }, [enableDownload, isDownloadAvailable]);

    /* ---------------------------------------------------------------------- */
    /* Image Change Handlers                                                  */
    /* ---------------------------------------------------------------------- */

    const handleImageChange = useCallback(
      (index) => {
        if (index !== currentIndex) {
          setCurrentIndex(index);
          setImageLoaded(false);
          setIsLoading(true);
          onImageChange?.(index);
        }
      },
      [currentIndex, onImageChange]
    );

    const scrollToIndex = useCallback(
      (index) => {
        if (flatListRef.current && index >= 0 && index < images.length) {
          flatListRef.current.scrollToIndex({
            index,
            animated: true,
          });
          handleImageChange(index);
        }
      },
      [images.length, handleImageChange]
    );

    /* ---------------------------------------------------------------------- */
    /* Download Image                                                         */
    /* ---------------------------------------------------------------------- */

    const handleDownload = useCallback(async () => {
      // Skip if download is not available on this platform
      if (!isDownloadAvailable) {
        Alert.alert('Info', 'Download is not available on this platform');
        return;
      }

      if (isDownloading) return;

      const mediaItem = images[currentIndex];
      const imageUrl = mediaItem?.url || mediaItem;

      if (!imageUrl) {
        Alert.alert('Error', 'No media available to download');
        return;
      }

      // Skip download for videos
      if (mediaItem?.type === 'video') {
        Alert.alert('Info', 'Videos cannot be downloaded as images');
        return;
      }

      try {
        setIsDownloading(true);

        if (permissionStatus !== 'granted') {
          const { status } = await MediaLibrary.requestPermissionsAsync();
          if (status !== 'granted') {
            Alert.alert('Permission Required', 'Please grant storage permission to download images.');
            return;
          }
        }

        const fileName = `${productName || 'image'}_${Date.now()}.jpg`;
        const fileUri = FileSystem.documentDirectory + fileName;

        const downloadResult = await FileSystem.downloadAsync(imageUrl, fileUri);

        if (downloadResult.status === 200) {
          const asset = await MediaLibrary.createAssetAsync(fileUri);
          await MediaLibrary.createAlbumAsync('Univa', asset, false);
          Alert.alert('Success', 'Image downloaded successfully to your gallery!');
        } else {
          throw new Error('Download failed');
        }
      } catch (error) {
        console.error('Download error:', error);
        Alert.alert('Error', 'Failed to download image. Please try again.');
      } finally {
        setIsDownloading(false);
      }
    }, [currentIndex, images, productName, permissionStatus, isDownloading, isDownloadAvailable]);

    /* ---------------------------------------------------------------------- */
    /* Share Image                                                            */
    /* ---------------------------------------------------------------------- */

    const handleShare = useCallback(async () => {
      const mediaItem = images[currentIndex];
      const imageUrl = mediaItem?.url || mediaItem;

      if (!imageUrl) return;

      if (mediaItem?.type === 'video') {
        Alert.alert('Info', 'Videos cannot be shared as images');
        return;
      }

      try {
        // Check if sharing is available
        const isAvailable = await Sharing.isAvailableAsync();
        if (!isAvailable) {
          Alert.alert('Error', 'Sharing is not available on this device');
          return;
        }

        const fileName = `${productName || 'image'}_${Date.now()}.jpg`;
        const fileUri = FileSystem.documentDirectory + fileName;

        const downloadResult = await FileSystem.downloadAsync(imageUrl, fileUri);

        if (downloadResult.status === 200) {
          await Sharing.shareAsync(fileUri, {
            dialogTitle: `Share ${productName || 'Image'}`,
          });
        }
      } catch (error) {
        console.error('Share error:', error);
        Alert.alert('Error', 'Failed to share image');
      }
    }, [currentIndex, images, productName]);

    /* ---------------------------------------------------------------------- */
    /* Wishlist Toggle                                                        */
    /* ---------------------------------------------------------------------- */

    const handleWishlistToggle = useCallback(() => {
      const newState = !isWishlisted;
      setIsWishlisted(newState);
      onWishlistToggle?.(productId, newState);
    }, [isWishlisted, productId, onWishlistToggle]);

    /* ---------------------------------------------------------------------- */
    /* Render Functions                                                       */
    /* ---------------------------------------------------------------------- */

    const renderMedia = useCallback(
      ({ item, index }) => {
        const mediaType = item?.type || 'image';
        const sourceUrl = item?.url || item;

        // Handle video with expo-video
        if (mediaType === 'video') {
          return (
            <VideoPlayer
              source={sourceUrl}
              style={styles.image}
              onLoad={() => {
                setImageLoaded(true);
                setIsLoading(false);
              }}
              onError={() => {
                setIsLoading(false);
              }}
            />
          );
        }

        // Handle regular image
        const imageSource = {
          uri: sourceUrl,
        };

        return (
          <View style={styles.mediaPage}>
            <ZoomableImage
              source={imageSource}
              style={styles.image}
              onLoad={() => {
                setImageLoaded(true);
                setIsLoading(false);
              }}
              onError={() => {
                setIsLoading(false);
              }}
              onZoomChange={(zoomLevel) => {
                // Handle zoom changes if needed
              }}
            />

            {isLoading && index === currentIndex && (
              <View style={styles.loaderContainer}>
                <ActivityIndicator size="large" color="#FFFFFF" />
              </View>
            )}
          </View>
        );
      },
      [currentIndex, isLoading]
    );

    const renderThumbnail = useCallback(
      ({ item, index }) => {
        const mediaType = item?.type || 'image';
        const sourceUrl = item?.thumbnail || item?.url || item;

        const isActive = currentIndex === index;

        return (
          <Pressable
            onPress={() => scrollToIndex(index)}
            style={[
              styles.thumbnailButton,
              {
                borderColor: isActive ? "#FFFFFF" : "transparent",
              },
            ]}
          >
            {mediaType === 'video' ? (
              <View style={[styles.thumbnailImage, styles.thumbnailPlaceholder]}>
                <MaterialCommunityIcons name="play-circle" size={24} color="#FFFFFF" />
              </View>
            ) : (
              <Image
                source={{ uri: sourceUrl }}
                style={styles.thumbnailImage}
                resizeMode="cover"
              />
            )}
          </Pressable>
        );
      },
      [currentIndex, scrollToIndex]
    );

    /* ---------------------------------------------------------------------- */
    /* Key Extractor                                                          */
    /* ---------------------------------------------------------------------- */

    const keyExtractor = useCallback(
      (item, index) => String(item?.id || item?.url || index),
      []
    );

    /* ---------------------------------------------------------------------- */
    /* FlatList Config                                                        */
    /* ---------------------------------------------------------------------- */

    const getItemLayout = useCallback(
      (_, index) => ({
        length: SCREEN_WIDTH,
        offset: SCREEN_WIDTH * index,
        index,
      }),
      []
    );

    const onScrollEnd = useCallback(
      (event) => {
        const index = Math.round(event.nativeEvent.contentOffset.x / SCREEN_WIDTH);
        handleImageChange(index);
      },
      [handleImageChange]
    );

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <Modal
        visible={visible}
        transparent={true}
        statusBarTranslucent
        onRequestClose={onClose}
      >
        <StatusBar
          translucent
          backgroundColor="black"
          barStyle="light-content"
        />

        <Animated.View
          style={[
            styles.container,
            {
              backgroundColor: "#000000",
              opacity: fadeAnim,
              transform: [{ scale: scaleAnim }],
            },
            style,
          ]}
        >
          {/* ---------------------------------------------------------- */}
          {/* Header                                                     */}
          {/* ---------------------------------------------------------- */}

          <View style={styles.header}>
            <Pressable onPress={onClose} style={styles.iconButton}>
              <MaterialCommunityIcons name="close" size={28} color="#FFFFFF" />
            </Pressable>

            <View style={styles.headerCenter}>
              <Text numberOfLines={1} style={styles.title}>
                {productName}
              </Text>
              <Text style={styles.counter}>
                {currentIndex + 1} / {images.length}
              </Text>
            </View>

            {enableDownload && isDownloadAvailable && (
              <Pressable
                onPress={handleDownload}
                style={styles.iconButton}
                disabled={isDownloading}
              >
                <MaterialCommunityIcons
                  name={isDownloading ? "loading" : "download-outline"}
                  size={24}
                  color="#FFFFFF"
                />
              </Pressable>
            )}
          </View>

          {/* ---------------------------------------------------------- */}
          {/* Media Gallery                                              */}
          {/* ---------------------------------------------------------- */}

          <FlatList
            ref={flatListRef}
            data={images}
            keyExtractor={keyExtractor}
            renderItem={renderMedia}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            initialScrollIndex={initialIndex}
            getItemLayout={getItemLayout}
            onMomentumScrollEnd={onScrollEnd}
            maxToRenderPerBatch={3}
            windowSize={5}
            removeClippedSubviews={true}
          />

          {/* ---------------------------------------------------------- */}
          {/* Previous Button                                            */}
          {/* ---------------------------------------------------------- */}

          {currentIndex > 0 && (
            <Pressable
              onPress={() => scrollToIndex(currentIndex - 1)}
              style={[styles.navButton, styles.leftButton]}
            >
              <MaterialCommunityIcons name="chevron-left" size={34} color="#FFFFFF" />
            </Pressable>
          )}

          {/* ---------------------------------------------------------- */}
          {/* Next Button                                                */}
          {/* ---------------------------------------------------------- */}

          {currentIndex < images.length - 1 && (
            <Pressable
              onPress={() => scrollToIndex(currentIndex + 1)}
              style={[styles.navButton, styles.rightButton]}
            >
              <MaterialCommunityIcons name="chevron-right" size={34} color="#FFFFFF" />
            </Pressable>
          )}

          {/* ---------------------------------------------------------- */}
          {/* Pagination Dots                                            */}
          {/* ---------------------------------------------------------- */}

          {showPagination && images.length > 1 && (
            <View style={styles.pagination}>
              {images.map((_, index) => (
                <Pressable
                  key={index}
                  onPress={() => scrollToIndex(index)}
                  style={[
                    styles.dot,
                    {
                      backgroundColor:
                        currentIndex === index
                          ? "#FFFFFF"
                          : "rgba(255,255,255,0.35)",
                    },
                  ]}
                />
              ))}
            </View>
          )}

          {/* ---------------------------------------------------------- */}
          {/* Thumbnail Strip                                            */}
          {/* ---------------------------------------------------------- */}

          {showThumbnails && images.length > 1 && (
            <View style={styles.thumbnailContainer}>
              <FlatList
                horizontal
                data={images}
                keyExtractor={keyExtractor}
                renderItem={renderThumbnail}
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.thumbnailContent}
                getItemLayout={(_, index) => ({
                  length: 80,
                  offset: 80 * index,
                  index,
                })}
              />
            </View>
          )}

          {/* ---------------------------------------------------------- */}
          {/* Bottom Action Bar                                          */}
          {/* ---------------------------------------------------------- */}

          <View style={styles.actionBar}>
            {enableShare && (
              <Pressable onPress={handleShare} style={styles.actionButton}>
                <MaterialCommunityIcons name="share-variant-outline" size={22} color="#FFFFFF" />
                <Text style={styles.actionText}>Share</Text>
              </Pressable>
            )}

            {enableWishlist && (
              <Pressable onPress={handleWishlistToggle} style={styles.actionButton}>
                <MaterialCommunityIcons
                  name={isWishlisted ? "heart" : "heart-outline"}
                  size={22}
                  color={isWishlisted ? "#EF4444" : "#FFFFFF"}
                />
                <Text style={styles.actionText}>
                  {isWishlisted ? "Saved" : "Wishlist"}
                </Text>
              </Pressable>
            )}

            {enableZoom && (
              <Pressable
                onPress={() => {
                  Alert.alert('Zoom', 'Pinch or double-tap to zoom');
                }}
                style={styles.actionButton}
              >
                <MaterialCommunityIcons name="magnify-plus-outline" size={22} color="#FFFFFF" />
                <Text style={styles.actionText}>Zoom</Text>
              </Pressable>
            )}
          </View>

          {/* ---------------------------------------------------------- */}
          {/* Zoom Hint                                                  */}
          {/* ---------------------------------------------------------- */}

          {showHint && images.length > 0 && (
            <View style={styles.hintContainer}>
              <MaterialCommunityIcons name="gesture-pinch" size={18} color="#FFFFFF" />
              <Text style={styles.hintText}>
                Pinch or double-tap to zoom
              </Text>
            </View>
          )}
        </Animated.View>
      </Modal>
    );
  }
);

ProductGalleryModal.displayName = "ProductGalleryModal";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const imageShape = PropTypes.oneOfType([
  PropTypes.string,
  PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    url: PropTypes.string.isRequired,
    type: PropTypes.oneOf(['image', 'video']),
    thumbnail: PropTypes.string,
  }),
]);

ProductGalleryModal.propTypes = {
  visible: PropTypes.bool,
  images: PropTypes.arrayOf(imageShape),
  initialIndex: PropTypes.number,
  productName: PropTypes.string,
  productId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onClose: PropTypes.func,
  onImageChange: PropTypes.func,
  enableDownload: PropTypes.bool,
  enableShare: PropTypes.bool,
  enableWishlist: PropTypes.bool,
  enableZoom: PropTypes.bool,
  showThumbnails: PropTypes.bool,
  showPagination: PropTypes.bool,
  showHint: PropTypes.bool,
  isWishlisted: PropTypes.bool,
  onWishlistToggle: PropTypes.func,
  style: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
};

ProductGalleryModal.defaultProps = {
  visible: false,
  images: [],
  initialIndex: 0,
  productName: "",
  productId: null,
  onClose: null,
  onImageChange: null,
  enableDownload: true,
  enableShare: true,
  enableWishlist: true,
  enableZoom: true,
  showThumbnails: true,
  showPagination: true,
  showHint: true,
  isWishlisted: false,
  onWishlistToggle: null,
  style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
  },

  /* ------------------------------------------------------------------ */
  /* Header                                                             */
  /* ------------------------------------------------------------------ */

  header: {
    position: "absolute",
    top: 45,
    left: 0,
    right: 0,
    zIndex: 100,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
  },

  iconButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "center",
    alignItems: "center",
  },

  headerCenter: {
    flex: 1,
    alignItems: "center",
    marginHorizontal: 16,
  },

  title: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "700",
  },

  counter: {
    marginTop: 4,
    color: "rgba(255,255,255,0.75)",
    fontSize: 13,
  },

  /* ------------------------------------------------------------------ */
  /* Gallery                                                            */
  /* ------------------------------------------------------------------ */

  mediaPage: {
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT,
    justifyContent: "center",
    alignItems: "center",
  },

  image: {
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT * 0.75,
  },

  video: {
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT * 0.75,
    backgroundColor: '#000',
  },

  videoOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
  },

  videoControlButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "center",
    alignItems: "center",
  },

  loaderContainer: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
  },

  /* ------------------------------------------------------------------ */
  /* Navigation                                                         */
  /* ------------------------------------------------------------------ */

  navButton: {
    position: "absolute",
    top: "50%",
    marginTop: -30,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "center",
    alignItems: "center",
  },

  leftButton: {
    left: 16,
  },

  rightButton: {
    right: 16,
  },

  /* ------------------------------------------------------------------ */
  /* Pagination                                                         */
  /* ------------------------------------------------------------------ */

  pagination: {
    position: "absolute",
    bottom: 165,
    left: 0,
    right: 0,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },

  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginHorizontal: 4,
  },

  /* ------------------------------------------------------------------ */
  /* Thumbnails                                                         */
  /* ------------------------------------------------------------------ */

  thumbnailContainer: {
    position: "absolute",
    bottom: 95,
    left: 0,
    right: 0,
  },

  thumbnailContent: {
    paddingHorizontal: 16,
  },

  thumbnailButton: {
    width: 70,
    height: 70,
    borderRadius: 10,
    borderWidth: 2,
    marginRight: 10,
    overflow: "hidden",
  },

  thumbnailImage: {
    width: "100%",
    height: "100%",
  },

  thumbnailPlaceholder: {
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "center",
    alignItems: "center",
  },

  /* ------------------------------------------------------------------ */
  /* Action Bar                                                         */
  /* ------------------------------------------------------------------ */

  actionBar: {
    position: "absolute",
    bottom: 24,
    left: 16,
    right: 16,
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
    borderRadius: 18,
    paddingVertical: 14,
    backgroundColor: "rgba(0,0,0,0.60)",
  },

  actionButton: {
    alignItems: "center",
  },

  actionText: {
    marginTop: 4,
    color: "#FFFFFF",
    fontSize: 12,
    fontWeight: "600",
  },

  /* ------------------------------------------------------------------ */
  /* Hint                                                               */
  /* ------------------------------------------------------------------ */

  hintContainer: {
    position: "absolute",
    bottom: 200,
    alignSelf: "center",
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: "rgba(0,0,0,0.55)",
  },

  hintText: {
    marginLeft: 8,
    color: "#FFFFFF",
    fontSize: 12,
  },
});

export default ProductGalleryModal;