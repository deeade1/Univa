/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/reviews/ReviewList.jsx         */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import {
  View,
  Text,
  FlatList,
  StyleSheet,
  RefreshControl,
} from "react-native";


import theme from "@/theme"

import ReviewCard from "./ReviewCard";
import OrdersEmpty from "../orders/OrdersEmpty";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ReviewList = memo(
  ({
    reviews = [],

    loading = false,

    refreshing = false,

    ListHeaderComponent,

    ListFooterComponent,

    EmptyComponent,

    contentContainerStyle,

    showProduct = false,

    showImages = true,

    showVerified = true,

    showHelpful = true,

    showReply = true,

    compact = false,

    onReviewPress,

    onHelpfulPress,

    onRefresh,

    keyExtractor,

    style,
  }) => {
    const { colors } = theme;


    const data = useMemo(
      () => reviews ?? [],
      [reviews]
    );

    const renderItem =
      useCallback(
        ({ item }) => (
          <ReviewCard
            review={item}
            compact={compact}
            showProduct={
              showProduct
            }
            showImages={
              showImages
            }
            showVerified={
              showVerified
            }
            showHelpful={
              showHelpful
            }
            showReply={
              showReply
            }
            onPress={
              onReviewPress
            }
            onHelpful={
              onHelpfulPress
            }
          />
        ),
        [
          compact,
          showProduct,
          showImages,
          showVerified,
          showHelpful,
          showReply,
          onReviewPress,
          onHelpfulPress,
        ]
      );

    const renderEmpty =
      useCallback(() => {
        if (loading)
          return null;

        if (
          EmptyComponent
        ) {
          return (
            <EmptyComponent />
          );
        }

        return (
          <OrdersEmpty
            icon="star-outline"
            title="No Reviews Yet"
            description="Be the first customer to review this product."
            showButton={
              false
            }
          />
        );
      }, [
        loading,
        EmptyComponent,
      ]);

    const extractKey =
      useCallback(
        (
          item,
          index
        ) => {
          if (
            keyExtractor
          ) {
            return keyExtractor(
              item,
              index
            );
          }

          return (
            item?.id?.toString?.() ??
            item?.pk?.toString?.() ??
            item?.uuid ??
            index.toString()
          );
        },
        [keyExtractor]
      );

    return (
      <FlatList
        data={data}
        renderItem={
          renderItem
        }
        keyExtractor={
          extractKey
        }
        style={style}
        ListHeaderComponent={
          ListHeaderComponent
        }
        ListFooterComponent={
          ListFooterComponent
        }
        ListEmptyComponent={
          renderEmpty
        }
        contentContainerStyle={[
          styles.content,
          data.length ===
            0 &&
            styles.emptyContent,
          contentContainerStyle,
        ]}
        showsVerticalScrollIndicator={
          false
        }
        keyboardShouldPersistTaps="handled"
        removeClippedSubviews
        initialNumToRender={
          6
        }
        maxToRenderPerBatch={
          8
        }
        windowSize={8}
        refreshControl={
          onRefresh ? (
            <RefreshControl
              refreshing={
                refreshing
              }
              onRefresh={
                onRefresh
              }
              tintColor={
                colors.primary
              }
            />
          ) : undefined
        }
      />
    );
  }
);

ReviewList.displayName =
  "ReviewList";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    content: {
      paddingHorizontal: 16,
      paddingBottom: 24,
    },

    emptyContent: {
      flexGrow: 1,
      justifyContent:
        "center",
    },
  });

export default ReviewList;