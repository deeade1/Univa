
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
import { signIn } from "../../apollo/auth/authService";

const C = {
  primary: "#0A84FF",
  pressed: "#0066CC",
  background: "#FFFFFF",
  text: "#172033",
  muted: "#737D8C",
  border: "#E1E6ED",
  danger: "#D92D20",
  white: "#FFFFFF",
};

export default function SignInScreen() {
  const router = useRouter();
  const { login } = useAuth();

  const [contact, setContact] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSignIn = useCallback(async () => {
    if (loading) return;

    Keyboard.dismiss();
    setError("");

    if (!contact.trim()) {
      setError("Enter your email address or phone number.");
      return;
    }

    if (!password) {
      setError("Enter your password.");
      return;
    }

    setLoading(true);

    try {
      // signIn() returns AuthUser directly, not { user }.
      const user = await signIn({
        contact: contact.trim(),
        password,
        rememberMe,
      });

      // Required: update AuthContext after session persistence.
      await login(user);

      router.replace("/(tabs)");
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to sign in. Please check your details and try again."
      );
    } finally {
      setLoading(false);
    }
  }, [contact, password, rememberMe, loading, login, router]);

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
              <Ionicons name="apps" size={26} color={C.white} />
            </View>
            <Text style={s.brand}>Univa</Text>
          </View>

          <Text style={s.eyebrow}>WELCOME BACK</Text>
          <Text style={s.title}>Sign in to Univa</Text>
          <Text style={s.subtitle}>
            Shop, travel, discover properties, and access your
            everyday services from one account.
          </Text>

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
              returnKeyType="next"
              accessibilityLabel="Email or phone number"
            />
          </View>

          <Text style={s.label}>Password</Text>
          <View style={s.inputRow}>
            <Ionicons
              name="lock-closed-outline"
              size={20}
              color={C.muted}
            />
            <TextInput
              style={s.input}
              value={password}
              onChangeText={(value) => {
                setPassword(value);
                setError("");
              }}
              placeholder="Enter your password"
              placeholderTextColor="#9AA3AF"
              secureTextEntry={!showPassword}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="current-password"
              editable={!loading}
              returnKeyType="go"
              onSubmitEditing={handleSignIn}
              accessibilityLabel="Password"
            />
            <Pressable
              onPress={() => setShowPassword((value) => !value)}
              hitSlop={10}
              accessibilityRole="button"
              accessibilityLabel={showPassword ? "Hide password" : "Show password"}
            >
              <Ionicons
                name={showPassword ? "eye-off-outline" : "eye-outline"}
                size={21}
                color={C.muted}
              />
            </Pressable>
          </View>

          <View style={s.options}>
            <Pressable
              style={s.rememberRow}
              onPress={() => setRememberMe((value) => !value)}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: rememberMe }}
            >
              <View style={[s.checkbox, rememberMe && s.checkboxChecked]}>
                {rememberMe && (
                  <Ionicons name="checkmark" size={14} color={C.white} />
                )}
              </View>
              <Text style={s.smallText}>Remember me</Text>
            </Pressable>

            <Link href="./forgot-password" asChild>
              <Pressable disabled={loading}>
                <Text style={s.link}>Forgot password?</Text>
              </Pressable>
            </Link>
          </View>

          {!!error && (
            <View style={s.errorBox} accessibilityRole="alert">
              <Ionicons name="alert-circle-outline" size={19} color={C.danger} />
              <Text style={s.errorText}>{error}</Text>
            </View>
          )}

          <Pressable
            style={({ pressed }) => [
              s.button,
              pressed && !loading && s.buttonPressed,
              loading && s.disabled,
            ]}
            onPress={handleSignIn}
            disabled={loading}
            accessibilityRole="button"
            accessibilityState={{ disabled: loading }}
          >
            {loading ? (
              <ActivityIndicator color={C.white} />
            ) : (
              <>
                <Text style={s.buttonText}>Sign in</Text>
                <Ionicons name="arrow-forward" size={20} color={C.white} />
              </>
            )}
          </Pressable>

                    
          <View style={s.footerRow}>
            <Text style={s.smallText}>Don't have an account?</Text>

            <Link href="./sign-up" asChild>
              <Pressable
                disabled={loading}
                accessibilityRole="button"
                accessibilityLabel="Sign up"
              >
                <Text style={s.link}>Sign up</Text>
              </Pressable>
            </Link>
          </View>
          <Text style={s.security}>
            <Ionicons name="shield-checkmark-outline" size={15} color="#16803D" />
            {" "}Your account and personal information matter to us.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.background },
  flex: { flex: 1 },
  content: {
    flexGrow: 1,
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    paddingHorizontal: 24,
    paddingTop: 28,
    paddingBottom: 32,
  },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 40 },
  brandIcon: {
    width: 46, height: 46, borderRadius: 14,
    alignItems: "center", justifyContent: "center",
    backgroundColor: C.primary,
  },
  brand: { fontSize: 25, fontWeight: "800", color: C.text },
  eyebrow: { fontSize: 11, fontWeight: "800", letterSpacing: 2, color: C.primary, marginBottom: 12 },
  title: { fontSize: 32, lineHeight: 39, fontWeight: "800", color: C.text, marginBottom: 12 },
  subtitle: { fontSize: 14, lineHeight: 23, color: C.muted, marginBottom: 25 },
  label: { fontSize: 13, fontWeight: "700", color: C.text, marginBottom: 9, marginTop: 17 },
  inputRow: {
    minHeight: 55, flexDirection: "row", alignItems: "center", gap: 11,
    paddingHorizontal: 14, borderWidth: 1, borderColor: C.border, borderRadius: 13,
  },
  input: { flex: 1, minWidth: 0, paddingVertical: 14, fontSize: 14, color: C.text },
  options: {
    flexDirection: "row", justifyContent: "space-between",
    alignItems: "center", flexWrap: "wrap", gap: 12, marginTop: 21,
  },
  rememberRow: { flexDirection: "row", alignItems: "center", gap: 9 },
  checkbox: {
    width: 19, height: 19, borderWidth: 1.5, borderColor: "#BBC4D0",
    borderRadius: 5, alignItems: "center", justifyContent: "center",
  },
  checkboxChecked: { backgroundColor: C.primary, borderColor: C.primary },
  smallText: { fontSize: 13, color: C.muted },
  link: { fontSize: 13, fontWeight: "700", color: C.primary },
  errorBox: {
    flexDirection: "row", alignItems: "flex-start", gap: 9,
    padding: 12, borderRadius: 12, backgroundColor: "#FFF2F0", marginTop: 18,
  },
  errorText: { flex: 1, fontSize: 13, lineHeight: 19, color: C.danger },
  button: {
    minHeight: 55, flexDirection: "row", alignItems: "center",
    justifyContent: "center", gap: 12, borderRadius: 14,
    backgroundColor: C.primary, marginTop: 25,
  },
  buttonPressed: { backgroundColor: C.pressed },
  disabled: { opacity: 0.7 },
  buttonText: { fontSize: 15, fontWeight: "800", color: C.white },
  footerRow: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 6, flexWrap: "wrap", marginTop: 27,
  },
  security: { fontSize: 12, textAlign: "center", color: C.muted, marginTop: 35 },
});
