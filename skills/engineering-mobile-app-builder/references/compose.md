# Jetpack Compose Example (Android)

Full product list implementation with Hilt, `StateFlow`, `LazyColumn`, search with debounce, and pagination.

```kotlin
// Type definitions

data class Product(
    val id: String,
    val name: String,
    val price: Double,
    val imageUrl: String?,
    val category: String
)

data class ProductListUiState(
    val products: List<Product> = emptyList(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

interface ProductRepository {
    suspend fun getProducts(page: Int = 0, pageSize: Int = 20): List<Product>
}

// Composables

@Composable
fun SearchBar(
    query: String,
    onQueryChange: (String) -> Unit,
    onSearch: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    TextField(
        value = query,
        onValueChange = onQueryChange,
        placeholder = { Text("Search products") },
        modifier = modifier,
        singleLine = true,
        keyboardActions = KeyboardActions(onSearch = { onSearch(query) })
    )
}

@Composable
fun ProductCard(
    product: Product,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(modifier = modifier.clickable(onClick = onClick)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = product.name, style = MaterialTheme.typography.titleMedium)
            Text(text = "$${product.price}", style = MaterialTheme.typography.bodyMedium)
        }
    }
}

// Main screen

@Composable
fun ProductListScreen(
    viewModel: ProductListViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val searchQuery by viewModel.searchQuery.collectAsStateWithLifecycle()

    Column {
        SearchBar(
            query = searchQuery,
            onQueryChange = viewModel::updateSearchQuery,
            onSearch = viewModel::search,
            modifier = Modifier.fillMaxWidth()
        )

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(
                items = uiState.products,
                key = { it.id }
            ) { product ->
                ProductCard(
                    product = product,
                    onClick = { viewModel.selectProduct(product) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .animateItem()
                )
            }

            if (uiState.isLoading) {
                item {
                    Box(
                        modifier = Modifier.fillMaxWidth(),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator()
                    }
                }
            }
        }
    }
}

@HiltViewModel
class ProductListViewModel @Inject constructor(
    private val productRepository: ProductRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProductListUiState())
    val uiState: StateFlow<ProductListUiState> = _uiState.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    init {
        loadProducts()
        observeSearchQuery()
    }

    private fun loadProducts() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }
            try {
                val products = productRepository.getProducts()
                _uiState.update { it.copy(products = products, isLoading = false) }
            } catch (exception: Exception) {
                _uiState.update { it.copy(isLoading = false, errorMessage = exception.message) }
            }
        }
    }

    fun updateSearchQuery(query: String) {
        _searchQuery.value = query
    }

    private fun observeSearchQuery() {
        searchQuery
            .debounce(300)
            .onEach { query -> filterProducts(query) }
            .launchIn(viewModelScope)
    }
}
```
