import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { SHOPPING_PRODUCTS } from '@/constants/shopping-products';

const STORAGE_KEY = '@univa/shopping-cart/v1';

export type ShoppingProduct = (typeof SHOPPING_PRODUCTS)[number];

export type ShoppingCartItem = {
  product: ShoppingProduct;
  quantity: number;
};

type ShoppingCartContextValue = {
  items: ShoppingCartItem[];
  itemCount: number;
  subtotal: number;
  isHydrated: boolean;
  addToCart: (product: ShoppingProduct, quantity?: number) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  incrementQuantity: (productId: string) => void;
  decrementQuantity: (productId: string) => void;
  removeFromCart: (productId: string) => void;
  clearCart: () => void;
};

const ShoppingCartContext =
  createContext<ShoppingCartContextValue | undefined>(undefined);

type ShoppingCartProviderProps = {
  children: ReactNode;
};

function isValidCartItem(value: unknown): value is ShoppingCartItem {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  const item = value as Record<string, unknown>;
  const product = item.product;

  if (typeof item.quantity !== 'number' || !Number.isInteger(item.quantity)) {
    return false;
  }

  if (item.quantity < 1 || typeof product !== 'object' || product === null) {
    return false;
  }

  const productRecord = product as Record<string, unknown>;

  return (
    typeof productRecord.id === 'string' &&
    typeof productRecord.name === 'string' &&
    typeof productRecord.price === 'number' &&
    Number.isFinite(productRecord.price) &&
    productRecord.price >= 0
  );
}

export function ShoppingCartProvider({
  children,
}: ShoppingCartProviderProps) {
  const [items, setItems] = useState<ShoppingCartItem[]>([]);
  const [isHydrated, setIsHydrated] = useState(false);

  // Restore the saved cart before enabling persistence writes.
  useEffect(() => {
    let active = true;

    async function restoreCart() {
      try {
        const storedValue = await AsyncStorage.getItem(STORAGE_KEY);

        if (storedValue && active) {
          const parsed: unknown = JSON.parse(storedValue);

          if (Array.isArray(parsed)) {
            const validItems = parsed.filter(isValidCartItem);

            // Use the current catalogue as the source of truth.
            const restoredItems = validItems.flatMap((item) => {
              const currentProduct = SHOPPING_PRODUCTS.find(
                (product) => product.id === item.product.id,
              );

              if (!currentProduct) {
                return [];
              }

              return [{
                product: currentProduct,
                quantity: item.quantity,
              }];
            });

            if (active) {
              setItems(restoredItems);
            }
          }
        }
      } catch (error) {
        console.error('[Univa Cart] Could not restore cart:', error);
      } finally {
        if (active) {
          setIsHydrated(true);
        }
      }
    }

    void restoreCart();

    return () => {
      active = false;
    };
  }, []);

  // Never overwrite saved data before restoration has finished.
  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    const serialized = JSON.stringify(items);

    void AsyncStorage.setItem(STORAGE_KEY, serialized).catch((error) => {
      console.error('[Univa Cart] Could not save cart:', error);
    });
  }, [items, isHydrated]);

  const addToCart = useCallback(
    (product: ShoppingProduct, quantity = 1) => {
      if (!Number.isInteger(quantity) || quantity < 1) {
        return;
      }

      setItems((currentItems) => {
        const existingItem = currentItems.find(
          (item) => item.product.id === product.id,
        );

        if (existingItem) {
          return currentItems.map((item) =>
            item.product.id === product.id
              ? { ...item, quantity: item.quantity + quantity }
              : item,
          );
        }

        return [...currentItems, { product, quantity }];
      });
    },
    [],
  );

  const updateQuantity = useCallback(
    (productId: string, quantity: number) => {
      if (!Number.isInteger(quantity)) {
        return;
      }

      setItems((currentItems) => {
        if (quantity <= 0) {
          return currentItems.filter(
            (item) => item.product.id !== productId,
          );
        }

        return currentItems.map((item) =>
          item.product.id === productId
            ? { ...item, quantity }
            : item,
        );
      });
    },
    [],
  );

  const incrementQuantity = useCallback((productId: string) => {
    setItems((currentItems) =>
      currentItems.map((item) =>
        item.product.id === productId
          ? { ...item, quantity: item.quantity + 1 }
          : item,
      ),
    );
  }, []);

  const decrementQuantity = useCallback((productId: string) => {
    setItems((currentItems) =>
      currentItems
        .map((item) =>
          item.product.id === productId
            ? { ...item, quantity: item.quantity - 1 }
            : item,
        )
        .filter((item) => item.quantity > 0),
    );
  }, []);

  const removeFromCart = useCallback((productId: string) => {
    setItems((currentItems) =>
      currentItems.filter((item) => item.product.id !== productId),
    );
  }, []);

  const clearCart = useCallback(() => {
    setItems([]);
  }, []);

  const itemCount = useMemo(
    () => items.reduce((total, item) => total + item.quantity, 0),
    [items],
  );

  const subtotal = useMemo(
    () =>
      items.reduce(
        (total, item) => total + item.product.price * item.quantity,
        0,
      ),
    [items],
  );

  const value = useMemo<ShoppingCartContextValue>(
    () => ({
      items,
      itemCount,
      subtotal,
      isHydrated,
      addToCart,
      updateQuantity,
      incrementQuantity,
      decrementQuantity,
      removeFromCart,
      clearCart,
    }),
    [
      items,
      itemCount,
      subtotal,
      isHydrated,
      addToCart,
      updateQuantity,
      incrementQuantity,
      decrementQuantity,
      removeFromCart,
      clearCart,
    ],
  );

  return (
    <ShoppingCartContext.Provider value={value}>
      {children}
    </ShoppingCartContext.Provider>
  );
}

export function useShoppingCart() {
  const context = useContext(ShoppingCartContext);

  if (!context) {
    throw new Error(
      'useShoppingCart must be used within ShoppingCartProvider.',
    );
  }

  return context;
}
