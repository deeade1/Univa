

import { router } from 'expo-router';

import { useMemo, useState } from 'react';

import {

  Image,

  Pressable,

  ScrollView,

  StatusBar,

  StyleSheet,

  Text,

  TextInput,

  View,

} from 'react-native';

import { SafeAreaView } from 'react-native-safe-area-context';



import {

  formatNaira,

  SHOPPING_CATEGORIES,

  SHOPPING_PRODUCTS,

} from '@/constants/shopping-products';

import { useShoppingCart } from '@/contexts/shopping-cart-context';



const C = {

  background: '#F7F8FC',

  surface: '#FFFFFF',

  primary: '#3659E3',

  primaryDark: '#2445C5',

  primarySoft: '#EAF0FF',

  text: '#172033',

  muted: '#758096',

  border: '#E8EBF2',

  gold: '#F4B740',

};



export default function ShoppingScreen() {



  const [search, setSearch] = useState('');

  const [category, setCategory] = useState<string>('All');

  const [favorites, setFavorites] = useState<string[]>([]);



  const { addToCart, itemCount, isHydrated } = useShoppingCart();





  const products = useMemo(() => {

    const query = search.trim().toLowerCase();



    return SHOPPING_PRODUCTS.filter((product) => {

      const matchesCategory =

        category === 'All' || product.category === category;



      const matchesSearch =

        !query ||

        `${product.name} ${product.category}`

          .toLowerCase()

          .includes(query);



      return matchesCategory && matchesSearch;

    });

  }, [search, category]);



  function toggleFavorite(id: string) {

    setFavorites((current) =>

      current.includes(id)

        ? current.filter((item) => item !== id)

        : [...current, id]

    );

  }



  function openProduct(id: string) {

    router.push({

      pathname: '/shopping/[id]',

      params: { id },

    });

  }



  return (

    <SafeAreaView style={styles.safeArea} edges={['top']}>

      <StatusBar

        barStyle="dark-content"

        backgroundColor={C.background}

      />



      <ScrollView

        showsVerticalScrollIndicator={false}

        keyboardShouldPersistTaps="handled"

        contentContainerStyle={styles.content}

      >

        <View style={styles.topBar}>

          <Pressable

            onPress={() => router.replace('/(tabs)')}

            accessibilityRole="button"

            accessibilityLabel="Return to Univa home"

            style={styles.backButton}

          >

            <Text style={styles.backIcon}>‹</Text>

          </Pressable>



          <View style={styles.topTitleWrap}>

            <Text style={styles.brand}>univa</Text>

            <Text style={styles.topSubtitle}>SHOPPING</Text>

          </View>



          <Pressable

            accessibilityRole="button"



accessibilityLabel={`Shopping cart, ${itemCount} items`}

onPress={() => router.push('/shopping/cart')}



            style={styles.cartButton}

          >

            <Text style={styles.cartIcon}>🛒</Text>

            {itemCount > 0 && (

              <View style={styles.cartBadge}>

                <Text style={styles.cartBadgeText}>

                  {itemCount > 99 ? '99+' : itemCount}

                </Text>

              </View>

            )}

          </Pressable>

        </View>



        <View style={styles.intro}>

          <Text style={styles.eyebrow}>THE UNIVA MARKETPLACE</Text>

          <Text style={styles.heading}>

            Find something{'\n'}

            <Text style={styles.headingAccent}>you&apos;ll love.</Text>

          </Text>

          <Text style={styles.description}>

            Discover everyday essentials and little luxuries.

          </Text>

        </View>



        <View style={styles.searchBox}>

          <Text style={styles.searchIcon}>⌕</Text>

          <TextInput

            value={search}

            onChangeText={setSearch}

            placeholder="Search products..."

            placeholderTextColor={C.muted}

            style={styles.searchInput}

            returnKeyType="search"

            accessibilityLabel="Search shopping products"

          />

          {search.length > 0 && (

            <Pressable

              onPress={() => setSearch('')}

              hitSlop={10}

              accessibilityLabel="Clear product search"

            >

              <Text style={styles.clearText}>×</Text>

            </Pressable>

          )}

        </View>



        <View style={styles.promoCard}>

          <View style={styles.promoTextArea}>

            <View style={styles.promoBadge}>

              <Text style={styles.promoBadgeText}>DISCOVER MORE</Text>

            </View>

            <Text style={styles.promoTitle}>

              Good finds.{'\n'}Great possibilities.

            </Text>

            <Text style={styles.promoDescription}>

              Your next favourite thing is waiting.

            </Text>

          </View>

          <View style={styles.promoArt}>

            <Text style={styles.promoEmoji}>✦</Text>

            <View style={styles.promoCircle} />

          </View>

        </View>



        <View style={styles.sectionHeader}>

          <View>

            <Text style={styles.sectionTitle}>Shop by category</Text>

            <Text style={styles.sectionSubtitle}>

              Find your next favourite.

            </Text>

          </View>

        </View>



        <ScrollView

          horizontal

          showsHorizontalScrollIndicator={false}

          contentContainerStyle={styles.categoryList}

        >

          {SHOPPING_CATEGORIES.map((item) => {

            const active = category === item;



            return (

              <Pressable

                key={item}

                onPress={() => setCategory(item)}

                accessibilityRole="button"

                accessibilityState={{ selected: active }}

                style={[

                  styles.categoryChip,

                  active && styles.categoryChipActive,

                ]}

              >

                <Text

                  style={[

                    styles.categoryText,

                    active && styles.categoryTextActive,

                  ]}

                >

                  {item}

                </Text>

              </Pressable>

            );

          })}

        </ScrollView>



        <View style={styles.sectionHeader}>

          <View>

            <Text style={styles.sectionTitle}>

              {search || category !== 'All'

                ? 'Your results'

                : 'Picked for you'}

            </Text>

            <Text style={styles.sectionSubtitle}>

              {products.length} products to explore

            </Text>

          </View>

        </View>



        {products.length > 0 ? (

          <View style={styles.productGrid}>

            {products.map((product) => {

              const favorite = favorites.includes(product.id);



              return (

                <View key={product.id} style={styles.productCard}>

                  <Pressable

                    onPress={() => openProduct(product.id)}

                    accessibilityRole="button"

                    accessibilityLabel={`View ${product.name}`}

                    style={({ pressed }) => [

                      styles.productImageWrap,

                      pressed && styles.pressed,

                    ]}

                  >

                    <Image

                      source={{ uri: product.image }}

                      style={styles.productImage}

                      resizeMode="cover"

                    />



                    {product.badge && (

                      <View style={styles.productBadge}>

                        <Text style={styles.productBadgeText}>

                          {product.badge}

                        </Text>

                      </View>

                    )}

                  </Pressable>



                  <Pressable

                    onPress={() => toggleFavorite(product.id)}

                    accessibilityRole="button"

                    accessibilityLabel={

                      favorite

                        ? `Remove ${product.name} from favourites`

                        : `Add ${product.name} to favourites`

                    }

                    accessibilityState={{ selected: favorite }}

                    hitSlop={6}

                    style={styles.favoriteButton}

                  >

                    <Text

                      style={[

                        styles.favoriteIcon,

                        favorite && styles.favoriteIconActive,

                      ]}

                    >

                      {favorite ? '♥' : '♡'}

                    </Text>

                  </Pressable>

                <View style={styles.productInfo}>
                  <Pressable
                    onPress={() => openProduct(product.id)}
                    accessibilityRole="button"
                    accessibilityLabel={`View ${product.name}`}
                  >
                    <Text style={styles.productCategory}>
                      {product.category.toUpperCase()}
                    </Text>

                    <Text style={styles.productName} numberOfLines={2}>
                      {product.name}
                    </Text>

                    <View style={styles.ratingRow}>
                      <Text style={styles.star}>★</Text>

                      <Text style={styles.rating}>
                        {product.rating.toFixed(1)}
                      </Text>

                      <Text style={styles.reviews}>
                        ({product.reviews})
                      </Text>
                    </View>

                    <Text style={styles.productPrice}>
                      {formatNaira(product.price)}
                    </Text>
                  </Pressable>

                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={`Add ${product.name} to cart`}
                    onPress={() => addToCart(product)}
                    disabled={!isHydrated}
                    style={({ pressed }) => [
                      styles.addButton,
                      pressed && styles.addButtonPressed,
                    ]}
                  >
                    <Text style={styles.addButtonText}>
                      + Add to cart
                    </Text>
                  </Pressable>
                </View>


                </View>

              );

            })}

          </View>

        ) : (

          <View style={styles.emptyState}>

            <Text style={styles.emptyIcon}>⌕</Text>

            <Text style={styles.emptyTitle}>No products found</Text>

            <Text style={styles.emptyDescription}>

              Try a different search or category.

            </Text>

            <Pressable

              onPress={() => {

                setSearch('');

                setCategory('All');

              }}

              style={styles.resetButton}

            >

              <Text style={styles.resetButtonText}>Show all products</Text>

            </Pressable>

          </View>

        )}



        <View style={styles.footer}>

          <Text style={styles.footerBrand}>univa</Text>

          <Text style={styles.footerText}>

            More to discover. More to love.

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

    paddingTop: 8,

    paddingBottom: 35,

  },

  topBar: {

    flexDirection: 'row',

    alignItems: 'center',

    marginBottom: 28,

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

  backIcon: {

    fontSize: 34,

    lineHeight: 37,

    color: C.text,

    marginTop: -4,

  },

  topTitleWrap: {

    flex: 1,

    alignItems: 'center',

  },

  brand: {

    color: C.text,

    fontSize: 22,

    fontWeight: '800',

    letterSpacing: -0.8,

  },

  topSubtitle: {

    color: C.muted,

    fontSize: 8,

    fontWeight: '800',

    letterSpacing: 2,

    marginTop: 2,

  },

  cartButton: {

    width: 42,

    height: 42,

    borderRadius: 15,

    backgroundColor: C.surface,

    borderWidth: 1,

    borderColor: C.border,

    alignItems: 'center',

    justifyContent: 'center',

  },

  cartIcon: {

    fontSize: 19,

  },

  cartBadge: {

    position: 'absolute',

    top: -5,

    right: -5,

    minWidth: 18,

    height: 18,

    borderRadius: 9,

    backgroundColor: C.primary,

    alignItems: 'center',

    justifyContent: 'center',

    paddingHorizontal: 4,

  },

  cartBadgeText: {

    color: '#FFFFFF',

    fontSize: 9,

    fontWeight: '800',

  },

  intro: {

    marginBottom: 22,

  },

  eyebrow: {

    color: C.primary,

    fontSize: 10,

    fontWeight: '800',

    letterSpacing: 1.7,

    marginBottom: 10,

  },

  heading: {

    color: C.text,

    fontSize: 32,

    fontWeight: '800',

    letterSpacing: -1.2,

    lineHeight: 38,

  },

  headingAccent: {

    color: C.primary,

  },

  description: {

    color: C.muted,

    fontSize: 13,

    lineHeight: 20,

    marginTop: 9,

  },

  searchBox: {

    minHeight: 54,

    backgroundColor: C.surface,

    borderRadius: 16,

    borderWidth: 1,

    borderColor: C.border,

    flexDirection: 'row',

    alignItems: 'center',

    paddingHorizontal: 14,

    marginBottom: 23,

  },

  searchIcon: {

    fontSize: 28,

    color: C.primary,

    marginRight: 10,

  },

  searchInput: {

    flex: 1,

    color: C.text,

    fontSize: 13,

    paddingVertical: 12,

  },

  clearText: {

    color: C.muted,

    fontSize: 25,

    paddingHorizontal: 5,

  },

  promoCard: {

    minHeight: 180,

    borderRadius: 23,

    backgroundColor: C.primary,

    padding: 20,

    overflow: 'hidden',

    marginBottom: 30,

    flexDirection: 'row',

  },

  promoTextArea: {

    flex: 1,

    zIndex: 1,

  },

  promoBadge: {

    alignSelf: 'flex-start',

    backgroundColor: 'rgba(255,255,255,0.17)',

    borderRadius: 20,

    paddingHorizontal: 10,

    paddingVertical: 6,

    marginBottom: 12,

  },

  promoBadgeText: {

    color: '#FFFFFF',

    fontSize: 8,

    fontWeight: '800',

    letterSpacing: 1,

  },

  promoTitle: {

    color: '#FFFFFF',

    fontSize: 22,

    fontWeight: '800',

    lineHeight: 27,

    letterSpacing: -0.4,

  },

  promoDescription: {

    color: '#E2E8FF',

    fontSize: 10,

    lineHeight: 15,

    marginTop: 8,

    maxWidth: 205,

  },

  promoArt: {

    width: 55,

    alignItems: 'center',

    justifyContent: 'center',

  },

  promoEmoji: {

    fontSize: 56,

    color: '#FFFFFF',

    zIndex: 1,

  },

  promoCircle: {

    position: 'absolute',

    width: 130,

    height: 130,

    borderRadius: 65,

    backgroundColor: 'rgba(255,255,255,0.09)',

    right: -68,

    bottom: -48,

  },

  sectionHeader: {

    flexDirection: 'row',

    alignItems: 'center',

    justifyContent: 'space-between',

    marginBottom: 15,

  },

  sectionTitle: {

    color: C.text,

    fontSize: 19,

    fontWeight: '800',

    letterSpacing: -0.5,

  },

  sectionSubtitle: {

    color: C.muted,

    fontSize: 11,

    marginTop: 5,

  },

  categoryList: {

    gap: 9,

    paddingBottom: 25,

  },

  categoryChip: {

    borderWidth: 1,

    borderColor: C.border,

    backgroundColor: C.surface,

    paddingHorizontal: 16,

    paddingVertical: 10,

    borderRadius: 22,

  },

  categoryChipActive: {

    backgroundColor: C.primary,

    borderColor: C.primary,

  },

  categoryText: {

    color: C.muted,

    fontSize: 11,

    fontWeight: '700',

  },

  categoryTextActive: {

    color: '#FFFFFF',

  },

  productGrid: {

    flexDirection: 'row',

    flexWrap: 'wrap',

    justifyContent: 'space-between',

    rowGap: 15,

  },

  productCard: {

    width: '48%',

    backgroundColor: C.surface,

    borderRadius: 19,

    borderWidth: 1,

    borderColor: C.border,

    overflow: 'hidden',

  },

  productImageWrap: {

    height: 155,

    backgroundColor: '#EDF0F6',

  },

  productImage: {

    width: '100%',

    height: '100%',

  },

  productBadge: {

    position: 'absolute',

    top: 10,

    left: 9,

    backgroundColor: C.primary,

    paddingHorizontal: 9,

    paddingVertical: 5,

    borderRadius: 9,

  },

  productBadgeText: {

    color: '#FFFFFF',

    fontSize: 8,

    fontWeight: '800',

  },

  favoriteButton: {

    position: 'absolute',

    top: 9,

    right: 9,

    width: 32,

    height: 32,

    borderRadius: 16,

    backgroundColor: 'rgba(255,255,255,0.95)',

    alignItems: 'center',

    justifyContent: 'center',

  },

  favoriteIcon: {

    color: C.text,

    fontSize: 21,

    lineHeight: 25,

  },

  favoriteIconActive: {

    color: '#E34D70',

  },

  productInfo: {

    padding: 12,

  },

  productCategory: {

    color: C.muted,

    fontSize: 8,

    fontWeight: '800',

    letterSpacing: 1,

    marginBottom: 5,

  },

  productName: {

    color: C.text,

    fontSize: 12,

    fontWeight: '800',

    lineHeight: 17,

    minHeight: 34,

  },

  ratingRow: {

    flexDirection: 'row',

    alignItems: 'center',

    gap: 4,

    marginTop: 7,

  },

  star: {

    color: C.gold,

    fontSize: 13,

  },

  rating: {

    color: C.text,

    fontSize: 10,

    fontWeight: '700',

  },

  reviews: {

    color: C.muted,

    fontSize: 9,

  },

  productPrice: {

    color: C.text,

    fontSize: 14,

    fontWeight: '800',

    marginTop: 9,

    marginBottom: 11,

  },

  addButton: {

    backgroundColor: C.primarySoft,

    borderRadius: 10,

    paddingVertical: 10,

    alignItems: 'center',

    justifyContent: 'center',

  },

  addButtonPressed: {

    backgroundColor: '#D8E2FF',

  },

  addButtonText: {

    color: C.primaryDark,

    fontSize: 10,

    fontWeight: '800',

  },

  pressed: {

    opacity: 0.85,

  },

  emptyState: {

    backgroundColor: C.surface,

    borderRadius: 20,

    borderWidth: 1,

    borderColor: C.border,

    alignItems: 'center',

    padding: 25,

  },

  emptyIcon: {

    color: C.primary,

    fontSize: 35,

  },

  emptyTitle: {

    color: C.text,

    fontSize: 16,

    fontWeight: '800',

    marginTop: 8,

  },

  emptyDescription: {

    color: C.muted,

    fontSize: 12,

    marginTop: 5,

    textAlign: 'center',

  },

  resetButton: {

    marginTop: 15,

    backgroundColor: C.primarySoft,

    borderRadius: 12,

    paddingHorizontal: 15,

    paddingVertical: 10,

  },

  resetButtonText: {

    color: C.primary,

    fontSize: 11,

    fontWeight: '800',

  },

  footer: {

    alignItems: 'center',

    paddingTop: 35,

    gap: 5,

  },

  footerBrand: {

    color: C.text,

    fontSize: 19,

    fontWeight: '800',

  },

  footerText: {

    color: C.muted,

    fontSize: 11,

  },

});
