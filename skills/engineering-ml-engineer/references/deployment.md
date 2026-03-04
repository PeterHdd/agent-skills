# Model Deployment Patterns

Production-grade patterns for exporting, optimizing, serving, and monitoring ML models.

## ONNX Export with Optimum

```python
from optimum.onnxruntime import ORTModelForSequenceClassification, ORTQuantizer
from optimum.onnxruntime.configuration import AutoQuantizationConfig
from transformers import AutoTokenizer

# Export a HuggingFace model to ONNX
model_id = "distilbert-base-uncased-finetuned-sst-2-english"

# Method 1: Export directly using Optimum
ort_model = ORTModelForSequenceClassification.from_pretrained(
    model_id,
    export=True,  # Triggers ONNX export
)
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Save ONNX model
ort_model.save_pretrained("./onnx_model")
tokenizer.save_pretrained("./onnx_model")

# Method 2: Export via CLI
# optimum-cli export onnx --model distilbert-base-uncased-finetuned-sst-2-english ./onnx_model

# Quantize the ONNX model (INT8 dynamic quantization)
quantizer = ORTQuantizer.from_pretrained(ort_model)
quantization_config = AutoQuantizationConfig.avx512_vnni(
    is_static=False,  # Dynamic quantization -- no calibration data needed
    per_channel=True,
)
quantizer.quantize(
    save_dir="./onnx_model_quantized",
    quantization_config=quantization_config,
)

# Inference with ONNX Runtime
from optimum.onnxruntime import ORTModelForSequenceClassification

quantized_model = ORTModelForSequenceClassification.from_pretrained("./onnx_model_quantized")
tokenizer = AutoTokenizer.from_pretrained("./onnx_model_quantized")

inputs = tokenizer("This movie was amazing!", return_tensors="pt")
outputs = quantized_model(**inputs)
predicted_class = outputs.logits.argmax(dim=-1).item()

# ONNX Runtime with custom session options
import onnxruntime as ort

session_options = ort.SessionOptions()
session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
session_options.intra_op_num_threads = 4
session_options.inter_op_num_threads = 1
session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

session = ort.InferenceSession(
    "./onnx_model/model.onnx",
    sess_options=session_options,
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
)

inputs = tokenizer("Great product!", return_tensors="np")
outputs = session.run(None, dict(inputs))
```

## Quantization Methods

### bitsandbytes (INT8/INT4) -- For GPU Inference

```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
import torch

# INT8 quantization -- 2x memory reduction, <1% accuracy loss
model_int8 = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    load_in_8bit=True,
    device_map="auto",
)

# INT4 quantization -- 4x memory reduction, 1-3% accuracy loss
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)
model_int4 = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantization_config=bnb_config,
    device_map="auto",
)
```

### GPTQ -- For Offline Quantization + Fast GPU Inference

```python
from transformers import AutoModelForCausalLM, GPTQConfig, AutoTokenizer

# Quantize a model with GPTQ (requires calibration dataset)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")

gptq_config = GPTQConfig(
    bits=4,
    dataset="c4",              # Calibration dataset
    tokenizer=tokenizer,
    group_size=128,            # Quantization group size
    desc_act=True,             # Activation order (slower but better quality)
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantization_config=gptq_config,
    device_map="auto",
)

model.save_pretrained("./llama-7b-gptq")
tokenizer.save_pretrained("./llama-7b-gptq")

# Load pre-quantized GPTQ model (many available on HuggingFace Hub)
model = AutoModelForCausalLM.from_pretrained(
    "TheBloke/Llama-2-7B-GPTQ",
    device_map="auto",
)
```

### AWQ -- For Fast GPU Inference (Activation-Aware)

```python
from transformers import AutoModelForCausalLM, AwqConfig

# Load pre-quantized AWQ model
model = AutoModelForCausalLM.from_pretrained(
    "TheBloke/Llama-2-7B-AWQ",
    device_map="auto",
)

# Quantize with AWQ (requires autoawq library)
from awq import AutoAWQForCausalLM

model = AutoAWQForCausalLM.from_pretrained("meta-llama/Llama-2-7b-hf")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")

quant_config = {
    "zero_point": True,
    "q_group_size": 128,
    "w_bit": 4,
    "version": "GEMM",       # GEMM for batched, GEMV for single-sequence
}

model.quantize(tokenizer, quant_config=quant_config)
model.save_quantized("./llama-7b-awq")
```

### When to Use Each Quantization Method

| Method | Best For | Speed | Quality | Requires |
|---|---|---|---|---|
| bitsandbytes INT8 | Quick inference, fine-tuning base | Medium | Highest | GPU only |
| bitsandbytes INT4 | QLoRA training, memory-constrained | Slow | Good | GPU only |
| GPTQ | Production inference, offline prep | Fast | Very good | Calibration data |
| AWQ | Production inference, batched serving | Fastest | Very good | Calibration data |

## vLLM Serving

```python
# Install: pip install vllm

# Basic server launch (CLI)
# python -m vllm.entrypoints.openai.api_server \
#     --model meta-llama/Llama-2-7b-chat-hf \
#     --dtype bfloat16 \
#     --max-model-len 4096 \
#     --gpu-memory-utilization 0.9 \
#     --tensor-parallel-size 1 \
#     --port 8000

# Python API for batched inference
from vllm import LLM, SamplingParams

llm = LLM(
    model="meta-llama/Llama-2-7b-chat-hf",
    dtype="bfloat16",
    max_model_len=4096,
    gpu_memory_utilization=0.9,
    tensor_parallel_size=1,      # Number of GPUs for tensor parallelism
)

sampling_params = SamplingParams(
    temperature=0.7,
    top_p=0.9,
    max_tokens=512,
    repetition_penalty=1.1,
    stop=["</s>", "[INST]"],
)

# Batch inference -- vLLM handles continuous batching automatically
prompts = [
    "[INST] Explain machine learning. [/INST]",
    "[INST] What is gradient descent? [/INST]",
    "[INST] Describe neural networks. [/INST]",
]

outputs = llm.generate(prompts, sampling_params)
for output in outputs:
    print(output.outputs[0].text)

# Streaming with async engine
from vllm import AsyncLLMEngine, AsyncEngineArgs
import asyncio

engine_args = AsyncEngineArgs(
    model="meta-llama/Llama-2-7b-chat-hf",
    dtype="bfloat16",
    max_model_len=4096,
)
engine = AsyncLLMEngine.from_engine_args(engine_args)

async def stream_response(prompt):
    results_generator = engine.generate(prompt, sampling_params, request_id="req-1")
    async for request_output in results_generator:
        if request_output.finished:
            return request_output.outputs[0].text
```

## TorchServe Deployment

```python
# 1. Create model handler (handler.py)
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from ts.torch_handler.base_handler import BaseHandler
import json

class TransformerHandler(BaseHandler):
    def initialize(self, context):
        self.manifest = context.manifest
        properties = context.system_properties
        model_dir = properties.get("model_dir")

        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.eval()

        if torch.cuda.is_available():
            self.model = self.model.to("cuda")
        self.device = next(self.model.parameters()).device

    def preprocess(self, data):
        texts = [item.get("data") or item.get("body") for item in data]
        texts = [t.decode("utf-8") if isinstance(t, bytes) else t for t in texts]
        inputs = self.tokenizer(
            texts, padding=True, truncation=True, max_length=512, return_tensors="pt"
        )
        return {k: v.to(self.device) for k, v in inputs.items()}

    def inference(self, inputs):
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.logits

    def postprocess(self, outputs):
        probs = torch.nn.functional.softmax(outputs, dim=-1)
        predictions = torch.argmax(probs, dim=-1)
        results = []
        for pred, prob in zip(predictions, probs):
            results.append({
                "label": self.model.config.id2label[pred.item()],
                "score": prob[pred].item(),
            })
        return results

# 2. Package model archive
# torch-model-archiver \
#     --model-name sentiment \
#     --version 1.0 \
#     --serialized-file ./model/pytorch_model.bin \
#     --handler handler.py \
#     --extra-files "./model/config.json,./model/tokenizer.json,./model/vocab.txt" \
#     --export-path model_store

# 3. Serve
# torchserve --start --model-store model_store --models sentiment=sentiment.mar
# curl -X POST http://localhost:8080/predictions/sentiment -d "This is great!"
```

## Model Optimization

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    torch_dtype=torch.bfloat16,
    device_map="auto",
    attn_implementation="flash_attention_2",  # Flash Attention 2 for faster attention
)

# torch.compile for static graph optimization (PyTorch 2.0+)
model = torch.compile(model, mode="reduce-overhead")
# Modes: "default" (safe), "reduce-overhead" (faster, more memory), "max-autotune" (slowest compile, fastest run)

# KV Cache for efficient autoregressive generation
# Enabled by default in model.generate(), but for custom loops:
from transformers import DynamicCache

cache = DynamicCache()
input_ids = tokenizer("Hello", return_tensors="pt").input_ids.to(model.device)

for _ in range(100):
    with torch.no_grad():
        outputs = model(input_ids, past_key_values=cache, use_cache=True)
    next_token = outputs.logits[:, -1, :].argmax(dim=-1, keepdim=True)
    input_ids = next_token
    cache = outputs.past_key_values

# Static KV cache (fixed size, avoids reallocation)
from transformers import StaticCache

static_cache = StaticCache(
    config=model.config,
    max_batch_size=1,
    max_cache_len=2048,
    device=model.device,
    dtype=torch.bfloat16,
)
```

## Inference Pipeline with Batching

```python
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from torch.utils.data import DataLoader, Dataset

class TextDataset(Dataset):
    def __init__(self, texts, tokenizer, max_length=512):
        self.encodings = tokenizer(
            texts, truncation=True, max_length=max_length,
            padding=True, return_tensors="pt",
        )

    def __len__(self):
        return self.encodings["input_ids"].shape[0]

    def __getitem__(self, idx):
        return {k: v[idx] for k, v in self.encodings.items()}

def batch_predict(model, tokenizer, texts, batch_size=32, device="cuda"):
    """Efficient batched inference."""
    dataset = TextDataset(texts, tokenizer)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    model.eval()
    all_predictions = []
    all_probabilities = []

    with torch.no_grad(), torch.cuda.amp.autocast():
        for batch in dataloader:
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            preds = torch.argmax(probs, dim=-1)
            all_predictions.extend(preds.cpu().numpy())
            all_probabilities.extend(probs.cpu().numpy())

    return all_predictions, all_probabilities
```

## Model Registry Pattern

```python
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

class ModelRegistry:
    """Simple file-based model registry with versioning and staging."""

    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.registry_path / "manifest.json"
        self.manifest = self._load_manifest()

    def _load_manifest(self):
        if self.manifest_path.exists():
            with open(self.manifest_path) as f:
                return json.load(f)
        return {"models": {}}

    def _save_manifest(self):
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def register(self, model_name: str, model_path: str, metrics: dict, metadata: dict = None):
        """Register a new model version."""
        if model_name not in self.manifest["models"]:
            self.manifest["models"][model_name] = {"versions": [], "production": None, "staging": None}

        version = len(self.manifest["models"][model_name]["versions"]) + 1
        version_dir = self.registry_path / model_name / f"v{version}"
        version_dir.mkdir(parents=True, exist_ok=True)

        # Copy model files
        shutil.copytree(model_path, version_dir / "model", dirs_exist_ok=True)

        entry = {
            "version": version,
            "path": str(version_dir),
            "metrics": metrics,
            "metadata": metadata or {},
            "registered_at": datetime.utcnow().isoformat(),
            "stage": "none",
        }
        self.manifest["models"][model_name]["versions"].append(entry)
        self._save_manifest()
        return version

    def promote(self, model_name: str, version: int, stage: str):
        """Promote a model version to staging or production."""
        assert stage in ("staging", "production")
        versions = self.manifest["models"][model_name]["versions"]
        versions[version - 1]["stage"] = stage
        self.manifest["models"][model_name][stage] = version
        self._save_manifest()

    def load_model(self, model_name: str, stage: str = "production"):
        """Get the path to the model at a given stage."""
        version = self.manifest["models"][model_name].get(stage)
        if version is None:
            raise ValueError(f"No {stage} model for {model_name}")
        version_entry = self.manifest["models"][model_name]["versions"][version - 1]
        return version_entry["path"] + "/model"

# Usage:
# registry = ModelRegistry("./model_registry")
# v = registry.register("sentiment", "./final_model", {"f1": 0.95, "accuracy": 0.94})
# registry.promote("sentiment", v, "staging")
# registry.promote("sentiment", v, "production")
# model_path = registry.load_model("sentiment", "production")
```

## A/B Testing Model Versions

```python
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class ABTestConfig:
    model_a_path: str
    model_b_path: str
    traffic_split: float = 0.5    # Fraction of traffic to model B
    test_name: str = "default"

@dataclass
class ABTestResult:
    model: str
    prediction: dict
    latency_ms: float

class ABTestRouter:
    """Route inference requests between two model versions."""

    def __init__(self, config: ABTestConfig):
        self.config = config
        self.results: Dict[str, List[dict]] = {"A": [], "B": []}

    def route(self, request_id: str) -> str:
        """Deterministic routing based on request ID for consistency."""
        hash_val = hash(request_id) % 100
        return "B" if hash_val < (self.config.traffic_split * 100) else "A"

    def record(self, model: str, latency_ms: float, prediction: dict, ground_truth=None):
        self.results[model].append({
            "latency_ms": latency_ms,
            "prediction": prediction,
            "ground_truth": ground_truth,
            "timestamp": time.time(),
        })

    def summary(self) -> dict:
        summary = {}
        for model_label in ["A", "B"]:
            records = self.results[model_label]
            if not records:
                continue
            latencies = [r["latency_ms"] for r in records]
            summary[model_label] = {
                "count": len(records),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            }
        return summary
```
