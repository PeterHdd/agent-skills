#!/usr/bin/env python3
"""Format image generation prompts for specific AI platforms.

Reformats a base prompt with platform-specific syntax for Midjourney,
DALL-E, Stable Diffusion, and Flux.
"""

import argparse
import json
import sys
import textwrap


PLATFORMS = ["midjourney", "dalle", "sd", "flux"]

MIDJOURNEY_DEFAULTS = {
    "ar": "16:9",
    "version": "6.1",
    "style": "raw",
    "quality": "1",
}

DALLE_MAX_LENGTH = 4000

SD_DEFAULT_NEGATIVE = "(blurry:1.2), text, watermark, oversaturated, cartoon, illustration, deformed, disfigured, bad anatomy, extra limbs"


def format_midjourney(prompt: str, ar: str = None, version: str = None,
                      style: str = None, no: str = None, quality: str = None,
                      stylize: str = None) -> dict:
    """Format prompt for Midjourney with appended parameters."""
    ar = ar or MIDJOURNEY_DEFAULTS["ar"]
    version = version or MIDJOURNEY_DEFAULTS["version"]
    style = style or MIDJOURNEY_DEFAULTS["style"]
    quality = quality or MIDJOURNEY_DEFAULTS["quality"]

    params = [
        f"--ar {ar}",
        f"--v {version}",
        f"--style {style}",
        f"--q {quality}",
    ]
    if stylize:
        params.append(f"--s {stylize}")
    if no:
        params.append(f"--no {no}")
    else:
        params.append("--no text, watermark, illustration")

    formatted = f"{prompt.strip()} {' '.join(params)}"

    return {
        "platform": "Midjourney",
        "formatted_prompt": formatted,
        "notes": [
            f"Aspect ratio: {ar}",
            f"Version: {version}",
            f"Style: {style}",
            "Use ::2 weighting on critical terms to emphasize (e.g., 'cinematic lighting::2')",
            "Paste directly into /imagine prompt in Discord",
        ],
    }


def format_dalle(prompt: str) -> dict:
    """Format prompt for DALL-E (natural language, front-loaded)."""
    # DALL-E works best with natural language paragraphs
    sentences = [s.strip() for s in prompt.replace("\n", " ").split(".") if s.strip()]

    # Front-load: keep the first sentence as-is, wrap the rest into a paragraph
    if len(sentences) > 1:
        formatted = ". ".join(sentences) + "."
    else:
        formatted = prompt.strip()

    # Ensure aspect ratio is described in natural language if not present
    ar_words = ["landscape", "portrait", "square", "wide", "tall", "panoramic"]
    has_ar = any(w in formatted.lower() for w in ar_words)
    if not has_ar:
        formatted += " Wide landscape format."

    truncated = False
    if len(formatted) > DALLE_MAX_LENGTH:
        formatted = formatted[:DALLE_MAX_LENGTH - 3] + "..."
        truncated = True

    notes = [
        f"Character count: {len(formatted)} / {DALLE_MAX_LENGTH}",
        "DALL-E parses natural language prose better than comma-separated tokens",
        "The most important visual element should be in the first sentence",
    ]
    if truncated:
        notes.append("WARNING: Prompt was truncated to fit DALL-E's max length")

    return {
        "platform": "DALL-E",
        "formatted_prompt": formatted,
        "notes": notes,
    }


def format_sd(prompt: str, negative: str = None) -> dict:
    """Format prompt for Stable Diffusion with weighted syntax."""
    # Convert key descriptive phrases to weighted syntax
    # Split by commas to identify distinct prompt segments
    segments = [s.strip() for s in prompt.split(",")]

    weighted_segments = []
    for i, seg in enumerate(segments):
        if not seg:
            continue
        # First segment (subject) gets highest weight
        if i == 0:
            weighted_segments.append(f"({seg}:1.2)")
        # Lighting and camera terms get moderate emphasis
        elif any(kw in seg.lower() for kw in ["lighting", "light", "illuminat", "lens", "f/", "aperture", "depth of field", "bokeh"]):
            weighted_segments.append(f"({seg}:1.1)")
        else:
            weighted_segments.append(seg)

    formatted = ", ".join(weighted_segments)
    neg = negative or SD_DEFAULT_NEGATIVE

    return {
        "platform": "Stable Diffusion",
        "formatted_prompt": formatted,
        "negative_prompt": neg,
        "notes": [
            "Positive and negative prompts should be entered in separate fields",
            "Weights range from 0.1 to 2.0; default is 1.0",
            "Subject weighted at 1.2, lighting/camera terms at 1.1",
            "Adjust weights based on generation results",
            "Consider specifying model checkpoint (e.g., Realistic Vision v5.1)",
        ],
    }


def format_flux(prompt: str) -> dict:
    """Format prompt for Flux with detailed natural language."""
    # Flux excels with long, detailed paragraphs
    # Ensure the prompt is sufficiently descriptive
    formatted = prompt.strip()

    # Add photorealistic detail hints if not present
    detail_keywords = ["texture", "detail", "resolution", "8k", "4k", "ultra", "photorealistic", "realistic"]
    has_detail = any(kw in formatted.lower() for kw in detail_keywords)
    if not has_detail:
        formatted += " Ultra high resolution, 8K detail, photorealistic rendering with fine skin texture, fabric weave detail, and accurate material reflections."

    return {
        "platform": "Flux",
        "formatted_prompt": formatted,
        "notes": [
            "Flux excels with long, detailed natural language descriptions",
            "Emphasize photorealistic details: skin texture, fabric weave, material reflections",
            "Resolution intent is specified for best results",
            "No special syntax needed -- descriptive prose works best",
        ],
    }


def format_result_text(result: dict) -> str:
    """Format a result dict as human-readable text."""
    lines = [
        f"Platform: {result['platform']}",
        "",
        "--- Formatted Prompt ---",
        result["formatted_prompt"],
        "",
    ]

    if "negative_prompt" in result:
        lines.extend([
            "--- Negative Prompt ---",
            result["negative_prompt"],
            "",
        ])

    lines.append("--- Notes ---")
    for note in result["notes"]:
        lines.append(f"  - {note}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Format image generation prompts for specific AI platforms (Midjourney, DALL-E, SD, Flux)."
    )
    parser.add_argument(
        "prompt",
        type=str,
        help="Base prompt text to format",
    )
    parser.add_argument(
        "--platform",
        type=str,
        required=True,
        choices=PLATFORMS,
        help="Target platform: midjourney, dalle, sd, flux",
    )
    parser.add_argument(
        "--ar",
        type=str,
        default=None,
        help="Aspect ratio (Midjourney only, e.g., '16:9', '1:1', '9:16')",
    )
    parser.add_argument(
        "--negative",
        type=str,
        default=None,
        help="Custom negative prompt (Stable Diffusion only)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output result as JSON",
    )

    args = parser.parse_args()

    if not args.prompt.strip():
        print("Error: Prompt text cannot be empty.", file=sys.stderr)
        sys.exit(1)

    platform = args.platform.lower()

    if platform == "midjourney":
        result = format_midjourney(args.prompt, ar=args.ar)
    elif platform == "dalle":
        result = format_dalle(args.prompt)
    elif platform == "sd":
        result = format_sd(args.prompt, negative=args.negative)
    elif platform == "flux":
        result = format_flux(args.prompt)
    else:
        print(f"Error: Unknown platform '{args.platform}'.", file=sys.stderr)
        sys.exit(1)

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        print(format_result_text(result))


if __name__ == "__main__":
    main()
