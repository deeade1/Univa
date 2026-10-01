import React from 'react';
import {
  Text,
  View,
  StyleSheet,
  ScrollView,
  Image,
  Pressable,
  Linking,
  Share,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons, FontAwesome5 } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

export default function AboutScreen() {
  const teamMembers = [
    {
      id: 1,
      name: 'Sarah Chen',
      role: 'CEO & Founder',
      image: 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=150&h=150&fit=crop&crop=face',
      social: { linkedin: '#', twitter: '#' }
    },
    {
      id: 2,
      name: 'Marcus Johnson',
      role: 'CTO',
      image: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&h=150&fit=crop&crop=face',
      social: { linkedin: '#', twitter: '#' }
    },
    {
      id: 3,
      name: 'Elena Rodriguez',
      role: 'Head of Design',
      image: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&h=150&fit=crop&crop=face',
      social: { linkedin: '#', twitter: '#' }
    },
    {
      id: 4,
      name: 'David Kim',
      role: 'Lead Developer',
      image: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face',
      social: { linkedin: '#', twitter: '#' }
    },
  ];

  const features = [
    { icon: 'shield-checkmark', title: 'Bank-Level Security', description: '256-bit encryption and biometric authentication' },
    { icon: 'rocket', title: 'Instant Transfers', description: 'Send money anywhere in seconds' },
    { icon: 'globe', title: 'Global Reach', description: 'Available in 50+ countries worldwide' },
    { icon: 'headset', title: '24/7 Support', description: 'Round-the-clock customer service' },
  ];

  const stats = [
    { number: '2M+', label: 'Active Users' },
    { number: '₦50B+', label: 'Processed' },
    { number: '150+', label: 'Countries' },
    { number: '99.9%', label: 'Uptime' },
  ];

  const shareApp = async () => {
    try {
      await Share.share({
        message: 'Check out Univa - The all-in-one financial super app! Download now: https://univa.app',
        title: 'Univa App'
      });
    } catch (error) {
      console.error(error);
    }
  };

  const openWebsite = () => {
    Linking.openURL('https://univa.app');
  };

  const contactSupport = () => {
    Linking.openURL('mailto:support@univa.app');
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Hero Section */}
      <LinearGradient
        colors={['#667eea', '#764ba2']}
        style={styles.heroSection}
      >
        <View style={styles.heroContent}>
          <Image
            source={{ uri: 'https://res.cloudinary.com/dw3hb6ec8/image/upload/v1718122191/opay-banner.png' }}
            style={styles.logo}
          />
          <Text style={styles.heroTitle}>Univa</Text>
          <Text style={styles.heroSubtitle}>Your All-in-One Financial Super App</Text>
          <Text style={styles.heroDescription}>
            Revolutionizing digital banking with seamless payments, instant transfers, 
            and comprehensive financial services for everyone.
          </Text>
        </View>
      </LinearGradient>

      {/* Stats Section */}
      <View style={styles.statsSection}>
        <Text style={styles.sectionTitle}>Our Impact</Text>
        <View style={styles.statsGrid}>
          {stats.map((stat, index) => (
            <View key={index} style={styles.statItem}>
              <Text style={styles.statNumber}>{stat.number}</Text>
              <Text style={styles.statLabel}>{stat.label}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Mission Section */}
      <View style={styles.missionSection}>
        <Text style={styles.sectionTitle}>Our Mission</Text>
        <View style={styles.missionCard}>
          <MaterialCommunityIcons name="target" size={32} color="#667eea" />
          <Text style={styles.missionText}>
            To democratize financial services and make advanced banking accessible 
            to everyone, regardless of their location or background. We believe in 
            empowering individuals and businesses through innovative technology.
          </Text>
        </View>
      </View>

      {/* Features Section */}
      <View style={styles.featuresSection}>
        <Text style={styles.sectionTitle}>Why Choose Univa?</Text>
        <View style={styles.featuresGrid}>
          {features.map((feature, index) => (
            <View key={index} style={styles.featureCard}>
              <View style={styles.featureIcon}>
                <Ionicons name={feature.icon} size={24} color="#667eea" />
              </View>
              <Text style={styles.featureTitle}>{feature.title}</Text>
              <Text style={styles.featureDescription}>{feature.description}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Team Section */}
      <View style={styles.teamSection}>
        <Text style={styles.sectionTitle}>Meet Our Team</Text>
        <ScrollView 
          horizontal 
          showsHorizontalScrollIndicator={false}
          style={styles.teamScroll}
        >
          {teamMembers.map((member) => (
            <View key={member.id} style={styles.teamCard}>
              <Image source={{ uri: member.image }} style={styles.teamImage} />
              <Text style={styles.teamName}>{member.name}</Text>
              <Text style={styles.teamRole}>{member.role}</Text>
              <View style={styles.socialLinks}>
                <Pressable style={styles.socialButton}>
                  <Ionicons name="logo-linkedin" size={16} color="#0077b5" />
                </Pressable>
                <Pressable style={styles.socialButton}>
                  <Ionicons name="logo-twitter" size={16} color="#1da1f2" />
                </Pressable>
              </View>
            </View>
          ))}
        </ScrollView>
      </View>

      {/* App Info */}
      <View style={styles.infoSection}>
        <View style={styles.infoCard}>
          <Ionicons name="information-circle" size={28} color="#667eea" />
          <View style={styles.infoContent}>
            <Text style={styles.infoTitle}>App Information</Text>
            <Text style={styles.infoDetail}>Version: 1.0.0</Text>
            <Text style={styles.infoDetail}>Build: 2024.12.1</Text>
            <Text style={styles.infoDetail}>Last Updated: December 2024</Text>
          </View>
        </View>
      </View>

      {/* Action Buttons */}
      <View style={styles.actionsSection}>
        <Pressable style={styles.actionButton} onPress={shareApp}>
          <Ionicons name="share-social" size={20} color="#fff" />
          <Text style={styles.actionButtonText}>Share Univa</Text>
        </Pressable>
        
        <Pressable style={[styles.actionButton, styles.secondaryButton]} onPress={openWebsite}>
          <Ionicons name="globe" size={20} color="#667eea" />
          <Text style={[styles.actionButtonText, styles.secondaryButtonText]}>Visit Website</Text>
        </Pressable>
        
        <Pressable style={[styles.actionButton, styles.secondaryButton]} onPress={contactSupport}>
          <Ionicons name="headset" size={20} color="#667eea" />
          <Text style={[styles.actionButtonText, styles.secondaryButtonText]}>Contact Support</Text>
        </Pressable>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>© 2024 Univa Technologies. All rights reserved.</Text>
        <View style={styles.footerLinks}>
          <Pressable>
            <Text style={styles.footerLink}>Privacy Policy</Text>
          </Pressable>
          <Text style={styles.footerDivider}>•</Text>
          <Pressable>
            <Text style={styles.footerLink}>Terms of Service</Text>
          </Pressable>
          <Text style={styles.footerDivider}>•</Text>
          <Pressable>
            <Text style={styles.footerLink}>Security</Text>
          </Pressable>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  heroSection: {
    paddingVertical: 60,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 30,
    borderBottomRightRadius: 30,
  },
  heroContent: {
    alignItems: 'center',
  },
  logo: {
    width: 80,
    height: 80,
    borderRadius: 20,
    marginBottom: 16,
  },
  heroTitle: {
    fontSize: 42,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  heroSubtitle: {
    fontSize: 18,
    color: 'rgba(255,255,255,0.9)',
    marginBottom: 16,
    textAlign: 'center',
  },
  heroDescription: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.8)',
    textAlign: 'center',
    lineHeight: 24,
  },
  statsSection: {
    padding: 24,
    backgroundColor: '#fff',
    marginTop: -20,
    marginHorizontal: 20,
    borderRadius: 20,
    // Updated shadow styles
    boxShadow: '0px 4px 12px rgba(0, 0, 0, 0.1)',
    elevation: 5,
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 20,
    textAlign: 'center',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statItem: {
    width: '48%',
    alignItems: 'center',
    paddingVertical: 16,
  },
  statNumber: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#667eea',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 14,
    color: '#64748b',
    fontWeight: '500',
  },
  missionSection: {
    padding: 24,
  },
  missionCard: {
    backgroundColor: '#fff',
    padding: 24,
    borderRadius: 16,
    alignItems: 'center',
    // Updated shadow styles
    boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.05)',
    elevation: 2,
  },
  missionText: {
    fontSize: 16,
    color: '#475569',
    lineHeight: 24,
    textAlign: 'center',
    marginTop: 12,
  },
  featuresSection: {
    padding: 24,
    backgroundColor: '#f1f5f9',
  },
  featuresGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  featureCard: {
    width: '48%',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    alignItems: 'center',
    // Updated shadow styles
    boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.05)',
    elevation: 2,
  },
  featureIcon: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#f0f4ff',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  featureTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4,
    textAlign: 'center',
  },
  featureDescription: {
    fontSize: 12,
    color: '#64748b',
    textAlign: 'center',
    lineHeight: 16,
  },
  teamSection: {
    padding: 24,
  },
  teamScroll: {
    flexDirection: 'row',
  },
  teamCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 16,
    alignItems: 'center',
    marginRight: 16,
    width: 140,
    // Updated shadow styles
    boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.05)',
    elevation: 2,
  },
  teamImage: {
    width: 80,
    height: 80,
    borderRadius: 40,
    marginBottom: 12,
  },
  teamName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4,
  },
  teamRole: {
    fontSize: 12,
    color: '#667eea',
    marginBottom: 12,
    textAlign: 'center',
  },
  socialLinks: {
    flexDirection: 'row',
  },
  socialButton: {
    padding: 6,
    marginHorizontal: 4,
  },
  infoSection: {
    padding: 24,
    paddingTop: 0,
  },
  infoCard: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 16,
    flexDirection: 'row',
    alignItems: 'flex-start',
    // Updated shadow styles
    boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.05)',
    elevation: 2,
  },
  infoContent: {
    marginLeft: 16,
    flex: 1,
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 8,
  },
  infoDetail: {
    fontSize: 14,
    color: '#64748b',
    marginBottom: 2,
  },
  actionsSection: {
    padding: 24,
    paddingTop: 0,
  },
  actionButton: {
    backgroundColor: '#667eea',
    padding: 16,
    borderRadius: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
    // Updated shadow styles
    boxShadow: '0px 4px 8px rgba(102, 126, 234, 0.3)',
    elevation: 4,
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: '#667eea',
    // Remove shadow for secondary button
    boxShadow: 'none',
    elevation: 0,
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  secondaryButtonText: {
    color: '#667eea',
  },
  footer: {
    padding: 24,
    paddingTop: 0,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 14,
    color: '#64748b',
    marginBottom: 12,
    textAlign: 'center',
  },
  footerLinks: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  footerLink: {
    fontSize: 14,
    color: '#667eea',
    fontWeight: '500',
  },
  footerDivider: {
    color: '#cbd5e1',
    marginHorizontal: 12,
  },
});


