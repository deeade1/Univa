import React, { useState } from "react";
import { View, Text, TextInput, Button, Alert, StyleSheet, ScrollView } from "react-native";
import { useMutation } from "@apollo/client/react";
import { SEND_CONTACT_MESSAGE } from "@/graphql/queries/accountQuery/mutations"; // optional if using GraphQL

export default function ContactUsScreen() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    message: "",
  });

  // optional GraphQL hook
  const [sendMessage, { loading }] = useMutation(SEND_CONTACT_MESSAGE, {
    onCompleted: () => {
      Alert.alert("✅ Message Sent", "We'll get back to you soon!");
      setForm({ name: "", email: "", message: "" });
    },
    onError: (err) => {
      Alert.alert("❌ Error", err.message);
    },
  });

  const handleSubmit = async () => {
    if (!form.name || !form.email || !form.message) {
      Alert.alert("⚠️ Missing Fields", "Please fill in all fields.");
      return;
    }

    try {
      await sendMessage({
        variables: { input: { ...form } },
      });
    } catch (err) {
      console.error("Send message error:", err);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Contact Us</Text>
      <Text style={styles.subtitle}>We’d love to hear from you!</Text>

      <TextInput
        placeholder="Your Name"
        style={styles.input}
        value={form.name}
        onChangeText={(text) => setForm({ ...form, name: text })}
      />

      <TextInput
        placeholder="Your Email"
        style={styles.input}
        keyboardType="email-address"
        value={form.email}
        onChangeText={(text) => setForm({ ...form, email: text })}
      />

      <TextInput
        placeholder="Your Message"
        style={[styles.input, styles.textArea]}
        multiline
        numberOfLines={5}
        value={form.message}
        onChangeText={(text) => setForm({ ...form, message: text })}
      />

      <Button
        title={loading ? "Sending..." : "Send Message"}
        onPress={handleSubmit}
        disabled={loading}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: "#fff",
    flexGrow: 1,
  },
  title: {
    fontSize: 26,
    fontWeight: "bold",
    textAlign: "center",
    marginBottom: 8,
  },
  subtitle: {
    textAlign: "center",
    color: "#666",
    marginBottom: 20,
  },
  input: {
    borderColor: "#ccc",
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 15,
    fontSize: 16,
  },
  textArea: {
    height: 120,
    textAlignVertical: "top",
  },
});
