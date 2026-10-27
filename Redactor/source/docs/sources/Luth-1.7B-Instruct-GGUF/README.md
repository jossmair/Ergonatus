---
library_name: transformers
license: apache-2.0
datasets:
- kurakurai/luth-sft
language:
- fr
- en
base_model:
- Qwen/Qwen3-1.7B
pipeline_tag: text-generation
---

![Kurakura AI Logo](media/logo_kurakura.png)

# Luth-1.7B-Instruct-GGUF

**Luth-1.7B-Instruct** is a French fine-tuned version of [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B), trained on the [Luth-SFT](https://huggingface.co/datasets/kurakurai/luth-sft) dataset. The model has drastically improved its French capabilities in instruction following, math, and general knowledge. Additionally, its English capabilities have remained stable and have even increased in some areas.

Find more details in the original model card: https://huggingface.co/kurakurai/Luth-1.7B-Instruct

## 🏃 How to run Luth

Example usage with [llama.cpp](https://github.com/ggml-org/llama.cpp):

```
llama-cli -hf kurakurai/Luth-1.7B-Instruct-GGUF
```