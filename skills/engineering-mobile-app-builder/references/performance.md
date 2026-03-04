# Mobile Performance Patterns

Production patterns for high-performance mobile apps. Covers React Native (Hermes, FlatList, memoization), SwiftUI (lazy stacks, image caching, background tasks), Compose (recomposition, Coil), battery optimization, memory leak prevention, and cold start optimization.

## React Native: Hermes Engine and FlatList Optimization

```typescript
// --- metro.config.js: Hermes + inline requires for fast startup ---
const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');

const config = {
  transformer: {
    getTransformOptions: async () => ({
      transform: {
        experimentalImportSupport: true,  // tree-shaking
        inlineRequires: true,             // defer module init to first use
        nonInlinedRequires: [
          'React',
          'react',
          'react-native',
        ],
      },
    }),
  },
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
```

```typescript
// --- Optimized FlatList with all performance levers ---
import React, { useCallback, useMemo, memo } from 'react';
import {
  FlatList,
  View,
  Text,
  StyleSheet,
  Platform,
  InteractionManager,
} from 'react-native';

interface Item {
  id: string;
  title: string;
  subtitle: string;
  height: number; // Pre-computed row height for getItemLayout
}

const ITEM_HEIGHT = 72;
const SEPARATOR_HEIGHT = 1;

// Memoized row component: only re-renders when its own props change
const ItemRow = memo<{ item: Item; onPress: (id: string) => void }>(
  ({ item, onPress }) => (
    <View style={styles.row}>
      <Text style={styles.title}>{item.title}</Text>
      <Text style={styles.subtitle}>{item.subtitle}</Text>
    </View>
  ),
  (prev, next) => prev.item.id === next.item.id
);

const ItemSeparator = () => <View style={styles.separator} />;

interface PerformantListProps {
  items: Item[];
  onItemPress: (id: string) => void;
  onEndReached: () => void;
}

export function PerformantList({ items, onItemPress, onEndReached }: PerformantListProps) {
  // getItemLayout: skip measurement, jump straight to render
  const getItemLayout = useCallback(
    (_data: unknown, index: number) => ({
      length: ITEM_HEIGHT,
      offset: (ITEM_HEIGHT + SEPARATOR_HEIGHT) * index,
      index,
    }),
    []
  );

  const renderItem = useCallback(
    ({ item }: { item: Item }) => <ItemRow item={item} onPress={onItemPress} />,
    [onItemPress]
  );

  const keyExtractor = useCallback((item: Item) => item.id, []);

  return (
    <FlatList
      data={items}
      renderItem={renderItem}
      keyExtractor={keyExtractor}
      getItemLayout={getItemLayout}
      ItemSeparatorComponent={ItemSeparator}
      onEndReached={onEndReached}
      onEndReachedThreshold={0.3}
      // --- Performance flags ---
      removeClippedSubviews={Platform.OS === 'android'} // reclaim memory offscreen
      maxToRenderPerBatch={10}          // render 10 items per JS frame
      updateCellsBatchingPeriod={50}    // batch updates every 50ms
      windowSize={11}                   // render 5 screens above + 5 below + visible
      initialNumToRender={15}           // first paint items
      maintainVisibleContentPosition={{  // prevent jump on prepend
        minIndexForVisible: 0,
      }}
    />
  );
}

// --- InteractionManager: defer heavy work until animations finish ---

export function deferHeavyWork(work: () => void): void {
  InteractionManager.runAfterInteractions(() => {
    requestAnimationFrame(() => {
      work();
    });
  });
}

// Usage: after navigating to a screen, defer data processing
// deferHeavyWork(() => processLargeDataset(rawData));

const styles = StyleSheet.create({
  row: {
    height: ITEM_HEIGHT,
    paddingHorizontal: 16,
    justifyContent: 'center',
  },
  title: { fontSize: 16, fontWeight: '600' },
  subtitle: { fontSize: 14, color: '#666', marginTop: 2 },
  separator: { height: SEPARATOR_HEIGHT, backgroundColor: '#E5E5E5' },
});
```

## SwiftUI: Lazy Stacks, Image Caching, and Background Tasks

```swift
import SwiftUI

// MARK: - LazyVStack with efficient data loading

struct EfficientListView: View {
    @StateObject private var viewModel = ListViewModel()

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                ForEach(viewModel.items) { item in
                    ItemRowView(item: item)
                        .onAppear {
                            viewModel.loadMoreIfNeeded(currentItem: item)
                        }
                }

                if viewModel.isLoadingMore {
                    ProgressView()
                        .padding()
                }
            }
        }
        .task {
            await viewModel.loadInitial()
        }
    }
}

// MARK: - @StateObject vs @ObservedObject lifecycle

// @StateObject: owns the object, creates it once, survives view re-creation
// Use for: view models created by this view
struct ParentView: View {
    @StateObject private var viewModel = ExpensiveViewModel() // Created once

    var body: some View {
        ChildView(viewModel: viewModel)
    }
}

// @ObservedObject: borrows the object, does NOT own it, may be recreated
// Use for: view models passed from a parent
struct ChildView: View {
    @ObservedObject var viewModel: ExpensiveViewModel // Passed in, not owned

    var body: some View {
        Text(viewModel.title)
    }
}

// MARK: - Image caching with AsyncImage + URLCache

struct CachedAsyncImage: View {
    let url: URL?
    let width: CGFloat
    let height: CGFloat

    // Configure a shared URLCache with generous limits
    private static let imageCache: URLCache = {
        let cache = URLCache(
            memoryCapacity: 50 * 1024 * 1024,  // 50MB memory
            diskCapacity: 200 * 1024 * 1024,    // 200MB disk
            directory: FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)
                .first?.appendingPathComponent("ImageCache")
        )
        return cache
    }()

    private static let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.urlCache = CachedAsyncImage.imageCache
        config.requestCachePolicy = .returnCacheDataElseLoad
        return URLSession(configuration: config)
    }()

    var body: some View {
        AsyncImage(url: url) { phase in
            switch phase {
            case .empty:
                ProgressView()
                    .frame(width: width, height: height)
            case .success(let image):
                image
                    .resizable()
                    .aspectRatio(contentMode: .fill)
                    .frame(width: width, height: height)
                    .clipped()
            case .failure:
                Image(systemName: "photo")
                    .frame(width: width, height: height)
                    .foregroundStyle(.secondary)
            @unknown default:
                EmptyView()
            }
        }
    }
}

// MARK: - Background task scheduling (iOS 13+)

import BackgroundTasks

final class BackgroundTaskScheduler {
    static let shared = BackgroundTaskScheduler()

    static let refreshTaskId = "com.app.refresh"
    static let processingTaskId = "com.app.processing"

    func registerTasks() {
        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: Self.refreshTaskId,
            using: nil
        ) { task in
            self.handleRefresh(task: task as! BGAppRefreshTask)
        }

        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: Self.processingTaskId,
            using: nil
        ) { task in
            self.handleProcessing(task: task as! BGProcessingTask)
        }
    }

    func scheduleRefresh() {
        let request = BGAppRefreshTaskRequest(identifier: Self.refreshTaskId)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 15 * 60) // 15 min
        try? BGTaskScheduler.shared.submit(request)
    }

    func scheduleProcessing() {
        let request = BGProcessingTaskRequest(identifier: Self.processingTaskId)
        request.requiresNetworkConnectivity = true
        request.requiresExternalPower = false
        request.earliestBeginDate = Date(timeIntervalSinceNow: 60 * 60) // 1 hour
        try? BGTaskScheduler.shared.submit(request)
    }

    private func handleRefresh(task: BGAppRefreshTask) {
        scheduleRefresh() // Re-schedule for next time

        let operation = Task {
            // Lightweight data refresh
            try await DataSyncService.shared.pullLatestChanges()
        }

        task.expirationHandler = { operation.cancel() }

        Task {
            do {
                try await operation.value
                task.setTaskCompleted(success: true)
            } catch {
                task.setTaskCompleted(success: false)
            }
        }
    }

    private func handleProcessing(task: BGProcessingTask) {
        let operation = Task {
            // Heavy work: image compression, log upload, cache cleanup
            try await MaintenanceService.shared.performCleanup()
        }

        task.expirationHandler = { operation.cancel() }

        Task {
            do {
                try await operation.value
                task.setTaskCompleted(success: true)
            } catch {
                task.setTaskCompleted(success: false)
            }
        }
    }
}
```

## Compose: LazyColumn, Recomposition Control, and Coil Image Loading

```kotlin
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import coil.compose.AsyncImage
import coil.request.ImageRequest

// --- LazyColumn with key-based recomposition and scroll-aware loading ---

@Composable
fun PerformantList(
    items: List<ItemUiModel>,
    onLoadMore: () -> Unit,
    modifier: Modifier = Modifier
) {
    val listState = rememberLazyListState()

    // derivedStateOf: only recompute when the derived value actually changes
    val shouldLoadMore by remember {
        derivedStateOf {
            val lastVisibleIndex = listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0
            lastVisibleIndex >= items.size - 5 // Load more when 5 items from end
        }
    }

    LaunchedEffect(shouldLoadMore) {
        if (shouldLoadMore) onLoadMore()
    }

    LazyColumn(
        state = listState,
        modifier = modifier
    ) {
        items(
            items = items,
            key = { it.id } // Stable keys prevent unnecessary recomposition
        ) { item ->
            // Each item only recomposes when its own data changes
            ItemRow(item = item)
        }
    }
}

// --- remember vs rememberSaveable ---

@Composable
fun SearchScreen() {
    // remember: survives recomposition, lost on configuration change
    var expandedFilter by remember { mutableStateOf(false) }

    // rememberSaveable: survives config change + process death (via Bundle)
    var searchQuery by rememberSaveable { mutableStateOf("") }

    // For complex objects, provide a custom Saver
    var filters by rememberSaveable(stateSaver = FiltersSaver) {
        mutableStateOf(SearchFilters())
    }
}

// --- Coil image loading with memory + disk caching ---

@Composable
fun CachedNetworkImage(
    url: String?,
    contentDescription: String?,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current

    AsyncImage(
        model = ImageRequest.Builder(context)
            .data(url)
            .crossfade(300)
            .memoryCacheKey(url)     // Explicit memory cache key
            .diskCacheKey(url)       // Explicit disk cache key
            .size(coil.size.Size.ORIGINAL) // Or specify exact pixel size
            .build(),
        contentDescription = contentDescription,
        modifier = modifier
    )
}

// --- Coil ImageLoader singleton with tuned caches ---

import coil.ImageLoader
import coil.disk.DiskCache
import coil.memory.MemoryCache

fun createImageLoader(context: android.content.Context): ImageLoader {
    return ImageLoader.Builder(context)
        .memoryCache {
            MemoryCache.Builder(context)
                .maxSizePercent(0.25) // 25% of app memory
                .build()
        }
        .diskCache {
            DiskCache.Builder()
                .directory(context.cacheDir.resolve("image_cache"))
                .maxSizeBytes(250L * 1024 * 1024) // 250MB
                .build()
        }
        .respectCacheHeaders(true)
        .build()
}
```

## Battery Optimization Patterns

```kotlin
// --- Batch network requests with a debounced dispatcher ---

import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

class BatchedNetworkDispatcher(
    private val batchWindow: Long = 2000L, // Collect requests for 2s then fire one batch
    private val scope: CoroutineScope
) {
    private val _requests = MutableSharedFlow<NetworkRequest>()

    init {
        _requests
            .buffer(64)
            .chunked(batchWindow)
            .onEach { batch -> executeBatch(batch) }
            .launchIn(scope)
    }

    fun enqueue(request: NetworkRequest) {
        scope.launch { _requests.emit(request) }
    }

    private suspend fun executeBatch(requests: List<NetworkRequest>) {
        if (requests.isEmpty()) return
        // Combine into a single batch API call
        val batchPayload = requests.map { it.toPayload() }
        apiClient.postBatch(batchPayload)
    }
}

// Collect Flow emissions into time-windowed chunks
fun <T> Flow<T>.chunked(windowMs: Long): Flow<List<T>> = flow {
    val buffer = mutableListOf<T>()
    var job: Job? = null
    collect { value ->
        buffer.add(value)
        job?.cancel()
        job = CoroutineScope(currentCoroutineContext()).launch {
            delay(windowMs)
            if (buffer.isNotEmpty()) {
                emit(buffer.toList())
                buffer.clear()
            }
        }
    }
    if (buffer.isNotEmpty()) emit(buffer.toList())
}
```

```swift
// --- Reduce GPS polling: significant location changes instead of continuous ---

import CoreLocation

final class BatteryEfficientLocationManager: NSObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    var onLocation: ((CLLocation) -> Void)?

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters // Save battery
        manager.allowsBackgroundLocationUpdates = false
        manager.pausesLocationUpdatesAutomatically = true
    }

    /// Use significant location changes: wakes app only on ~500m movement
    func startMonitoring() {
        manager.startMonitoringSignificantLocationChanges()
    }

    /// Only for active navigation — switch back when done
    func startPreciseTracking() {
        manager.desiredAccuracy = kCLLocationAccuracyBest
        manager.distanceFilter = 10 // meters
        manager.startUpdatingLocation()
    }

    func stopPreciseTracking() {
        manager.stopUpdatingLocation()
        startMonitoring() // Fall back to significant changes
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        onLocation?(location)
    }
}
```

## Memory Leak Prevention

```swift
// MARK: - Swift: common leak patterns and fixes

// LEAK: closure captures self strongly in a long-lived observer
class LeakyViewModel: ObservableObject {
    private var cancellable: AnyCancellable?

    func startObserving() {
        // BAD: self is captured strongly — ViewModel never deallocates
        // cancellable = NotificationCenter.default.publisher(for: .someNotification)
        //     .sink { _ in self.handleNotification() }

        // GOOD: use [weak self]
        cancellable = NotificationCenter.default.publisher(for: UIApplication.didBecomeActiveNotification)
            .sink { [weak self] _ in
                self?.handleNotification()
            }
    }

    private func handleNotification() { /* ... */ }

    deinit {
        cancellable?.cancel() // Always cancel subscriptions
    }
}

// LEAK: retain cycle with delegate
protocol ServiceDelegate: AnyObject { // Must be AnyObject for weak ref
    func serviceDidUpdate()
}

class Service {
    weak var delegate: ServiceDelegate? // MUST be weak
}
```

```kotlin
// MARK: - Kotlin: common leak patterns and fixes

// LEAK: ViewModel holds Activity reference
// BAD: class MyViewModel(private val activity: Activity) : ViewModel()
// GOOD: use Application context for anything that outlives an Activity

class SafeViewModel(application: android.app.Application) : AndroidViewModel(application) {
    // getApplication() returns Application context — safe to hold long-term
    private val prefs = getApplication<android.app.Application>()
        .getSharedPreferences("prefs", android.content.Context.MODE_PRIVATE)
}

// LEAK: coroutine outlives lifecycle scope
// BAD: GlobalScope.launch { /* work referencing Activity */ }

// GOOD: use viewModelScope / lifecycleScope — auto-cancelled
class LifecycleAwareViewModel : ViewModel() {
    fun loadData() {
        viewModelScope.launch { // Cancelled when ViewModel is cleared
            val data = repository.fetchData()
            _uiState.value = data
        }
    }
}

// LEAK: anonymous inner class / lambda capturing Activity
// GOOD: use weak reference for callbacks that outlive the component
class SafeCallback(activity: android.app.Activity) {
    private val activityRef = java.lang.ref.WeakReference(activity)

    fun onComplete(result: String) {
        activityRef.get()?.let { activity ->
            activity.runOnUiThread { /* update UI */ }
        }
    }
}
```

```typescript
// React Native: common leak patterns and fixes

import { useEffect, useRef } from 'react';

// LEAK: uncleared timer / subscription in useEffect
function LeakyComponent() {
  useEffect(() => {
    const timer = setInterval(() => {
      // This keeps running after unmount
    }, 1000);

    const subscription = eventEmitter.addListener('event', handler);

    // GOOD: always return cleanup
    return () => {
      clearInterval(timer);
      subscription.remove();
    };
  }, []);
}

// LEAK: async operation updating state after unmount
function SafeAsyncComponent() {
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;

    async function loadData() {
      const data = await fetchData();
      // Only update state if still mounted
      if (isMounted.current) {
        setData(data);
      }
    }

    loadData();

    return () => {
      isMounted.current = false;
    };
  }, []);
}

// BETTER: use AbortController for fetch cancellation
function AbortableComponent() {
  useEffect(() => {
    const controller = new AbortController();

    async function loadData() {
      try {
        const response = await fetch('/api/data', {
          signal: controller.signal,
        });
        const data = await response.json();
        setData(data);
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          setError(error);
        }
      }
    }

    loadData();
    return () => controller.abort();
  }, []);
}
```

## App Startup Optimization (Cold Start < 1s)

```swift
// MARK: - Swift: minimal AppDelegate for fast launch

import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        // ONLY essential initialization here:
        // 1. Crash reporting (< 50ms)
        // 2. Auth token check (from Keychain, no network)
        // 3. Core Data stack (lazy-loaded anyway)

        // DEFER everything else to after first frame:
        DispatchQueue.main.async {
            self.performDeferredSetup()
        }

        return true
    }

    private func performDeferredSetup() {
        // Analytics, feature flags, remote config, push registration
        // These can all wait 100-200ms after first paint
        Analytics.shared.initialize()
        FeatureFlags.shared.refresh()
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { _, _ in }
    }
}
```

```kotlin
// MARK: - Kotlin: optimized Application class

import android.app.Application
import androidx.startup.AppInitializer

class MyApplication : Application() {
    override fun onCreate() {
        super.onCreate()

        // ONLY critical-path initialization:
        // Use AndroidX Startup for lazy, dependency-ordered init
        // Non-critical initializers run on first access, not app start
    }
}

// --- AndroidX App Startup: lazy initializer pattern ---

import android.content.Context
import androidx.startup.Initializer

// Critical: runs at startup
class CrashReportingInitializer : Initializer<Unit> {
    override fun create(context: Context) {
        CrashReporter.init(context)
    }
    override fun dependencies(): List<Class<out Initializer<*>>> = emptyList()
}

// Deferred: runs only when AnalyticsService is first accessed
class AnalyticsInitializer : Initializer<AnalyticsService> {
    override fun create(context: Context): AnalyticsService {
        return AnalyticsService(context).also { it.initialize() }
    }
    override fun dependencies(): List<Class<out Initializer<*>>> =
        listOf(CrashReportingInitializer::class.java)
}
```

```typescript
// React Native: fast startup with lazy screens and inline requires

// app.json / app.config.ts — ensure Hermes is enabled
// { "expo": { "jsEngine": "hermes" } }
// or in react-native.config.js: hermes_enabled: true

// --- Lazy-load screens: only bundle the initial screen at startup ---
import { lazy, Suspense } from 'react';
import { ActivityIndicator, View } from 'react-native';

const HomeScreen = lazy(() => import('./screens/HomeScreen'));
const ProfileScreen = lazy(() => import('./screens/ProfileScreen'));
const SettingsScreen = lazy(() => import('./screens/SettingsScreen'));

function LazyScreen({ component: Component }: { component: React.LazyExoticComponent<any> }) {
  return (
    <Suspense
      fallback={
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" />
        </View>
      }
    >
      <Component />
    </Suspense>
  );
}

// --- Measure cold start time ---
const APP_START_TIME = global.performance?.now?.() ?? Date.now();

export function measureStartupTime(): number {
  return (global.performance?.now?.() ?? Date.now()) - APP_START_TIME;
}

// Call in your root component's useEffect:
// useEffect(() => {
//   const startupMs = measureStartupTime();
//   analytics.track('cold_start', { duration_ms: startupMs });
// }, []);
```
