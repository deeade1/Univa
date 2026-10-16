
import { Pressable, ScrollView, StatusBar, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Colors, Radius } from '@/constants/theme';

const C = Colors.light;

const options = [
  { icon: '👤', title: 'Personal information', detail: 'Manage your profile' },
  { icon: '🔔', title: 'Notifications', detail: 'Your notification preferences' },
  { icon: '🛡️', title: 'Security', detail: 'Account and security settings' },
  { icon: '❓', title: 'Help and support', detail: 'Find help using Univa' },
];

export default function ProfileScreen() {
  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <StatusBar barStyle="dark-content" backgroundColor={C.background} />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.eyebrow}>YOUR ACCOUNT</Text>
        <Text style={styles.title}>Profile</Text>

        <View style={styles.profileCard}>
          <View style={styles.avatar}><Text style={styles.avatarText}>U</Text></View>
          <Text style={styles.name}>Welcome to Univa</Text>
          <Text style={styles.body}>Your profile and preferences will live here.</Text>
        </View>

        <Text style={styles.sectionTitle}>Account settings</Text>
        {options.map((option) => (
          <Pressable key={option.title} onPress={() => {}} style={styles.option}>
            <View style={styles.optionIcon}><Text style={styles.optionEmoji}>{option.icon}</Text></View>
            <View style={styles.optionCopy}>
              <Text style={styles.optionTitle}>{option.title}</Text>
              <Text style={styles.body}>{option.detail}</Text>
            </View>
            <Text style={styles.arrow}>›</Text>
          </Pressable>
        ))}

        <Pressable style={styles.backButton} onPress={() => router.replace('/(tabs)')}>
          <Text style={styles.backText}>Back to Home</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.background },
  content: { padding: 20, paddingTop: 24, paddingBottom: 110 },
  eyebrow: { color: C.primary, fontSize: 10, fontWeight: '800', letterSpacing: 1.4, marginBottom: 10 },
  title: { color: C.text, fontSize: 30, fontWeight: '800', marginBottom: 22 },
  profileCard: { backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: C.border, borderRadius: Radius.large, padding: 22, alignItems: 'center', marginBottom: 28 },
  avatar: { width: 68, height: 68, borderRadius: 24, backgroundColor: C.primary, alignItems: 'center', justifyContent: 'center', marginBottom: 13 },
  avatarText: { color: '#FFFFFF', fontSize: 32, fontWeight: '800' },
  name: { color: C.text, fontSize: 18, fontWeight: '800', marginBottom: 7 },
  body: { color: C.textSecondary, fontSize: 12, lineHeight: 18 },
  sectionTitle: { color: C.text, fontSize: 17, fontWeight: '800', marginBottom: 13 },
  option: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 13, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: C.border, borderRadius: Radius.medium, marginBottom: 10 },
  optionIcon: { width: 42, height: 42, borderRadius: 13, backgroundColor: C.surfaceBlue, alignItems: 'center', justifyContent: 'center' },
  optionEmoji: { fontSize: 20 },
  optionCopy: { flex: 1, gap: 4 },
  optionTitle: { color: C.text, fontSize: 13, fontWeight: '800' },
  arrow: { color: C.textSecondary, fontSize: 24 },
  backButton: { backgroundColor: C.primary, borderRadius: Radius.medium, padding: 15, alignItems: 'center', marginTop: 12 },
  backText: { color: '#FFFFFF', fontWeight: '800', fontSize: 13 },
});
