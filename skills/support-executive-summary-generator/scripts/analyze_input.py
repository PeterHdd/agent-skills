#!/usr/bin/env python3
"""analyze_input.py — Analyze a text or markdown file for executive summary generation.

Extracts word count, reading time, key metrics, named entities, section headings,
and identifies the most important sentences to support writing an executive summary.
"""

import argparse
import json
import math
import os
import re
import sys
from collections import Counter


# Business keywords that boost sentence importance
IMPORTANCE_KEYWORDS = [
    "revenue",
    "profit",
    "loss",
    "growth",
    "decline",
    "increase",
    "decrease",
    "risk",
    "opportunity",
    "critical",
    "strategic",
    "impact",
    "recommend",
    "action",
    "decision",
    "priority",
    "budget",
    "cost",
    "savings",
    "market",
    "share",
    "customer",
    "performance",
    "target",
    "goal",
    "deadline",
    "milestone",
    "roi",
    "kpi",
    "quarter",
    "annual",
    "forecast",
    "trend",
    "competitive",
    "advantage",
    "threat",
    "stakeholder",
    "investment",
    "efficiency",
    "scalability",
    "compliance",
    "regulation",
]


def read_file(filepath):
    """Read a file and return its content."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERROR: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"ERROR: File is not valid UTF-8 text: {filepath}", file=sys.stderr)
        sys.exit(1)


def strip_markdown(text):
    """Remove markdown formatting for plain text analysis."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    # Remove links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    # Remove heading markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove blockquote markers
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    return text


def count_words(text):
    """Count words in text."""
    words = re.findall(r"\b\w+\b", text)
    return len(words)


def estimate_reading_time(word_count, wpm=200):
    """Estimate reading time in minutes (average 200 WPM for business text)."""
    return max(1, math.ceil(word_count / wpm))


def extract_headings(content):
    """Extract markdown headings with their levels."""
    headings = []
    for line in content.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append({"level": level, "text": text})
    return headings


def extract_metrics(text):
    """Extract numbers with their surrounding context (key metrics)."""
    metrics = []

    # Patterns: percentages, dollar amounts, large numbers with context
    patterns = [
        (r"(\$[\d,.]+\s*(?:million|billion|trillion|[MBT]|k)?)", "currency"),
        (r"([\d,.]+%)", "percentage"),
        (r"([\d,.]+x)", "multiplier"),
        (r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?)", "large_number"),
    ]

    for pattern, metric_type in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(1)
            # Get surrounding context (up to 60 chars each side)
            start = max(0, match.start() - 60)
            end = min(len(text), match.end() + 60)
            context = text[start:end].strip()
            # Clean up context to sentence-like boundaries
            context = re.sub(r"^\S*\s", "", context)
            context = re.sub(r"\s\S*$", "", context)

            metrics.append(
                {"value": value, "type": metric_type, "context": context}
            )

    # Deduplicate by value
    seen = set()
    unique_metrics = []
    for m in metrics:
        if m["value"] not in seen:
            seen.add(m["value"])
            unique_metrics.append(m)

    return unique_metrics[:20]  # Cap at 20 to keep output manageable


def extract_named_entities(text):
    """Extract likely named entities using regex heuristics.

    Looks for capitalized multi-word phrases that are likely proper nouns.
    """
    entities = Counter()

    # Multi-word capitalized phrases (2-4 words)
    multi_word = re.findall(
        r"\b([A-Z][a-z]+(?:\s+(?:[A-Z][a-z]+|&|of|the|and|for)){1,3})\b", text
    )
    for entity in multi_word:
        # Filter out sentence starters by checking if preceded by period/newline
        entities[entity] += 1

    # Acronyms (2-6 uppercase letters)
    acronyms = re.findall(r"\b([A-Z]{2,6})\b", text)
    for acr in acronyms:
        # Filter common non-entity acronyms
        if acr not in {"THE", "AND", "FOR", "BUT", "NOT", "ARE", "WAS", "HAS", "ITS"}:
            entities[acr] += 1

    # Return most common, filtering out likely false positives
    result = []
    for entity, count in entities.most_common(20):
        if count >= 1 and len(entity) > 1:
            result.append({"entity": entity, "count": count})

    return result


def score_sentences(text, total_sentences):
    """Score sentences by importance using keyword density and position."""
    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if not sentences:
        return []

    scored = []
    for i, sentence in enumerate(sentences):
        score = 0.0
        lower = sentence.lower()

        # Keyword density scoring
        keyword_count = 0
        for keyword in IMPORTANCE_KEYWORDS:
            if keyword in lower:
                keyword_count += 1
        word_count = len(sentence.split())
        if word_count > 0:
            score += (keyword_count / word_count) * 10

        # Bonus for containing numbers/metrics (quantified statements)
        if re.search(r"\d+", sentence):
            score += 2.0

        # Bonus for containing percentage or currency
        if re.search(r"[\d,.]+%|\$[\d,.]+", sentence):
            score += 3.0

        # Position scoring: first and last sentences of sections tend to be important
        position_ratio = i / max(len(sentences) - 1, 1)
        if position_ratio < 0.1:  # First 10% of text
            score += 2.0
        elif position_ratio > 0.85:  # Last 15%
            score += 1.5

        # Penalty for very short or very long sentences
        if word_count < 5:
            score -= 2.0
        elif word_count > 50:
            score -= 1.0

        # Bonus for action-oriented language
        action_words = [
            "recommend",
            "should",
            "must",
            "need",
            "require",
            "action",
            "implement",
            "launch",
            "deploy",
            "invest",
        ]
        for word in action_words:
            if word in lower:
                score += 1.5
                break

        scored.append(
            {
                "text": sentence[:300],  # Cap length for readability
                "score": round(score, 2),
                "position": i + 1,
                "word_count": word_count,
            }
        )

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:5]


def output_text(analysis):
    """Output the analysis in structured text format."""
    print("=== INPUT ANALYSIS ===")
    print()
    print(f"source: {analysis['source']}")
    print(f"word_count: {analysis['word_count']}")
    print(f"reading_time_minutes: {analysis['reading_time_minutes']}")
    print(f"sentence_count: {analysis['sentence_count']}")
    print(f"paragraph_count: {analysis['paragraph_count']}")
    print()

    # Headings
    print("--- Document Structure ---")
    if analysis["headings"]:
        for h in analysis["headings"]:
            indent = "  " * (h["level"] - 1)
            print(f"  {indent}{'#' * h['level']} {h['text']}")
    else:
        print("  (no headings found)")
    print()

    # Key metrics
    print(f"--- Key Metrics ({len(analysis['metrics'])} found) ---")
    for m in analysis["metrics"]:
        print(f"  [{m['type']}] {m['value']}")
        print(f"    context: ...{m['context']}...")
    print()

    # Named entities
    print(f"--- Named Entities ({len(analysis['entities'])} found) ---")
    for e in analysis["entities"]:
        print(f"  {e['entity']} (mentioned {e['count']}x)")
    print()

    # Top sentences
    print("--- Top 5 Important Sentences ---")
    for i, s in enumerate(analysis["top_sentences"], 1):
        print(f"  {i}. [score={s['score']}, position={s['position']}]")
        print(f"     {s['text']}")
    print()

    print("=== END ANALYSIS ===")


def output_json(analysis):
    """Output the analysis in JSON format."""
    print(json.dumps(analysis, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a text or markdown file for executive summary generation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
The analysis extracts:
  - Word count and estimated reading time
  - Document structure (headings)
  - Key metrics (numbers with context)
  - Named entities (capitalized phrases, acronyms)
  - Top 5 most important sentences (by keyword density + position)

examples:
  %(prog)s report.md
  %(prog)s --format json quarterly-review.txt
  %(prog)s --format json report.md | jq '.top_sentences'
        """,
    )
    parser.add_argument(
        "input_file",
        help="Path to a text or markdown file to analyze",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        print(f"ERROR: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    content = read_file(args.input_file)
    plain_text = strip_markdown(content)

    word_count = count_words(plain_text)
    sentences = re.split(r"(?<=[.!?])\s+", plain_text)
    sentences = [s for s in sentences if len(s.strip()) > 0]
    paragraphs = [p for p in plain_text.split("\n\n") if p.strip()]

    analysis = {
        "source": args.input_file,
        "word_count": word_count,
        "reading_time_minutes": estimate_reading_time(word_count),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "headings": extract_headings(content),
        "metrics": extract_metrics(plain_text),
        "entities": extract_named_entities(plain_text),
        "top_sentences": score_sentences(plain_text, len(sentences)),
    }

    if args.format == "json":
        output_json(analysis)
    else:
        output_text(analysis)


if __name__ == "__main__":
    main()
