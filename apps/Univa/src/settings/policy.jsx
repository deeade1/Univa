import { ScrollView, Text, StyleSheet } from "react-native";

export default function Policy() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.heading}>Terms & Privacy Policy</Text>

      <Text style={styles.sectionTitle}>1. Introduction</Text>
      <Text style={styles.paragraph}>
        Welcome to Univa! Your privacy and trust are important to us. This
        policy explains how we handle your data and protect your information.
      </Text>

      <Text style={styles.sectionTitle}>2. Data Collection</Text>
      <Text style={styles.paragraph}>
        We collect only the information necessary to provide our services —
        such as your name, email, and preferences.
      </Text>

      <Text style={styles.sectionTitle}>3. Usage</Text>
      <Text style={styles.paragraph}>
        Data is used to improve our services, personalize your experience, and
        maintain security across the Univa ecosystem.
      </Text>

      <Text style={styles.sectionTitle}>4. Contact</Text>
      <Text style={styles.paragraph}>
        If you have any questions about this policy, please contact us at{" "}
        <Text style={styles.link}>support@univa.app</Text>.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: "#fff",
    minHeight: "100%",
  },
  heading: {
    fontSize: 24,
    fontWeight: "700",
    marginBottom: 20,
    color: "#111",
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#222",
    marginTop: 16,
    marginBottom: 6,
  },
  paragraph: {
    fontSize: 16,
    color: "#555",
    lineHeight: 24,
  },
  link: {
    color: "#1E90FF",
  },
});
