
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useShoppingCart } from '@/contexts/shopping-cart-context';
import {
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

const COLORS = {
  background: '#F7F8FC',
  white: '#FFFFFF',
  text: '#101828',
  muted: '#667085',
  primary: '#6941C6',
  border: '#EAECF0',
  danger: '#D92D20',
  softPurple: '#F0EAFE',
};

function formatNaira(amount: number) {
  return `₦${amount.toLocaleString('en-NG')}`;
}

export default function ShoppingCartScreen() {
  const router = useRouter();

  const {
    items,
    itemCount,
    subtotal,
    isHydrated,
    incrementQuantity,
    decrementQuantity,
    removeFromCart,
    clearCart,
  } = useShoppingCart();

  function checkout() {
    Alert.alert(
      'Checkout',
      'Checkout is not connected yet. Your cart is ready for payment integration.',
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={styles.backButton}
          accessibilityRole="button"
          accessibilityLabel="Go back"
        >
          <Ionicons name="arrow-back" size={22} color={COLORS.text} />
        </Pressable>

        <View style={styles.headerTitleContainer}>
          <Text style={styles.headerTitle}>My Cart</Text>
          <Text style={styles.headerSubtitle}>
            {!isHydrated
              ? 'Loading your cart...'
              : `${itemCount} ${itemCount === 1 ? 'item' : 'items'}`}
          </Text>
        </View>

        <View style={styles.headerPlaceholder} />
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {!isHydrated ? (
          <View style={styles.emptyState}>
            <Ionicons
              name="bag-handle-outline"
              size={44}
              color={COLORS.primary}
            />
            <Text style={styles.emptyTitle}>Loading your cart</Text>
            <Text style={styles.emptyDescription}>
              Restoring your saved shopping items.
            </Text>
          </View>
        ) : items.length === 0 ? (
          <View style={styles.emptyState}>
            <View style={styles.emptyIcon}>
              <Ionicons
                name="bag-handle-outline"
                size={44}
                color={COLORS.primary}
              />
            </View>

            <Text style={styles.emptyTitle}>Your cart is empty</Text>

            <Text style={styles.emptyDescription}>
              Discover products you love and add them to your cart.
            </Text>

            <Pressable
              onPress={() => router.push('/shopping')}
              style={styles.primaryButton}
              accessibilityRole="button"
            >
              <Text style={styles.primaryButtonText}>
                Continue shopping
              </Text>
              <Ionicons
                name="arrow-forward"
                size={18}
                color={COLORS.white}
              />
            </Pressable>
          </View>
        ) : (
          <>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Cart items</Text>

              <Pressable
                onPress={clearCart}
                disabled={!isHydrated}
                accessibilityRole="button"
              >
                <Text style={styles.clearText}>Clear cart</Text>
              </Pressable>
            </View>

            {items.map((item) => (
              <View key={item.product.id} style={styles.cartItem}>
                <View style={styles.productIcon}>
                  <Ionicons
                    name="cube-outline"
                    size={28}
                    color={COLORS.primary}
                  />
                </View>

                <View style={styles.productDetails}>
                  <Text style={styles.productName}>
                    {item.product.name}
                  </Text>

                  <Text style={styles.productPrice}>
                    {formatNaira(item.product.price)}
                  </Text>

                  <View style={styles.quantityControls}>
                    <Pressable
                      onPress={() => decrementQuantity(item.product.id)}
                      disabled={!isHydrated}
                      style={styles.quantityButton}
                      accessibilityRole="button"
                      accessibilityLabel={`Decrease quantity of ${item.product.name}`}
                    >
                      <Ionicons
                        name="remove"
                        size={16}
                        color={COLORS.text}
                      />
                    </Pressable>

                    <Text style={styles.quantityText}>
                      {item.quantity}
                    </Text>

                    <Pressable
                      onPress={() => incrementQuantity(item.product.id)}
                      disabled={!isHydrated}
                      style={styles.quantityButton}
                      accessibilityRole="button"
                      accessibilityLabel={`Increase quantity of ${item.product.name}`}
                    >
                      <Ionicons
                        name="add"
                        size={16}
                        color={COLORS.text}
                      />
                    </Pressable>
                  </View>
                </View>

                <View style={styles.itemRight}>
                  <Text style={styles.lineTotal}>
                    {formatNaira(item.product.price * item.quantity)}
                  </Text>

                  <Pressable
                    onPress={() => removeFromCart(item.product.id)}
                    disabled={!isHydrated}
                    style={styles.removeButton}
                    accessibilityRole="button"
                    accessibilityLabel={`Remove ${item.product.name}`}
                  >
                    <Ionicons
                      name="trash-outline"
                      size={19}
                      color={COLORS.danger}
                    />
                  </Pressable>
                </View>
              </View>
            ))}

            <View style={styles.summaryCard}>
              <Text style={styles.sectionTitle}>Order summary</Text>

              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Items</Text>
                <Text style={styles.summaryValue}>{itemCount}</Text>
              </View>

              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Subtotal</Text>
                <Text style={styles.summaryValue}>
                  {formatNaira(subtotal)}
                </Text>
              </View>

              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Delivery</Text>
                <Text style={styles.summaryValue}>
                  Calculated at checkout
                </Text>
              </View>

              <View style={styles.summaryDivider} />

              <View style={styles.summaryRow}>
                <Text style={styles.totalLabel}>Total</Text>
                <Text style={styles.totalValue}>
                  {formatNaira(subtotal)}
                </Text>
              </View>

              <Pressable
                onPress={checkout}
                style={styles.primaryButton}
                accessibilityRole="button"
              >
                <Text style={styles.primaryButtonText}>
                  Proceed to checkout
                </Text>
                <Ionicons
                  name="arrow-forward"
                  size={18}
                  color={COLORS.white}
                />
              </Pressable>
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    backgroundColor: COLORS.white,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  backButton: {
    width: 42,
    height: 42,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 14,
    backgroundColor: COLORS.background,
  },
  headerTitleContainer: {
    flex: 1,
    alignItems: 'center',
  },
  headerTitle: {
    color: COLORS.text,
    fontSize: 18,
    fontWeight: '800',
  },
  headerSubtitle: {
    color: COLORS.muted,
    fontSize: 12,
    marginTop: 3,
  },
  headerPlaceholder: {
    width: 42,
  },
  content: {
    padding: 20,
    paddingBottom: 40,
    flexGrow: 1,
  },
  emptyState: {
    flex: 1,
    minHeight: 420,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 12,
  },
  emptyIcon: {
    width: 100,
    height: 100,
    borderRadius: 32,
    backgroundColor: COLORS.softPurple,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  emptyTitle: {
    color: COLORS.text,
    fontSize: 23,
    fontWeight: '800',
    textAlign: 'center',
    marginTop: 12,
  },
  emptyDescription: {
    color: COLORS.muted,
    fontSize: 14,
    lineHeight: 22,
    textAlign: 'center',
    marginTop: 10,
    maxWidth: 280,
  },
  primaryButton: {
    minHeight: 52,
    width: '100%',
    backgroundColor: COLORS.primary,
    borderRadius: 15,
    paddingHorizontal: 18,
    marginTop: 24,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  primaryButtonText: {
    color: COLORS.white,
    fontSize: 14,
    fontWeight: '800',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 14,
  },
  sectionTitle: {
    color: COLORS.text,
    fontSize: 17,
    fontWeight: '800',
  },
  clearText: {
    color: COLORS.danger,
    fontSize: 13,
    fontWeight: '700',
  },
  cartItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: COLORS.white,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 18,
    padding: 14,
    marginBottom: 12,
    gap: 12,
  },
  productIcon: {
    width: 62,
    height: 68,
    borderRadius: 15,
    backgroundColor: COLORS.softPurple,
    alignItems: 'center',
    justifyContent: 'center',
  },
  productDetails: {
    flex: 1,
  },
  productName: {
    color: COLORS.text,
    fontSize: 14,
    fontWeight: '800',
  },
  productPrice: {
    color: COLORS.primary,
    fontSize: 13,
    fontWeight: '700',
    marginTop: 5,
  },
  quantityControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 13,
    marginTop: 12,
  },
  quantityButton: {
    width: 29,
    height: 29,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 9,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  quantityText: {
    color: COLORS.text,
    fontSize: 13,
    fontWeight: '700',
  },
  itemRight: {
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    minHeight: 68,
  },
  lineTotal: {
    color: COLORS.text,
    fontSize: 13,
    fontWeight: '800',
  },
  removeButton: {
    padding: 5,
    marginTop: 10,
  },
  summaryCard: {
    backgroundColor: COLORS.white,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 20,
    padding: 18,
    marginTop: 12,
  },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    marginTop: 17,
  },
  summaryLabel: {
    color: COLORS.muted,
    fontSize: 13,
  },
  summaryValue: {
    color: COLORS.text,
    fontSize: 13,
    fontWeight: '600',
  },
  summaryDivider: {
    height: 1,
    backgroundColor: COLORS.border,
    marginTop: 19,
  },
  totalLabel: {
    color: COLORS.text,
    fontSize: 15,
    fontWeight: '800',
  },
  totalValue: {
    color: COLORS.primary,
    fontSize: 18,
    fontWeight: '800',
  },
});
