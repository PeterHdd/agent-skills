# Flutter Example (Cross-Platform)

Full product list implementation with Riverpod, `ListView.builder`, search with debounce, pagination, and pull-to-refresh.

```dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Models

class Product {
  final String id;
  final String name;
  final double price;
  final String? imageUrl;
  final String category;

  const Product({
    required this.id,
    required this.name,
    required this.price,
    this.imageUrl,
    required this.category,
  });
}

class ProductListState {
  final List<Product> products;
  final bool isLoading;
  final String? errorMessage;
  final int currentPage;
  final bool hasMore;

  const ProductListState({
    this.products = const [],
    this.isLoading = false,
    this.errorMessage,
    this.currentPage = 0,
    this.hasMore = true,
  });

  ProductListState copyWith({
    List<Product>? products,
    bool? isLoading,
    String? errorMessage,
    int? currentPage,
    bool? hasMore,
  }) {
    return ProductListState(
      products: products ?? this.products,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      currentPage: currentPage ?? this.currentPage,
      hasMore: hasMore ?? this.hasMore,
    );
  }
}

// Repository

abstract class ProductRepository {
  Future<List<Product>> getProducts({int page = 0, int pageSize = 20});
}

// Notifier (state management with Riverpod)

class ProductListNotifier extends StateNotifier<ProductListState> {
  final ProductRepository _repository;
  Timer? _debounce;
  String _searchQuery = '';

  ProductListNotifier(this._repository) : super(const ProductListState()) {
    loadProducts();
  }

  Future<void> loadProducts() async {
    if (state.isLoading || !state.hasMore) return;
    state = state.copyWith(isLoading: true);
    try {
      final products = await _repository.getProducts(page: state.currentPage);
      state = state.copyWith(
        products: [...state.products, ...products],
        isLoading: false,
        currentPage: state.currentPage + 1,
        hasMore: products.length == 20,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  Future<void> refresh() async {
    state = const ProductListState();
    await loadProducts();
  }

  void updateSearchQuery(String query) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () {
      _searchQuery = query;
      state = const ProductListState();
      loadProducts();
    });
  }

  List<Product> get filteredProducts {
    if (_searchQuery.isEmpty) return state.products;
    return state.products
        .where((p) => p.name.toLowerCase().contains(_searchQuery.toLowerCase()))
        .toList();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }
}

// Providers

final productRepositoryProvider = Provider<ProductRepository>((ref) {
  throw UnimplementedError('Override with actual implementation');
});

final productListProvider =
    StateNotifierProvider<ProductListNotifier, ProductListState>((ref) {
  return ProductListNotifier(ref.watch(productRepositoryProvider));
});

// Widgets

class ProductCard extends StatelessWidget {
  final Product product;
  final VoidCallback onTap;

  const ProductCard({super.key, required this.product, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: ListTile(
        title: Text(product.name),
        subtitle: Text(
          '\$${product.price.toStringAsFixed(2)}',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        onTap: onTap,
      ),
    );
  }
}

// Main screen

class ProductListScreen extends ConsumerStatefulWidget {
  const ProductListScreen({super.key});

  @override
  ConsumerState<ProductListScreen> createState() => _ProductListScreenState();
}

class _ProductListScreenState extends ConsumerState<ProductListScreen> {
  final _scrollController = ScrollController();
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      ref.read(productListProvider.notifier).loadProducts();
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(productListProvider);
    final notifier = ref.read(productListProvider.notifier);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Products'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: TextField(
              controller: _searchController,
              decoration: const InputDecoration(
                hintText: 'Search products',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(),
                filled: true,
              ),
              onChanged: notifier.updateSearchQuery,
            ),
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: notifier.refresh,
        child: ListView.builder(
          controller: _scrollController,
          itemCount: notifier.filteredProducts.length + (state.isLoading ? 1 : 0),
          itemBuilder: (context, index) {
            if (index == notifier.filteredProducts.length) {
              return const Center(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: CircularProgressIndicator(),
                ),
              );
            }
            final product = notifier.filteredProducts[index];
            return ProductCard(
              product: product,
              onTap: () {
                // Navigate to product detail
              },
            );
          },
        ),
      ),
    );
  }
}
```
