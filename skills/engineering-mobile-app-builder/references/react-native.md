# React Native Example (Cross-Platform)

Full product list implementation with `FlatList`, `react-query` infinite scrolling, pull-to-refresh, and platform-specific styling.

```typescript
import React, { useMemo, useCallback } from 'react';
import {
  FlatList,
  StyleSheet,
  Platform,
  RefreshControl,
  View,
  Text,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useInfiniteQuery } from '@tanstack/react-query';

interface Product {
  id: string;
  name: string;
  price: number;
}

// Product card component used in the list
const ProductCard: React.FC<{
  product: Product;
  onPress: () => void;
  style?: ViewStyle;
}> = ({ product, onPress, style }) => (
  <TouchableOpacity onPress={onPress} style={style}>
    <View style={{ padding: 16 }}>
      <Text style={{ fontSize: 16, fontWeight: '600' }}>{product.name}</Text>
      <Text style={{ fontSize: 14, color: '#666' }}>${product.price.toFixed(2)}</Text>
    </View>
  </TouchableOpacity>
);

// Fetch function used by react-query
async function fetchProducts(page: number): Promise<{ products: Product[]; nextPage: number | undefined }> {
  const response = await fetch(`https://api.example.com/products?page=${page}`);
  return response.json();
}

interface ProductListProps {
  onProductSelect: (product: Product) => void;
}

export const ProductList: React.FC<ProductListProps> = ({ onProductSelect }) => {
  const insets = useSafeAreaInsets();

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
    isRefetching,
  } = useInfiniteQuery({
    queryKey: ['products'],
    queryFn: ({ pageParam }) => fetchProducts(pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextPage,
  });

  const products = useMemo(
    () => data?.pages.flatMap(page => page.products) ?? [],
    [data]
  );

  const renderItem = useCallback(({ item }: { item: Product }) => (
    <ProductCard
      product={item}
      onPress={() => onProductSelect(item)}
      style={styles.productCard}
    />
  ), [onProductSelect]);

  const handleEndReached = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const keyExtractor = useCallback((item: Product) => item.id, []);

  return (
    <FlatList
      data={products}
      renderItem={renderItem}
      keyExtractor={keyExtractor}
      onEndReached={handleEndReached}
      onEndReachedThreshold={0.5}
      refreshControl={
        <RefreshControl
          refreshing={isRefetching}
          onRefresh={refetch}
          colors={['#007AFF']}
          tintColor="#007AFF"
        />
      }
      contentContainerStyle={[styles.container, { paddingBottom: insets.bottom }]}
      showsVerticalScrollIndicator={false}
      removeClippedSubviews={Platform.OS === 'android'}
      maxToRenderPerBatch={10}
      updateCellsBatchingPeriod={50}
      windowSize={21}
    />
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 16,
  },
  productCard: {
    marginBottom: 12,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
      },
      android: {
        elevation: 3,
      },
    }),
  },
});
```
