# Offline-First Architecture Patterns

Production patterns for offline-first mobile apps across React Native, Swift, and Kotlin. Covers local-first data, background sync, conflict resolution, optimistic UI, and queue-based mutations.

## React Native: NetInfo + Async Storage Queue

```typescript
import NetInfo, { NetInfoState } from '@react-native-community/netinfo';
import AsyncStorage from '@react-native-async-storage/async-storage';

// --- Mutation queue: enqueue offline, flush when online ---

interface QueuedMutation {
  id: string;
  endpoint: string;
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body: Record<string, unknown>;
  createdAt: number;
  retryCount: number;
}

const QUEUE_KEY = '@mutation_queue';
const MAX_RETRIES = 5;

async function getQueue(): Promise<QueuedMutation[]> {
  const raw = await AsyncStorage.getItem(QUEUE_KEY);
  return raw ? JSON.parse(raw) : [];
}

async function persistQueue(queue: QueuedMutation[]): Promise<void> {
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

export async function enqueueMutation(
  mutation: Omit<QueuedMutation, 'id' | 'createdAt' | 'retryCount'>
): Promise<string> {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
  const entry: QueuedMutation = {
    ...mutation,
    id,
    createdAt: Date.now(),
    retryCount: 0,
  };
  const queue = await getQueue();
  queue.push(entry);
  await persistQueue(queue);
  return id;
}

async function executeMutation(mutation: QueuedMutation): Promise<boolean> {
  try {
    const response = await fetch(mutation.endpoint, {
      method: mutation.method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mutation.body),
    });
    if (response.status === 409) {
      // Conflict — server rejected; apply conflict resolution
      await handleConflict(mutation, await response.json());
      return true; // Remove from queue after handling
    }
    return response.ok;
  } catch {
    return false;
  }
}

export async function flushQueue(): Promise<{ succeeded: number; failed: number }> {
  const queue = await getQueue();
  const remaining: QueuedMutation[] = [];
  let succeeded = 0;
  let failed = 0;

  for (const mutation of queue) {
    const ok = await executeMutation(mutation);
    if (ok) {
      succeeded++;
    } else if (mutation.retryCount < MAX_RETRIES) {
      remaining.push({ ...mutation, retryCount: mutation.retryCount + 1 });
      failed++;
    } else {
      // Dead letter — log and discard
      console.error('[OfflineQueue] Dropping mutation after max retries:', mutation.id);
      failed++;
    }
  }

  await persistQueue(remaining);
  return { succeeded, failed };
}

// --- Network listener: auto-flush on reconnect ---

let unsubscribe: (() => void) | null = null;

export function startNetworkSync(): void {
  unsubscribe = NetInfo.addEventListener((state: NetInfoState) => {
    if (state.isConnected && state.isInternetReachable) {
      flushQueue().then(({ succeeded, failed }) => {
        if (succeeded > 0 || failed > 0) {
          console.log(`[OfflineQueue] Flushed: ${succeeded} ok, ${failed} failed`);
        }
      });
    }
  });
}

export function stopNetworkSync(): void {
  unsubscribe?.();
  unsubscribe = null;
}
```

## Swift: Core Data + CloudKit Sync with Conflict Resolution

```swift
import CoreData
import CloudKit
import Network

// MARK: - Core Data Stack with CloudKit

final class PersistenceController {
    static let shared = PersistenceController()

    let container: NSPersistentCloudKitContainer

    private init() {
        container = NSPersistentCloudKitContainer(name: "AppModel")

        guard let description = container.persistentStoreDescriptions.first else {
            fatalError("No persistent store description found")
        }

        // Enable CloudKit sync
        description.cloudKitContainerOptions = NSPersistentCloudKitContainerOptions(
            containerIdentifier: "iCloud.com.app.identifier"
        )

        // Enable remote change notifications
        description.setOption(true as NSNumber,
                              forKey: NSPersistentStoreRemoteChangeNotificationPostOptionKey)

        // Enable history tracking for sync
        description.setOption(true as NSNumber,
                              forKey: NSPersistentHistoryTrackingKey)

        container.loadPersistentStores { _, error in
            if let error { fatalError("Core Data load failed: \(error)") }
        }

        container.viewContext.automaticallyMergesChangesFromParent = true
        container.viewContext.mergePolicy = NSMergeByPropertyObjectTrumpMergePolicy

        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleRemoteChange),
            name: .NSPersistentStoreRemoteChange,
            object: container.persistentStoreCoordinator
        )
    }

    @objc private func handleRemoteChange(_ notification: Notification) {
        // Process remote changes on background context
        let context = container.newBackgroundContext()
        context.perform {
            self.processRemoteChanges(in: context)
        }
    }

    private func processRemoteChanges(in context: NSManagedObjectContext) {
        let request = NSPersistentHistoryChangeRequest.fetchHistory(after: lastHistoryToken)
        guard let result = try? context.execute(request) as? NSPersistentHistoryResult,
              let transactions = result.result as? [NSPersistentHistoryTransaction] else {
            return
        }

        for transaction in transactions {
            guard let changes = transaction.changes else { continue }
            for change in changes {
                resolveConflictIfNeeded(change: change, in: context)
            }
        }

        if let lastToken = transactions.last?.token {
            lastHistoryToken = lastToken
        }

        try? context.save()
    }

    // MARK: - Conflict Resolution

    private func resolveConflictIfNeeded(
        change: NSPersistentHistoryChange,
        in context: NSManagedObjectContext
    ) {
        guard change.changeType == .update,
              let objectID = change.changedObjectID,
              let object = try? context.existingObject(with: objectID) as? SyncableEntity else {
            return
        }

        // Last-write-wins using updatedAt timestamp
        if let remoteUpdatedAt = object.remoteUpdatedAt,
           let localUpdatedAt = object.localUpdatedAt,
           localUpdatedAt > remoteUpdatedAt {
            // Local wins — re-mark as needing sync
            object.needsSync = true
        }
        // Otherwise remote wins — already merged by Core Data merge policy
    }

    private var lastHistoryToken: NSPersistentHistoryToken? {
        get {
            guard let data = UserDefaults.standard.data(forKey: "lastHistoryToken") else { return nil }
            return try? NSKeyedUnarchiver.unarchivedObject(
                ofClass: NSPersistentHistoryToken.self, from: data
            )
        }
        set {
            guard let newValue,
                  let data = try? NSKeyedArchiver.archivedData(
                    withRootObject: newValue, requiringSecureCoding: true
                  ) else { return }
            UserDefaults.standard.set(data, forKey: "lastHistoryToken")
        }
    }
}

// MARK: - Syncable Protocol

@objc protocol SyncableEntity: NSFetchRequestResult {
    var needsSync: Bool { get set }
    var localUpdatedAt: Date? { get set }
    var remoteUpdatedAt: Date? { get set }
}

// MARK: - Background Sync Coordinator

final class SyncCoordinator {
    private let monitor = NWPathMonitor()
    private let syncQueue = DispatchQueue(label: "com.app.sync")
    private let context: NSManagedObjectContext

    init(container: NSPersistentCloudKitContainer) {
        self.context = container.newBackgroundContext()
        context.mergePolicy = NSMergeByPropertyObjectTrumpMergePolicy
    }

    func startMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            if path.status == .satisfied {
                self?.syncPendingChanges()
            }
        }
        monitor.start(queue: syncQueue)
    }

    func syncPendingChanges() {
        context.perform { [weak self] in
            guard let self else { return }
            let request = NSFetchRequest<NSManagedObject>(entityName: "Item")
            request.predicate = NSPredicate(format: "needsSync == YES")
            request.fetchBatchSize = 50

            guard let pendingItems = try? self.context.fetch(request) else { return }

            for item in pendingItems {
                // Push to server, mark synced on success
                item.setValue(false, forKey: "needsSync")
            }

            try? self.context.save()
        }
    }
}
```

## Kotlin: Room + WorkManager Background Sync

```kotlin
import android.content.Context
import androidx.room.*
import androidx.work.*
import kotlinx.coroutines.flow.Flow
import java.util.concurrent.TimeUnit

// --- Room entities with sync metadata ---

@Entity(tableName = "items")
data class ItemEntity(
    @PrimaryKey val id: String,
    val title: String,
    val content: String,
    val updatedAt: Long = System.currentTimeMillis(),
    val needsSync: Boolean = false,
    val syncVersion: Int = 0
)

@Entity(tableName = "mutation_queue")
data class PendingMutation(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val entityId: String,
    val entityType: String,
    val action: String, // "create", "update", "delete"
    val payload: String, // JSON serialized body
    val createdAt: Long = System.currentTimeMillis(),
    val retryCount: Int = 0
)

// --- DAO ---

@Dao
interface ItemDao {
    @Query("SELECT * FROM items ORDER BY updatedAt DESC")
    fun observeAll(): Flow<List<ItemEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(item: ItemEntity)

    @Query("SELECT * FROM items WHERE needsSync = 1")
    suspend fun getPendingSync(): List<ItemEntity>

    @Query("UPDATE items SET needsSync = 0 WHERE id = :id")
    suspend fun markSynced(id: String)
}

@Dao
interface MutationQueueDao {
    @Insert
    suspend fun enqueue(mutation: PendingMutation)

    @Query("SELECT * FROM mutation_queue ORDER BY createdAt ASC")
    suspend fun getAll(): List<PendingMutation>

    @Delete
    suspend fun remove(mutation: PendingMutation)

    @Query("UPDATE mutation_queue SET retryCount = retryCount + 1 WHERE id = :id")
    suspend fun incrementRetry(id: Long)

    @Query("DELETE FROM mutation_queue WHERE retryCount > :maxRetries")
    suspend fun removeDeadLetters(maxRetries: Int = 5)
}

// --- Database ---

@Database(entities = [ItemEntity::class, PendingMutation::class], version = 1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun itemDao(): ItemDao
    abstract fun mutationQueueDao(): MutationQueueDao
}

// --- Repository: offline-first reads, queued writes ---

class ItemRepository(
    private val db: AppDatabase,
    private val api: ApiService
) {
    fun observeItems(): Flow<List<ItemEntity>> = db.itemDao().observeAll()

    suspend fun createItem(title: String, content: String) {
        val id = java.util.UUID.randomUUID().toString()
        val item = ItemEntity(
            id = id,
            title = title,
            content = content,
            needsSync = true
        )
        db.itemDao().upsert(item)
        db.mutationQueueDao().enqueue(
            PendingMutation(
                entityId = id,
                entityType = "item",
                action = "create",
                payload = """{"id":"$id","title":"$title","content":"$content"}"""
            )
        )
    }

    suspend fun syncPendingMutations(): SyncResult {
        val mutations = db.mutationQueueDao().getAll()
        var succeeded = 0
        var failed = 0

        for (mutation in mutations) {
            try {
                val response = when (mutation.action) {
                    "create" -> api.createItem(mutation.payload)
                    "update" -> api.updateItem(mutation.entityId, mutation.payload)
                    "delete" -> api.deleteItem(mutation.entityId)
                    else -> throw IllegalArgumentException("Unknown action: ${mutation.action}")
                }
                if (response.isSuccessful) {
                    db.mutationQueueDao().remove(mutation)
                    db.itemDao().markSynced(mutation.entityId)
                    succeeded++
                } else if (response.code() == 409) {
                    resolveConflict(mutation, response.errorBody()?.string())
                    db.mutationQueueDao().remove(mutation)
                    succeeded++
                } else {
                    db.mutationQueueDao().incrementRetry(mutation.id)
                    failed++
                }
            } catch (e: Exception) {
                db.mutationQueueDao().incrementRetry(mutation.id)
                failed++
            }
        }

        db.mutationQueueDao().removeDeadLetters()
        return SyncResult(succeeded, failed)
    }

    private suspend fun resolveConflict(mutation: PendingMutation, serverBody: String?) {
        // Last-write-wins: fetch server version, compare timestamps, keep newer
        val serverItem = api.getItem(mutation.entityId).body() ?: return
        val localItem = db.itemDao().getPendingSync()
            .firstOrNull { it.id == mutation.entityId } ?: return

        if (localItem.updatedAt > serverItem.updatedAt) {
            // Local wins — re-push
            api.updateItem(mutation.entityId, mutation.payload)
        } else {
            // Server wins — overwrite local
            db.itemDao().upsert(
                ItemEntity(
                    id = serverItem.id,
                    title = serverItem.title,
                    content = serverItem.content,
                    updatedAt = serverItem.updatedAt,
                    needsSync = false
                )
            )
        }
    }
}

data class SyncResult(val succeeded: Int, val failed: Int)

// --- WorkManager: periodic background sync ---

class SyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val db = Room.databaseBuilder(
            applicationContext, AppDatabase::class.java, "app-db"
        ).build()
        val api = ApiService.create()
        val repository = ItemRepository(db, api)

        return try {
            val result = repository.syncPendingMutations()
            if (result.failed > 0 && runAttemptCount < 3) Result.retry()
            else Result.success()
        } catch (e: Exception) {
            if (runAttemptCount < 3) Result.retry() else Result.failure()
        }
    }
}

// Schedule sync: call once at app startup
fun scheduleSyncWork(context: Context) {
    val constraints = Constraints.Builder()
        .setRequiredNetworkType(NetworkType.CONNECTED)
        .build()

    val periodicSync = PeriodicWorkRequestBuilder<SyncWorker>(
        repeatInterval = 15, repeatIntervalTimeUnit = TimeUnit.MINUTES
    )
        .setConstraints(constraints)
        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
        .build()

    WorkManager.getInstance(context).enqueueUniquePeriodicWork(
        "periodic_sync",
        ExistingPeriodicWorkPolicy.KEEP,
        periodicSync
    )
}

// One-shot sync when network becomes available
fun requestImmediateSync(context: Context) {
    val constraints = Constraints.Builder()
        .setRequiredNetworkType(NetworkType.CONNECTED)
        .build()

    val syncRequest = OneTimeWorkRequestBuilder<SyncWorker>()
        .setConstraints(constraints)
        .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
        .build()

    WorkManager.getInstance(context).enqueueUniqueWork(
        "immediate_sync",
        ExistingWorkPolicy.REPLACE,
        syncRequest
    )
}
```

## Conflict Resolution Strategies

### Last-Write-Wins (LWW)

Simplest strategy. Every record carries a `updatedAt` timestamp; the most recent write wins.

```typescript
// Generic LWW resolver — works on any entity with updatedAt
function resolveLastWriteWins<T extends { updatedAt: number }>(
  local: T,
  remote: T
): { winner: T; source: 'local' | 'remote' } {
  if (local.updatedAt >= remote.updatedAt) {
    return { winner: local, source: 'local' };
  }
  return { winner: remote, source: 'remote' };
}
```

### Field-Level Merge

Merge non-conflicting field changes; flag true conflicts for manual resolution.

```typescript
interface MergeResult<T> {
  merged: T;
  conflicts: Array<{ field: keyof T; local: unknown; remote: unknown }>;
}

function fieldLevelMerge<T extends Record<string, unknown>>(
  base: T,    // Last synced version both sides agree on
  local: T,   // Current local version
  remote: T   // Current server version
): MergeResult<T> {
  const merged = { ...base } as T;
  const conflicts: MergeResult<T>['conflicts'] = [];

  for (const key of Object.keys(base) as Array<keyof T>) {
    const localChanged = local[key] !== base[key];
    const remoteChanged = remote[key] !== base[key];

    if (localChanged && remoteChanged && local[key] !== remote[key]) {
      // True conflict — both sides changed the same field differently
      conflicts.push({ field: key, local: local[key], remote: remote[key] });
      merged[key] = remote[key]; // Default to remote; UI can override
    } else if (localChanged) {
      merged[key] = local[key];
    } else if (remoteChanged) {
      merged[key] = remote[key];
    }
  }

  return { merged, conflicts };
}
```

### CRDT-Like Counter / Set Merge

For counters (likes, inventory) and sets (tags, collaborators) that must converge without coordination.

```typescript
// G-Counter: grow-only counter that merges by taking max per node
interface GCounter {
  counts: Record<string, number>; // nodeId -> count
}

function incrementGCounter(counter: GCounter, nodeId: string): GCounter {
  return {
    counts: {
      ...counter.counts,
      [nodeId]: (counter.counts[nodeId] ?? 0) + 1,
    },
  };
}

function mergeGCounters(a: GCounter, b: GCounter): GCounter {
  const allNodes = new Set([...Object.keys(a.counts), ...Object.keys(b.counts)]);
  const merged: Record<string, number> = {};
  for (const node of allNodes) {
    merged[node] = Math.max(a.counts[node] ?? 0, b.counts[node] ?? 0);
  }
  return { counts: merged };
}

function gCounterValue(counter: GCounter): number {
  return Object.values(counter.counts).reduce((sum, v) => sum + v, 0);
}

// OR-Set (Observed-Remove Set): add/remove converge correctly
interface ORSet<T> {
  elements: Map<string, { value: T; tag: string }>; // tag -> element
  tombstones: Set<string>; // removed tags
}

function addToORSet<T>(set: ORSet<T>, value: T): ORSet<T> {
  const tag = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
  const elements = new Map(set.elements);
  elements.set(tag, { value, tag });
  return { elements, tombstones: set.tombstones };
}

function removeFromORSet<T>(set: ORSet<T>, value: T): ORSet<T> {
  const tombstones = new Set(set.tombstones);
  const elements = new Map(set.elements);
  for (const [tag, entry] of elements) {
    if (entry.value === value) {
      tombstones.add(tag);
      elements.delete(tag);
    }
  }
  return { elements, tombstones };
}

function mergeORSets<T>(a: ORSet<T>, b: ORSet<T>): ORSet<T> {
  const tombstones = new Set([...a.tombstones, ...b.tombstones]);
  const elements = new Map<string, { value: T; tag: string }>();
  for (const [tag, entry] of [...a.elements, ...b.elements]) {
    if (!tombstones.has(tag)) {
      elements.set(tag, entry);
    }
  }
  return { elements, tombstones };
}
```

## Optimistic UI with Rollback

```typescript
import { create } from 'zustand';

interface Todo {
  id: string;
  text: string;
  done: boolean;
}

interface OptimisticState {
  todos: Todo[];
  pendingOps: Map<string, Todo[]>; // opId -> snapshot before mutation
}

interface TodoStore extends OptimisticState {
  toggleTodo: (id: string) => Promise<void>;
  deleteTodo: (id: string) => Promise<void>;
}

const useTodoStore = create<TodoStore>((set, get) => ({
  todos: [],
  pendingOps: new Map(),

  toggleTodo: async (id: string) => {
    const opId = crypto.randomUUID();
    const snapshot = [...get().todos];

    // Optimistic update
    set((state) => ({
      todos: state.todos.map((t) =>
        t.id === id ? { ...t, done: !t.done } : t
      ),
      pendingOps: new Map(state.pendingOps).set(opId, snapshot),
    }));

    try {
      const todo = get().todos.find((t) => t.id === id)!;
      const res = await fetch(`/api/todos/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ done: todo.done }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch {
      // Rollback on failure
      const rollbackSnapshot = get().pendingOps.get(opId);
      if (rollbackSnapshot) {
        set({ todos: rollbackSnapshot });
      }
    } finally {
      set((state) => {
        const ops = new Map(state.pendingOps);
        ops.delete(opId);
        return { pendingOps: ops };
      });
    }
  },

  deleteTodo: async (id: string) => {
    const opId = crypto.randomUUID();
    const snapshot = [...get().todos];

    set((state) => ({
      todos: state.todos.filter((t) => t.id !== id),
      pendingOps: new Map(state.pendingOps).set(opId, snapshot),
    }));

    try {
      const res = await fetch(`/api/todos/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch {
      const rollbackSnapshot = get().pendingOps.get(opId);
      if (rollbackSnapshot) {
        set({ todos: rollbackSnapshot });
      }
    } finally {
      set((state) => {
        const ops = new Map(state.pendingOps);
        ops.delete(opId);
        return { pendingOps: ops };
      });
    }
  },
}));
```
