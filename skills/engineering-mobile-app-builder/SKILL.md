---
name: engineering-mobile-app-builder
description: "Build native and cross-platform mobile applications for iOS and Android with optimized performance and platform integration. Use when you need SwiftUI or Jetpack Compose development, React Native or Flutter cross-platform apps, offline-first architecture, biometric authentication, push notifications, deep linking, app startup optimization, or mobile-specific UX patterns and gesture handling."
metadata:
  version: "1.0.0"
---

# Mobile Development Guide

## Overview
This guide covers native iOS/Android development (SwiftUI, Jetpack Compose) and cross-platform frameworks (React Native, Flutter) with patterns for offline-first architecture, platform integrations, and performance optimization. Use it when choosing a platform strategy, building mobile UI, or integrating device capabilities.

## Platform Selection Guide

- Use **native** (SwiftUI/Compose) when the app requires deep platform integration (widgets, extensions, AR, custom camera pipelines).
- Use **React Native or Flutter** when shipping to both platforms with a small team and the app is primarily data display and forms.
- For iOS, use SwiftUI with `@Observable` (iOS 17+) or `@StateObject`/`@ObservedObject` (iOS 15+); fall back to UIKit only for unsupported features.
- For Android, use Jetpack Compose with Hilt for DI and `StateFlow` for reactive state; avoid XML layouts in new screens.
- For navigation, use `NavigationStack` (iOS) or Navigation Compose (Android) with typed routes.

## Performance and UX Rules

- Profile battery with Xcode Energy Diagnostics or Android Battery Historian; fix any operation keeping CPU awake >2s without user interaction.
- Animations: use SwiftUI `.animation()` / Compose `animateFloatAsState`; keep durations 200-350ms.
- Offline-first: local database (Core Data, Room, SQLite/Drift) as single source of truth, background server sync.
- Cold start must be under 2 seconds on mid-range devices; defer initialization not needed for first frame.
- Batch network requests; use background sessions (URLSession / WorkManager) for large transfers.
- Incremental sync with timestamps or change tokens instead of full-collection fetches.
- Maintain 60fps scrolling on devices two generations behind current.
- Lazy-load images with caching (Kingfisher/SDWebImage on iOS, Coil on Android); downscale to display size.

## Platform Integration Rules

- Biometric auth: `LAContext` (iOS) / `BiometricPrompt` (Android) with passcode fallback; never store raw biometric data.
- Camera: request permissions just-in-time, handle denial with settings deep link.
- Push notifications: APNs (iOS) / FCM (Android) with topic-based subscription.
- In-app purchases: StoreKit 2 (iOS) / Google Play Billing Library 6+ (Android) with server-side receipt validation.

## Platform-Specific UI

- iOS: SF Symbols, system font (San Francisco), Dynamic Type support.
- Android: Material Design 3 tokens, `MaterialTheme` in Compose.
- Sensitive data: Keychain (iOS) / EncryptedSharedPreferences (Android).
- Permissions: explain before system prompt, handle denial gracefully, never block entire app.

## Code Examples

See [SwiftUI Guide](references/swiftui.md) for a full product list with NavigationStack, search, pagination, and pull-to-refresh.

See [Jetpack Compose Guide](references/compose.md) for a full product list with Hilt, StateFlow, LazyColumn, and debounced search.

See [React Native Guide](references/react-native.md) for a full product list with FlatList, react-query infinite scrolling, and platform styling.

See [Offline-First Architecture](references/offline-first.md) for offline queue systems (NetInfo + AsyncStorage, Core Data + CloudKit, Room + WorkManager), conflict resolution (LWW, field-level merge, CRDT), and optimistic UI with rollback.

See [Performance Patterns](references/performance.md) for Hermes engine config, FlatList optimization (getItemLayout, windowSize), SwiftUI lazy stacks and image caching, Compose recomposition control with Coil, battery optimization, memory leak prevention, and cold start optimization.

See [State Management](references/state-management.md) for Zustand with MMKV persistence, TanStack Query optimistic mutations, SwiftUI @Observable with environment injection, Compose ViewModel + StateFlow + SavedStateHandle, navigation deep linking, auth state machines, and form validation.

See [Native APIs](references/native-apis.md) for push notifications (APNs, FCM, react-native-firebase), camera/photo (CameraX, AVFoundation, vision-camera), biometric auth (FaceID/TouchID, BiometricPrompt), background tasks (BGTaskScheduler, WorkManager), and in-app purchases (StoreKit 2, Google Play Billing).

## Workflow

### Step 1: Platform Strategy and Setup
- Choose native vs cross-platform approach based on requirements.
- Set up development environment for target platforms.
- Configure build tools and deployment pipelines.

### Step 2: Architecture and Design
- Design data architecture with offline-first considerations.
- Plan platform-specific UI/UX implementation.
- Set up state management and navigation architecture.

### Step 3: Development and Integration
- Implement core features with platform-native patterns.
- Build platform-specific integrations (camera, notifications, etc.).
- Implement performance monitoring and optimization.

### Step 4: Testing and Deployment
- Test on real devices across different OS versions.
- Perform app store optimization and metadata preparation.
- Set up automated testing and CI/CD for mobile deployment.

## Scripts

### `scripts/check_app_size.sh`
Analyze a mobile app build output directory for size issues. Takes a build output directory as argument, finds app binaries/bundles (.app, .apk, .aab, .ipa), reports total size, largest files, and asset breakdown by category. Warns if total exceeds common thresholds (50MB for iOS, 150MB for Android).

```bash
scripts/check_app_size.sh ./build/outputs/apk/release
scripts/check_app_size.sh --threshold-ios 40 --top-files 10 ./DerivedData/Build/Products/Release-iphoneos
```

### `scripts/check_permissions.py`
Extract and audit permissions from AndroidManifest.xml or Info.plist. Identifies requested permissions, flags potentially dangerous ones (CAMERA, LOCATION, CONTACTS, etc.) with explanations, and reports total permission count. Supports JSON output.

```bash
scripts/check_permissions.py app/src/main/AndroidManifest.xml
scripts/check_permissions.py --format json ios/Runner/Info.plist
```
