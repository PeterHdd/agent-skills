# SwiftUI Example (iOS 17+)

Full product list implementation with `@StateObject`, `NavigationStack`, search, pagination, and pull-to-refresh.

```swift
import SwiftUI

// MARK: - Type definitions

struct Product: Identifiable, Equatable {
    let id: String
    let name: String
    let price: Decimal
    let imageURL: URL?
    let category: String
}

struct ProductFilters {
    var category: String?
    var minPrice: Decimal?
    var maxPrice: Decimal?
}

class ProductService {
    func fetchProducts(page: Int = 0, pageSize: Int = 20) async throws -> [Product] {
        // Network call to fetch products from API
        fatalError("Implement with URLSession or networking library")
    }
}

// MARK: - Views

struct ProductRowView: View {
    let product: Product
    var body: some View {
        HStack {
            Text(product.name)
            Spacer()
            Text(product.price, format: .currency(code: "USD"))
        }
    }
}

struct FilterView: View {
    @Binding var filters: ProductFilters
    var body: some View {
        Form {
            TextField("Category", text: Binding(
                get: { filters.category ?? "" },
                set: { filters.category = $0.isEmpty ? nil : $0 }
            ))
        }
    }
}

// MARK: - Main view

struct ProductListView: View {
    @StateObject private var viewModel = ProductListViewModel()
    @State private var searchText = ""

    var body: some View {
        NavigationStack {
            List(viewModel.filteredProducts) { product in
                ProductRowView(product: product)
                    .onAppear {
                        if product == viewModel.filteredProducts.last {
                            viewModel.loadMoreProducts()
                        }
                    }
            }
            .searchable(text: $searchText)
            .onChange(of: searchText) { oldValue, newValue in
                viewModel.filterProducts(newValue)
            }
            .refreshable {
                await viewModel.refreshProducts()
            }
            .navigationTitle("Products")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Filter") {
                        viewModel.showFilterSheet = true
                    }
                }
            }
            .sheet(isPresented: $viewModel.showFilterSheet) {
                FilterView(filters: $viewModel.filters)
            }
        }
        .task {
            await viewModel.loadInitialProducts()
        }
    }
}

@MainActor
class ProductListViewModel: ObservableObject {
    @Published var products: [Product] = []
    @Published var filteredProducts: [Product] = []
    @Published var isLoading = false
    @Published var showFilterSheet = false
    @Published var filters = ProductFilters()

    private let productService = ProductService()

    func loadInitialProducts() async {
        isLoading = true
        defer { isLoading = false }
        do {
            products = try await productService.fetchProducts()
            filteredProducts = products
        } catch {
            print("Error loading products: \(error)")
        }
    }

    func refreshProducts() async {
        await loadInitialProducts()
    }

    func loadMoreProducts() {
        // Pagination logic
    }

    func filterProducts(_ searchText: String) {
        if searchText.isEmpty {
            filteredProducts = products
        } else {
            filteredProducts = products.filter { product in
                product.name.localizedCaseInsensitiveContains(searchText)
            }
        }
    }
}
```
