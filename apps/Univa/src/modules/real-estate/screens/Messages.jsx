// src/modules/real-estate/screens/Messages.jsx
import React, {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  Image,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Modal,
  Animated,
  Dimensions,
} from "react-native";

import { useRouter, useLocalSearchParams } from "expo-router";

import { Ionicons } from "@expo/vector-icons";
import { useTheme } from "@/theme";
import { useSafeAreaInsets } from "react-native-safe-area-context";

// Mock data - replace with GraphQL later
const MOCK_CONVERSATIONS = [
  {
    id: "conv_1",
    propertyId: "prop_1",
    propertyTitle: "Modern 3-Bedroom Apartment in Ikoyi",
    propertyImage: "https://via.placeholder.com/60x60",
    agentId: "agent_1",
    agentName: "John Doe",
    agentAvatar: "https://via.placeholder.com/40x40",
    agentOnline: true,
    lastMessage: {
      id: "msg_1",
      text: "Yes, the property is still available. Would you like to schedule a viewing?",
      timestamp: "2024-01-15T10:30:00Z",
      sender: "agent",
      read: true,
    },
    unreadCount: 2,
    createdAt: "2024-01-10T08:00:00Z",
    updatedAt: "2024-01-15T10:30:00Z",
  },
  {
    id: "conv_2",
    propertyId: "prop_2",
    propertyTitle: "Luxury 4-Bedroom Duplex in Banana Island",
    propertyImage: "https://via.placeholder.com/60x60",
    agentId: "agent_2",
    agentName: "Jane Smith",
    agentAvatar: "https://via.placeholder.com/40x40",
    agentOnline: false,
    lastMessage: {
      id: "msg_2",
      text: "The price is ₦250,000,000. Would you like to negotiate?",
      timestamp: "2024-01-14T16:45:00Z",
      sender: "buyer",
      read: false,
    },
    unreadCount: 0,
    createdAt: "2024-01-05T14:00:00Z",
    updatedAt: "2024-01-14T16:45:00Z",
  },
  {
    id: "conv_3",
    propertyId: "prop_3",
    propertyTitle: "Cozy Studio Apartment in VI",
    propertyImage: "https://via.placeholder.com/60x60",
    agentId: "agent_3",
    agentName: "Mike Johnson",
    agentAvatar: "https://via.placeholder.com/40x40",
    agentOnline: true,
    lastMessage: {
      id: "msg_3",
      text: "Great! I'll send you the viewing schedule.",
      timestamp: "2024-01-13T09:15:00Z",
      sender: "agent",
      read: true,
    },
    unreadCount: 1,
    createdAt: "2024-01-02T10:00:00Z",
    updatedAt: "2024-01-13T09:15:00Z",
  },
];

const MOCK_MESSAGES = {
  conv_1: [
    {
      id: "msg_1",
      text: "Hi, I'm interested in the Modern 3-Bedroom Apartment in Ikoyi. Is it still available?",
      timestamp: "2024-01-15T09:00:00Z",
      sender: "buyer",
      read: true,
    },
    {
      id: "msg_2",
      text: "Yes, the property is still available. Would you like to schedule a viewing?",
      timestamp: "2024-01-15T10:00:00Z",
      sender: "agent",
      read: true,
    },
    {
      id: "msg_3",
      text: "That would be great! When are you available?",
      timestamp: "2024-01-15T10:15:00Z",
      sender: "buyer",
      read: true,
    },
    {
      id: "msg_4",
      text: "I'm available tomorrow at 2pm. Would that work for you?",
      timestamp: "2024-01-15T10:30:00Z",
      sender: "agent",
      read: false,
    },
  ],
  conv_2: [
    {
      id: "msg_5",
      text: "Hello, I saw your listing for the Luxury 4-Bedroom Duplex. Can you tell me more about it?",
      timestamp: "2024-01-14T15:00:00Z",
      sender: "buyer",
      read: true,
    },
    {
      id: "msg_6",
      text: "Of course! It's a 4-bedroom duplex with a swimming pool and 24/7 security. The price is ₦250,000,000.",
      timestamp: "2024-01-14T16:00:00Z",
      sender: "agent",
      read: true,
    },
    {
      id: "msg_7",
      text: "The price is ₦250,000,000. Would you like to negotiate?",
      timestamp: "2024-01-14T16:45:00Z",
      sender: "agent",
      read: false,
    },
  ],
  conv_3: [
    {
      id: "msg_8",
      text: "Hi, is the Cozy Studio Apartment in VI still available?",
      timestamp: "2024-01-13T08:00:00Z",
      sender: "buyer",
      read: true,
    },
    {
      id: "msg_9",
      text: "Yes, it's available! Would you like to schedule a viewing?",
      timestamp: "2024-01-13T08:30:00Z",
      sender: "agent",
      read: true,
    },
    {
      id: "msg_10",
      text: "Great! I'll send you the viewing schedule.",
      timestamp: "2024-01-13T09:15:00Z",
      sender: "agent",
      read: true,
    },
  ],
};

const { width } = Dimensions.get("window");
/* -------------------------------------------------------------------------- */
/* Conversation List */
/* -------------------------------------------------------------------------- */

function Messages() {
  const router = useRouter();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { conversationId } = useLocalSearchParams();

  // State
  const [conversations, setConversations] = useState(MOCK_CONVERSATIONS);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

  // Refs
  const flatListRef = useRef(null);
  const inputRef = useRef(null);
  const typingTimeoutRef = useRef(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Animation on mount
  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 400,
      useNativeDriver: true,
    }).start();
  }, []);

  // Load conversation when selected
  useEffect(() => {
    if (selectedConversation) {
      const msgs = MOCK_MESSAGES[selectedConversation.id] || [];
      setMessages(msgs);
      // Mark messages as read
      markConversationRead(selectedConversation.id);
    }
  }, [selectedConversation]);

  // Handle initial conversation from params
  useEffect(() => {
    if (conversationId) {
      const conv = conversations.find(c => c.id === conversationId);
      if (conv) {
        setSelectedConversation(conv);
      }
    }
  }, [conversationId, conversations]);

  // Filter conversations
  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    const query = searchQuery.toLowerCase().trim();
    return conversations.filter(conv =>
      conv.agentName.toLowerCase().includes(query) ||
      conv.propertyTitle.toLowerCase().includes(query) ||
      conv.lastMessage.text.toLowerCase().includes(query)
    );
  }, [conversations, searchQuery]);

  // Format time
  const formatTime = useCallback((timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m`;
    if (hours < 24) return `${hours}h`;
    if (days < 7) return `${days}d`;
    return date.toLocaleDateString("en-NG", { day: "numeric", month: "short" });
  }, []);

  // Format date for message separator
  const formatDate = useCallback((timestamp) => {
    const date = new Date(timestamp);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) return "Today";
    if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
    return date.toLocaleDateString("en-NG", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
  }, []);

  // Mark conversation as read
  const markConversationRead = useCallback((convId) => {
    setConversations(prev =>
      prev.map(conv =>
        conv.id === convId
          ? { ...conv, unreadCount: 0 }
          : conv
      )
    );
  }, []);

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    setIsRefreshing(false);
  }, []);

  // Handle conversation press
  const handleConversationPress = useCallback((conversation) => {
    setSelectedConversation(conversation);
  }, []);

  // Handle back from chat
  const handleBack = useCallback(() => {
    setSelectedConversation(null);
  }, []);

  // Send message
  const handleSend = useCallback(() => {
    if (!inputText.trim() || !selectedConversation) return;

    const newMessage = {
      id: `msg_${Date.now()}`,
      text: inputText.trim(),
      timestamp: new Date().toISOString(),
      sender: "buyer",
      read: false,
    };

    setMessages(prev => [...prev, newMessage]);
    setInputText("");

    // Update last message in conversation list
    setConversations(prev =>
      prev.map(conv =>
        conv.id === selectedConversation.id
          ? {
              ...conv,
              lastMessage: {
                id: newMessage.id,
                text: newMessage.text,
                timestamp: newMessage.timestamp,
                sender: "buyer",
                read: false,
              },
              updatedAt: newMessage.timestamp,
            }
          : conv
      )
    );

    // Simulate agent reply
    setTimeout(() => {
      const replyMessage = {
        id: `msg_${Date.now() + 1}`,
        text: "Thanks for your message. I'll get back to you shortly.",
        timestamp: new Date().toISOString(),
        sender: "agent",
        read: false,
      };
      setMessages(prev => [...prev, replyMessage]);
      
      setConversations(prev =>
        prev.map(conv =>
          conv.id === selectedConversation.id
            ? {
                ...conv,
                lastMessage: {
                  id: replyMessage.id,
                  text: replyMessage.text,
                  timestamp: replyMessage.timestamp,
                  sender: "agent",
                  read: false,
                },
                updatedAt: replyMessage.timestamp,
                unreadCount: (conv.unreadCount || 0) + 1,
              }
            : conv
        )
      );
    }, 2000);

    // Simulate typing indicator
    setIsTyping(true);
    setTimeout(() => {
      setIsTyping(false);
    }, 1500);
  }, [inputText, selectedConversation]);

  // Render conversation item
  const renderConversationItem = useCallback(({ item }) => {
    const isUnread = item.unreadCount > 0;

    return (
      <Pressable
        style={[
          styles.conversationItem,
          {
            backgroundColor: isUnread ? colors.primary + "08" : "transparent",
            borderBottomColor: colors.border,
          },
        ]}
        onPress={() => handleConversationPress(item)}
      >
        {/* Agent Avatar */}
        <View style={styles.conversationAvatar}>
          {item.agentAvatar ? (
            <Image source={{ uri: item.agentAvatar }} style={styles.avatarImage} />
          ) : (
            <View style={[styles.avatarPlaceholder, { backgroundColor: colors.primary + "20" }]}>
              <Text style={[styles.avatarText, { color: colors.primary }]}>
                {item.agentName.charAt(0)}
              </Text>
            </View>
          )}
          {item.agentOnline && (
            <View style={[styles.onlineDot, { backgroundColor: "#22C55E" }]} />
          )}
        </View>

        {/* Content */}
        <View style={styles.conversationContent}>
          <View style={styles.conversationHeader}>
            <Text style={[styles.conversationName, { color: colors.text }]} numberOfLines={1}>
              {item.agentName}
            </Text>
            <Text style={[styles.conversationTime, { color: colors.textSecondary }]}>
              {formatTime(item.updatedAt)}
            </Text>
          </View>

          <Text style={[styles.conversationProperty, { color: colors.textSecondary }]} numberOfLines={1}>
            {item.propertyTitle}
          </Text>

          <View style={styles.conversationFooter}>
            <Text
              style={[
                styles.conversationLastMessage,
                { color: isUnread ? colors.text : colors.textSecondary },
                isUnread && styles.conversationLastMessageUnread,
              ]}
              numberOfLines={1}
            >
              {item.lastMessage.sender === "agent" ? "👤 " : "👤 "}
              {item.lastMessage.text}
            </Text>

            {isUnread && (
              <View style={[styles.unreadBadge, { backgroundColor: colors.primary }]}>
                <Text style={styles.unreadText}>{item.unreadCount}</Text>
              </View>
            )}
          </View>
        </View>
      </Pressable>
    );
  }, [colors, formatTime, handleConversationPress]);

  // Render chat messages
  const renderMessage = useCallback(({ item, index }) => {
    const isOwn = item.sender === "buyer";
    const showDate = index === 0 || 
      new Date(item.timestamp).toDateString() !== new Date(messages[index - 1]?.timestamp).toDateString();

    return (
      <View>
        {showDate && (
          <View style={styles.dateSeparator}>
            <View style={[styles.dateSeparatorLine, { backgroundColor: colors.border }]} />
            <Text style={[styles.dateSeparatorText, { color: colors.textSecondary }]}>
              {formatDate(item.timestamp)}
            </Text>
            <View style={[styles.dateSeparatorLine, { backgroundColor: colors.border }]} />
          </View>
        )}

        <View style={[styles.messageRow, isOwn ? styles.messageRowOwn : styles.messageRowOther]}>
          {!isOwn && (
            <View style={styles.messageAvatar}>
              {selectedConversation?.agentAvatar ? (
                <Image source={{ uri: selectedConversation.agentAvatar }} style={styles.messageAvatarImage} />
              ) : (
                <View style={[styles.messageAvatarPlaceholder, { backgroundColor: colors.primary + "20" }]}>
                  <Text style={[styles.messageAvatarText, { color: colors.primary }]}>
                    {selectedConversation?.agentName?.charAt(0) || "A"}
                  </Text>
                </View>
              )}
            </View>
          )}

          <View style={[styles.messageBubble, isOwn ? styles.messageBubbleOwn : styles.messageBubbleOther]}>
            <Text style={[
              styles.messageText,
              { color: isOwn ? "#FFFFFF" : colors.text }
            ]}>
              {item.text}
            </Text>
            <Text style={[
              styles.messageTime,
              { color: isOwn ? "rgba(255,255,255,0.7)" : colors.textSecondary }
            ]}>
              {formatTime(item.timestamp)}
            </Text>
          </View>
        </View>
      </View>
    );
  }, [selectedConversation, colors, formatDate, formatTime]);

  // Key extractor
  const keyExtractor = useCallback((item) => item.id, []);

  // Render empty conversations
  const renderEmptyConversations = () => (
    <View style={styles.emptyContainer}>
      <Ionicons name="chatbubbles-outline" size={64} color={colors.textSecondary} />
      <Text style={[styles.emptyTitle, { color: colors.text }]}>
        No Conversations Yet
      </Text>
      <Text style={[styles.emptyDescription, { color: colors.textSecondary }]}>
        When you contact an agent about a property, your conversations will appear here.
      </Text>
    </View>
  );  /* -------------------------------------------------------------------------- */
  /* Chat View */
  /* -------------------------------------------------------------------------- */

  const renderChatView = useCallback(() => {
    if (!selectedConversation) return null;

    return (
      <View style={styles.chatContainer}>
        {/* Chat Header */}
        <View style={[styles.chatHeader, { borderBottomColor: colors.border }]}>
          <TouchableOpacity onPress={handleBack} hitSlop={8}>
            <Ionicons name="arrow-back" size={24} color={colors.text} />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.chatHeaderInfo}
            onPress={() => {
              // Navigate to agent profile
              router.push(`/real-estate/agent/${selectedConversation.agentId}`);
            }}
          >
            <View style={styles.chatHeaderAvatar}>
              {selectedConversation.agentAvatar ? (
                <Image source={{ uri: selectedConversation.agentAvatar }} style={styles.chatAvatarImage} />
              ) : (
                <View style={[styles.chatAvatarPlaceholder, { backgroundColor: colors.primary + "20" }]}>
                  <Text style={[styles.chatAvatarText, { color: colors.primary }]}>
                    {selectedConversation.agentName.charAt(0)}
                  </Text>
                </View>
              )}
              {selectedConversation.agentOnline && (
                <View style={[styles.chatOnlineDot, { backgroundColor: "#22C55E" }]} />
              )}
            </View>

            <View style={styles.chatHeaderText}>
              <Text style={[styles.chatHeaderName, { color: colors.text }]}>
                {selectedConversation.agentName}
              </Text>
              <Text style={[styles.chatHeaderStatus, { color: colors.textSecondary }]}>
                {selectedConversation.agentOnline ? "Online" : "Offline"}
              </Text>
            </View>
          </TouchableOpacity>

          <View style={styles.chatHeaderActions}>
            <TouchableOpacity
              onPress={() => {
                // Navigate to property details
                router.push(`/real-estate/property/${selectedConversation.propertyId}`);
              }}
              hitSlop={8}
            >
              <Ionicons name="home-outline" size={22} color={colors.text} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Messages List */}
        <FlatList
          ref={flatListRef}
          data={messages}
          renderItem={renderMessage}
          keyExtractor={keyExtractor}
          contentContainerStyle={styles.messagesList}
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() => {
            flatListRef.current?.scrollToEnd({ animated: true });
          }}
          onLayout={() => {
            flatListRef.current?.scrollToEnd({ animated: true });
          }}
          ListEmptyComponent={
            <View style={styles.emptyChatContainer}>
              <Ionicons name="chatbubble-outline" size={48} color={colors.textSecondary} />
              <Text style={[styles.emptyChatTitle, { color: colors.text }]}>
                No messages yet
              </Text>
              <Text style={[styles.emptyChatDescription, { color: colors.textSecondary }]}>
                Start the conversation with {selectedConversation.agentName}
              </Text>
            </View>
          }
        />

        {/* Typing Indicator */}
        {isTyping && (
          <View style={styles.typingIndicator}>
            <View style={[styles.typingBubble, { backgroundColor: colors.card }]}>
              <View style={styles.typingDot} />
              <View style={[styles.typingDot, styles.typingDotDelay]} />
              <View style={[styles.typingDot, styles.typingDotDelay2]} />
            </View>
          </View>
        )}

        {/* Message Composer */}
        <View style={[styles.composer, { borderTopColor: colors.border }]}>
          <TouchableOpacity
            onPress={() => {
              // TODO: Implement attachment picker
            }}
            style={styles.composerButton}
          >
            <Ionicons name="attach-outline" size={24} color={colors.textSecondary} />
          </TouchableOpacity>

          <TextInput
            ref={inputRef}
            style={[
              styles.composerInput,
              {
                color: colors.text,
                backgroundColor: colors.card,
              },
            ]}
            placeholder="Type a message..."
            placeholderTextColor={colors.textSecondary}
            value={inputText}
            onChangeText={setInputText}
            multiline
            maxLength={500}
          />

          <TouchableOpacity
            onPress={() => {
              // TODO: Implement emoji picker
            }}
            style={styles.composerButton}
          >
            <Ionicons name="happy-outline" size={24} color={colors.textSecondary} />
          </TouchableOpacity>

          <TouchableOpacity
            onPress={handleSend}
            disabled={!inputText.trim()}
            style={[
              styles.sendButton,
              {
                backgroundColor: inputText.trim() ? colors.primary : colors.border,
              },
            ]}
          >
            <Ionicons
              name="send"
              size={20}
              color={inputText.trim() ? "#FFFFFF" : colors.textSecondary}
            />
          </TouchableOpacity>
        </View>
      </View>
    );
  }, [
    selectedConversation,
    messages,
    inputText,
    isTyping,
    colors,
    handleBack,
    handleSend,
    renderMessage,
    keyExtractor,
  ]);
    /* -------------------------------------------------------------------------- */
  /* Main Render */
  /* -------------------------------------------------------------------------- */

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {selectedConversation ? (
        // Chat View
        <Animated.View style={{ flex: 1, opacity: fadeAnim }}>
          <KeyboardAvoidingView
            style={styles.keyboardView}
            behavior={Platform.OS === "ios" ? "padding" : undefined}
            keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
          >
            {renderChatView()}
          </KeyboardAvoidingView>
        </Animated.View>
      ) : (
        // Conversation List
        <Animated.View style={{ flex: 1, opacity: fadeAnim }}>
          {/* Header */}
          <View style={[styles.header, { borderBottomColor: colors.border }]}>
            <View style={styles.headerLeft}>
              <TouchableOpacity onPress={() => router.back()} hitSlop={8}>
                <Ionicons name="arrow-back" size={24} color={colors.text} />
              </TouchableOpacity>
              <Text style={[styles.headerTitle, { color: colors.text }]}>
                Messages
              </Text>
            </View>

            <View style={styles.headerRight}>
              <TouchableOpacity
                onPress={() => setShowSearch(!showSearch)}
                hitSlop={8}
              >
                <Ionicons name="search-outline" size={22} color={colors.text} />
              </TouchableOpacity>
            </View>
          </View>

          {/* Search Bar */}
          {showSearch && (
            <View style={[styles.searchContainer, { borderBottomColor: colors.border }]}>
              <View style={[styles.searchBar, { backgroundColor: colors.card }]}>
                <Ionicons name="search-outline" size={20} color={colors.textSecondary} />
                <TextInput
                  style={[styles.searchInput, { color: colors.text }]}
                  placeholder="Search conversations..."
                  placeholderTextColor={colors.textSecondary}
                  value={searchQuery}
                  onChangeText={setSearchQuery}
                  autoFocus
                />
                {searchQuery.length > 0 && (
                  <TouchableOpacity onPress={() => setSearchQuery("")}>
                    <Ionicons name="close-circle" size={20} color={colors.textSecondary} />
                  </TouchableOpacity>
                )}
              </View>
            </View>
          )}

          {/* Unread Count */}
          {conversations.some(c => c.unreadCount > 0) && (
            <View style={[styles.unreadSummary, { backgroundColor: colors.primary + "10" }]}>
              <Ionicons name="mail-unread-outline" size={18} color={colors.primary} />
              <Text style={[styles.unreadSummaryText, { color: colors.primary }]}>
                {conversations.reduce((sum, c) => sum + (c.unreadCount || 0), 0)} unread messages
              </Text>
            </View>
          )}

          {/* Conversation List */}
          <FlatList
            data={filteredConversations}
            renderItem={renderConversationItem}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.conversationList}
            showsVerticalScrollIndicator={false}
            refreshControl={
              <RefreshControl
                refreshing={isRefreshing}
                onRefresh={handleRefresh}
                tintColor={colors.primary}
                colors={[colors.primary]}
              />
            }
            ListEmptyComponent={renderEmptyConversations}
          />
        </Animated.View>
      )}
    </View>
  );
}
/* -------------------------------------------------------------------------- */
/* Styles */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  keyboardView: {
    flex: 1,
  },

  /* ---------------------------------------------------------------------- */
  /* Header */
  /* ---------------------------------------------------------------------- */

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
  },

  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },

  headerTitle: {
    fontSize: 20,
    fontWeight: "700",
  },

  headerRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },

  /* ---------------------------------------------------------------------- */
  /* Search */
  /* ---------------------------------------------------------------------- */

  searchContainer: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },

  searchBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 12,
    gap: 8,
  },

  searchInput: {
    flex: 1,
    fontSize: 15,
    paddingVertical: 4,
  },

  /* ---------------------------------------------------------------------- */
  /* Unread Summary */
  /* ---------------------------------------------------------------------- */

  unreadSummary: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 8,
  },

  unreadSummaryText: {
    fontSize: 13,
    fontWeight: "600",
  },

  /* ---------------------------------------------------------------------- */
  /* Conversation List */
  /* ---------------------------------------------------------------------- */

  conversationList: {
    flexGrow: 1,
  },

  conversationItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },

  conversationAvatar: {
    position: "relative",
    marginRight: 12,
  },

  avatarImage: {
    width: 52,
    height: 52,
    borderRadius: 26,
  },

  avatarPlaceholder: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
  },

  avatarText: {
    fontSize: 20,
    fontWeight: "700",
  },

  onlineDot: {
    position: "absolute",
    bottom: 0,
    right: 0,
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 2,
    borderColor: "#FFFFFF",
  },

  conversationContent: {
    flex: 1,
  },

  conversationHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 2,
  },

  conversationName: {
    fontSize: 16,
    fontWeight: "700",
  },

  conversationTime: {
    fontSize: 12,
  },

  conversationProperty: {
    fontSize: 13,
    marginBottom: 4,
  },

  conversationFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  conversationLastMessage: {
    flex: 1,
    fontSize: 14,
    marginRight: 8,
  },

  conversationLastMessageUnread: {
    fontWeight: "600",
  },

  unreadBadge: {
    minWidth: 20,
    height: 20,
    borderRadius: 10,
    paddingHorizontal: 6,
    alignItems: "center",
    justifyContent: "center",
  },

  unreadText: {
    color: "#FFFFFF",
    fontSize: 11,
    fontWeight: "700",
  },

  /* ---------------------------------------------------------------------- */
  /* Empty State */
  /* ---------------------------------------------------------------------- */

  emptyContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 40,
    paddingVertical: 60,
  },

  emptyTitle: {
    fontSize: 20,
    fontWeight: "700",
    marginTop: 16,
    marginBottom: 8,
  },

  emptyDescription: {
    fontSize: 14,
    textAlign: "center",
    lineHeight: 22,
  },

  /* ---------------------------------------------------------------------- */
  /* Chat View */
  /* ---------------------------------------------------------------------- */

  chatContainer: {
    flex: 1,
  },

  chatHeader: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },

  chatHeaderInfo: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    marginLeft: 12,
  },

  chatHeaderAvatar: {
    position: "relative",
  },

  chatAvatarImage: {
    width: 40,
    height: 40,
    borderRadius: 20,
  },

  chatAvatarPlaceholder: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
  },

  chatAvatarText: {
    fontSize: 16,
    fontWeight: "700",
  },

  chatOnlineDot: {
    position: "absolute",
    bottom: 0,
    right: 0,
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: "#FFFFFF",
  },

  chatHeaderText: {
    marginLeft: 10,
  },

  chatHeaderName: {
    fontSize: 16,
    fontWeight: "700",
  },

  chatHeaderStatus: {
    fontSize: 12,
  },

  chatHeaderActions: {
    flexDirection: "row",
    gap: 12,
  },

  /* ---------------------------------------------------------------------- */
  /* Messages */
  /* ---------------------------------------------------------------------- */

  messagesList: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexGrow: 1,
  },

  dateSeparator: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 16,
    gap: 12,
  },

  dateSeparatorLine: {
    flex: 1,
    height: StyleSheet.hairlineWidth,
  },

  dateSeparatorText: {
    fontSize: 12,
    fontWeight: "500",
  },

  messageRow: {
    flexDirection: "row",
    marginBottom: 8,
    alignItems: "flex-end",
  },

  messageRowOwn: {
    justifyContent: "flex-end",
  },

  messageRowOther: {
    justifyContent: "flex-start",
  },

  messageAvatar: {
    marginRight: 8,
  },

  messageAvatarImage: {
    width: 30,
    height: 30,
    borderRadius: 15,
  },

  messageAvatarPlaceholder: {
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: "center",
    justifyContent: "center",
  },

  messageAvatarText: {
    fontSize: 12,
    fontWeight: "700",
  },

  messageBubble: {
    maxWidth: width * 0.75,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 16,
  },

  messageBubbleOwn: {
    backgroundColor: "#1DC66C",
    borderBottomRightRadius: 4,
  },

  messageBubbleOther: {
    backgroundColor: "#F1F5F9",
    borderBottomLeftRadius: 4,
  },

  messageText: {
    fontSize: 15,
    lineHeight: 20,
  },

  messageTime: {
    fontSize: 11,
    marginTop: 4,
    textAlign: "right",
  },

  /* ---------------------------------------------------------------------- */
  /* Empty Chat */
  /* ---------------------------------------------------------------------- */

  emptyChatContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 40,
  },

  emptyChatTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginTop: 12,
  },

  emptyChatDescription: {
    fontSize: 14,
    textAlign: "center",
    marginTop: 4,
  },

  /* ---------------------------------------------------------------------- */
  /* Typing Indicator */
  /* ---------------------------------------------------------------------- */

  typingIndicator: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },

  typingBubble: {
    alignSelf: "flex-start",
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: 16,
    flexDirection: "row",
    gap: 4,
    minWidth: 56,
  },

  typingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#94A3B8",
    opacity: 0.4,
  },

  typingDotDelay: {
    opacity: 0.6,
  },

  typingDotDelay2: {
    opacity: 0.8,
  },

  /* ---------------------------------------------------------------------- */
  /* Composer */
  /* ---------------------------------------------------------------------- */

  composer: {
    flexDirection: "row",
    alignItems: "flex-end",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderTopWidth: 1,
    gap: 8,
  },

  composerButton: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
  },

  composerInput: {
    flex: 1,
    maxHeight: 100,
    minHeight: 40,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    fontSize: 15,
    textAlignVertical: "top",
  },

  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
  },
});

/* -------------------------------------------------------------------------- */
/* Export */
/* -------------------------------------------------------------------------- */

export default memo(Messages);