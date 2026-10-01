// apps/Univa/app/ecommerce/components/Reviews.jsx
import React from 'react';
import { View, Text, ScrollView, ActivityIndicator } from 'react-native';
import { useQuery } from '@apollo/client';
import { PRODUCT_REVIEWS_QUERY } from '@/modules/ecommerce/api/productQuery/queries';

export default function Reviews({ productId }) {
  const { data, loading, error, fetchMore } = useQuery(PRODUCT_REVIEWS_QUERY, {
    variables: { productId, first: 20 },
    skip: !productId,
  });

  if (loading) return <ActivityIndicator size="small" />;
  if (error) return <Text style={{ color: 'red' }}>Failed to load reviews</Text>;

  const reviews = (data?.productReviews?.edges || []).map(e => e.node);

  return (
    <ScrollView style={{ padding: 16 }}>
      <Text style={{ fontSize: 18, fontWeight: '700', marginBottom: 12 }}>
        Reviews ({reviews.length})
      </Text>

      {reviews.length === 0 && (
        <Text style={{ color: '#6B7280' }}>No reviews yet — be the first to review!</Text>
      )}

      {reviews.map(r => (
        <View key={r.id} style={{ marginBottom: 16 }}>
          <Text style={{ fontWeight: '700' }}>{r.user?.fullName || 'Anonymous'}</Text>
          <Text style={{ marginVertical: 4 }}>{'★'.repeat(Math.round(r.rating || 0))} ({r.rating})</Text>
          <Text style={{ color: '#374151' }}>{r.comment}</Text>
          <Text style={{ color: '#9CA3AF', marginTop: 6 }}>{new Date(r.createdAt).toLocaleDateString()}</Text>
        </View>
      ))}

      {/* optional: load more */}
      {data?.productReviews?.pageInfo?.hasNextPage && (
        <Text
          onPress={() => fetchMore({ variables: { after: data.productReviews.pageInfo.endCursor } })}
          style={{ color: '#1E90FF', marginTop: 12 }}
        >
          Load more
        </Text>
      )}
    </ScrollView>
  );
}
