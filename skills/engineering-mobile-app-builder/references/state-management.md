# Cross-Platform State Management

Production patterns for state management across React Native (Zustand + MMKV, TanStack Query), SwiftUI (@Observable, environment injection), and Compose (ViewModel + StateFlow, Hilt). Includes navigation state, authentication state machines, and form validation.

## React Native: Zustand with MMKV Persistence

```typescript
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { MMKV } from 'react-native-mmkv';

// --- MMKV storage adapter for Zustand ---

const storage = new MMKV({ id: 'app-storage' });

const mmkvStorage = createJSONStorage(() => ({
  getItem: (key: string) => storage.getString(key) ?? null,
  setItem: (key: string, value: string) => storage.set(key, value),
  removeItem: (key: string) => storage.delete(key),
}));

// --- User preferences store: persisted to MMKV ---

interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  notificationsEnabled: boolean;
  onboardingComplete: boolean;
}

interface PreferencesStore extends UserPreferences {
  setTheme: (theme: UserPreferences['theme']) => void;
  setLanguage: (language: string) => void;
  toggleNotifications: () => void;
  completeOnboarding: () => void;
  reset: () => void;
}

const defaultPreferences: UserPreferences = {
  theme: 'system',
  language: 'en',
  notificationsEnabled: true,
  onboardingComplete: false,
};

export const usePreferencesStore = create<PreferencesStore>()(
  persist(
    (set) => ({
      ...defaultPreferences,
      setTheme: (theme) => set({ theme }),
      setLanguage: (language) => set({ language }),
      toggleNotifications: () =>
        set((state) => ({ notificationsEnabled: !state.notificationsEnabled })),
      completeOnboarding: () => set({ onboardingComplete: true }),
      reset: () => set(defaultPreferences),
    }),
    {
      name: 'user-preferences',
      storage: mmkvStorage,
    }
  )
);

// --- Cart store: computed totals with selectors ---

interface CartItem {
  productId: string;
  name: string;
  price: number;
  quantity: number;
}

interface CartStore {
  items: CartItem[];
  addItem: (product: Omit<CartItem, 'quantity'>) => void;
  removeItem: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clear: () => void;
}

export const useCartStore = create<CartStore>()(
  persist(
    (set) => ({
      items: [],
      addItem: (product) =>
        set((state) => {
          const existing = state.items.find((i) => i.productId === product.productId);
          if (existing) {
            return {
              items: state.items.map((i) =>
                i.productId === product.productId
                  ? { ...i, quantity: i.quantity + 1 }
                  : i
              ),
            };
          }
          return { items: [...state.items, { ...product, quantity: 1 }] };
        }),
      removeItem: (productId) =>
        set((state) => ({
          items: state.items.filter((i) => i.productId !== productId),
        })),
      updateQuantity: (productId, quantity) =>
        set((state) => ({
          items: quantity <= 0
            ? state.items.filter((i) => i.productId !== productId)
            : state.items.map((i) =>
                i.productId === productId ? { ...i, quantity } : i
              ),
        })),
      clear: () => set({ items: [] }),
    }),
    {
      name: 'cart',
      storage: mmkvStorage,
    }
  )
);

// Derived selectors — call outside the store to avoid unnecessary re-renders
export const useCartTotal = () =>
  useCartStore((state) =>
    state.items.reduce((sum, item) => sum + item.price * item.quantity, 0)
  );

export const useCartItemCount = () =>
  useCartStore((state) =>
    state.items.reduce((sum, item) => sum + item.quantity, 0)
  );
```

## React Native: TanStack Query for Server State

```typescript
import {
  useQuery,
  useMutation,
  useQueryClient,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query';

// --- Query client with sensible mobile defaults ---

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,       // 5 min before refetch
      gcTime: 30 * 60 * 1000,          // 30 min garbage collection
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
      refetchOnWindowFocus: false,      // Mobile: no window focus concept
      refetchOnReconnect: true,         // Refetch when network returns
    },
    mutations: {
      retry: 1,
    },
  },
});

// --- Typed API hooks with optimistic mutations ---

interface Todo {
  id: string;
  text: string;
  completed: boolean;
}

async function fetchTodos(): Promise<Todo[]> {
  const res = await fetch('/api/todos');
  if (!res.ok) throw new Error(`Failed to fetch todos: ${res.status}`);
  return res.json();
}

async function updateTodo(todo: Todo): Promise<Todo> {
  const res = await fetch(`/api/todos/${todo.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(todo),
  });
  if (!res.ok) throw new Error(`Failed to update todo: ${res.status}`);
  return res.json();
}

export function useTodos() {
  return useQuery({
    queryKey: ['todos'],
    queryFn: fetchTodos,
  });
}

export function useToggleTodo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateTodo,
    // Optimistic update: toggle immediately in the cache
    onMutate: async (updatedTodo) => {
      await queryClient.cancelQueries({ queryKey: ['todos'] });

      const previousTodos = queryClient.getQueryData<Todo[]>(['todos']);

      queryClient.setQueryData<Todo[]>(['todos'], (old) =>
        old?.map((t) =>
          t.id === updatedTodo.id ? updatedTodo : t
        )
      );

      return { previousTodos };
    },
    // Rollback on error
    onError: (_err, _todo, context) => {
      if (context?.previousTodos) {
        queryClient.setQueryData(['todos'], context.previousTodos);
      }
    },
    // Refetch after success or error to ensure consistency
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['todos'] });
    },
  });
}
```

## SwiftUI: @Observable (iOS 17+) and Environment Injection

```swift
import SwiftUI
import Observation

// MARK: - @Observable macro (iOS 17+): simpler than ObservableObject

@Observable
final class UserProfile {
    var name: String = ""
    var email: String = ""
    var avatarURL: URL?
    var isPremium: Bool = false

    // Private properties that don't trigger view updates
    @ObservationIgnored
    private var analyticsId: String = ""
}

// MARK: - Environment-based dependency injection

@Observable
final class AppState {
    var isAuthenticated: Bool = false
    var currentUser: UserProfile?

    func signOut() {
        currentUser = nil
        isAuthenticated = false
    }
}

// Environment key for type-safe injection
struct AppStateKey: EnvironmentKey {
    static let defaultValue = AppState()
}

extension EnvironmentValues {
    var appState: AppState {
        get { self[AppStateKey.self] }
        set { self[AppStateKey.self] = newValue }
    }
}

// Inject at app root
@main
struct MyApp: App {
    @State private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(\.appState, appState)
        }
    }
}

// Consume in any child view
struct ProfileView: View {
    @Environment(\.appState) private var appState

    var body: some View {
        if let user = appState.currentUser {
            VStack {
                Text(user.name)
                Text(user.email)
                    .foregroundStyle(.secondary)
                Button("Sign Out") {
                    appState.signOut()
                }
            }
        }
    }
}

// MARK: - Actor-based state for concurrency safety

actor DataStore {
    private var cache: [String: Any] = [:]

    func get<T>(_ key: String) -> T? {
        cache[key] as? T
    }

    func set(_ key: String, value: Any) {
        cache[key] = value
    }

    func remove(_ key: String) {
        cache.removeValue(forKey: key)
    }

    func clear() {
        cache.removeAll()
    }
}

// Usage in a view model — actor isolation prevents data races
@Observable
@MainActor
final class CatalogViewModel {
    var products: [Product] = []
    var isLoading = false
    var error: String?

    private let store = DataStore()
    private let api: ProductAPI

    init(api: ProductAPI) {
        self.api = api
    }

    func loadProducts() async {
        // Check actor-isolated cache first
        if let cached: [Product] = await store.get("products") {
            self.products = cached
            return
        }

        isLoading = true
        defer { isLoading = false }

        do {
            let fetched = try await api.fetchProducts()
            self.products = fetched
            await store.set("products", value: fetched)
        } catch {
            self.error = error.localizedDescription
        }
    }
}
```

## Compose: ViewModel + StateFlow + SavedStateHandle

```kotlin
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

// --- UI State: single sealed hierarchy for screen state ---

data class ProductListState(
    val products: List<Product> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val searchQuery: String = "",
    val selectedCategory: String? = null
)

// --- ViewModel with SavedStateHandle for process death survival ---

@HiltViewModel
class ProductListViewModel @Inject constructor(
    private val repository: ProductRepository,
    private val savedStateHandle: SavedStateHandle
) : ViewModel() {

    // Survives process death via SavedStateHandle
    private val searchQuery = savedStateHandle.getStateFlow("search_query", "")
    private val selectedCategory = savedStateHandle.getStateFlow<String?>("category", null)

    // Combine multiple state sources into one UI state flow
    val uiState: StateFlow<ProductListState> = combine(
        repository.observeProducts(),
        searchQuery,
        selectedCategory
    ) { products, query, category ->
        val filtered = products
            .filter { product ->
                (query.isBlank() || product.name.contains(query, ignoreCase = true)) &&
                (category == null || product.category == category)
            }

        ProductListState(
            products = filtered,
            searchQuery = query,
            selectedCategory = category
        )
    }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000), // Keep alive 5s after last subscriber
            initialValue = ProductListState(isLoading = true)
        )

    fun updateSearchQuery(query: String) {
        savedStateHandle["search_query"] = query
    }

    fun selectCategory(category: String?) {
        savedStateHandle["category"] = category
    }

    fun refresh() {
        viewModelScope.launch {
            try {
                repository.refreshProducts()
            } catch (e: Exception) {
                // Error handled via repository's Flow emission
            }
        }
    }
}

// --- Hilt Module for dependency injection ---

import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    @Binds
    @Singleton
    abstract fun bindProductRepository(
        impl: ProductRepositoryImpl
    ): ProductRepository
}

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides
    @Singleton
    fun provideDatabase(app: android.app.Application): AppDatabase {
        return Room.databaseBuilder(app, AppDatabase::class.java, "app-db")
            .fallbackToDestructiveMigration()
            .build()
    }

    @Provides
    fun provideProductDao(db: AppDatabase): ProductDao = db.productDao()
}
```

## Navigation State: Deep Linking, Tab Preservation, Back Stack

```typescript
// React Native: typed navigation with deep linking

import { NavigationContainer, LinkingOptions } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

// Typed route params
type RootTabParams = {
  Home: undefined;
  Search: undefined;
  Profile: undefined;
};

type HomeStackParams = {
  Feed: undefined;
  ProductDetail: { productId: string };
  CategoryList: { categorySlug: string };
};

const Tab = createBottomTabNavigator<RootTabParams>();
const HomeStack = createNativeStackNavigator<HomeStackParams>();

// Deep linking configuration
const linking: LinkingOptions<RootTabParams> = {
  prefixes: ['myapp://', 'https://myapp.com'],
  config: {
    screens: {
      Home: {
        screens: {
          Feed: '',
          ProductDetail: 'product/:productId',
          CategoryList: 'category/:categorySlug',
        },
      },
      Search: 'search',
      Profile: 'profile',
    },
  },
};

function HomeStackNavigator() {
  return (
    <HomeStack.Navigator>
      <HomeStack.Screen name="Feed" component={FeedScreen} />
      <HomeStack.Screen name="ProductDetail" component={ProductDetailScreen} />
      <HomeStack.Screen name="CategoryList" component={CategoryListScreen} />
    </HomeStack.Navigator>
  );
}

export default function App() {
  return (
    <NavigationContainer linking={linking}>
      <Tab.Navigator
        screenOptions={{
          // Tab state is automatically preserved when switching tabs
          lazy: true, // Only mount tab screen on first visit
        }}
      >
        <Tab.Screen name="Home" component={HomeStackNavigator} />
        <Tab.Screen name="Search" component={SearchScreen} />
        <Tab.Screen name="Profile" component={ProfileScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
```

```swift
// SwiftUI: NavigationStack with typed paths and deep linking

import SwiftUI

// Typed navigation destinations
enum AppRoute: Hashable {
    case productDetail(id: String)
    case categoryList(slug: String)
    case settings
    case profile(userId: String)
}

struct ContentView: View {
    @State private var selectedTab = 0
    @State private var homePath = NavigationPath()
    @State private var searchPath = NavigationPath()

    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationStack(path: $homePath) {
                FeedView()
                    .navigationDestination(for: AppRoute.self) { route in
                        destinationView(for: route)
                    }
            }
            .tabItem { Label("Home", systemImage: "house") }
            .tag(0)

            NavigationStack(path: $searchPath) {
                SearchView()
                    .navigationDestination(for: AppRoute.self) { route in
                        destinationView(for: route)
                    }
            }
            .tabItem { Label("Search", systemImage: "magnifyingglass") }
            .tag(1)
        }
        .onOpenURL { url in
            handleDeepLink(url)
        }
    }

    @ViewBuilder
    private func destinationView(for route: AppRoute) -> some View {
        switch route {
        case .productDetail(let id):
            ProductDetailView(productId: id)
        case .categoryList(let slug):
            CategoryListView(categorySlug: slug)
        case .settings:
            SettingsView()
        case .profile(let userId):
            ProfileView(userId: userId)
        }
    }

    private func handleDeepLink(_ url: URL) {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: true) else { return }
        let pathParts = components.path.split(separator: "/")

        switch pathParts.first {
        case "product":
            if let id = pathParts.dropFirst().first {
                selectedTab = 0
                homePath.append(AppRoute.productDetail(id: String(id)))
            }
        case "category":
            if let slug = pathParts.dropFirst().first {
                selectedTab = 0
                homePath.append(AppRoute.categoryList(slug: String(slug)))
            }
        case "profile":
            if let userId = pathParts.dropFirst().first {
                selectedTab = 1
                searchPath.append(AppRoute.profile(userId: String(userId)))
            }
        default:
            break
        }
    }
}
```

## Authentication State Machine

```typescript
// Finite state machine for auth — no impossible states

type AuthState =
  | { status: 'logged_out' }
  | { status: 'loading' }
  | { status: 'authenticated'; user: User; token: string; expiresAt: number }
  | { status: 'expired'; user: User }  // Token expired, need refresh
  | { status: 'error'; message: string };

interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthStore {
  auth: AuthState;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  refreshToken: () => Promise<void>;
  checkSession: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      auth: { status: 'logged_out' } as AuthState,

      signIn: async (email, password) => {
        set({ auth: { status: 'loading' } });
        try {
          const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          });
          if (!response.ok) {
            const body = await response.json();
            set({ auth: { status: 'error', message: body.message ?? 'Login failed' } });
            return;
          }
          const { user, token, expiresAt } = await response.json();
          set({ auth: { status: 'authenticated', user, token, expiresAt } });
        } catch (error) {
          set({ auth: { status: 'error', message: 'Network error' } });
        }
      },

      signOut: () => {
        set({ auth: { status: 'logged_out' } });
      },

      refreshToken: async () => {
        const current = get().auth;
        if (current.status !== 'authenticated' && current.status !== 'expired') return;

        try {
          const response = await fetch('/api/auth/refresh', { method: 'POST' });
          if (!response.ok) {
            set({ auth: { status: 'logged_out' } });
            return;
          }
          const { token, expiresAt } = await response.json();
          const user = current.user;
          set({ auth: { status: 'authenticated', user, token, expiresAt } });
        } catch {
          set({ auth: { status: 'logged_out' } });
        }
      },

      checkSession: async () => {
        const current = get().auth;
        if (current.status !== 'authenticated') return;
        if (Date.now() > current.expiresAt) {
          set({ auth: { status: 'expired', user: current.user } });
          await get().refreshToken();
        }
      },
    }),
    {
      name: 'auth',
      storage: mmkvStorage,
      // Only persist token and user, not transient loading/error states
      partialize: (state) => {
        if (state.auth.status === 'authenticated') {
          return { auth: state.auth };
        }
        return { auth: { status: 'logged_out' as const } };
      },
    }
  )
);
```

## Form State with Validation

```typescript
import { useCallback, useMemo, useReducer } from 'react';

// --- Generic form state with field-level validation ---

interface FieldState<T> {
  value: T;
  error: string | null;
  touched: boolean;
  dirty: boolean;
}

interface FormState<T extends Record<string, unknown>> {
  fields: { [K in keyof T]: FieldState<T[K]> };
  isSubmitting: boolean;
  submitError: string | null;
  submitCount: number;
}

type Validators<T extends Record<string, unknown>> = {
  [K in keyof T]?: (value: T[K], allValues: T) => string | null;
};

type FormAction<T extends Record<string, unknown>> =
  | { type: 'SET_FIELD'; field: keyof T; value: T[keyof T] }
  | { type: 'SET_ERROR'; field: keyof T; error: string | null }
  | { type: 'TOUCH_FIELD'; field: keyof T }
  | { type: 'SUBMIT_START' }
  | { type: 'SUBMIT_SUCCESS' }
  | { type: 'SUBMIT_FAILURE'; error: string }
  | { type: 'RESET'; initialValues: T };

function createInitialFormState<T extends Record<string, unknown>>(
  initialValues: T
): FormState<T> {
  const fields = {} as FormState<T>['fields'];
  for (const key of Object.keys(initialValues) as Array<keyof T>) {
    fields[key] = {
      value: initialValues[key],
      error: null,
      touched: false,
      dirty: false,
    } as FieldState<T[typeof key]>;
  }
  return { fields, isSubmitting: false, submitError: null, submitCount: 0 };
}

function formReducer<T extends Record<string, unknown>>(
  state: FormState<T>,
  action: FormAction<T>
): FormState<T> {
  switch (action.type) {
    case 'SET_FIELD':
      return {
        ...state,
        fields: {
          ...state.fields,
          [action.field]: {
            ...state.fields[action.field],
            value: action.value,
            dirty: true,
          },
        },
      };
    case 'SET_ERROR':
      return {
        ...state,
        fields: {
          ...state.fields,
          [action.field]: {
            ...state.fields[action.field],
            error: action.error,
          },
        },
      };
    case 'TOUCH_FIELD':
      return {
        ...state,
        fields: {
          ...state.fields,
          [action.field]: {
            ...state.fields[action.field],
            touched: true,
          },
        },
      };
    case 'SUBMIT_START':
      return { ...state, isSubmitting: true, submitError: null };
    case 'SUBMIT_SUCCESS':
      return { ...state, isSubmitting: false, submitCount: state.submitCount + 1 };
    case 'SUBMIT_FAILURE':
      return { ...state, isSubmitting: false, submitError: action.error };
    case 'RESET':
      return createInitialFormState(action.initialValues);
    default:
      return state;
  }
}

export function useForm<T extends Record<string, unknown>>(
  initialValues: T,
  validators: Validators<T>,
  onSubmit: (values: T) => Promise<void>
) {
  const [state, dispatch] = useReducer(
    formReducer<T>,
    initialValues,
    createInitialFormState
  );

  const currentValues = useMemo(() => {
    const values = {} as T;
    for (const key of Object.keys(state.fields) as Array<keyof T>) {
      values[key] = state.fields[key].value;
    }
    return values;
  }, [state.fields]);

  const setField = useCallback(
    <K extends keyof T>(field: K, value: T[K]) => {
      dispatch({ type: 'SET_FIELD', field, value });
      const validator = validators[field];
      if (validator) {
        const error = validator(value, { ...currentValues, [field]: value });
        dispatch({ type: 'SET_ERROR', field, error });
      }
    },
    [validators, currentValues]
  );

  const touchField = useCallback(
    (field: keyof T) => dispatch({ type: 'TOUCH_FIELD', field }),
    []
  );

  const isValid = useMemo(
    () =>
      (Object.keys(state.fields) as Array<keyof T>).every(
        (key) => state.fields[key].error === null
      ),
    [state.fields]
  );

  const isDirty = useMemo(
    () =>
      (Object.keys(state.fields) as Array<keyof T>).some(
        (key) => state.fields[key].dirty
      ),
    [state.fields]
  );

  const handleSubmit = useCallback(async () => {
    // Touch all fields to show errors
    for (const key of Object.keys(state.fields) as Array<keyof T>) {
      dispatch({ type: 'TOUCH_FIELD', field: key });
      const validator = validators[key];
      if (validator) {
        const error = validator(state.fields[key].value, currentValues);
        dispatch({ type: 'SET_ERROR', field: key, error });
      }
    }

    // Recheck validity after touching all fields
    const hasErrors = (Object.keys(state.fields) as Array<keyof T>).some(
      (key) => validators[key]?.(state.fields[key].value, currentValues) !== null
    );
    if (hasErrors) return;

    dispatch({ type: 'SUBMIT_START' });
    try {
      await onSubmit(currentValues);
      dispatch({ type: 'SUBMIT_SUCCESS' });
    } catch (error) {
      dispatch({
        type: 'SUBMIT_FAILURE',
        error: error instanceof Error ? error.message : 'Submit failed',
      });
    }
  }, [state.fields, validators, currentValues, onSubmit]);

  const reset = useCallback(
    () => dispatch({ type: 'RESET', initialValues }),
    [initialValues]
  );

  return {
    fields: state.fields,
    isSubmitting: state.isSubmitting,
    submitError: state.submitError,
    submitCount: state.submitCount,
    isValid,
    isDirty,
    setField,
    touchField,
    handleSubmit,
    reset,
  };
}

// --- Usage example ---

interface SignUpForm {
  email: string;
  password: string;
  confirmPassword: string;
}

const signUpValidators: Validators<SignUpForm> = {
  email: (value) => {
    if (!value) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'Invalid email';
    return null;
  },
  password: (value) => {
    if (!value) return 'Password is required';
    if (value.length < 8) return 'Password must be at least 8 characters';
    if (!/[A-Z]/.test(value)) return 'Must contain an uppercase letter';
    if (!/[0-9]/.test(value)) return 'Must contain a number';
    return null;
  },
  confirmPassword: (value, allValues) => {
    if (!value) return 'Please confirm your password';
    if (value !== allValues.password) return 'Passwords do not match';
    return null;
  },
};

// In a component:
// const { fields, setField, touchField, handleSubmit, isValid, isSubmitting } = useForm(
//   { email: '', password: '', confirmPassword: '' },
//   signUpValidators,
//   async (values) => { await api.signUp(values); }
// );
```
