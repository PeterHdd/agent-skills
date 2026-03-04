#!/usr/bin/env python3
"""Validate app store metadata against platform character limits and quality rules.

Checks iOS App Store and Google Play Store metadata for character limit
violations, keyword stuffing, and readability issues.
"""

import argparse
import json
import re
import sys
from collections import Counter


# Platform-specific character limits
LIMITS = {
    "ios": {
        "title": 30,
        "subtitle": 30,
        "description": 4000,
        "keyword_field": 100,
    },
    "android": {
        "title": 50,
        "short_description": 80,
        "description": 4000,
    },
}

# Common stop words to exclude from keyword analysis
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "are",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "this", "that",
    "these", "those", "i", "you", "he", "she", "we", "they", "my", "your",
    "his", "her", "our", "their", "its", "not", "no", "all", "any", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "than",
    "too", "very", "just", "about", "up", "out", "so", "if", "then",
    "into", "also", "how", "when", "where", "what", "which", "who",
    "get", "got", "app", "new",
}


def extract_words(text):
    """Extract meaningful words from text, lowercased."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def check_character_limits(field_name, value, limit):
    """Check a field against its character limit."""
    length = len(value)
    return {
        "field": field_name,
        "length": length,
        "limit": limit,
        "status": "PASS" if length <= limit else "OVER",
        "remaining": limit - length,
    }


def check_keyword_stuffing(text, threshold=3):
    """Check for repeated words that may indicate keyword stuffing."""
    words = extract_words(text)
    if not words:
        return []

    counts = Counter(words)
    warnings = []
    for word, count in counts.most_common():
        if count > threshold:
            warnings.append({
                "word": word,
                "count": count,
                "warning": "'{}' appears {} times (threshold: {})".format(
                    word, count, threshold
                ),
            })

    return warnings


def readability_score(text):
    """Calculate a simple readability score based on word complexity.

    Uses ratio of short/common words to total words as a proxy for readability.
    Short words (<=6 chars) are considered simpler.
    """
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return {"score": 0, "total_words": 0, "simple_words": 0, "ratio": 0.0}

    simple_words = [w for w in words if len(w) <= 6]
    ratio = len(simple_words) / len(words)
    score = round(ratio * 100)

    if score >= 80:
        assessment = "Excellent"
    elif score >= 60:
        assessment = "Good"
    elif score >= 40:
        assessment = "Fair"
    else:
        assessment = "Complex - consider simplifying"

    return {
        "score": score,
        "total_words": len(words),
        "simple_words": len(simple_words),
        "ratio": round(ratio, 3),
        "assessment": assessment,
    }


def validate_ios(title, subtitle, description):
    """Validate iOS App Store metadata."""
    results = {
        "platform": "iOS App Store",
        "character_checks": [],
        "keyword_warnings": [],
        "readability": {},
        "overall_status": "PASS",
        "issues": [],
    }

    if title:
        results["character_checks"].append(
            check_character_limits("title", title, LIMITS["ios"]["title"])
        )
    if subtitle:
        results["character_checks"].append(
            check_character_limits("subtitle", subtitle, LIMITS["ios"]["subtitle"])
        )
    if description:
        results["character_checks"].append(
            check_character_limits(
                "description", description, LIMITS["ios"]["description"]
            )
        )

    combined = "{} {} {}".format(title or "", subtitle or "", description or "")
    results["keyword_warnings"] = check_keyword_stuffing(combined)

    if description:
        results["readability"] = readability_score(description)

    for check in results["character_checks"]:
        if check["status"] == "OVER":
            results["overall_status"] = "FAIL"
            results["issues"].append(
                "{} exceeds limit by {} characters".format(
                    check["field"], abs(check["remaining"])
                )
            )

    if results["keyword_warnings"]:
        results["issues"].append(
            "{} keyword(s) appear excessively".format(
                len(results["keyword_warnings"])
            )
        )

    if title and subtitle:
        title_words = set(extract_words(title))
        subtitle_words = set(extract_words(subtitle))
        overlap = title_words & subtitle_words
        if overlap:
            results["issues"].append(
                "Title and subtitle share words: {}. "
                "Apple may penalize duplicate keywords.".format(
                    ", ".join(overlap)
                )
            )

    return results


def validate_android(title, short_desc, description):
    """Validate Google Play Store metadata."""
    results = {
        "platform": "Google Play Store",
        "character_checks": [],
        "keyword_warnings": [],
        "readability": {},
        "overall_status": "PASS",
        "issues": [],
    }

    if title:
        results["character_checks"].append(
            check_character_limits("title", title, LIMITS["android"]["title"])
        )
    if short_desc:
        results["character_checks"].append(
            check_character_limits(
                "short_description",
                short_desc,
                LIMITS["android"]["short_description"],
            )
        )
    if description:
        results["character_checks"].append(
            check_character_limits(
                "description", description, LIMITS["android"]["description"]
            )
        )

    combined = "{} {} {}".format(title or "", short_desc or "", description or "")
    results["keyword_warnings"] = check_keyword_stuffing(combined)

    if description:
        results["readability"] = readability_score(description)

    for check in results["character_checks"]:
        if check["status"] == "OVER":
            results["overall_status"] = "FAIL"
            results["issues"].append(
                "{} exceeds limit by {} characters".format(
                    check["field"], abs(check["remaining"])
                )
            )

    if results["keyword_warnings"]:
        results["issues"].append(
            "{} keyword(s) appear excessively".format(
                len(results["keyword_warnings"])
            )
        )

    return results


def format_result(result):
    """Format validation result as human-readable text."""
    lines = [
        "Platform: {}".format(result["platform"]),
        "Overall:  {}".format(result["overall_status"]),
        "",
        "Character Limits:",
    ]

    for check in result["character_checks"]:
        status_indicator = "PASS" if check["status"] == "PASS" else "OVER"
        lines.append(
            "  {:20s} {:4d} / {:4d}  [{}]  ({:+d} remaining)".format(
                check["field"],
                check["length"],
                check["limit"],
                status_indicator,
                check["remaining"],
            )
        )

    if result["keyword_warnings"]:
        lines.append("")
        lines.append("Keyword Stuffing Warnings:")
        for w in result["keyword_warnings"]:
            lines.append("  - {}".format(w["warning"]))

    if result.get("readability"):
        r = result["readability"]
        lines.append("")
        lines.append("Readability:")
        lines.append(
            "  Score:        {}/100 ({})".format(r["score"], r["assessment"])
        )
        lines.append("  Total words:  {}".format(r["total_words"]))
        lines.append(
            "  Simple words: {} ({:.1%})".format(r["simple_words"], r["ratio"])
        )

    if result["issues"]:
        lines.append("")
        lines.append("Issues:")
        for issue in result["issues"]:
            lines.append("  - {}".format(issue))

    return "\n".join(lines)


def main():
    """Entry point for app store metadata validation CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate app store metadata against platform character limits "
            "and quality rules."
        ),
    )
    parser.add_argument(
        "--title",
        type=str,
        default="",
        help="App title",
    )
    parser.add_argument(
        "--subtitle",
        type=str,
        default="",
        help="App subtitle (iOS only)",
    )
    parser.add_argument(
        "--short-desc",
        type=str,
        default="",
        dest="short_desc",
        help="Short description (Android only)",
    )
    parser.add_argument(
        "--description",
        type=str,
        default="",
        help="Full app description",
    )
    parser.add_argument(
        "--platform",
        type=str,
        required=True,
        choices=["ios", "android"],
        help="Target platform: ios or android",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    if not any([args.title, args.subtitle, args.short_desc, args.description]):
        parser.error(
            "Provide at least one metadata field "
            "(--title, --subtitle, --short-desc, --description)."
        )

    if args.platform == "ios":
        result = validate_ios(args.title, args.subtitle, args.description)
    else:
        result = validate_android(
            args.title, args.short_desc, args.description
        )

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        print(format_result(result))

    if result["overall_status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
