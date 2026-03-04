---
name: design-image-prompt-engineer
description: "Craft precise, structured prompts for AI image generation grounded in real photography technique. Use when you need prompts for Midjourney, DALL-E, Stable Diffusion, or Flux, including lighting direction, lens selection, depth of field, composition, negative prompts, style references, or platform-specific syntax optimization for professional-quality AI-generated images."
metadata:
  version: "1.0.0"
---

# Image Prompt Engineering Guide

## Overview

This guide covers how to translate visual concepts into precise, structured prompts for AI image generation platforms. It bridges real photography knowledge (lens selection, lighting setups, composition) with platform-specific syntax for Midjourney, DALL-E, Stable Diffusion, and Flux.

## The Five-Layer Framework

Every prompt should address these five layers in order:

1. **Subject**: Who/what, specific attributes, pose, expression, materials, textures.
2. **Environment**: Location, background treatment, atmospheric conditions, time of day.
3. **Lighting**: Source type, direction, quality (hard/soft), color temperature.
4. **Camera**: Focal length, aperture, angle, depth of field, exposure style.
5. **Style**: Genre, era, post-processing, color grade, reference photographer.

Use correct photography terminology throughout: "shallow depth of field, f/1.8 bokeh" not "blurry background." Keep lighting direction consistent with shadow descriptions within the same prompt. Include negative prompts when the platform supports them to exclude unwanted artifacts.

When a requested effect is physically implausible in real photography, flag it and suggest a plausible alternative.

### How to Build a Prompt

1. **Brief intake** -- Clarify the visual goal, intended use (web hero, social, print), and target platform. Identify any reference images and deconstruct them into the five layers. Determine aspect ratio and resolution requirements.
2. **Layer-by-layer construction** -- Build the prompt in order: subject, environment, lighting, camera, style. Verify lighting direction is consistent with described shadows. Add platform-specific parameters and negative prompts.
3. **Iteration** -- If results miss the target, identify which layer is weakest and add specificity there. Adjust keyword weighting rather than adding more keywords. Log successful prompt patterns for reuse across the campaign.

### Working from a Reference Image

When a client provides a reference image, deconstruct it into the five layers before writing the prompt. Identify which layer creates the "feel" they want and weight that layer most heavily.

### Generating Campaign Sets

When generating a set of images for a campaign, lock the lighting setup, color palette, and camera angle across all prompts to ensure visual cohesion.

### Handling the Unknown Platform Case

When the target platform is unknown, write for Midjourney syntax first (most widely used) and note adaptation instructions for other platforms.

## Platform-Specific Syntax

### Midjourney
- Append parameters: `--ar 16:9 --v 6.1 --style raw` for photorealism.
- Use `::2` weighting to emphasize critical layers (e.g., `cinematic lighting::2`).
- Add `--no text, watermark, illustration` as negative prompt.

### DALL-E
- Write in natural language paragraphs; DALL-E parses prose better than pipe-separated tokens.
- Front-load the most important visual element in the first sentence.
- Avoid parameter syntax; describe aspect ratio as "wide landscape format."

### Stable Diffusion
- Use parenthetical weighting: `(shallow depth of field:1.3)`.
- Negative prompt field: `(blurry:1.2), text, watermark, oversaturated, cartoon, illustration`.
- Specify model checkpoint if known (e.g., "optimized for Realistic Vision v5.1").

### Flux
- Use detailed natural language; Flux excels with long descriptive paragraphs.
- Emphasize photorealistic details: skin texture, fabric weave, material reflections.
- Specify resolution intent: "ultra high resolution, 8K detail."

## Reference

### Prompt Quality Checklist

- All five layers (subject, environment, lighting, camera, style) are explicitly addressed.
- Photography terms are technically accurate (correct aperture-to-depth-of-field relationship, consistent light-shadow geometry).
- Platform-specific syntax is correct for the target platform (valid Midjourney parameters, proper SD weighting format).
- An aspect ratio is specified.
- A photographer reading the prompt could identify the lighting setup and camera settings without ambiguity.

## Scripts

The following script is available in the `scripts/` directory for prompt formatting:

### `scripts/format_prompt.py`
Reformats a base prompt with platform-specific syntax for Midjourney, DALL-E, Stable Diffusion, or Flux. Adds appropriate parameters, weighting syntax, and negative prompts per platform.
```
python scripts/format_prompt.py "portrait of a woman in golden hour light" --platform midjourney
python scripts/format_prompt.py "product shot of a watch on marble" --platform sd --json
python scripts/format_prompt.py "modern office workspace" --platform dalle
python scripts/format_prompt.py "landscape with mountains at sunset" --platform flux
```

See [Worked Prompts](references/worked-prompts.md) for full portrait, product, and lifestyle prompt examples with explanations of why each works.
