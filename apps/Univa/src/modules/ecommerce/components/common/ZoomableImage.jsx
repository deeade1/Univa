/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/ZoomableImage.jsx       */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useCallback,
  useImperativeHandle,
  forwardRef,
} from "react";

import {
  StyleSheet,
} from "react-native";

import { Image } from "expo-image";

import Animated, {
  runOnJS,
  useAnimatedStyle,
  useDerivedValue,
  useSharedValue,
  withDecay,
  withSpring,
  cancelAnimation,
} from "react-native-reanimated";

import {
  Gesture,
  GestureDetector,
} from "react-native-gesture-handler";

/* -------------------------------------------------------------------------- */
/* Animated Components                                                        */
/* -------------------------------------------------------------------------- */

const AnimatedImage =
  Animated.createAnimatedComponent(
    Image
  );

/* -------------------------------------------------------------------------- */
/* Configuration                                                              */
/* -------------------------------------------------------------------------- */

const DEFAULT_MIN_SCALE = 1;

const DEFAULT_MAX_SCALE = 5;

const DEFAULT_DOUBLE_TAP_SCALE = 2.5;

const SPRING_CONFIG = {
  damping: 18,
  stiffness: 220,
};

const RUBBER_BAND_FACTOR = 0.35;

/* -------------------------------------------------------------------------- */
/* Worklet Helpers                                                            */
/* -------------------------------------------------------------------------- */

const clamp = (value, min, max) => {
  "worklet";
  return Math.min(max, Math.max(min, value));
};

const rubberBand = (value, limit) => {
  "worklet";
  if (limit <= 0) {
    return 0;
  }
  const distance = Math.abs(value);
  if (distance <= limit) {
    return value;
  }
  const excess = distance - limit;
  return Math.sign(value) * (limit + excess * RUBBER_BAND_FACTOR);
};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ZoomableImage = memo(
  forwardRef(({
    uri,
    alt = "",
    width = "100%",
    height = "100%",
    resizeMode = "contain",
    minScale = DEFAULT_MIN_SCALE,
    maxScale = DEFAULT_MAX_SCALE,
    doubleTapScale = DEFAULT_DOUBLE_TAP_SCALE,
    onTap,
    onDoubleTap,
    onZoomChange,
    onZoomStart,
    onZoomEnd,
    style,
    imageStyle,
  }, ref) => {

    /* ---------------------------------------------------------------------- */
    /* Shared Values                                                          */
    /* ---------------------------------------------------------------------- */

    const scale = useSharedValue(minScale);
    const savedScale = useSharedValue(minScale);
    const translateX = useSharedValue(0);
    const translateY = useSharedValue(0);
    const startX = useSharedValue(0);
    const startY = useSharedValue(0);

    /* ---------------------------------------------------------------------- */
    /* Pinch State                                                            */
    /* ---------------------------------------------------------------------- */

    const pinchFocalX = useSharedValue(0);
    const pinchFocalY = useSharedValue(0);
    const pinchTranslateX = useSharedValue(0);
    const pinchTranslateY = useSharedValue(0);

    /* ---------------------------------------------------------------------- */
    /* Container Measurements                                                 */
    /* ---------------------------------------------------------------------- */

    const containerWidth = useSharedValue(0);
    const containerHeight = useSharedValue(0);

    /* ---------------------------------------------------------------------- */
    /* Image Measurements                                                     */
    /* ---------------------------------------------------------------------- */

    const imageWidth = useSharedValue(0);
    const imageHeight = useSharedValue(0);
    const displayWidth = useSharedValue(0);
    const displayHeight = useSharedValue(0);

    /* ---------------------------------------------------------------------- */
    /* Translation Limits                                                     */
    /* ---------------------------------------------------------------------- */

    const maxTranslateX = useSharedValue(0);
    const maxTranslateY = useSharedValue(0);

    /* ---------------------------------------------------------------------- */
    /* Reset Method                                                           */
    /* ---------------------------------------------------------------------- */

    const reset = useCallback(() => {
      scale.value = withSpring(minScale, SPRING_CONFIG);
      savedScale.value = minScale;
      translateX.value = withSpring(0, SPRING_CONFIG);
      translateY.value = withSpring(0, SPRING_CONFIG);
    }, [minScale]);

    /* ---------------------------------------------------------------------- */
    /* Expose Reset Method                                                    */
    /* ---------------------------------------------------------------------- */

    useImperativeHandle(
      ref,
      () => ({
        reset,
      }),
      [reset]
    );

    /* ---------------------------------------------------------------------- */
    /* Automatically Update Bounds                                            */
    /* ---------------------------------------------------------------------- */

    useDerivedValue(() => {
      if (
        imageWidth.value === 0 ||
        imageHeight.value === 0 ||
        containerWidth.value === 0 ||
        containerHeight.value === 0
      ) {
        return;
      }

      const imageAspect = imageWidth.value / imageHeight.value;
      const containerAspect = containerWidth.value / containerHeight.value;

      if (imageAspect > containerAspect) {
        displayWidth.value = containerWidth.value;
        displayHeight.value = containerWidth.value / imageAspect;
      } else {
        displayHeight.value = containerHeight.value;
        displayWidth.value = containerHeight.value * imageAspect;
      }

      const scaledWidth = displayWidth.value * scale.value;
      const scaledHeight = displayHeight.value * scale.value;

      maxTranslateX.value = Math.max(0, (scaledWidth - displayWidth.value) / 2);
      maxTranslateY.value = Math.max(0, (scaledHeight - displayHeight.value) / 2);
    });

    /* ---------------------------------------------------------------------- */
    /* Layout                                                                 */
    /* ---------------------------------------------------------------------- */

    const handleLayout = useCallback((event) => {
      containerWidth.value = event.nativeEvent.layout.width;
      containerHeight.value = event.nativeEvent.layout.height;

      translateX.value = clamp(
        translateX.value,
        -maxTranslateX.value,
        maxTranslateX.value
      );

      translateY.value = clamp(
        translateY.value,
        -maxTranslateY.value,
        maxTranslateY.value
      );
    }, []);

    /* ---------------------------------------------------------------------- */
    /* Pinch Gesture                                                          */
    /* ---------------------------------------------------------------------- */

    const pinchGesture = Gesture.Pinch()
      .onBegin((event) => {
        cancelAnimation(translateX);
        cancelAnimation(translateY);

        savedScale.value = scale.value;
        pinchTranslateX.value = translateX.value;
        pinchTranslateY.value = translateY.value;
        pinchFocalX.value = event.focalX;
        pinchFocalY.value = event.focalY;

        if (onZoomStart) {
          runOnJS(onZoomStart)();
        }
      })
      .onUpdate((event) => {
        const nextScale = clamp(
          savedScale.value * event.scale,
          minScale,
          maxScale
        );

        const scaleRatio = nextScale / savedScale.value;
        const centerX = containerWidth.value / 2;
        const centerY = containerHeight.value / 2;

        translateX.value = pinchTranslateX.value + (pinchFocalX.value - centerX) * (1 - scaleRatio);
        translateY.value = pinchTranslateY.value + (pinchFocalY.value - centerY) * (1 - scaleRatio);

        scale.value = nextScale;

        translateX.value = rubberBand(translateX.value, maxTranslateX.value);
        translateY.value = rubberBand(translateY.value, maxTranslateY.value);
      })
      .onEnd(() => {
        savedScale.value = scale.value;

        translateX.value = withSpring(
          clamp(translateX.value, -maxTranslateX.value, maxTranslateX.value),
          SPRING_CONFIG
        );

        translateY.value = withSpring(
          clamp(translateY.value, -maxTranslateY.value, maxTranslateY.value),
          SPRING_CONFIG
        );

        if (onZoomChange) {
          runOnJS(onZoomChange)(scale.value);
        }

        if (onZoomEnd) {
          runOnJS(onZoomEnd)();
        }
      });

    /* ---------------------------------------------------------------------- */
    /* Pan Gesture                                                            */
    /* ---------------------------------------------------------------------- */

    const panGesture = Gesture.Pan()
      .onBegin(() => {
        cancelAnimation(translateX);
        cancelAnimation(translateY);

        startX.value = translateX.value;
        startY.value = translateY.value;
      })
      .onUpdate((event) => {
        if (scale.value <= minScale + 0.01) {
          return;
        }

        const nextX = startX.value + event.translationX;
        const nextY = startY.value + event.translationY;

        translateX.value = rubberBand(nextX, maxTranslateX.value);
        translateY.value = rubberBand(nextY, maxTranslateY.value);
      })
      .onEnd((event) => {
        if (scale.value <= minScale + 0.01) {
          translateX.value = withSpring(0, SPRING_CONFIG);
          translateY.value = withSpring(0, SPRING_CONFIG);
          return;
        }

        translateX.value = withDecay({
          velocity: event.velocityX,
          deceleration: 0.995,
          clamp: [-maxTranslateX.value, maxTranslateX.value],
          rubberBandEffect: true,
        });

        translateY.value = withDecay({
          velocity: event.velocityY,
          deceleration: 0.995,
          clamp: [-maxTranslateY.value, maxTranslateY.value],
          rubberBandEffect: true,
        });
      });

    /* ---------------------------------------------------------------------- */
    /* Double Tap Gesture                                                     */
    /* ---------------------------------------------------------------------- */

    const doubleTapGesture = Gesture.Tap()
      .numberOfTaps(2)
      .maxDuration(250)
      .onEnd((event) => {
        const zoomingIn = scale.value <= minScale + 0.01;

        if (zoomingIn) {
          const targetScale = clamp(doubleTapScale, minScale, maxScale);
          const centerX = containerWidth.value / 2;
          const centerY = containerHeight.value / 2;
          const scaleRatio = targetScale / scale.value;

          const targetTranslateX = translateX.value + (event.x - centerX) * (1 - scaleRatio);
          const targetTranslateY = translateY.value + (event.y - centerY) * (1 - scaleRatio);

          scale.value = withSpring(targetScale, SPRING_CONFIG);
          savedScale.value = targetScale;

          translateX.value = withSpring(
            clamp(targetTranslateX, -maxTranslateX.value, maxTranslateX.value),
            SPRING_CONFIG
          );

          translateY.value = withSpring(
            clamp(targetTranslateY, -maxTranslateY.value, maxTranslateY.value),
            SPRING_CONFIG
          );
        } else {
          scale.value = withSpring(minScale, SPRING_CONFIG);
          savedScale.value = minScale;
          translateX.value = withSpring(0, SPRING_CONFIG);
          translateY.value = withSpring(0, SPRING_CONFIG);
        }

        if (onDoubleTap) {
          runOnJS(onDoubleTap)();
        }
      });

    /* ---------------------------------------------------------------------- */
    /* Single Tap Gesture                                                     */
    /* ---------------------------------------------------------------------- */

    const singleTapGesture = Gesture.Tap()
      .numberOfTaps(1)
      .maxDuration(250)
      .onEnd(() => {
        if (onTap) {
          runOnJS(onTap)();
        }
      });

    /* ---------------------------------------------------------------------- */
    /* Gesture Composition                                                    */
    /* ---------------------------------------------------------------------- */

    const composedGesture = Gesture.Simultaneous(
      pinchGesture,
      panGesture,
      Gesture.Exclusive(doubleTapGesture, singleTapGesture)
    );

    /* ---------------------------------------------------------------------- */
    /* Animated Style                                                         */
    /* ---------------------------------------------------------------------- */

    const animatedStyle = useAnimatedStyle(() => {
      return {
        transform: [
          { translateX: translateX.value },
          { translateY: translateY.value },
          { scale: scale.value },
        ],
      };
    });

    /* ---------------------------------------------------------------------- */
    /* Render                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
      <GestureDetector gesture={composedGesture}>
        <Animated.View
          onLayout={handleLayout}
          style={[
            styles.container,
            {
              width,
              height,
            },
            style,
          ]}
          collapsable={false}
          renderToHardwareTextureAndroid
        >
          <AnimatedImage
            source={{ uri }}
            accessibilityLabel={alt}
            contentFit={resizeMode}
            cachePolicy="memory-disk"
            transition={250}
            recyclingKey={uri}
            style={[
              styles.image,
              imageStyle,
              animatedStyle,
            ]}
            onLoad={(event) => {
              const source = event.source ?? {};
              imageWidth.value = source.width ?? 0;
              imageHeight.value = source.height ?? 0;
            }}
          />
        </Animated.View>
      </GestureDetector>
    );
  })
);

/* -------------------------------------------------------------------------- */

ZoomableImage.displayName = "ZoomableImage";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    overflow: "hidden",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "transparent",
  },
  image: {
    width: "100%",
    height: "100%",
  },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default ZoomableImage;