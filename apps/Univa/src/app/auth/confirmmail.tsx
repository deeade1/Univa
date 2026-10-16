import { useCallback, useEffect, useRef, useState } from "react";
import { router, useLocalSearchParams } from "expo-router";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { confirmEmail } from "../../apollo/auth/authService";

type VerificationStatus =
  | "verifying"
  | "success"
  | "error"
  | "missing-token";

export default function ConfirmMailScreen() {
  const params = useLocalSearchParams<{
    token?: string | string[];
  }>();

  const token = Array.isArray(params.token)
    ? params.token[0]
    : params.token;

  const startedToken = useRef<string | null>(null);

  const [status, setStatus] =
    useState<VerificationStatus>("verifying");

  const [message, setMessage] = useState(
    "Please wait while we verify your email address.",
  );

  const verifyEmail = useCallback(async (value: string) => {
    setStatus("verifying");
    setMessage("Verifying your email address...");

    try {
      const result = await confirmEmail(value);

      setStatus("success");
      setMessage(result.message);
    } catch (error: unknown) {
      setStatus("error");
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to verify your email address. Please try again.",
      );
    }
  }, []);

  useEffect(() => {
    if (!token?.trim()) {
      setStatus("missing-token");
      setMessage(
        "This verification link is missing its token. Please open the complete link from your email.",
      );
      return;
    }

    if (startedToken.current === token) {
      return;
    }

    startedToken.current = token;
    void verifyEmail(token);
  }, [token, verifyEmail]);

  const isVerifying = status === "verifying";

  const title =
    status === "success"
      ? "Email verified!"
      : status === "missing-token"
        ? "Invalid verification link"
        : status === "error"
          ? "Verification unsuccessful"
          : "Verifying your email";

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View
          style={[
            styles.iconContainer,
            status === "success" && styles.successIcon,
            (status === "error" || status === "missing-token") &&
              styles.errorIcon,
          ]}
        >
          {isVerifying ? (
            <ActivityIndicator size="large" color="#2563EB" />
          ) : (
            <Text style={styles.icon}>
              {status === "success"
                ? "✓"
                : status === "error" || status === "missing-token"
                  ? "!"
                  : "✉"}
            </Text>
          )}
        </View>

        <Text style={styles.title}>{title}</Text>

        <Text style={styles.message}>{message}</Text>

        {status === "success" && (
          <Pressable
            style={styles.primaryButton}
            onPress={() => router.replace("/auth/sign-in")}
          >
            <Text style={styles.primaryButtonText}>
              Continue to sign in
            </Text>
          </Pressable>
        )}

        {status === "error" && token && (
          <Pressable
            style={styles.primaryButton}
            onPress={() => void verifyEmail(token)}
            disabled={isVerifying}
          >
            <Text style={styles.primaryButtonText}>
              Try again
            </Text>
          </Pressable>
        )}

        {status === "missing-token" && (
          <Pressable
            style={styles.primaryButton}
            onPress={() => router.replace("/auth/sign-in")}
          >
            <Text style={styles.primaryButtonText}>
              Return to sign in
            </Text>
          </Pressable>
        )}

        <Text style={styles.footer}>
          Univa · Your account, connected.
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },
  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 28,
  },
  iconContainer: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: "#EFF6FF",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 28,
  },
  successIcon: {
    backgroundColor: "#DCFCE7",
  },
  errorIcon: {
    backgroundColor: "#FEE2E2",
  },
  icon: {
    fontSize: 38,
    fontWeight: "700",
    color: "#2563EB",
  },
  title: {
    fontSize: 26,
    fontWeight: "700",
    color: "#111827",
    textAlign: "center",
    marginBottom: 14,
  },
  message: {
    fontSize: 16,
    lineHeight: 24,
    color: "#6B7280",
    textAlign: "center",
    marginBottom: 28,
  },
  primaryButton: {
    width: "100%",
    minHeight: 52,
    borderRadius: 12,
    backgroundColor: "#2563EB",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 20,
  },
  primaryButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  footer: {
    marginTop: 32,
    fontSize: 13,
    color: "#9CA3AF",
    textAlign: "center",
  },
});