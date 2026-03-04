# Fine-Tuning Patterns

Production-grade patterns for LoRA, QLoRA, instruction tuning, and hyperparameter optimization.

## LoRA with PEFT: Full Working Example

```python
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import (
    LoraConfig,
    get_peft_model,
    TaskType,
    prepare_model_for_kbit_training,
)
from datasets import load_dataset

# 1. Load base model and tokenizer
model_name = "meta-llama/Llama-2-7b-hf"
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# 2. Configure LoRA
lora_config = LoraConfig(
    r=16,                          # Rank -- higher = more capacity, more memory
    lora_alpha=32,                 # Scaling factor (alpha/r = effective LR multiplier)
    target_modules=[               # Which layers to apply LoRA to
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

# 3. Apply LoRA to model
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# trainable params: 4,194,304 || all params: 6,742,609,920 || trainable%: 0.0622

# 4. Load and preprocess dataset
dataset = load_dataset("tatsu-lab/alpaca", split="train")

def format_instruction(example):
    if example["input"]:
        text = (
            f"### Instruction:\n{example['instruction']}\n\n"
            f"### Input:\n{example['input']}\n\n"
            f"### Response:\n{example['output']}"
        )
    else:
        text = (
            f"### Instruction:\n{example['instruction']}\n\n"
            f"### Response:\n{example['output']}"
        )
    return {"text": text}

dataset = dataset.map(format_instruction, remove_columns=dataset.column_names)

def tokenize(examples):
    result = tokenizer(
        examples["text"],
        truncation=True,
        max_length=1024,
        padding=False,
    )
    result["labels"] = result["input_ids"].copy()
    return result

tokenized = dataset.map(tokenize, batched=True, num_proc=4, remove_columns=["text"])

# 5. Train
training_args = TrainingArguments(
    output_dir="./lora_output",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=8,    # Effective batch = 32
    learning_rate=2e-4,               # LoRA can use higher LR than full fine-tuning
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    logging_steps=25,
    save_strategy="steps",
    save_steps=200,
    save_total_limit=3,
    bf16=True,
    optim="adamw_torch_fused",
    gradient_checkpointing=True,
    max_grad_norm=0.3,
    report_to="tensorboard",
    seed=42,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized,
    data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
)

trainer.train()

# 6. Save LoRA adapter
model.save_pretrained("./lora_adapter")
tokenizer.save_pretrained("./lora_adapter")

# 7. Merge LoRA weights back to base model for deployment
from peft import PeftModel

base_model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
merged_model = PeftModel.from_pretrained(base_model, "./lora_adapter")
merged_model = merged_model.merge_and_unload()

merged_model.save_pretrained("./merged_model")
tokenizer.save_pretrained("./merged_model")
```

## QLoRA: 4-Bit Quantization + LoRA

```python
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model

# 4-bit quantization config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",          # NormalFloat4 -- best for weights
    bnb_4bit_compute_dtype=torch.bfloat16,  # Compute in bf16 for speed
    bnb_4bit_use_double_quant=True,      # Nested quantization saves ~0.4 bits/param
)

# Load model in 4-bit
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-13b-hf",
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=False,
)

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-13b-hf")
tokenizer.pad_token = tokenizer.eos_token

# Prepare for k-bit training (freezes quantized layers, casts others to fp32)
model = prepare_model_for_kbit_training(model)

# LoRA config for QLoRA
lora_config = LoraConfig(
    r=64,                    # Higher rank compensates for quantization
    lora_alpha=16,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Training -- same as LoRA but with lower memory footprint
# A 13B model that normally needs 26 GB (fp16) now fits in ~8 GB VRAM
training_args = TrainingArguments(
    output_dir="./qlora_output",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    logging_steps=25,
    save_strategy="steps",
    save_steps=200,
    bf16=True,
    optim="paged_adamw_32bit",   # Paged optimizer for QLoRA memory management
    gradient_checkpointing=True,
    max_grad_norm=0.3,
)
```

## SFTTrainer for Instruction Tuning

```python
from trl import SFTTrainer, SFTConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset
from peft import LoraConfig

model_name = "meta-llama/Llama-2-7b-hf"
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto",
)

# Dataset with "text" column containing formatted instructions
dataset = load_dataset("timdettmers/openassistant-guanaco", split="train")

# LoRA configuration
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

# SFTConfig replaces TrainingArguments in newer trl versions
sft_config = SFTConfig(
    output_dir="./sft_output",
    num_train_epochs=1,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    max_seq_length=1024,
    packing=True,             # Pack multiple short examples into one sequence
    bf16=True,
    logging_steps=10,
    save_strategy="steps",
    save_steps=500,
    gradient_checkpointing=True,
    dataset_text_field="text",
)

trainer = SFTTrainer(
    model=model,
    args=sft_config,
    train_dataset=dataset,
    tokenizer=tokenizer,
    peft_config=peft_config,
)

trainer.train()
trainer.save_model("./sft_adapter")

# Chat template formatting for multi-turn conversations
def format_chat(example):
    """Format for models that expect chat template."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": example["instruction"]},
        {"role": "assistant", "content": example["response"]},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False)
    return {"text": text}
```

## Hyperparameter Search with Optuna

```python
import optuna
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
)
from datasets import load_dataset
import numpy as np
from sklearn.metrics import f1_score

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
dataset = load_dataset("imdb")

def tokenize(examples):
    return tokenizer(examples["text"], truncation=True, max_length=512)

tokenized = dataset.map(tokenize, batched=True, num_proc=4, remove_columns=["text"])

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {"f1": f1_score(labels, preds, average="weighted")}

def model_init():
    """Fresh model for each trial -- required by hyperparameter_search."""
    return AutoModelForSequenceClassification.from_pretrained(
        "bert-base-uncased", num_labels=2
    )

def optuna_hp_space(trial):
    """Define search space."""
    return {
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 5e-5, log=True),
        "per_device_train_batch_size": trial.suggest_categorical(
            "per_device_train_batch_size", [8, 16, 32]
        ),
        "num_train_epochs": trial.suggest_int("num_train_epochs", 2, 5),
        "weight_decay": trial.suggest_float("weight_decay", 0.0, 0.1),
        "warmup_ratio": trial.suggest_float("warmup_ratio", 0.0, 0.2),
    }

training_args = TrainingArguments(
    output_dir="./hp_search",
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    greater_is_better=True,
    fp16=True,
    report_to="none",
)

trainer = Trainer(
    model_init=model_init,
    args=training_args,
    train_dataset=tokenized["train"].select(range(5000)),  # Subset for speed
    eval_dataset=tokenized["test"].select(range(1000)),
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
)

# Run search
best_run = trainer.hyperparameter_search(
    direction="maximize",
    backend="optuna",
    hp_space=optuna_hp_space,
    n_trials=20,
    compute_objective=lambda metrics: metrics["eval_f1"],
)

print(f"Best trial: {best_run.hyperparameters}")
print(f"Best F1: {best_run.objective}")

# Retrain with best hyperparameters
for key, value in best_run.hyperparameters.items():
    setattr(training_args, key, value)

final_trainer = Trainer(
    model=model_init(),
    args=training_args,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["test"],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
)
final_trainer.train()
```

## Evaluation During Training

```python
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

def compute_metrics_multiclass(eval_pred):
    """Comprehensive metrics for multi-class classification."""
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    probs = torch.nn.functional.softmax(torch.tensor(logits), dim=-1).numpy()

    metrics = {
        "accuracy": accuracy_score(labels, predictions),
        "f1_macro": f1_score(labels, predictions, average="macro"),
        "f1_weighted": f1_score(labels, predictions, average="weighted"),
        "precision_macro": precision_score(labels, predictions, average="macro"),
        "recall_macro": recall_score(labels, predictions, average="macro"),
    }

    # AUC-ROC for multi-class (one-vs-rest)
    try:
        metrics["auc_roc"] = roc_auc_score(
            labels, probs, multi_class="ovr", average="weighted"
        )
    except ValueError:
        pass  # Skip if not all classes present in batch

    return metrics

def compute_metrics_binary(eval_pred):
    """Comprehensive metrics for binary classification."""
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    probs = torch.nn.functional.softmax(torch.tensor(logits), dim=-1).numpy()[:, 1]

    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1": f1_score(labels, predictions),
        "precision": precision_score(labels, predictions),
        "recall": recall_score(labels, predictions),
        "auc_roc": roc_auc_score(labels, probs),
    }
```

## Common Pitfalls and Solutions

### Catastrophic Forgetting
- **Symptom**: Model forgets pretrained knowledge after fine-tuning
- **Solution**: Use lower learning rate (1e-5 to 5e-5), shorter training, or LoRA instead of full fine-tuning
- **Solution**: Add a small portion of pretraining data to the fine-tuning mix

### Overfitting on Small Datasets
- **Symptom**: Training loss drops but validation loss increases after 1-2 epochs
- **Solution**: Use LoRA with low rank (r=8), increase dropout, reduce epochs to 1-3
- **Solution**: Use early stopping with patience of 2-3 evaluation rounds

### Learning Rate Too High
- **Symptom**: Loss spikes or NaN during training
- **Solution**: For full fine-tuning use 1e-5 to 5e-5; for LoRA use 1e-4 to 3e-4
- **Solution**: Always use warmup (3-10% of total steps)

### Tokenizer Mismatch
- **Symptom**: Garbage output, special tokens in wrong positions
- **Solution**: Always load tokenizer from the same checkpoint as the model
- **Solution**: Set `pad_token = eos_token` for decoder-only models that lack a pad token

### Memory Issues During Training
- **Symptom**: CUDA OOM errors
- **Solution**: Enable gradient checkpointing, reduce batch size, increase gradient accumulation
- **Solution**: Use QLoRA (4-bit) instead of LoRA (fp16)

## Full Fine-Tuning vs LoRA Comparison

| Aspect | Full Fine-Tuning | LoRA (r=16) | QLoRA (r=64, 4-bit) |
|---|---|---|---|
| **7B model VRAM (training)** | ~56 GB (fp16 + Adam) | ~18 GB (fp16) | ~8 GB |
| **13B model VRAM (training)** | ~104 GB (fp16 + Adam) | ~32 GB (fp16) | ~14 GB |
| **70B model VRAM (training)** | ~560 GB | ~160 GB | ~48 GB |
| **Trainable parameters** | 100% | 0.05-0.1% | 0.05-0.1% |
| **Training speed** | 1x (baseline) | 1.2-1.5x faster | 1.5-2x slower (quantization overhead) |
| **Accuracy** | Best (given enough data) | Within 1-2% of full | Within 2-3% of full |
| **Best for data size** | 10K+ examples | 100-10K examples | 100-10K examples |
| **Minimum GPU** | A100 80GB (7B) | A10G 24GB (7B) | T4 16GB (7B) |
| **Deployment** | Ship full model | Merge + ship, or ship adapter | Merge + ship |
| **Risk of forgetting** | High | Low | Low |

## LoRA Rank Selection Guide

| Rank (r) | Trainable Params (7B) | Use Case |
|---|---|---|
| 4 | ~1M | Simple task adaptation, style transfer |
| 8 | ~2M | Single-task fine-tuning, classification |
| 16 | ~4M | General instruction tuning (recommended default) |
| 32 | ~8M | Complex multi-task, significant domain shift |
| 64 | ~17M | QLoRA (compensate for quantization loss) |
| 128 | ~34M | Approaching full fine-tuning capacity |
