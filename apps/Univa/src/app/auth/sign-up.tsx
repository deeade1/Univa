
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

import { useAuth } from "../../contexts/AuthContext";
import { createUser } from "../../apollo/auth/authService";

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

export default function SignUpScreen() {
  const router = useRouter();
  const { login } = useAuth();

  const [contact, setContact] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [verificationSent, setVerificationSent] = useState(false);

  const handleSignUp = useCallback(async () => {
    if (loading) return;

    Keyboard.dismiss();
    setError("");

    const normalizedContact = contact.trim();

    if (!normalizedContact) {
      setError("Enter your email address or phone number.");
      return;
    }

    if (password.length < 8) {
      setError("Your password must contain at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Your passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const result = await createUser({
        contact: normalizedContact,
        password,
        sendVerification: true,
      });

      if (result.verificationSent) {
        setVerificationSent(true);
        return;
      }

      if (result.user) {
        await login(result.user);
        router.replace("/(tabs)");
        return;
      }

      setError(
        "Your account was created, but we could not complete sign-in. Please try signing in.",
      );
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "We could not create your account. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [
    contact,
    password,
    confirmPassword,
    loading,
    login,
    router,
  ]);

  if (verificationSent) {
    return (
      <SafeAreaView style={s.safe}>
        <View style={s.confirmation}>
          <View style={s.successIcon}>
            <Ionicons
              name="mail-outline"
              size={34}
              color={C.success}
            />
          </View>

          <Text style={s.title}>You're almost there!</Text>

          <Text style={s.subtitle}>
            Your registration was submitted. Check your email for
            verification instructions, if required, before signing in.
          </Text>

          <Pressable
            style={s.button}
            onPress={() => router.replace("./sign-in")}
          >
            <Text style={s.buttonText}>Go to sign in</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

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
          <View style={s.brandRow}>
            <View style={s.brandIcon}>
              <Ionicons name="apps" size={25} color={C.white} />
            </View>

            <Text style={s.brand}>Univa</Text>
          </View>

          <Text style={s.eyebrow}>GET STARTED</Text>

          <Text style={s.title}>Create your account</Text>

          <Text style={s.subtitle}>
            One account for shopping, transport, real estate, and
            everyday services.
          </Text>

          <Text style={s.label}>Email or phone number</Text>

          <TextInput
            style={s.input}
            value={contact}
            onChangeText={setContact}
            placeholder="Enter email or phone number"
            placeholderTextColor="#9AA3AF"
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="username"
            keyboardType="email-address"
            editable={!loading}
            returnKeyType="next"
          />

          <Text style={s.label}>Password</Text>

          <View style={s.passwordRow}>
            <TextInput
              style={s.passwordInput}
              value={password}
              onChangeText={setPassword}
              placeholder="At least 8 characters"
              placeholderTextColor="#9AA3AF"
              secureTextEntry={!showPassword}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="new-password"
              editable={!loading}
              returnKeyType="next"
            />

            <Pressable
              onPress={() => setShowPassword((value) => !value)}
              hitSlop={10}
              accessibilityRole="button"
              accessibilityLabel={
                showPassword ? "Hide password" : "Show password"
              }
            >
              <Ionicons
                name={
                  showPassword ? "eye-off-outline" : "eye-outline"
                }
                size={21}
                color={C.muted}
              />
            </Pressable>
          </View>

          <Text style={s.label}>Confirm password</Text>

          <TextInput
            style={s.input}
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            placeholder="Enter your password again"
            placeholderTextColor="#9AA3AF"
            secureTextEntry={!showPassword}
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="new-password"
            editable={!loading}
            returnKeyType="go"
            onSubmitEditing={handleSignUp}
          />

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
            onPress={handleSignUp}
            disabled={loading}
            accessibilityRole="button"
            accessibilityState={{ disabled: loading }}
          >
            {loading ? (
              <ActivityIndicator color={C.white} />
            ) : (
              <Text style={s.buttonText}>Create account</Text>
            )}
          </Pressable>

          <View style={s.footerRow}>
            <Text style={s.smallText}>
              Already have an account?
            </Text>

            <Link href="./sign-in" asChild>
              <Pressable disabled={loading}>
                <Text style={s.link}>Sign in</Text>
              </Pressable>
            </Link>
          </View>

          <Text style={s.legal}>
            By creating an account, you agree to Univa's applicable
            terms and privacy policy.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: C.background,
  },
  flex: {
    flex: 1,
  },
  content: {
    flexGrow: 1,
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    paddingHorizontal: 24,
    paddingTop: 22,
    paddingBottom: 32,
  },
  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 28,
  },
  brandIcon: {
    width: 44,
    height: 44,
    borderRadius: 13,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.primary,
  },
  brand: {
    fontSize: 24,
    fontWeight: "800",
    color: C.text,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 2,
    color: C.primary,
    marginBottom: 10,
  },
  title: {
    fontSize: 30,
    lineHeight: 37,
    fontWeight: "800",
    color: C.text,
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 22,
    color: C.muted,
    marginBottom: 19,
  },
  label: {
    fontSize: 13,
    fontWeight: "700",
    color: C.text,
    marginTop: 14,
    marginBottom: 8,
  },
  input: {
    minHeight: 52,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 13,
    paddingHorizontal: 14,
    fontSize: 14,
    color: C.text,
  },
  passwordRow: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 13,
    paddingHorizontal: 14,
  },
  passwordInput: {
    flex: 1,
    minWidth: 0,
    paddingVertical: 13,
    fontSize: 14,
    color: C.text,
  },
  errorBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 9,
    padding: 12,
    marginTop: 17,
    borderRadius: 12,
    backgroundColor: "#FFF2F0",
  },
  errorText: {
    flex: 1,
    fontSize: 13,
    lineHeight: 19,
    color: C.danger,
  },
  button: {
    minHeight: 54,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 20,
    borderRadius: 14,
    backgroundColor: C.primary,
    marginTop: 24,
  },
  buttonPressed: {
    backgroundColor: C.pressed,
  },
  disabled: {
    opacity: 0.7,
  },
  buttonText: {
    fontSize: 15,
    fontWeight: "800",
    color: C.white,
  },
  footerRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 25,
  },
  smallText: {
    fontSize: 13,
    color: C.muted,
  },
  link: {
    fontSize: 13,
    fontWeight: "800",
    color: C.primary,
  },
  legal: {
    fontSize: 11,
    lineHeight: 17,
    textAlign: "center",
    color: C.muted,
    marginTop: 25,
  },
  confirmation: {
    flex: 1,
    maxWidth: 480,
    width: "100%",
    alignSelf: "center",
    justifyContent: "center",
    padding: 28,
  },
  successIcon: {
    width: 72,
    height: 72,
    borderRadius: 24,
    backgroundColor: "#E8F7ED",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 24,
  },
});
