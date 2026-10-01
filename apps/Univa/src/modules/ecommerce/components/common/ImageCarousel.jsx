/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ImageCarousel.jsx       */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useState,
  useMemo,
  useRef,
  useCallback,
  useEffect,
} from "react";

import {
  View,
  StyleSheet,
  Dimensions,
  Pressable,
  Modal,
  StatusBar,
  FlatList,
} from "react-native";

import Carousel from "react-native-reanimated-carousel";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import Animated, {
  useSharedValue,
  useAnimatedStyle,
  interpolate,
  Extrapolation,
} from "react-native-reanimated";

import { Image } from "expo-image";

import theme from "@/theme";

import NetworkImage from "./NetworkImage";

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const { width: SCREEN_WIDTH } = Dimensions.get("window");

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ImageCarousel = memo(
  ({
    /* ---------------------------------------------------------------------- */
    /* Images                                                                  */
    /* ---------------------------------------------------------------------- */

    images = [],
    initialIndex = 0,

    /* ---------------------------------------------------------------------- */
    /* Layout                                                                  */
    /* ---------------------------------------------------------------------- */

    width = SCREEN_WIDTH,
    height = 360,
    borderRadius = 20,
    resizeMode = "contain",
    spacing = 16,

    /* ---------------------------------------------------------------------- */
    /* Features                                                                */
    /* ---------------------------------------------------------------------- */

    loop = false,
    autoPlay = false,
    autoPlayInterval = 4000,
    pagingEnabled = true,
    snapEnabled = true,
    enabled = true,

    /* ---------------------------------------------------------------------- */
    /* UI                                                                      */
    /* ---------------------------------------------------------------------- */

    showDots = true,
    showThumbnails = true,
    showCounter = false,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                  */
    /* ---------------------------------------------------------------------- */

    onIndexChange,
    onImagePress,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,
  }) => {
    const { colors } = theme;

    /* ---------------------------------------------------------------------- */
    /* Refs                                                                   */
    /* ---------------------------------------------------------------------- */

    const carouselRef = useRef(null);
    const thumbnailRef = useRef(null);
    const fullscreenCarouselRef = useRef(null);

    const progress = useSharedValue(0);

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    const [currentIndex, setCurrentIndex] = useState(initialIndex);
    const [fullscreenVisible, setFullscreenVisible] = useState(false);
    const [fullscreenIndex, setFullscreenIndex] = useState(initialIndex);

    /* ---------------------------------------------------------------------- */
    /* Normalize Images                                                        */
    /* ---------------------------------------------------------------------- */

    const data = useMemo(() => {
      return images.map((item, index) => ({
        id: item?.id ?? item?.image?.id ?? `${index}`,
        uri: item?.image?.url ?? item?.url ?? item?.thumbnail ?? null,
        thumbnail:
          item?.image?.thumbnail ??
          item?.thumbnail ??
          item?.image?.url ??
          item?.url ??
          null,
        alt: item?.image?.alt ?? item?.alt ?? "",
      }));
    }, [images]);

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleSnap = useCallback(
      (index) => {
        setCurrentIndex(index);

        thumbnailRef.current?.scrollToIndex({
          index,
          animated: true,
          viewPosition: 0.5,
        });

        onIndexChange?.(index);
      },
      [onIndexChange]
    );

    /* ---------------------------------------------------------------------- */
    /* Render Functions                                                       */
    /* ---------------------------------------------------------------------- */

    const renderItem = useCallback(
      ({ item, index }) => (
        <Pressable
          style={{ flex: 1 }}
          onPress={() => {
            setFullscreenIndex(index);
            setFullscreenVisible(true);
            onImagePress?.(item, index);
          }}
        >
          <NetworkImage
            uri={item.uri}
            alt={item.alt}
            width="100%"
            height="100%"
            borderRadius={borderRadius}
            resizeMode={resizeMode}
          />
        </Pressable>
      ),
      [borderRadius, resizeMode, onImagePress]
    );

    const renderDot = useCallback(
      (_, index) => {
        const animatedStyle = useAnimatedStyle(() => {
          const distance = Math.abs(progress.value - index);

          return {
            width: interpolate(
              distance,
              [0, 1],
              [24, 8],
              Extrapolation.CLAMP
            ),
            opacity: interpolate(
              distance,
              [0, 1],
              [1, 0.35],
              Extrapolation.CLAMP
            ),
          };
        });

        return (
          <Animated.View
            key={index}
            style={[
              styles.dot,
              animatedStyle,
              {
                backgroundColor:
                  index === currentIndex ? colors.primary : colors.border,
              },
            ]}
          />
        );
      },
      [currentIndex, colors, progress]
    );

    const renderThumbnail = useCallback(
      ({ item, index }) => (
        <Pressable
          onPress={() => {
            carouselRef.current?.scrollTo({
              index,
              animated: true,
            });
          }}
          style={[
            styles.thumbnail,
            {
              borderColor:
                index === currentIndex ? colors.primary : colors.border,
              borderWidth: index === currentIndex ? 2 : 1,
            },
          ]}
        >
          <NetworkImage
            uri={item.thumbnail}
            width={68}
            height={68}
            borderRadius={10}
          />
        </Pressable>
      ),
      [currentIndex, colors]
    );

    const renderFullscreenItem = useCallback(
      ({ item }) => (
        <View style={styles.fullscreenSlide}>
          <NetworkImage
            uri={item.uri}
            alt={item.alt}
            width="100%"
            height="100%"
            resizeMode="contain"
            borderRadius={0}
          />
        </View>
      ),
      []
    );

    /* ---------------------------------------------------------------------- */
    /* Preload Images                                                         */
    /* ---------------------------------------------------------------------- */

    useEffect(() => {
      if (!data.length) return;

      Image.prefetch(data.filter((i) => i.uri).map((i) => i.uri));
    }, [data]);

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <View
        style={[
          styles.container,
          {
            width,
          },
          style,
        ]}
      >
        {/* -------------------------------------------------------------- */}
        {/* Carousel                                                       */}
        {/* -------------------------------------------------------------- */}

        <Carousel
          ref={carouselRef}
          data={data}
          width={width}
          height={height}
          loop={loop}
          enabled={enabled}
          pagingEnabled={pagingEnabled}
          snapEnabled={snapEnabled}
          autoPlay={autoPlay}
          autoPlayInterval={autoPlayInterval}
          defaultIndex={initialIndex}
          onProgressChange={progress}
          onSnapToItem={handleSnap}
          renderItem={renderItem}
        />

        {/* -------------------------------------------------------------- */}
        {/* Pagination Dots                                                */}
        {/* -------------------------------------------------------------- */}

        {showDots && data.length > 1 && (
          <View style={styles.pagination}>{data.map(renderDot)}</View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Counter                                                        */}
        {/* -------------------------------------------------------------- */}

        {showCounter && (
          <View style={styles.counter}>
            <Animated.Text
              style={[
                styles.counterText,
                {
                  color: colors.text,
                },
              ]}
            >
              {currentIndex + 1} / {data.length}
            </Animated.Text>
          </View>
        )}

        {/* -------------------------------------------------------------- */}
        {/* Thumbnails                                                     */}
        {/* -------------------------------------------------------------- */}

        {showThumbnails && data.length > 1 && (
          <FlatList
            ref={thumbnailRef}
            horizontal
            data={data}
            keyExtractor={(item) => item.id}
            renderItem={renderThumbnail}
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.thumbnailList}
            getItemLayout={(_, index) => ({
              length: 80,
              offset: 80 * index,
              index,
            })}
          />
        )}

        {/* -------------------------------------------------------------- */}
        {/* Fullscreen Modal                                               */}
        {/* -------------------------------------------------------------- */}

        <Modal
          visible={fullscreenVisible}
          animationType="fade"
          transparent={false}
          statusBarTranslucent
          onRequestClose={() => setFullscreenVisible(false)}
        >
          <StatusBar hidden />

          <View
            style={[
              styles.fullscreenContainer,
              {
                backgroundColor: colors.background,
              },
            ]}
          >
            {/* Close Button */}
            <Pressable
              style={styles.closeButton}
              onPress={() => setFullscreenVisible(false)}
            >
              <MaterialCommunityIcons name="close" size={30} color="#FFFFFF" />
            </Pressable>

            {/* Counter */}
            <View style={styles.fullscreenCounter}>
              <Animated.Text style={styles.fullscreenCounterText}>
                {fullscreenIndex + 1} / {data.length}
              </Animated.Text>
            </View>

            {/* Fullscreen Carousel */}
            <Carousel
              ref={fullscreenCarouselRef}
              width={SCREEN_WIDTH}
              height={Dimensions.get("window").height}
              data={data}
              defaultIndex={fullscreenIndex}
              loop={loop}
              pagingEnabled
              renderItem={renderFullscreenItem}
              onSnapToItem={(i) => setFullscreenIndex(i)}
            />
          </View>
        </Modal>
      </View>
    );
  }
);

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ImageCarousel.displayName = "ImageCarousel";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    alignSelf: "center",
  },

  pagination: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 16,
  },

  dot: {
    height: 8,
    borderRadius: 100,
    marginHorizontal: 4,
  },

  counter: {
    alignItems: "center",
    marginTop: 18,
  },

  counterText: {
    fontWeight: "700",
    fontSize: 14,
  },

  thumbnailList: {
    paddingTop: 18,
    paddingHorizontal: 12,
  },

  thumbnail: {
    marginRight: 12,
    borderRadius: 10,
    overflow: "hidden",
  },

  fullscreenContainer: {
    flex: 1,
    justifyContent: "center",
  },

  fullscreenSlide: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },

  closeButton: {
    position: "absolute",
    top: 55,
    right: 24,
    zIndex: 100,
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,.45)",
  },

  fullscreenCounter: {
    position: "absolute",
    top: 58,
    left: 24,
    zIndex: 100,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "rgba(0,0,0,.45)",
  },

  fullscreenCounterText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default ImageCarousel;