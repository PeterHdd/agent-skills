#!/usr/bin/env python3
"""check_permissions.py — Extract and audit permissions from AndroidManifest.xml or Info.plist.

Parses mobile app manifest files to identify requested permissions and flags
potentially dangerous ones with explanations.
"""

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

# Android dangerous permissions and their explanations
ANDROID_DANGEROUS_PERMISSIONS = {
    "android.permission.CAMERA": {
        "level": "dangerous",
        "reason": "Access to device camera. Can capture photos/video without user awareness.",
    },
    "android.permission.ACCESS_FINE_LOCATION": {
        "level": "dangerous",
        "reason": "Precise GPS location tracking. High privacy impact.",
    },
    "android.permission.ACCESS_COARSE_LOCATION": {
        "level": "dangerous",
        "reason": "Approximate location via network. Moderate privacy impact.",
    },
    "android.permission.ACCESS_BACKGROUND_LOCATION": {
        "level": "dangerous",
        "reason": "Location access when app is in background. Very high privacy impact.",
    },
    "android.permission.READ_CONTACTS": {
        "level": "dangerous",
        "reason": "Read user's contact list. Sensitive personal data.",
    },
    "android.permission.WRITE_CONTACTS": {
        "level": "dangerous",
        "reason": "Modify user's contacts. Can alter personal data.",
    },
    "android.permission.READ_CALENDAR": {
        "level": "dangerous",
        "reason": "Read calendar events. Reveals personal schedule.",
    },
    "android.permission.WRITE_CALENDAR": {
        "level": "dangerous",
        "reason": "Modify calendar events. Can alter personal schedule.",
    },
    "android.permission.RECORD_AUDIO": {
        "level": "dangerous",
        "reason": "Microphone access. Can record audio without user awareness.",
    },
    "android.permission.READ_PHONE_STATE": {
        "level": "dangerous",
        "reason": "Access phone number, IMEI, call state. Device fingerprinting risk.",
    },
    "android.permission.CALL_PHONE": {
        "level": "dangerous",
        "reason": "Initiate phone calls without user interaction.",
    },
    "android.permission.READ_CALL_LOG": {
        "level": "dangerous",
        "reason": "Read call history. Sensitive communication metadata.",
    },
    "android.permission.SEND_SMS": {
        "level": "dangerous",
        "reason": "Send SMS messages. Potential for premium-rate abuse.",
    },
    "android.permission.READ_SMS": {
        "level": "dangerous",
        "reason": "Read SMS messages. Exposes private communications.",
    },
    "android.permission.READ_EXTERNAL_STORAGE": {
        "level": "dangerous",
        "reason": "Read files on shared storage. Access to user photos/documents.",
    },
    "android.permission.WRITE_EXTERNAL_STORAGE": {
        "level": "dangerous",
        "reason": "Write to shared storage. Can modify user files.",
    },
    "android.permission.READ_MEDIA_IMAGES": {
        "level": "dangerous",
        "reason": "Read user photos and images from media store.",
    },
    "android.permission.READ_MEDIA_VIDEO": {
        "level": "dangerous",
        "reason": "Read user videos from media store.",
    },
    "android.permission.BODY_SENSORS": {
        "level": "dangerous",
        "reason": "Access body sensors (heart rate, etc.). Health data privacy risk.",
    },
    "android.permission.ACTIVITY_RECOGNITION": {
        "level": "dangerous",
        "reason": "Detect physical activity. Behavioral tracking risk.",
    },
    "android.permission.BLUETOOTH_CONNECT": {
        "level": "dangerous",
        "reason": "Connect to paired Bluetooth devices. Proximity tracking risk.",
    },
    "android.permission.NEARBY_WIFI_DEVICES": {
        "level": "dangerous",
        "reason": "Discover nearby Wi-Fi devices. Location inference risk.",
    },
    "android.permission.POST_NOTIFICATIONS": {
        "level": "moderate",
        "reason": "Show notifications. Low risk but can be intrusive.",
    },
    "android.permission.SYSTEM_ALERT_WINDOW": {
        "level": "dangerous",
        "reason": "Draw over other apps. Can be used for tapjacking attacks.",
    },
    "android.permission.REQUEST_INSTALL_PACKAGES": {
        "level": "dangerous",
        "reason": "Install APKs. Potential vector for malware delivery.",
    },
}

# iOS permission usage description keys and their meanings
IOS_PERMISSION_KEYS = {
    "NSCameraUsageDescription": {
        "level": "dangerous",
        "reason": "Camera access. Can capture photos/video.",
    },
    "NSLocationWhenInUseUsageDescription": {
        "level": "dangerous",
        "reason": "Location while app is in foreground. Privacy impact.",
    },
    "NSLocationAlwaysUsageDescription": {
        "level": "dangerous",
        "reason": "Location access at all times. Very high privacy impact.",
    },
    "NSLocationAlwaysAndWhenInUseUsageDescription": {
        "level": "dangerous",
        "reason": "Combined always + in-use location. Very high privacy impact.",
    },
    "NSContactsUsageDescription": {
        "level": "dangerous",
        "reason": "Access to user's contacts. Sensitive personal data.",
    },
    "NSCalendarsUsageDescription": {
        "level": "dangerous",
        "reason": "Calendar access. Reveals personal schedule.",
    },
    "NSRemindersUsageDescription": {
        "level": "moderate",
        "reason": "Reminders access. Personal task data.",
    },
    "NSPhotoLibraryUsageDescription": {
        "level": "dangerous",
        "reason": "Photo library access. Personal media exposure.",
    },
    "NSPhotoLibraryAddUsageDescription": {
        "level": "moderate",
        "reason": "Save to photo library. Lower risk (write-only).",
    },
    "NSMicrophoneUsageDescription": {
        "level": "dangerous",
        "reason": "Microphone access. Can record audio.",
    },
    "NSSpeechRecognitionUsageDescription": {
        "level": "moderate",
        "reason": "Speech recognition. Audio processing.",
    },
    "NSMotionUsageDescription": {
        "level": "moderate",
        "reason": "Motion and fitness data. Activity tracking.",
    },
    "NSHealthShareUsageDescription": {
        "level": "dangerous",
        "reason": "Read HealthKit data. Sensitive health information.",
    },
    "NSHealthUpdateUsageDescription": {
        "level": "dangerous",
        "reason": "Write HealthKit data. Can modify health records.",
    },
    "NSBluetoothAlwaysUsageDescription": {
        "level": "moderate",
        "reason": "Bluetooth access. Proximity tracking potential.",
    },
    "NSBluetoothPeripheralUsageDescription": {
        "level": "moderate",
        "reason": "Bluetooth peripheral access. Device communication.",
    },
    "NSFaceIDUsageDescription": {
        "level": "moderate",
        "reason": "Face ID authentication. Biometric data usage.",
    },
    "NSLocalNetworkUsageDescription": {
        "level": "moderate",
        "reason": "Local network access. Can discover nearby devices.",
    },
    "NSUserTrackingUsageDescription": {
        "level": "dangerous",
        "reason": "App Tracking Transparency. Cross-app tracking.",
    },
    "NSAppleMusicUsageDescription": {
        "level": "low",
        "reason": "Apple Music library access.",
    },
    "NFCReaderUsageDescription": {
        "level": "low",
        "reason": "NFC reader access.",
    },
}


def parse_android_manifest(filepath):
    """Parse AndroidManifest.xml and extract permissions."""
    try:
        tree = ET.parse(filepath)
    except ET.ParseError as e:
        print(f"ERROR: Failed to parse XML: {e}", file=sys.stderr)
        sys.exit(1)

    root = tree.getroot()
    ns = {"android": "http://schemas.android.com/apk/res/android"}

    permissions = []
    for elem in root.iter():
        tag = elem.tag
        # Strip namespace prefix if present
        if "}" in tag:
            tag = tag.split("}", 1)[1]

        if tag == "uses-permission" or tag == "uses-permission-sdk-23":
            name = elem.get("{http://schemas.android.com/apk/res/android}name", "")
            if not name:
                name = elem.get("android:name", "")
            max_sdk = elem.get(
                "{http://schemas.android.com/apk/res/android}maxSdkVersion", ""
            )
            permissions.append({"name": name, "max_sdk": max_sdk, "tag": tag})

    return permissions


def parse_info_plist(filepath):
    """Parse Info.plist and extract permission usage descriptions."""
    import plistlib

    try:
        with open(filepath, "rb") as f:
            plist = plistlib.load(f)
    except Exception:
        # Try parsing as XML text (some plists are XML formatted)
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            plist = _parse_plist_xml(root)
        except Exception as e:
            print(f"ERROR: Failed to parse plist: {e}", file=sys.stderr)
            sys.exit(1)

    permissions = []
    for key, value in plist.items():
        if key.startswith("NS") and key.endswith("UsageDescription"):
            permissions.append({"key": key, "description": str(value)})
        elif key == "NFCReaderUsageDescription":
            permissions.append({"key": key, "description": str(value)})
        elif key == "ITSAppUsesNonExemptEncryption":
            permissions.append({"key": key, "description": str(value)})

    return permissions


def _parse_plist_xml(root):
    """Fallback XML-based plist parser for non-binary plists."""
    result = {}
    dict_elem = root.find(".//dict")
    if dict_elem is None:
        return result

    children = list(dict_elem)
    i = 0
    while i < len(children) - 1:
        if children[i].tag == "key":
            key = children[i].text or ""
            val_elem = children[i + 1]
            if val_elem.tag == "string":
                result[key] = val_elem.text or ""
            elif val_elem.tag == "true":
                result[key] = True
            elif val_elem.tag == "false":
                result[key] = False
            else:
                result[key] = val_elem.text or ""
            i += 2
        else:
            i += 1

    return result


def detect_file_type(filepath):
    """Detect whether the file is an Android manifest or iOS plist."""
    basename = os.path.basename(filepath).lower()
    if basename == "androidmanifest.xml":
        return "android"
    if basename == "info.plist":
        return "ios"

    # Try content-based detection
    try:
        with open(filepath, "r", errors="replace") as f:
            head = f.read(1024)
        if "<manifest" in head and "android" in head:
            return "android"
        if "<!DOCTYPE plist" in head or "<plist" in head:
            return "ios"
    except Exception:
        pass

    # Extension-based fallback
    if filepath.endswith(".xml"):
        return "android"
    if filepath.endswith(".plist"):
        return "ios"

    return None


def report_android(permissions):
    """Generate structured report for Android permissions."""
    print("=== PERMISSION ANALYSIS (Android) ===")
    print()
    print(f"total_permissions: {len(permissions)}")
    print()

    dangerous_count = 0
    moderate_count = 0

    print("--- Permissions ---")
    for perm in permissions:
        name = perm["name"]
        short_name = name.replace("android.permission.", "")
        info = ANDROID_DANGEROUS_PERMISSIONS.get(name, None)

        if info:
            level = info["level"]
            reason = info["reason"]
            flag = "DANGEROUS" if level == "dangerous" else "MODERATE"
            if level == "dangerous":
                dangerous_count += 1
            else:
                moderate_count += 1
        else:
            flag = "OK"
            reason = ""

        line = f"  [{flag}] {short_name}"
        if perm["max_sdk"]:
            line += f" (maxSdkVersion={perm['max_sdk']})"
        print(line)
        if reason:
            print(f"          -> {reason}")

    print()
    print("--- Summary ---")
    print(f"dangerous_count: {dangerous_count}")
    print(f"moderate_count: {moderate_count}")
    print(f"safe_count: {len(permissions) - dangerous_count - moderate_count}")

    if dangerous_count > 5:
        print()
        print(
            "WARNING: High number of dangerous permissions. Review whether all are necessary."
        )
        print(
            "  Consider: request permissions just-in-time rather than all at install."
        )

    print()
    print("=== END ANALYSIS ===")
    return dangerous_count


def report_ios(permissions):
    """Generate structured report for iOS permissions."""
    print("=== PERMISSION ANALYSIS (iOS) ===")
    print()
    print(f"total_permissions: {len(permissions)}")
    print()

    dangerous_count = 0
    moderate_count = 0

    print("--- Permissions ---")
    for perm in permissions:
        key = perm["key"]
        desc = perm["description"]
        info = IOS_PERMISSION_KEYS.get(key, None)

        if info:
            level = info["level"]
            reason = info["reason"]
            if level == "dangerous":
                flag = "DANGEROUS"
                dangerous_count += 1
            elif level == "moderate":
                flag = "MODERATE"
                moderate_count += 1
            else:
                flag = "OK"
        else:
            flag = "OK"
            reason = ""

        print(f"  [{flag}] {key}")
        print(f"          Usage string: \"{desc}\"")
        if reason:
            print(f"          -> {reason}")

        # Check for vague usage descriptions
        vague_patterns = ["we need", "required", "this app", "the app"]
        if any(p in desc.lower() for p in vague_patterns) and len(desc) < 40:
            print(
                "          NOTE: Usage description may be too vague for App Store review."
            )

    print()
    print("--- Summary ---")
    print(f"dangerous_count: {dangerous_count}")
    print(f"moderate_count: {moderate_count}")
    print(f"low_risk_count: {len(permissions) - dangerous_count - moderate_count}")

    if dangerous_count > 5:
        print()
        print(
            "WARNING: High number of dangerous permissions. Review whether all are necessary."
        )

    print()
    print("=== END ANALYSIS ===")
    return dangerous_count


def main():
    parser = argparse.ArgumentParser(
        description="Extract and audit permissions from AndroidManifest.xml or Info.plist.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s app/src/main/AndroidManifest.xml
  %(prog)s ios/Runner/Info.plist
        """,
    )
    parser.add_argument(
        "manifest",
        help="Path to AndroidManifest.xml or Info.plist",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.manifest):
        print(f"ERROR: File not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    file_type = detect_file_type(args.manifest)
    if file_type is None:
        print(
            "ERROR: Cannot determine file type. Expected AndroidManifest.xml or Info.plist.",
            file=sys.stderr,
        )
        sys.exit(1)

    if file_type == "android":
        permissions = parse_android_manifest(args.manifest)
        if args.format == "json":
            import json

            result = {
                "platform": "android",
                "total": len(permissions),
                "permissions": [],
            }
            for p in permissions:
                info = ANDROID_DANGEROUS_PERMISSIONS.get(p["name"], {})
                result["permissions"].append(
                    {
                        "name": p["name"],
                        "level": info.get("level", "normal"),
                        "reason": info.get("reason", ""),
                    }
                )
            print(json.dumps(result, indent=2))
        else:
            exit_code = report_android(permissions)
            sys.exit(1 if exit_code > 0 else 0)
    else:
        permissions = parse_info_plist(args.manifest)
        if args.format == "json":
            import json

            result = {
                "platform": "ios",
                "total": len(permissions),
                "permissions": [],
            }
            for p in permissions:
                info = IOS_PERMISSION_KEYS.get(p["key"], {})
                result["permissions"].append(
                    {
                        "key": p["key"],
                        "description": p["description"],
                        "level": info.get("level", "normal"),
                        "reason": info.get("reason", ""),
                    }
                )
            print(json.dumps(result, indent=2))
        else:
            exit_code = report_ios(permissions)
            sys.exit(1 if exit_code > 0 else 0)


if __name__ == "__main__":
    main()
