#!/usr/bin/env python3
"""
estimate_gpu_memory.py -- Estimate GPU VRAM requirements for ML model inference and training.

Takes a model name (with known parameter counts) or an explicit parameter count,
plus a target precision, and outputs:
  - Estimated VRAM for inference
  - Estimated VRAM for training (with optimizer states, gradients, activations)
  - Recommended GPU

Self-contained: uses only stdlib + argparse. Outputs markdown.
"""

import argparse
import math
import sys

# Known model parameter counts (in billions)
KNOWN_MODELS = {
    # Encoder models
    "bert-base": 0.110,
    "bert-large": 0.340,
    "roberta-base": 0.125,
    "roberta-large": 0.355,
    "distilbert": 0.066,
    "deberta-v3-base": 0.184,
    "deberta-v3-large": 0.434,
    # Decoder models
    "gpt2": 0.124,
    "gpt2-medium": 0.355,
    "gpt2-large": 0.774,
    "gpt2-xl": 1.5,
    "llama-2-7b": 7.0,
    "llama-2-13b": 13.0,
    "llama-2-70b": 70.0,
    "llama-3-8b": 8.0,
    "llama-3-70b": 70.0,
    "llama-3.1-8b": 8.0,
    "llama-3.1-70b": 70.0,
    "llama-3.1-405b": 405.0,
    "mistral-7b": 7.3,
    "mixtral-8x7b": 46.7,
    "mixtral-8x22b": 141.0,
    "phi-2": 2.7,
    "phi-3-mini": 3.8,
    "phi-3-medium": 14.0,
    "gemma-2b": 2.5,
    "gemma-7b": 8.5,
    "qwen-2-7b": 7.6,
    "qwen-2-72b": 72.7,
    # Encoder-decoder models
    "t5-small": 0.060,
    "t5-base": 0.220,
    "t5-large": 0.770,
    "t5-xl": 3.0,
    "t5-xxl": 11.0,
    "flan-t5-base": 0.250,
    "flan-t5-large": 0.780,
    "flan-t5-xl": 3.0,
    "bart-base": 0.140,
    "bart-large": 0.400,
    # Vision
    "clip-vit-base": 0.150,
    "clip-vit-large": 0.430,
    # Audio
    "whisper-tiny": 0.039,
    "whisper-base": 0.074,
    "whisper-small": 0.244,
    "whisper-medium": 0.769,
    "whisper-large": 1.55,
}

# Bytes per parameter by precision
BYTES_PER_PARAM = {
    "fp32": 4,
    "fp16": 2,
    "bf16": 2,
    "int8": 1,
    "int4": 0.5,
}

# GPU catalog: name -> VRAM in GB
GPU_CATALOG = [
    ("T4", 16),
    ("RTX 3090", 24),
    ("RTX 4090", 24),
    ("A10G", 24),
    ("L4", 24),
    ("A100 40GB", 40),
    ("A100 80GB", 80),
    ("H100 80GB", 80),
    ("H100 NVL (2x)", 188),
    ("8x A100 80GB", 640),
    ("8x H100 80GB", 640),
]


def estimate_inference_vram(params_billions, precision):
    """
    Inference VRAM = model weights + KV cache overhead + framework overhead.
    KV cache and framework overhead estimated at ~20% of model weights.
    """
    params = params_billions * 1e9
    bytes_per_param = BYTES_PER_PARAM[precision]
    model_size_bytes = params * bytes_per_param
    # Add 20% for KV cache, activations, and framework overhead
    total_bytes = model_size_bytes * 1.2
    total_gb = total_bytes / (1024 ** 3)
    return total_gb


def estimate_training_vram(params_billions, precision, optimizer="adam"):
    """
    Training VRAM breakdown:
    - Model weights: params * bytes_per_param
    - Gradients: params * bytes_per_param (same precision as weights)
    - Optimizer states (Adam): params * 8 bytes (fp32 momentum + variance)
    - Activations: ~estimated as 1.0-1.5x model weights (depends on batch size, seq len)
    - Framework overhead: ~10%

    Rule of thumb: training ~= 4x inference for Adam optimizer in fp16/bf16.
    For fp32: training ~= 4x inference.
    For QLoRA: only trainable params need gradients/optimizer.
    """
    params = params_billions * 1e9
    bytes_per_param = BYTES_PER_PARAM[precision]

    model_weights_bytes = params * bytes_per_param

    if precision in ("int4", "int8"):
        # QLoRA-style: model in low precision, trainable adapter in fp16
        # Assume ~0.06% of params are trainable (LoRA r=16)
        trainable_ratio = 0.0006
        trainable_params = params * trainable_ratio
        gradients_bytes = trainable_params * 2  # fp16 gradients
        optimizer_bytes = trainable_params * 8  # Adam fp32 states
        activations_bytes = model_weights_bytes * 0.5  # Lower due to checkpointing
    else:
        gradients_bytes = params * bytes_per_param
        optimizer_bytes = params * 8  # Adam stores 2x fp32 copies
        activations_bytes = model_weights_bytes * 1.2

    total_bytes = model_weights_bytes + gradients_bytes + optimizer_bytes + activations_bytes
    # Framework overhead
    total_bytes *= 1.1
    total_gb = total_bytes / (1024 ** 3)
    return total_gb


def recommend_gpu(vram_gb):
    """Recommend the smallest GPU that fits the requirement."""
    recommendations = []
    for name, capacity in GPU_CATALOG:
        if capacity >= vram_gb:
            recommendations.append((name, capacity))
            break
    if not recommendations:
        # Need multi-GPU
        for name, capacity in GPU_CATALOG:
            if capacity >= vram_gb:
                recommendations.append((name, capacity))
                break
        if not recommendations:
            return "Requires custom multi-node setup"
    return recommendations[0]


def format_size(gb):
    """Format GB to a human-readable string."""
    if gb < 1:
        return f"{gb * 1024:.0f} MB"
    return f"{gb:.1f} GB"


def main():
    parser = argparse.ArgumentParser(
        description="Estimate GPU VRAM requirements for ML model inference and training.",
        epilog=(
            "Examples:\n"
            "  %(prog)s --model llama-2-7b --precision fp16\n"
            "  %(prog)s --params 13 --precision int4\n"
            "  %(prog)s --model mistral-7b --precision bf16\n"
            "  %(prog)s --list-models\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model name (see --list-models for known models)",
    )
    parser.add_argument(
        "--params",
        type=float,
        help="Number of parameters in billions (e.g., 7 for 7B)",
    )
    parser.add_argument(
        "--precision",
        type=str,
        choices=list(BYTES_PER_PARAM.keys()),
        default="fp16",
        help="Target precision (default: fp16)",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List all known models and their parameter counts",
    )
    args = parser.parse_args()

    if args.list_models:
        print("## Known Models\n")
        print("| Model | Parameters |")
        print("|---|---|")
        for name, params in sorted(KNOWN_MODELS.items(), key=lambda x: x[1]):
            if params >= 1.0:
                print(f"| {name} | {params:.1f}B |")
            else:
                print(f"| {name} | {params * 1000:.0f}M |")
        return

    if args.model and args.params:
        print("Error: Specify either --model or --params, not both.", file=sys.stderr)
        sys.exit(1)

    if not args.model and args.params is None:
        parser.print_help()
        sys.exit(1)

    if args.model:
        model_key = args.model.lower().strip()
        if model_key not in KNOWN_MODELS:
            print(f"Error: Unknown model '{args.model}'. Use --list-models to see known models.", file=sys.stderr)
            sys.exit(1)
        params_b = KNOWN_MODELS[model_key]
        model_display = args.model
    else:
        params_b = args.params
        model_display = f"Custom ({params_b}B params)"

    precision = args.precision

    inference_gb = estimate_inference_vram(params_b, precision)
    training_gb = estimate_training_vram(params_b, precision)

    inference_gpu = recommend_gpu(inference_gb)
    training_gpu = recommend_gpu(training_gb)

    # Output markdown
    print(f"## GPU Memory Estimate: {model_display}\n")
    print(f"| Property | Value |")
    print(f"|---|---|")
    print(f"| Model | {model_display} |")
    if params_b >= 1.0:
        print(f"| Parameters | {params_b:.1f}B |")
    else:
        print(f"| Parameters | {params_b * 1000:.0f}M |")
    print(f"| Precision | {precision} |")
    print(f"| Bytes per parameter | {BYTES_PER_PARAM[precision]} |")
    print()

    print("### Inference\n")
    print(f"| Metric | Value |")
    print(f"|---|---|")
    model_size_gb = (params_b * 1e9 * BYTES_PER_PARAM[precision]) / (1024 ** 3)
    print(f"| Model weights | {format_size(model_size_gb)} |")
    print(f"| Total VRAM (with overhead) | {format_size(inference_gb)} |")
    if isinstance(inference_gpu, tuple):
        print(f"| Recommended GPU | {inference_gpu[0]} ({inference_gpu[1]} GB) |")
    else:
        print(f"| Recommended GPU | {inference_gpu} |")
    print()

    print("### Training (Adam optimizer)\n")
    print(f"| Metric | Value |")
    print(f"|---|---|")
    print(f"| Total VRAM estimate | {format_size(training_gb)} |")
    if precision in ("int4", "int8"):
        print(f"| Training method | QLoRA (model in {precision}, adapter in fp16) |")
        trainable = params_b * 1e9 * 0.0006
        if trainable >= 1e6:
            print(f"| Trainable parameters | ~{trainable / 1e6:.1f}M (LoRA r=16) |")
        else:
            print(f"| Trainable parameters | ~{trainable / 1e3:.0f}K (LoRA r=16) |")
    else:
        print(f"| Training method | Full / LoRA in {precision} |")
    if isinstance(training_gpu, tuple):
        print(f"| Recommended GPU | {training_gpu[0]} ({training_gpu[1]} GB) |")
    else:
        print(f"| Recommended GPU | {training_gpu} |")
    print()

    # Comparison across precisions
    print("### Comparison Across Precisions\n")
    print("| Precision | Inference VRAM | Training VRAM |")
    print("|---|---|---|")
    for prec in ["fp32", "fp16", "bf16", "int8", "int4"]:
        inf = estimate_inference_vram(params_b, prec)
        trn = estimate_training_vram(params_b, prec)
        print(f"| {prec} | {format_size(inf)} | {format_size(trn)} |")

    print()
    print("*Note: Estimates are approximate. Actual VRAM depends on batch size, sequence length,")
    print("gradient checkpointing, and framework overhead. Training estimates assume Adam optimizer.*")


if __name__ == "__main__":
    main()
