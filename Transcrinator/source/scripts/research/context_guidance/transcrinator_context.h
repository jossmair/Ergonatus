#pragma once
#include "parakeet_capi.h"

#ifdef __cplusplus
extern "C" {
#endif
// Additive extension to ABI 10. Original entry points keep their behavior.
// Configure only when this context is idle. UTF-8 phrases are newline-separated.
// Empty phrases disable guidance. A failure leaves the prior graph intact.
// strength: 0..2 logit units; minimum_prefix: 2..8 Unicode characters.
int transcrinator_context_set(parakeet_ctx* ctx, const char* phrases,
                              float strength, int minimum_prefix);
char* transcrinator_transcribe_guided(parakeet_ctx* ctx, const float* samples,
                                    int count, int sample_rate, int decoder);
int transcrinator_context_last_changes(parakeet_ctx* ctx);
// Only at process shutdown: all contexts freed and all inference stopped.
// Uses the existing shutdown_backend() to release buffers before CUDA exits.
void transcrinator_shutdown_backend(void);
#ifdef __cplusplus
}
#endif
