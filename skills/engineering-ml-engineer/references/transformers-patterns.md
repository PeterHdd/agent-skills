# HuggingFace Transformers Patterns

Production-grade patterns for inference, training, and evaluation with HuggingFace Transformers.

Prefer locally mirrored model and dataset artifacts in production code. If a workflow must pull from a public registry, pin the exact revision, keep `trust_remote_code=False`, and record the source in the experiment or deployment metadata.

## Model and Tokenizer Loading

```python
from transformers import AutoModel, AutoTokenizer, AutoModelForSequenceClassification
import torch

# Basic loading with automatic device placement
model_name = "bert-base-uncased"
model_revision = "main"
tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    revision=model_revision,
    trust_remote_code=False,
)
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    revision=model_revision,
    num_labels=3,
    torch_dtype=torch.float16,
    device_map="auto",  # Automatically places layers across available GPUs
    trust_remote_code=False,
)

# Loading a large model across multiple GPUs with offloading
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    revision="3f2b9c8",
    torch_dtype=torch.bfloat16,
    device_map="auto",
    offload_folder="offload",        # Offload to disk if GPU memory insufficient
    offload_state_dict=True,
    trust_remote_code=False,         # Never enable unless you audited the repo
)

# Loading with specific device map for multi-GPU
device_map = {
    "model.embed_tokens": 0,
    "model.layers.0": 0,
    "model.layers.1": 0,
    "model.layers.2": 1,
    "model.layers.3": 1,
    "model.norm": 1,
    "lm_head": 1,
}
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    revision="3f2b9c8",
    device_map=device_map,
    torch_dtype=torch.bfloat16,
    trust_remote_code=False,
)
```

## Pipeline API for Quick Inference

```python
from transformers import pipeline

# Text classification
classifier = pipeline(
    "text-classification",
    model="distilbert-base-uncased-finetuned-sst-2-english",
    device=0,  # GPU index, or -1 for CPU
)
results = classifier(["I love this product!", "Terrible experience."])
# [{'label': 'POSITIVE', 'score': 0.9998}, {'label': 'NEGATIVE', 'score': 0.9994}]

# Named Entity Recognition
ner = pipeline(
    "ner",
    model="dbmdz/bert-large-cased-finetuned-conll03-english",
    aggregation_strategy="simple",  # Merges subword tokens into entities
    device=0,
)
entities = ner("Hugging Face is based in New York City.")
# [{'entity_group': 'ORG', 'word': 'Hugging Face', ...}, {'entity_group': 'LOC', ...}]

# Summarization
summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn",
    device=0,
)
summary = summarizer(
    long_article_text,
    max_length=150,
    min_length=40,
    do_sample=False,
)

# Text generation with proper sampling
generator = pipeline(
    "text-generation",
    model="meta-llama/Llama-2-7b-chat-hf",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
output = generator(
    "Explain machine learning in simple terms:",
    max_new_tokens=256,
    temperature=0.7,
    top_p=0.9,
    top_k=50,
    repetition_penalty=1.1,
    do_sample=True,
)

# Zero-shot classification (no fine-tuning needed)
zero_shot = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=0,
)
result = zero_shot(
    "The stock market crashed today after the Fed raised rates.",
    candidate_labels=["finance", "sports", "technology", "politics"],
)
```

## Dataset Loading and Preprocessing

```python
from datasets import load_dataset, DatasetDict
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

# Load from local CSV files
dataset = load_dataset("csv", data_files={
    "train": "data/train.csv",
    "validation": "data/val.csv",
    "test": "data/test.csv",
})

# Load from local JSON lines
dataset = load_dataset("json", data_files="data/train.jsonl")

# Tokenization function for classification
def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        padding="max_length",
        truncation=True,
        max_length=512,
    )

tokenized_dataset = dataset.map(
    tokenize_function,
    batched=True,
    num_proc=4,              # Parallel processing
    remove_columns=["text"], # Remove raw text column after tokenization
)

# Set format for PyTorch
tokenized_dataset.set_format("torch", columns=["input_ids", "attention_mask", "label"])

# Tokenization for token classification (NER)
def tokenize_and_align_labels(examples):
    tokenized_inputs = tokenizer(
        examples["tokens"],
        truncation=True,
        is_split_into_words=True,
        padding="max_length",
        max_length=256,
    )
    labels = []
    for i, label in enumerate(examples["ner_tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        label_ids = []
        previous_word_idx = None
        for word_idx in word_ids:
            if word_idx is None:
                label_ids.append(-100)  # Ignore padding in loss
            elif word_idx != previous_word_idx:
                label_ids.append(label[word_idx])
            else:
                label_ids.append(-100)  # Ignore subword tokens
            previous_word_idx = word_idx
        labels.append(label_ids)
    tokenized_inputs["labels"] = labels
    return tokenized_inputs

# Data collator for dynamic padding (more efficient than max_length padding)
from transformers import DataCollatorWithPadding

data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
```

## Text Classification End-to-End with Trainer API

```python
import numpy as np
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

# Load data and model
dataset = load_dataset("csv", data_files={
    "train": "data/train.csv",
    "test": "data/test.csv",
})
tokenizer = AutoTokenizer.from_pretrained(
    "distilbert-base-uncased",
    revision="main",
    trust_remote_code=False,
)
model = AutoModelForSequenceClassification.from_pretrained(
    "distilbert-base-uncased",
    revision="main",
    num_labels=2,
    trust_remote_code=False,
)

# Tokenize
def tokenize(examples):
    return tokenizer(examples["text"], truncation=True, max_length=512)

tokenized = dataset.map(tokenize, batched=True, num_proc=4, remove_columns=["text"])

# Define metrics
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1": f1_score(labels, predictions, average="weighted"),
        "precision": precision_score(labels, predictions, average="weighted"),
        "recall": recall_score(labels, predictions, average="weighted"),
    }

# Training arguments
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    learning_rate=2e-5,
    weight_decay=0.01,
    eval_strategy="steps",
    eval_steps=500,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=3,
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    greater_is_better=True,
    logging_dir="./logs",
    logging_steps=100,
    fp16=True,                        # Mixed precision on NVIDIA GPUs
    dataloader_num_workers=4,
    report_to="tensorboard",
    seed=42,
)

# Trainer with early stopping
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["test"],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
)

# Train
trainer.train()

# Evaluate
metrics = trainer.evaluate()
print(metrics)

# Save model
trainer.save_model("./final_model")
tokenizer.save_pretrained("./final_model")
```

## Named Entity Recognition with Token Classification

```python
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification,
)
from datasets import load_dataset
import numpy as np
from seqeval.metrics import classification_report, f1_score as seqeval_f1

dataset = load_dataset("json", data_files={
    "train": "data/ner/train.jsonl",
    "validation": "data/ner/validation.jsonl",
})
label_names = dataset["train"].features["ner_tags"].feature.names
# ['O', 'B-PER', 'I-PER', 'B-ORG', 'I-ORG', 'B-LOC', 'I-LOC', 'B-MISC', 'I-MISC']

tokenizer = AutoTokenizer.from_pretrained(
    "bert-base-cased",
    revision="main",
    trust_remote_code=False,
)
model = AutoModelForTokenClassification.from_pretrained(
    "bert-base-cased",
    revision="main",
    num_labels=len(label_names),
    id2label={i: l for i, l in enumerate(label_names)},
    label2id={l: i for i, l in enumerate(label_names)},
    trust_remote_code=False,
)

# Tokenize and align labels (see tokenize_and_align_labels above)
tokenized = dataset.map(tokenize_and_align_labels, batched=True, num_proc=4)

data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

def compute_ner_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    true_labels = []
    true_preds = []
    for pred_seq, label_seq in zip(predictions, labels):
        true_label = []
        true_pred = []
        for p, l in zip(pred_seq, label_seq):
            if l != -100:
                true_label.append(label_names[l])
                true_pred.append(label_names[p])
        true_labels.append(true_label)
        true_preds.append(true_pred)
    return {
        "f1": seqeval_f1(true_labels, true_preds),
    }

training_args = TrainingArguments(
    output_dir="./ner_results",
    num_train_epochs=5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    learning_rate=3e-5,
    weight_decay=0.01,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    fp16=True,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["validation"],
    data_collator=data_collator,
    tokenizer=tokenizer,
    compute_metrics=compute_ner_metrics,
)

trainer.train()
```

## Text Generation with Proper Sampling

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_name = "meta-llama/Llama-2-7b-chat-hf"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# Chat template formatting
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain gradient descent in simple terms."},
]
prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

# Generation with proper parameters
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.7,          # Lower = more deterministic
        top_p=0.9,                # Nucleus sampling
        top_k=50,                 # Top-k sampling
        repetition_penalty=1.1,   # Penalize repeated tokens
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )

# Decode only the generated tokens (skip the prompt)
generated = outputs[0][inputs["input_ids"].shape[-1]:]
response = tokenizer.decode(generated, skip_special_tokens=True)
print(response)

# Streaming generation
from transformers import TextStreamer

streamer = TextStreamer(tokenizer, skip_special_tokens=True)
with torch.no_grad():
    model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
        streamer=streamer,
    )
```

## Embedding Extraction with Sentence-Transformers

```python
from sentence_transformers import SentenceTransformer, util
import numpy as np

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")  # Fast, 384-dim
# model = SentenceTransformer("all-mpnet-base-v2")  # Higher quality, 768-dim

# Encode texts
sentences = [
    "Machine learning is a subset of artificial intelligence.",
    "Deep learning uses neural networks with many layers.",
    "The weather is sunny today.",
]
embeddings = model.encode(sentences, convert_to_tensor=True, show_progress_bar=True)

# Compute pairwise similarity
cosine_scores = util.cos_sim(embeddings, embeddings)
print(cosine_scores)

# Semantic search
query = "What is deep learning?"
query_embedding = model.encode(query, convert_to_tensor=True)

corpus_embeddings = model.encode(sentences, convert_to_tensor=True)
hits = util.semantic_search(query_embedding, corpus_embeddings, top_k=3)
for hit in hits[0]:
    print(f"Score: {hit['score']:.4f} | {sentences[hit['corpus_id']]}")

# Batch encoding for large corpora
all_embeddings = model.encode(
    large_text_list,
    batch_size=256,
    show_progress_bar=True,
    convert_to_numpy=True,
    normalize_embeddings=True,  # For cosine similarity via dot product
)

# Clustering with embeddings
from sklearn.cluster import KMeans

kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
clusters = kmeans.fit_predict(all_embeddings)
```

## Multi-GPU Training with Accelerate

```python
# accelerate_config.yaml:
# compute_environment: LOCAL_MACHINE
# distributed_type: MULTI_GPU
# num_machines: 1
# num_processes: 4
# mixed_precision: bf16

from accelerate import Accelerator
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_scheduler
import torch

accelerator = Accelerator(mixed_precision="bf16")

model = AutoModelForSequenceClassification.from_pretrained("bert-base-uncased", num_labels=2)
optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)

train_dataloader = DataLoader(train_dataset, batch_size=16, shuffle=True)
eval_dataloader = DataLoader(eval_dataset, batch_size=32)

num_training_steps = len(train_dataloader) * 3  # 3 epochs
lr_scheduler = get_scheduler(
    "linear",
    optimizer=optimizer,
    num_warmup_steps=int(0.1 * num_training_steps),
    num_training_steps=num_training_steps,
)

# Prepare everything with accelerator -- handles device placement and distribution
model, optimizer, train_dataloader, eval_dataloader, lr_scheduler = accelerator.prepare(
    model, optimizer, train_dataloader, eval_dataloader, lr_scheduler
)

# Training loop
model.train()
for epoch in range(3):
    for batch in train_dataloader:
        outputs = model(**batch)
        loss = outputs.loss
        accelerator.backward(loss)
        optimizer.step()
        lr_scheduler.step()
        optimizer.zero_grad()

    # Evaluation
    model.eval()
    all_preds, all_labels = [], []
    for batch in eval_dataloader:
        with torch.no_grad():
            outputs = model(**batch)
        predictions = outputs.logits.argmax(dim=-1)
        preds, labels = accelerator.gather_for_metrics((predictions, batch["labels"]))
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())
    model.train()

# Launch with: accelerate launch train.py
```

## Mixed Precision and Gradient Accumulation

```python
from transformers import TrainingArguments

# Mixed precision training (fp16 on NVIDIA, bf16 on Ampere+)
training_args = TrainingArguments(
    output_dir="./results",
    fp16=True,                            # Use fp16 on V100/T4
    # bf16=True,                          # Use bf16 on A100/H100 (more stable)
    fp16_full_eval=False,                 # Keep eval in fp32 for metric stability
    gradient_accumulation_steps=4,        # Effective batch = per_device * 4
    per_device_train_batch_size=8,        # Actual batch per GPU = 8
    # Effective batch size = 8 * 4 = 32 per GPU
    # With 4 GPUs: 8 * 4 * 4 = 128 effective
    gradient_checkpointing=True,          # Trade compute for memory (30-40% savings)
    optim="adamw_torch_fused",            # Fused optimizer for faster training
    max_grad_norm=1.0,                    # Gradient clipping
    warmup_ratio=0.1,                     # 10% warmup steps
    lr_scheduler_type="cosine",           # Cosine decay with warmup
    learning_rate=2e-5,
    num_train_epochs=3,
)

# Gradient checkpointing with custom model
model.gradient_checkpointing_enable()
# This recomputes activations during backward pass instead of storing them
# Reduces memory by ~30-40% at the cost of ~20% slower training
```
