#!/usr/bin/env python3
"""Analyze keyword density in app store descriptions or text content.

Extracts word frequencies, reports top 20 keywords, and flags potential
keyword stuffing (words exceeding 3% of total word count).
"""

import argparse
import json
import re
import sys
from collections import Counter


# Stop words excluded from keyword analysis
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
    "get", "got",
}


def extract_words(text):
    """Extract meaningful words from text, lowercased, excluding stop words."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def analyze_density(text, top_n=20, stuffing_threshold=3.0):
    """Analyze keyword density in the given text.

    Args:
        text: The text to analyze.
        top_n: Number of top keywords to report.
        stuffing_threshold: Percentage threshold above which a word is flagged.

    Returns:
        dict with analysis results.
    """
    all_words = re.findall(r"[a-zA-Z]+", text.lower())
    meaningful_words = extract_words(text)

    if not meaningful_words:
        return {
            "total_words": len(all_words),
            "meaningful_words": 0,
            "unique_keywords": 0,
            "top_keywords": [],
            "stuffing_warnings": [],
        }

    counts = Counter(meaningful_words)
    total = len(meaningful_words)

    top_keywords = []
    for word, count in counts.most_common(top_n):
        density = (count / total) * 100
        top_keywords.append({
            "keyword": word,
            "count": count,
            "density_pct": round(density, 2),
        })

    stuffing_warnings = []
    for word, count in counts.items():
        density = (count / total) * 100
        if density > stuffing_threshold:
            stuffing_warnings.append({
                "keyword": word,
                "count": count,
                "density_pct": round(density, 2),
                "warning": "'{}' at {:.1f}% density exceeds {}% threshold".format(
                    word, density, stuffing_threshold
                ),
            })

    # Sort warnings by density descending
    stuffing_warnings.sort(key=lambda x: x["density_pct"], reverse=True)

    return {
        "total_words": len(all_words),
        "meaningful_words": total,
        "unique_keywords": len(counts),
        "top_keywords": top_keywords,
        "stuffing_warnings": stuffing_warnings,
    }


def format_result(result):
    """Format analysis result as human-readable text."""
    lines = [
        "Keyword Density Analysis",
        "========================",
        "",
        "Total words (all):        {}".format(result["total_words"]),
        "Meaningful words:         {}".format(result["meaningful_words"]),
        "Unique keywords:          {}".format(result["unique_keywords"]),
        "",
        "Top {} Keywords:".format(len(result["top_keywords"])),
        "  {:<20s} {:>6s} {:>8s}".format("Keyword", "Count", "Density"),
        "  {} {} {}".format("-" * 20, "-" * 6, "-" * 8),
    ]

    for kw in result["top_keywords"]:
        lines.append(
            "  {:<20s} {:>6d} {:>7.2f}%".format(
                kw["keyword"], kw["count"], kw["density_pct"]
            )
        )

    if result["stuffing_warnings"]:
        lines.append("")
        lines.append("Keyword Stuffing Warnings (> 3% density):")
        for w in result["stuffing_warnings"]:
            lines.append("  - {}".format(w["warning"]))
    else:
        lines.append("")
        lines.append("No keyword stuffing detected.")

    return "\n".join(lines)


def main():
    """Entry point for keyword density analysis CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyze keyword density in text content. "
            "Reports top keywords and flags potential stuffing."
        ),
    )
    parser.add_argument(
        "--text",
        type=str,
        default=None,
        help="Text string to analyze",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to a text file to analyze",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top keywords to report (default: 20)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=3.0,
        help="Keyword stuffing threshold as percentage (default: 3.0)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    if not args.text and not args.file:
        parser.error("Provide either --text or --file.")

    text = None
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                text = fh.read()
        except FileNotFoundError:
            print(
                "Error: File not found: {}".format(args.file), file=sys.stderr
            )
            sys.exit(1)
        except IOError as exc:
            print("Error reading file: {}".format(exc), file=sys.stderr)
            sys.exit(1)
    else:
        text = args.text

    if not text or not text.strip():
        print("Error: Input text is empty.", file=sys.stderr)
        sys.exit(1)

    result = analyze_density(
        text, top_n=args.top, stuffing_threshold=args.threshold
    )

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        print(format_result(result))

    # Exit with non-zero if stuffing detected
    if result["stuffing_warnings"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
