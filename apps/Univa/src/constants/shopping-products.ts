
export type ShoppingProduct = {
  id: string;
  name: string;
  category: string;
  price: number;
  rating: number;
  reviews: number;
  image: string;
  badge?: string;
  description: string;
};

export const SHOPPING_CATEGORIES = [
  'All',
  'Electronics',
  'Fashion',
  'Home',
  'Beauty',
] as const;

export const SHOPPING_PRODUCTS: ShoppingProduct[] = [
  {
    id: 'wireless-headphones',
    name: 'Wireless Headphones',
    category: 'Electronics',
    price: 48500,
    rating: 4.8,
    reviews: 124,
    image:
      'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=700&auto=format&fit=crop&q=85',
    badge: 'Popular',
    description:
      'Enjoy your favourite music with comfortable wireless headphones, rich sound, and a clean everyday design.',
  },
  {
    id: 'classic-sneakers',
    name: 'Classic Sneakers',
    category: 'Fashion',
    price: 32000,
    rating: 4.6,
    reviews: 89,
    image:
      'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=700&auto=format&fit=crop&q=85',
    badge: 'Trending',
    description:
      'Versatile everyday sneakers designed to complement casual outfits and keep you comfortable on the go.',
  },
  {
    id: 'everyday-watch',
    name: 'Everyday Watch',
    category: 'Fashion',
    price: 27500,
    rating: 4.5,
    reviews: 63,
    image:
      'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=700&auto=format&fit=crop&q=85',
    description:
      'A timeless everyday accessory with a minimalist look that works for casual and formal occasions.',
  },
  {
    id: 'leather-handbag',
    name: 'Leather Handbag',
    category: 'Fashion',
    price: 42000,
    rating: 4.7,
    reviews: 51,
    image:
      'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=700&auto=format&fit=crop&q=85',
    description:
      'A versatile handbag with a refined silhouette for everyday essentials and special occasions.',
  },
  {
    id: 'skincare-set',
    name: 'Daily Skincare Set',
    category: 'Beauty',
    price: 18500,
    rating: 4.4,
    reviews: 42,
    image:
      'https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=700&auto=format&fit=crop&q=85',
    description:
      'A curated skincare set for a simple daily self-care routine. Check individual product ingredients before use.',
  },
  {
    id: 'table-lamp',
    name: 'Modern Table Lamp',
    category: 'Home',
    price: 22000,
    rating: 4.6,
    reviews: 36,
    image:
      'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=700&auto=format&fit=crop&q=85',
    description:
      'Bring a warm, modern touch to your desk, bedside table, or favourite reading corner.',
  },
  {
    id: 'smart-speaker',
    name: 'Smart Speaker',
    category: 'Electronics',
    price: 56000,
    rating: 4.7,
    reviews: 77,
    image:
      'https://images.unsplash.com/photo-1589003077984-894e133dabab?w=700&auto=format&fit=crop&q=85',
    description:
      'A compact speaker for enjoying music, podcasts, and audio throughout your home.',
  },
  {
    id: 'sunglasses',
    name: 'Everyday Sunglasses',
    category: 'Fashion',
    price: 14500,
    rating: 4.3,
    reviews: 28,
    image:
      'https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=700&auto=format&fit=crop&q=85',
    description:
      'Complete your everyday look with a versatile pair of sunglasses. Check the actual UV protection specification before purchasing.',
  },
];

export function formatNaira(amount: number): string {
  return `₦${amount.toLocaleString('en-NG')}`;
}
