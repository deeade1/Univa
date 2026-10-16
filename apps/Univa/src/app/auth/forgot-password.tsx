
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Link, useRouter } from "expo-router";

import { forgotPassword } from "../../apollo/auth/authService";

const C = {
  primary: "#0A84FF",
  pressed: "#0066CC",
  background: "#FFFFFF",
  text: "#172033",
  muted: "#737D8C",
  border: "#E1E6ED",
  danger: "#D92D20",
  success: "#16803D",
  white: "#FFFFFF",
};

export default function ForgotPasswordScreen() {
  const router = useRouter();

  const [contact, setContact] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleRequestReset = useCallback(async () => {
    if (loading) return;

    Keyboard.dismiss();
    setError("");

    if (!contact.trim()) {
      setError("Enter your email address or phone number.");
      return;
    }

    setLoading(true);

    try {
      await forgotPassword({
        contact: contact.trim(),
      });

      // Show a generic confirmation regardless of account existence.
      setSubmitted(true);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "We could not process your request. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }, [contact, loading]);

  return (
    <SafeAreaView style={s.safe}>
      <KeyboardAvoidingView
        style={s.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={s.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <Link href="./sign-in" asChild>
            <Pressable style={s.backRow} accessibilityRole="button">
              <Ionicons name="arrow-back" size={21} color={C.text} />
              <Text style={s.backText}>Back to sign in</Text>
            </Pressable>
          </Link>

          <View style={s.brandRow}>
            <View style={s.brandIcon}>
              <Ionicons name="apps" size={25} color={C.white} />
            </View>
            <Text style={s.brand}>Univa</Text>
          </View>

          <View style={s.illustration}>
            <Ionicons
              name={submitted ? "mail-open-outline" : "lock-closed-outline"}
              size={38}
              color={C.primary}
            />
          </View>

          <Text style={s.title}>
            {submitted ? "Check your messages" : "Forgot your password?"}
          </Text>

          <Text style={s.subtitle}>
            {submitted
              ? "If an account matches the details you entered, you will receive password-reset instructions. Check your inbox or messages, including your spam folder."
              : "Enter the email address or phone number associated with your Univa account to request password-reset instructions."}
          </Text>

          {!submitted ? (
            <View>
              <Text style={s.label}>Email or phone number</Text>

              <View style={s.inputRow}>
                <Ionicons name="person-outline" size={20} color={C.muted} />
                <TextInput
                  style={s.input}
                  value={contact}
                  onChangeText={(value) => {
                    setContact(value);
                    setError("");
                  }}
                  placeholder="Enter email or phone number"
                  placeholderTextColor="#9AA3AF"
                  autoCapitalize="none"
                  autoCorrect={false}
                  autoComplete="username"
                  keyboardType="email-address"
                  editable={!loading}
                  returnKeyType="go"
                  onSubmitEditing={handleRequestReset}
                  accessibilityLabel="Email or phone number"
                />
              </View>

              {!!error && (
                <View style={s.errorBox} accessibilityRole="alert">
                  <Ionicons
                    name="alert-circle-outline"
                    size={19}
                    color={C.danger}
                  />
                  <Text style={s.errorText}>{error}</Text>
                </View>
              )}

              <Pressable
                style={({ pressed }) => [
                  s.button,
                  pressed && !loading && s.buttonPressed,
                  loading && s.disabled,
                ]}
                onPress={handleRequestReset}
                disabled={loading}
                accessibilityRole="button"
                accessibilityState={{ disabled: loading }}
              >
                {loading ? (
                  <ActivityIndicator color={C.white} />
                ) : (
                  <Text style={s.buttonText}>Send reset instructions</Text>
                )}
              </Pressable>
            </View>
          ) : (
            <View>
              <View style={s.confirmationBox}>
                <Ionicons
                  name="checkmark-circle-outline"
                  size={25}
                  color={C.success}
                />
                <Text style={s.confirmationText}>
                  For your security, this confirmation does not reveal
                  whether an account exists for those details.
                </Text>
              </View>

              <Pressable
                style={s.button}
                onPress={() => router.replace("./sign-in")}
              >
                <Text style={s.buttonText}>Return to sign in</Text>
              </Pressable>

              <Pressable
                style={s.secondaryButton}
                onPress={() => {
                  setSubmitted(false);
                  setError("");
                }}
              >
                <Text style={s.secondaryText}>
                  Try another email or number
                </Text>
              </Pressable>
            </View>
          )}

          <View style={s.securityRow}>
            <Ionicons
              name="shield-checkmark-outline"
              size={18}
              color={C.success}
            />
            <Text style={s.securityText}>
              Never share your password or reset code with anyone.
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.background },
  flex: { flex: 1 },
  content: {
    flexGrow: 1, width: "100%", maxWidth: 520,
    alignSelf: "center", paddingHorizontal: 24,
    paddingTop: 20, paddingBottom: 32,
  },
  backRow: {
    flexDirection: "row", alignItems: "center", alignSelf: "flex-start",
    gap: 9, paddingVertical: 10, marginBottom: 27,
  },
  backText: { fontSize: 14, fontWeight: "600", color: C.text },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 35 },
  brandIcon: {
    width: 44, height: 44, borderRadius: 13,
    alignItems: "center", justifyContent: "center", backgroundColor: C.primary,
  },
  brand: { fontSize: 24, fontWeight: "800", color: C.text },
  illustration: {
    width: 78, height: 78, borderRadius: 24, backgroundColor: "#EAF4FF",
    alignItems: "center", justifyContent: "center", marginBottom: 25,
  },
  title: { fontSize: 30, lineHeight: 37, fontWeight: "800", color: C.text, marginBottom: 12 },
  subtitle: { fontSize: 14, lineHeight: 23, color: C.muted, marginBottom: 27 },
  label: { fontSize: 13, fontWeight: "700", color: C.text, marginBottom: 9 },
  inputRow: {
    minHeight: 55, flexDirection: "row", alignItems: "center", gap: 11,
    paddingHorizontal: 14, borderWidth: 1, borderColor: C.border, borderRadius: 13,
  },
  input: { flex: 1, minWidth: 0, paddingVertical: 14, fontSize: 14, color: C.text },
  errorBox: {
    flexDirection: "row", alignItems: "flex-start", gap: 9,
    padding: 12, marginTop: 17, borderRadius: 12, backgroundColor: "#FFF2F0",
  },
  errorText: { flex: 1, fontSize: 13, lineHeight: 19, color: C.danger },
  button: {
    minHeight: 54, alignItems: "center", justifyContent: "center",
    paddingHorizontal: 20, borderRadius: 14, backgroundColor: C.primary, marginTop: 24,
  },
  buttonPressed: { backgroundColor: C.pressed },
  disabled: { opacity: 0.7 },
  buttonText: { fontSize: 15, fontWeight: "800", color: C.white },
  confirmationBox: {
    flexDirection: "row", alignItems: "flex-start", gap: 11,
    padding: 14, backgroundColor: "#F0F9F2", borderRadius: 13, marginTop: 5,
  },
  confirmationText: { flex: 1, fontSize: 13, lineHeight: 20, color: C.text },
  secondaryButton: { minHeight: 48, alignItems: "center", justifyContent: "center", marginTop: 10 },
  secondaryText: { fontSize: 13, fontWeight: "700", color: C.primary },
  securityRow: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, marginTop: 38,
  },
  securityText: { flexShrink: 1, fontSize: 11, lineHeight: 17, textAlign: "center", color: C.muted },
});
