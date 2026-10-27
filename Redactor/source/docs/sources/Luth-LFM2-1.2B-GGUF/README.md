---
library_name: transformers
license: other
license_name: lfm1.0
license_link: LICENSE
datasets:
- kurakurai/luth-sft
language:
- fr
- en
base_model:
- LiquidAI/LFM2-1.2B
pipeline_tag: text-generation
tags:
- liquid
- lfm2
- luth
---

![Luth x LFM2](media/logo_collab.png)


# Luth-LFM2-1.2B-GGUF

**Luth-LFM2** are French fine-tuned versions of LFM2 models by [Kurakura AI](https://huggingface.co/kurakurai), trained on the [Luth-SFT](https://huggingface.co/datasets/kurakurai/luth-sft) dataset. The models have improved their French capabilities in instruction following, math, and general knowledge. Additionally, their English capabilities have remained stable.

Find more details in the original model card: https://huggingface.co/kurakurai/Luth-LFM2-1.2B

## 🏃 How to run Luth-LFM2

Example usage with [llama.cpp](https://github.com/ggml-org/llama.cpp):

```
llama-cli -hf kurakurai/Luth-LFM2-1.2B-GGUF
```