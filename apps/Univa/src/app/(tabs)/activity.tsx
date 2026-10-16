
import { ScrollView, StatusBar, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors, Radius } from '@/constants/theme';

const C = Colors.light;

export default function ActivityScreen() {
  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <StatusBar barStyle="dark-content" backgroundColor={C.background} />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.eyebrow}>YOUR UNIVA JOURNEY</Text>
        <Text style={styles.title}>Activity</Text>
        <Text style={styles.subtitle}>Your recent activity will appear here.</Text>
        <View style={styles.card}>
          <Text style={styles.icon}>🧭</Text>
          <Text style={styles.cardTitle}>Your journey starts here</Text>
          <Text style={styles.body}>As you explore Univa services, your activity can be collected here.</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.background },
  content: { padding: 22, paddingTop: 24 },
  eyebrow: { color: C.primary, fontSize: 10, fontWeight: '800', letterSpacing: 1.4, marginBottom: 10 },
  title: { color: C.text, fontSize: 30, fontWeight: '800' },
  subtitle: { color: C.textSecondary, fontSize: 14, lineHeight: 21, marginTop: 8 },
  card: { marginTop: 30, padding: 26, alignItems: 'center', backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: C.border, borderRadius: Radius.large },
  icon: { fontSize: 38, marginBottom: 16 },
  cardTitle: { color: C.text, fontSize: 17, fontWeight: '800', marginBottom: 9 },
  body: { color: C.textSecondary, fontSize: 13, lineHeight: 20, textAlign: 'center' },
});
