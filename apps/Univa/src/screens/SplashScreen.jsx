import React from "react";
import { ActivityIndicator, Text } from "react-native";
import Animated, { FadeIn, FadeOut } from "react-native-reanimated";

export default function SplashScreen() {
  return (
    <Animated.View
      entering={FadeIn.duration(800)}
      exiting={FadeOut.duration(600)}
      style={{
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#fff",
      }}
    >
      <ActivityIndicator size="large" color="#0A84FF" />
      <Text style={{ marginTop: 20, fontSize: 16, color: "#333" }}>
        Checking biometrics...
      </Text>
    </Animated.View>
  );
}
