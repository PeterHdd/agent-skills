# Platform API Integration

Production patterns for native platform APIs: push notifications (APNs, FCM, react-native-firebase), camera/photo (CameraX, AVFoundation, react-native-vision-camera), biometric auth (FaceID/TouchID, BiometricPrompt), file system access, background tasks, and high-level entitlement architecture notes for app-store subscriptions.

## Push Notifications

### Swift: APNs Setup

```swift
import UserNotifications
import UIKit

// MARK: - AppDelegate: register for push notifications

final class PushNotificationManager: NSObject, UNUserNotificationCenterDelegate {
    static let shared = PushNotificationManager()

    func requestPermission() async -> Bool {
        let center = UNUserNotificationCenter.current()
        center.delegate = self
        do {
            let granted = try await center.requestAuthorization(options: [.alert, .badge, .sound])
            if granted {
                await MainActor.run {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            }
            return granted
        } catch {
            return false
        }
    }

    // Called when device token is received — send to your server
    func didRegisterForRemoteNotifications(deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        Task {
            try? await APIClient.shared.registerPushToken(token)
        }
    }

    // Handle notification when app is in foreground
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        let userInfo = notification.request.content.userInfo
        handleNotificationPayload(userInfo)
        return [.banner, .badge, .sound]
    }

    // Handle notification tap
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        let userInfo = response.notification.request.content.userInfo
        guard let deepLink = userInfo["deep_link"] as? String,
              let url = URL(string: deepLink) else { return }
        await MainActor.run {
            UIApplication.shared.open(url)
        }
    }

    // Topic-based subscription
    func subscribeToTopic(_ topic: String) {
        // Use your push provider's topic subscription API
        // For Firebase: Messaging.messaging().subscribe(toTopic: topic)
    }

    private func handleNotificationPayload(_ userInfo: [AnyHashable: Any]) {
        guard let type = userInfo["type"] as? String else { return }
        switch type {
        case "message":
            NotificationCenter.default.post(name: .newMessageReceived, object: nil, userInfo: userInfo)
        case "order_update":
            NotificationCenter.default.post(name: .orderUpdated, object: nil, userInfo: userInfo)
        default:
            break
        }
    }
}

extension Notification.Name {
    static let newMessageReceived = Notification.Name("newMessageReceived")
    static let orderUpdated = Notification.Name("orderUpdated")
}
```

### Kotlin: FCM Setup

```kotlin
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class AppFirebaseMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        // Send token to your backend
        kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
            try {
                ApiClient.registerPushToken(token)
            } catch (e: Exception) {
                // Store locally, retry later
                getSharedPreferences("push", MODE_PRIVATE)
                    .edit()
                    .putString("pending_token", token)
                    .apply()
            }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val data = message.data
        val type = data["type"] ?: return

        when (type) {
            "message" -> showMessageNotification(data)
            "order_update" -> showOrderNotification(data)
            "silent_sync" -> triggerBackgroundSync()
        }
    }

    private fun showMessageNotification(data: Map<String, String>) {
        createNotificationChannel()

        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("deep_link", data["deep_link"])
        }

        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(data["title"] ?: "New Message")
            .setContentText(data["body"] ?: "")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(System.currentTimeMillis().toInt(), notification)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Messages",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Message notifications"
                enableVibration(true)
            }
            val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun triggerBackgroundSync() {
        val syncRequest = androidx.work.OneTimeWorkRequestBuilder<SyncWorker>()
            .setExpedited(androidx.work.OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            .build()
        androidx.work.WorkManager.getInstance(this)
            .enqueue(syncRequest)
    }

    companion object {
        private const val CHANNEL_ID = "messages_channel"
    }
}
```

### React Native: react-native-firebase

```typescript
import messaging from '@react-native-firebase/messaging';
import notifee, { AndroidImportance } from '@notifee/react-native';
import { Platform, PermissionsAndroid } from 'react-native';

// --- Permission request ---

export async function requestNotificationPermission(): Promise<boolean> {
  if (Platform.OS === 'android' && Platform.Version >= 33) {
    const result = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS
    );
    if (result !== PermissionsAndroid.RESULTS.GRANTED) return false;
  }

  const authStatus = await messaging().requestPermission();
  return (
    authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
    authStatus === messaging.AuthorizationStatus.PROVISIONAL
  );
}

// --- Token management ---

export async function getAndRegisterToken(): Promise<string | null> {
  try {
    const token = await messaging().getToken();
    await fetch('/api/push/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, platform: Platform.OS }),
    });
    return token;
  } catch {
    return null;
  }
}

// --- Foreground notification display with notifee ---

export function setupForegroundHandler(): () => void {
  return messaging().onMessage(async (remoteMessage) => {
    const channelId = await notifee.createChannel({
      id: 'default',
      name: 'Default',
      importance: AndroidImportance.HIGH,
    });

    await notifee.displayNotification({
      title: remoteMessage.notification?.title ?? 'Notification',
      body: remoteMessage.notification?.body ?? '',
      android: { channelId, pressAction: { id: 'default' } },
      data: remoteMessage.data,
    });
  });
}

// --- Background / quit handler (must be registered at top level, outside components) ---

messaging().setBackgroundMessageHandler(async (remoteMessage) => {
  // Handle silent data messages
  if (remoteMessage.data?.type === 'silent_sync') {
    // Trigger local sync — limited execution time
  }
});

// --- Topic subscription ---

export async function subscribeToTopic(topic: string): Promise<void> {
  await messaging().subscribeToTopic(topic);
}

export async function unsubscribeFromTopic(topic: string): Promise<void> {
  await messaging().unsubscribeFromTopic(topic);
}
```

## Camera and Photo

### Kotlin: CameraX

```kotlin
import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import java.io.File
import java.util.concurrent.Executors

@Composable
fun CameraScreen(
    onPhotoCaptured: (File) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
                PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> hasCameraPermission = granted }

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    if (hasCameraPermission) {
        CameraPreview(onPhotoCaptured = onPhotoCaptured, modifier = modifier)
    } else {
        // Show explanation and settings link
        Column(modifier = modifier, verticalArrangement = Arrangement.Center) {
            Text("Camera permission is required to take photos.")
            Button(onClick = { permissionLauncher.launch(Manifest.permission.CAMERA) }) {
                Text("Grant Permission")
            }
        }
    }
}

@Composable
private fun CameraPreview(
    onPhotoCaptured: (File) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = androidx.lifecycle.compose.LocalLifecycleOwner.current
    val cameraExecutor = remember { Executors.newSingleThreadExecutor() }

    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }

    Box(modifier = modifier) {
        AndroidView(
            factory = { ctx ->
                val previewView = PreviewView(ctx)
                val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)

                cameraProviderFuture.addListener({
                    val cameraProvider = cameraProviderFuture.get()

                    val preview = Preview.Builder().build().also {
                        it.surfaceProvider = previewView.surfaceProvider
                    }

                    val capture = ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
                        .build()
                    imageCapture = capture

                    val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

                    cameraProvider.unbindAll()
                    cameraProvider.bindToLifecycle(
                        lifecycleOwner, cameraSelector, preview, capture
                    )
                }, ContextCompat.getMainExecutor(ctx))

                previewView
            },
            modifier = Modifier.fillMaxSize()
        )

        Button(
            onClick = {
                val capture = imageCapture ?: return@Button
                val photoFile = File(
                    context.cacheDir,
                    "photo_${System.currentTimeMillis()}.jpg"
                )
                val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()
                capture.takePicture(
                    outputOptions,
                    cameraExecutor,
                    object : ImageCapture.OnImageSavedCallback {
                        override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                            onPhotoCaptured(photoFile)
                        }
                        override fun onError(exception: ImageCaptureException) {
                            // Handle error
                        }
                    }
                )
            },
            modifier = Modifier.align(androidx.compose.ui.Alignment.BottomCenter)
        ) {
            Text("Capture")
        }
    }
}
```

### Swift: AVFoundation Camera

```swift
import SwiftUI
import AVFoundation

// MARK: - Camera service wrapping AVCaptureSession

final class CameraService: NSObject, ObservableObject {
    @Published var capturedImage: UIImage?
    @Published var isAuthorized = false
    @Published var error: String?

    private let session = AVCaptureSession()
    private let output = AVCapturePhotoOutput()
    private let sessionQueue = DispatchQueue(label: "camera.session")
    private var continuation: CheckedContinuation<UIImage?, Error>?

    func checkPermission() async {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            await MainActor.run { isAuthorized = true }
        case .notDetermined:
            let granted = await AVCaptureDevice.requestAccess(for: .video)
            await MainActor.run { isAuthorized = granted }
        case .denied, .restricted:
            await MainActor.run {
                isAuthorized = false
                error = "Camera access denied. Enable in Settings."
            }
        @unknown default:
            break
        }
    }

    func configureSession() {
        sessionQueue.async { [weak self] in
            guard let self else { return }
            session.beginConfiguration()
            session.sessionPreset = .photo

            guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
                  let input = try? AVCaptureDeviceInput(device: camera),
                  session.canAddInput(input) else {
                session.commitConfiguration()
                return
            }

            session.addInput(input)
            if session.canAddOutput(output) {
                session.addOutput(output)
            }
            session.commitConfiguration()
            session.startRunning()
        }
    }

    func capturePhoto() async throws -> UIImage? {
        return try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            let settings = AVCapturePhotoSettings()
            settings.flashMode = .auto
            output.capturePhoto(with: settings, delegate: self)
        }
    }

    func stopSession() {
        sessionQueue.async { [weak self] in
            self?.session.stopRunning()
        }
    }
}

extension CameraService: AVCapturePhotoCaptureDelegate {
    func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: Error?
    ) {
        if let error {
            continuation?.resume(throwing: error)
            continuation = nil
            return
        }
        guard let data = photo.fileDataRepresentation(),
              let image = UIImage(data: data) else {
            continuation?.resume(returning: nil)
            continuation = nil
            return
        }
        continuation?.resume(returning: image)
        continuation = nil
        Task { @MainActor in self.capturedImage = image }
    }
}
```

## Biometric Authentication

### Swift: FaceID / TouchID with LocalAuthentication

```swift
import LocalAuthentication

enum BiometricType {
    case none, touchID, faceID, opticID
}

final class BiometricAuthService {
    static let shared = BiometricAuthService()

    var availableBiometricType: BiometricType {
        let context = LAContext()
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: nil) else {
            return .none
        }
        switch context.biometryType {
        case .touchID: return .touchID
        case .faceID: return .faceID
        case .opticID: return .opticID
        case .none: return .none
        @unknown default: return .none
        }
    }

    /// Authenticate with biometrics, falling back to device passcode
    func authenticate(reason: String) async -> Result<Void, BiometricError> {
        let context = LAContext()
        context.localizedFallbackTitle = "Use Passcode"
        context.localizedCancelTitle = "Cancel"

        // Check biometric availability
        var authError: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &authError) else {
            return .failure(.notAvailable(authError?.localizedDescription ?? "Biometrics not available"))
        }

        do {
            // .deviceOwnerAuthentication falls back to passcode automatically
            let success = try await context.evaluatePolicy(
                .deviceOwnerAuthentication,
                localizedReason: reason
            )
            return success ? .success(()) : .failure(.failed)
        } catch let error as LAError {
            switch error.code {
            case .userCancel: return .failure(.userCancelled)
            case .userFallback: return .failure(.userFallback)
            case .biometryLockout: return .failure(.lockedOut)
            case .biometryNotEnrolled: return .failure(.notEnrolled)
            default: return .failure(.failed)
            }
        } catch {
            return .failure(.failed)
        }
    }
}

enum BiometricError: Error {
    case notAvailable(String)
    case notEnrolled
    case lockedOut
    case userCancelled
    case userFallback
    case failed
}
```

### Kotlin: BiometricPrompt

```kotlin
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

sealed class BiometricResult {
    data object Success : BiometricResult()
    data class Error(val code: Int, val message: String) : BiometricResult()
    data object Cancelled : BiometricResult()
}

class BiometricAuthService {

    fun canAuthenticate(activity: FragmentActivity): Boolean {
        val manager = BiometricManager.from(activity)
        return manager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG or
            BiometricManager.Authenticators.DEVICE_CREDENTIAL
        ) == BiometricManager.BIOMETRIC_SUCCESS
    }

    suspend fun authenticate(
        activity: FragmentActivity,
        title: String = "Authenticate",
        subtitle: String = "Verify your identity",
        negativeButtonText: String = "Cancel"
    ): BiometricResult = suspendCancellableCoroutine { continuation ->

        val executor = ContextCompat.getMainExecutor(activity)

        val callback = object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                if (continuation.isActive) continuation.resume(BiometricResult.Success)
            }

            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                if (continuation.isActive) {
                    if (errorCode == BiometricPrompt.ERROR_USER_CANCELED ||
                        errorCode == BiometricPrompt.ERROR_NEGATIVE_BUTTON
                    ) {
                        continuation.resume(BiometricResult.Cancelled)
                    } else {
                        continuation.resume(BiometricResult.Error(errorCode, errString.toString()))
                    }
                }
            }

            override fun onAuthenticationFailed() {
                // Called on each failed attempt; prompt stays open for retry
            }
        }

        val prompt = BiometricPrompt(activity, executor, callback)

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .setSubtitle(subtitle)
            .setAllowedAuthenticators(
                BiometricManager.Authenticators.BIOMETRIC_STRONG or
                BiometricManager.Authenticators.DEVICE_CREDENTIAL
            )
            .build()

        prompt.authenticate(promptInfo)
    }
}
```

## Background Tasks

### Swift: BGTaskScheduler

```swift
import BackgroundTasks
import UIKit

// MARK: - Register in AppDelegate or App init

final class BackgroundTaskManager {
    static let shared = BackgroundTaskManager()

    private let refreshIdentifier = "com.app.data.refresh"
    private let cleanupIdentifier = "com.app.maintenance.cleanup"

    func registerAllTasks() {
        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: refreshIdentifier,
            using: nil
        ) { task in
            self.handleDataRefresh(task: task as! BGAppRefreshTask)
        }

        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: cleanupIdentifier,
            using: nil
        ) { task in
            self.handleCleanup(task: task as! BGProcessingTask)
        }
    }

    func scheduleDataRefresh() {
        let request = BGAppRefreshTaskRequest(identifier: refreshIdentifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 30 * 60) // 30 min
        do {
            try BGTaskScheduler.shared.submit(request)
        } catch {
            print("Failed to schedule refresh: \(error)")
        }
    }

    func scheduleCleanup() {
        let request = BGProcessingTaskRequest(identifier: cleanupIdentifier)
        request.requiresNetworkConnectivity = false
        request.requiresExternalPower = false
        request.earliestBeginDate = Date(timeIntervalSinceNow: 2 * 60 * 60) // 2 hours
        do {
            try BGTaskScheduler.shared.submit(request)
        } catch {
            print("Failed to schedule cleanup: \(error)")
        }
    }

    private func handleDataRefresh(task: BGAppRefreshTask) {
        scheduleDataRefresh() // Re-schedule next occurrence

        let refreshTask = Task {
            try await SyncService.shared.pullChanges()
        }

        task.expirationHandler = {
            refreshTask.cancel()
        }

        Task {
            do {
                try await refreshTask.value
                task.setTaskCompleted(success: true)
            } catch {
                task.setTaskCompleted(success: false)
            }
        }
    }

    private func handleCleanup(task: BGProcessingTask) {
        let cleanupTask = Task {
            let cacheDir = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first!
            let files = try FileManager.default.contentsOfDirectory(
                at: cacheDir, includingPropertiesForKeys: [.contentModificationDateKey]
            )
            let cutoff = Date(timeIntervalSinceNow: -7 * 24 * 60 * 60) // 7 days
            for file in files {
                let attrs = try file.resourceValues(forKeys: [.contentModificationDateKey])
                if let modified = attrs.contentModificationDate, modified < cutoff {
                    try FileManager.default.removeItem(at: file)
                }
            }
        }

        task.expirationHandler = { cleanupTask.cancel() }

        Task {
            do {
                try await cleanupTask.value
                task.setTaskCompleted(success: true)
            } catch {
                task.setTaskCompleted(success: false)
            }
        }
    }
}
```

### Kotlin: WorkManager

```kotlin
import android.content.Context
import androidx.work.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

// --- Periodic sync worker ---

class DataSyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            val syncService = SyncService.getInstance(applicationContext)
            syncService.pullAndPushChanges()
            Result.success()
        } catch (e: Exception) {
            if (runAttemptCount < 3) Result.retry() else Result.failure()
        }
    }
}

// --- Cache cleanup worker ---

class CacheCleanupWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val cacheDir = applicationContext.cacheDir
        val cutoffMs = System.currentTimeMillis() - 7 * 24 * 60 * 60 * 1000L
        var bytesFreed = 0L

        cacheDir.listFiles()?.forEach { file ->
            if (file.lastModified() < cutoffMs) {
                bytesFreed += file.length()
                file.delete()
            }
        }

        Result.success(workDataOf("bytes_freed" to bytesFreed))
    }
}

// --- Schedule at app startup ---

object WorkScheduler {
    fun scheduleAll(context: Context) {
        schedulePeriodicSync(context)
        scheduleCacheCleanup(context)
    }

    private fun schedulePeriodicSync(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val request = PeriodicWorkRequestBuilder<DataSyncWorker>(
            repeatInterval = 15, repeatIntervalTimeUnit = TimeUnit.MINUTES
        )
            .setConstraints(constraints)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
            .build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "data_sync", ExistingPeriodicWorkPolicy.KEEP, request
        )
    }

    private fun scheduleCacheCleanup(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiresBatteryNotLow(true)
            .build()

        val request = PeriodicWorkRequestBuilder<CacheCleanupWorker>(
            repeatInterval = 24, repeatIntervalTimeUnit = TimeUnit.HOURS
        )
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "cache_cleanup", ExistingPeriodicWorkPolicy.KEEP, request
        )
    }
}
```

## In-App Purchases

This skill does not provide code that initiates, completes, restores, acknowledges, or validates monetary transactions.

Use this section only for entitlement architecture and review planning:

- Model premium access as an entitlement state machine with explicit states such as `unknown`, `active`, `expired`, `grace_period`, `revoked`, and `pending_review`.
- Keep the mobile client read-only with respect to entitlements. The app may display entitlement state returned by your backend, but server-side systems should remain the source of truth for receipt validation and access changes.
- Record the exact product identifiers, platform, environment, and validation event IDs in backend audit logs so support and finance teams can reconcile disputes without relying on device state.
- Treat restore, refund, renewal, family sharing, and interrupted-purchase handling as policy-sensitive flows that require platform-documentation review and dedicated payments testing before release.
- Separate pricing presentation from entitlement enforcement. UI can render product metadata from configuration, but unlocking paid features should depend on backend-confirmed entitlement status.
- Before shipping any subscription feature, run a checklist with legal/compliance, tax handling, fraud review, customer-support playbooks, and App Store / Play policy review.
