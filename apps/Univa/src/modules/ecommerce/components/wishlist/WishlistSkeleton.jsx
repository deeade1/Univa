/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/Skeleton.jsx            */
/* -------------------------------------------------------------------------- */

import React, { memo, useEffect, useRef } from "react";
import PropTypes from "prop-types";

import {
  View,
  Animated,
} from "react-native";

import theme from "@/theme";

const Skeleton = memo(({
  width,
  height,
  borderRadius = 8,
  animated = true,
  colors,
  style,
}) => {
  const { colors: themeColors } = theme;
  
  const bgColor = colors?.backgroundColor || themeColors.border;
  const highlightColor = colors?.highlightColor || themeColors.surfaceVariant || "#E5E7EB";
  
  const animatedValue = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!animated) return;

    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(animatedValue, {
          toValue: 1,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(animatedValue, {
          toValue: 0,
          duration: 800,
          useNativeDriver: true,
        }),
      ])
    );

    animation.start();

    return () => animation.stop();
  }, [animated, animatedValue]);

  const opacity = animatedValue.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0.6, 1, 0.6],
  });

  const animatedStyle = animated
    ? {
        opacity,
        backgroundColor: highlightColor,
      }
    : {
        backgroundColor: bgColor,
      };

  return (
    <Animated.View
      style={[
        {
          width,
          height,
          borderRadius,
          backgroundColor: bgColor,
        },
        animated && animatedStyle,
        style,
      ]}
    />
  );
});

Skeleton.displayName = "Skeleton";

Skeleton.propTypes = {
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  borderRadius: PropTypes.number,
  animated: PropTypes.bool,
  colors: PropTypes.shape({
    backgroundColor: PropTypes.string,
    highlightColor: PropTypes.string,
  }),
  style: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
};

Skeleton.defaultProps = {
  borderRadius: 8,
  animated: true,
  colors: null,
  style: null,
};

export default Skeleton;