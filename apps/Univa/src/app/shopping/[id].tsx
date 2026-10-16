import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import {
  Alert,
  Image,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import {
  formatNaira,
  SHOPPING_PRODUCTS,
} from '@/constants/shopping-products';
import { useShoppingCart } from '@/contexts/shopping-cart-context';

const C = {
  background: '#F7F8FC',
  surface: '#FFFFFF',
  primary: '#3659E3',
  primaryDark: '#2445C5',
  text: '#172033',
  muted: '#758096',
  border: '#E8EBF2',
};

export default function ProductDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [quantity, setQuantity] = useState(1);
  const { addToCart, isHydrated } = useShoppingCart();

  const product = SHOPPING_PRODUCTS.find((item) => item.id === id);

  if (!product) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.center}>
          <Text style={styles.title}>Product not found</Text>

          <Pressable
            onPress={() => router.replace('/shopping')}
            style={styles.primaryButton}
            accessibilityRole="button"
          >
            <Text style={styles.primaryButtonText}>
              Back to Shopping
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  
  const handleAddToCart = () => {
    if (!product) {
      Alert.alert('Product unavailable', 'This product could not be found.');
      return;
    }

    if (!isHydrated) {
      Alert.alert('Please wait', 'Your cart is still loading.');
      return;
    }

    addToCart(product, quantity);
    router.push('/shopping/cart');
  };


  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar
        barStyle="dark-content"
        backgroundColor={C.background}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <View style={styles.header}>
          <Pressable
            onPress={() => router.back()}
            accessibilityRole="button"
            accessibilityLabel="Go back"
            style={styles.backButton}
          >
            <Text style={styles.backText}>‹</Text>
          </Pressable>

          <Text style={styles.headerTitle}>Product details</Text>

          <View style={styles.headerSpacer} />
        </View>

        <View style={styles.imageCard}>
          <Image
            source={{ uri: product.image }}
            style={styles.image}
            resizeMode="cover"
          />

          {product.badge && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>
                {product.badge}
              </Text>
            </View>
          )}
        </View>

        <View style={styles.productContent}>
          <Text style={styles.category}>
            {product.category.toUpperCase()}
          </Text>

          <Text style={styles.title}>{product.name}</Text>

          <View style={styles.ratingRow}>
            <Text style={styles.star}>★</Text>

            <Text style={styles.rating}>
              {product.rating.toFixed(1)}
            </Text>

            <Text style={styles.reviews}>
              {product.reviews} reviews
            </Text>
          </View>

          <Text style={styles.price}>
            {formatNaira(product.price)}
          </Text>

          <View style={styles.divider} />

          <Text style={styles.sectionTitle}>
            About this product
          </Text>

          <Text style={styles.description}>
            {product.description}
          </Text>

          <View style={styles.quantityRow}>
            <View>
              <Text style={styles.sectionTitle}>Quantity</Text>

              <Text style={styles.quantityHint}>
                Select how many you need
              </Text>
            </View>

            <View style={styles.quantityControl}>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Decrease quantity"
                accessibilityState={{ disabled: quantity <= 1 }}
                disabled={quantity <= 1}
                onPress={() =>
                  setQuantity((value) => Math.max(1, value - 1))
                }
                style={styles.quantityButton}
              >
                <Text style={styles.quantityButtonText}>−</Text>
              </Pressable>

              <Text style={styles.quantityValue}>
                {quantity}
              </Text>

              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Increase quantity"
                accessibilityState={{ disabled: quantity >= 99 }}
                disabled={quantity >= 99}
                onPress={() =>
                  setQuantity((value) => Math.min(99, value + 1))
                }
                style={styles.quantityButton}
              >
                <Text style={styles.quantityButtonText}>+</Text>
              </Pressable>
            </View>
          </View>

          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Subtotal</Text>

            <Text style={styles.totalPrice}>
              {formatNaira(product.price * quantity)}
            </Text>
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Add ${quantity} ${product.name} to cart`}
            disabled={!isHydrated}
            onPress={handleAddToCart}
            style={({ pressed }) => [
              styles.primaryButton,
              pressed && styles.pressed,
              !isHydrated && styles.disabledButton,
            ]}
          >
            <Text style={styles.primaryButtonText}>
              {isHydrated
                ? `Add to Cart · ${formatNaira(product.price * quantity)}`
                : 'Loading cart...'}
            </Text>
          </Pressable>

          <Text style={styles.disclaimer}>
            Demonstration catalogue. Availability, prices, delivery,
            and payment have not been connected to a backend.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: C.background,
  },
  content: {
    paddingHorizontal: 20,
    paddingBottom: 35,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    marginBottom: 12,
  },
  backButton: {
    width: 42,
    height: 42,
    borderRadius: 15,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backText: {
    color: C.text,
    fontSize: 34,
    lineHeight: 38,
    marginTop: -4,
  },
  headerTitle: {
    color: C.text,
    fontSize: 15,
    fontWeight: '800',
  },
  headerSpacer: {
    width: 42,
  },
  imageCard: {
    height: 310,
    backgroundColor: '#EDF0F6',
    borderRadius: 24,
    overflow: 'hidden',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  badge: {
    position: 'absolute',
    top: 14,
    left: 14,
    backgroundColor: C.primary,
    borderRadius: 10,
    paddingHorizontal: 11,
    paddingVertical: 7,
  },
  badgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '800',
  },
  productContent: {
    paddingTop: 24,
  },
  category: {
    color: C.primary,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1.5,
  },
  title: {
    color: C.text,
    fontSize: 27,
    lineHeight: 34,
    fontWeight: '800',
    letterSpacing: -0.8,
    marginTop: 7,
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 10,
  },
  star: {
    color: '#F4B740',
    fontSize: 17,
  },
  rating: {
    color: C.text,
    fontSize: 12,
    fontWeight: '800',
  },
  reviews: {
    color: C.muted,
    fontSize: 12,
  },
  price: {
    color: C.primaryDark,
    fontSize: 26,
    fontWeight: '800',
    marginTop: 18,
  },
  divider: {
    height: 1,
    backgroundColor: C.border,
    marginVertical: 22,
  },
  sectionTitle: {
    color: C.text,
    fontSize: 15,
    fontWeight: '800',
  },
  description: {
    color: C.muted,
    fontSize: 13,
    lineHeight: 22,
    marginTop: 9,
  },
  quantityRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 27,
  },
  quantityHint: {
    color: C.muted,
    fontSize: 10,
    marginTop: 4,
  },
  quantityControl: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 13,
    padding: 5,
    gap: 12,
  },
  quantityButton: {
    width: 32,
    height: 32,
    borderRadius: 9,
    backgroundColor: '#EDF1FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  quantityButtonText: {
    color: C.primary,
    fontSize: 21,
    fontWeight: '700',
  },
  quantityValue: {
    minWidth: 18,
    textAlign: 'center',
    color: C.text,
    fontSize: 14,
    fontWeight: '800',
  },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: C.border,
    marginTop: 25,
    paddingTop: 19,
  },
  totalLabel: {
    color: C.muted,
    fontSize: 13,
  },
  totalPrice: {
    color: C.text,
    fontSize: 18,
    fontWeight: '800',
  },
  primaryButton: {
    minHeight: 54,
    backgroundColor: C.primary,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
    marginTop: 20,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '800',
  },
  pressed: {
    opacity: 0.85,
  },
  disabledButton: {
    opacity: 0.6,
  },
  disclaimer: {
    color: C.muted,
    fontSize: 10,
    lineHeight: 16,
    textAlign: 'center',
    marginTop: 14,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
});
