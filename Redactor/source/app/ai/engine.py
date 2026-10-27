"""CPU inference with one resident GGUF, streaming and cooperative native abort."""
from abc import ABC, abstractmethod
import ctypes
import os
from pathlib import Path
import threading
import time
from dataclasses import dataclass

from .model_manager import validate_model
from .gguf import metadata, luciole_template
from .prompts import Request


@dataclass
class Metrics:
    load_seconds: float = 0.
    first_token_seconds: float | None = None
    total_seconds: float = 0.
    output_tokens: int = 0
    tokens_per_second: float = 0.
    finish_reason: str = ""


class AIEngine(ABC):
    @abstractmethod
    def load(self, path: Path, threads=0, context=2048): ...

    @abstractmethod
    def stream(self, request: Request, max_tokens=384): ...

    @abstractmethod
    def cancel(self): ...

    @abstractmethod
    def close(self): ...


class ReasoningFilter:
    """Streaming tag parser: never expose split <think> blocks in an editor."""
    def __init__(self):
        self.pending = ""
        self.hidden = False

    def feed(self, chunk, final=False):
        self.pending += chunk
        result = []
        while self.pending:
            tag = "</think>" if self.hidden else "<think>"
            index = self.pending.find(tag)
            if index >= 0:
                if not self.hidden:
                    result.append(self.pending[:index])
                self.pending = self.pending[index + len(tag):]
                self.hidden = not self.hidden
                continue
            keep = 0
            if not final:
                for size in range(1, min(len(tag), len(self.pending) + 1)):
                    if self.pending.endswith(tag[:size]):
                        keep = size
            safe = self.pending[:-keep] if keep else self.pending
            if not self.hidden:
                result.append(safe)
            self.pending = self.pending[-keep:] if keep else ""
            break
        return "".join(result)


class LlamaEngine(AIEngine):
    def __init__(self):
        self.llm = None
        self.path = None
        self.stop = threading.Event()
        self.metrics = Metrics()
        self.context = 2048
        self._abort_callback = None

    def load(self, path: Path, threads=0, context=2048):
        if os.environ.get('ERGONATUS_SHARED_AI')=='1' and Path(path).name=='LFM2-700M-Q4_K_M.gguf':
            validate_model(path,check_hash=True)
            from .ergonatus_shared import SharedEngine
            self.close();self._shared=SharedEngine(context=context,threads=threads);self.path=Path(path);self.stop.clear();self.metrics=Metrics();return self.metrics
        started = time.perf_counter()
        import psutil
        from llama_cpp import Llama
        known = validate_model(path, check_hash=True, available_ram=psutil.virtual_memory().available)
        meta = metadata(path)
        template = meta.get("tokenizer.chat_template")
        if not isinstance(template, str) or not template.strip():
            raise ValueError("Ce GGUF ne fournit pas de format de conversation. Utilisez un modèle instruct vérifié.")
        luciole = known is not None and known.id in ("luciole", "luth17")
        backend = Llama
        if luciole:
            class LucioleLlama(Llama):
                # Adapt the Python view of this verified model's metadata before
                # Llama builds its Jinja handler. Neither file nor tensors change.
                @property
                def metadata(self):
                    return self._redactor_metadata

                @metadata.setter
                def metadata(self, values):
                    self._redactor_metadata = dict(values)
                    if "tokenizer.chat_template" in values:
                        self._redactor_metadata["tokenizer.chat_template"] = luciole_template(values["tokenizer.chat_template"])
            backend = LucioleLlama
        self.close()
        self.stop.clear()
        self.context = context
        cores = psutil.cpu_count(logical=False) or os.cpu_count() or 2
        threads = threads or max(1, min(8, cores - 1))
        self.llm = backend(model_path=str(path), n_ctx=context, n_threads=threads,
                         n_threads_batch=threads, n_gpu_layers=0, use_mmap=True,
                         use_mlock=False, verbose=False, logits_all=False, seed=42)
        self.path = Path(path)
        self.metrics = Metrics(load_seconds=time.perf_counter() - started)
        template = self.llm.metadata.get("tokenizer.chat_template", "")
        if not template and not self.llm.chat_format:
            self.close()
            raise ValueError("Ce GGUF ne fournit pas de format de conversation. Utilisez un modèle instruct vérifié.")
        try:
            from llama_cpp import llama_cpp as native
            callback_type = native.ggml_abort_callback
            self._abort_callback = callback_type(lambda _: self.stop.is_set())
            native.llama_set_abort_callback(self.llm._ctx.ctx, self._abort_callback, None)
        except (AttributeError, TypeError):
            self._abort_callback = None  # StoppingCriteria still cancels between decoding steps.
        return self.metrics

    def stream(self, request, max_tokens=384):
        proxy=getattr(self,'_shared',None)
        if proxy is not None:
            self.stop.clear();started=time.perf_counter();self.metrics=Metrics();filtering=ReasoningFilter()
            for chunk in proxy.stream(request.messages(),self.stop,max_tokens):
                if self.metrics.first_token_seconds is None:self.metrics.first_token_seconds=time.perf_counter()-started
                visible=filtering.feed(chunk)
                if visible:yield visible
            if not self.stop.is_set():
                tail=filtering.feed('',final=True)
                if tail:yield tail
            self.metrics.total_seconds=time.perf_counter()-started;self.metrics.output_tokens=proxy.metrics.get('output_tokens',0);self.metrics.tokens_per_second=proxy.metrics.get('tokens_per_second',0);self.metrics.finish_reason='cancelled' if self.stop.is_set() else proxy.metrics.get('finish_reason','stop')
            return
        if self.llm is None:
            raise ValueError("Le moteur n’est pas prêt. Choisissez un modèle local dans les réglages.")
        # Recurrent LFM2 state cannot trim an arbitrary cached prefix on this
        # llama.cpp build. Clear its context, retaining model weights in RAM.
        if self.llm.metadata.get("general.architecture") == "lfm2":
            self.llm.reset()
            self.llm._ctx.kv_cache_clear()
        messages = request.messages()
        estimated = sum(len(self.llm.tokenize(m["content"].encode("utf-8"), add_bos=False)) for m in messages) + 96
        while estimated + max_tokens > self.context and len(messages) > 2:
            messages.pop(1)
            if len(messages) > 2 and messages[1]["role"] == "assistant": messages.pop(1)
            estimated = sum(len(self.llm.tokenize(m["content"].encode("utf-8"), add_bos=False)) for m in messages) + 96
        if estimated + max_tokens > self.context:
            raise ValueError("Le passage est trop long pour le contexte du modèle. Réduisez le texte ou augmentez le contexte dans les réglages.")
        metrics = Metrics(load_seconds=self.metrics.load_seconds)
        self.metrics = metrics
        started, raw = time.perf_counter(), []
        if self.stop.is_set():
            metrics.finish_reason = "cancelled"
            return
        filtering = ReasoningFilter()
        # The embedded GGUF template selects the actual architecture's format.
        # Do not pretend LFM2, Nemotron and Qwen share a template.
        kwargs = dict(messages=messages, max_tokens=max_tokens, stream=True,
                      temperature=.2 if request.action == "correct" else .55,
                      top_p=.9, repeat_penalty=1.1)
        iterator = self.llm.create_chat_completion(**kwargs)
        try:
            for part in iterator:
                if self.stop.is_set():
                    break
                choice = part["choices"][0]
                piece = choice.get("delta", {}).get("content") or ""
                if choice.get("finish_reason"):
                    metrics.finish_reason = choice["finish_reason"]
                if not piece:
                    continue
                if metrics.first_token_seconds is None:
                    metrics.first_token_seconds = time.perf_counter() - started
                raw.append(piece)
                visible = filtering.feed(piece)
                if visible:
                    yield visible
            if not self.stop.is_set():
                tail = filtering.feed("", final=True)
                if tail:
                    yield tail
        except Exception:
            if not self.stop.is_set():
                raise
        finally:
            if hasattr(iterator, "close"):
                iterator.close()
            metrics.total_seconds = time.perf_counter() - started
            metrics.output_tokens = len(self.llm.tokenize("".join(raw).encode("utf-8"), add_bos=False))
            decode = metrics.total_seconds - (metrics.first_token_seconds or 0)
            metrics.tokens_per_second = max(0, metrics.output_tokens - 1) / max(.001, decode)
            if self.stop.is_set():
                metrics.finish_reason = "cancelled"
                self.llm.reset()
                self.llm._ctx.kv_cache_clear()

    def cancel(self):
        self.stop.set()
        if getattr(self,'_shared',None):self._shared.cancel()

    def close(self):
        if getattr(self,'_shared',None):self._shared.cancel();self._shared=None
        if self.llm:
            self.llm.close()
            self.llm = None
        self.path = None
        self._abort_callback = None
