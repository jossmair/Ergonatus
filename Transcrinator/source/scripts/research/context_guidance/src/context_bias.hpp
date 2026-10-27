#pragma once
#include <atomic>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace pk {
// Immutable sparse prefix graph, compiled once when the vocabulary changes.
// A cursor belongs to one decode. No second encoder pass or beam expansion.
class ContextBias {
public:
    ContextBias(const std::vector<std::string>& pieces, const std::string& lines,
                float strength, int minimum_prefix);
    int select(int state, const float* logits, int count, int best, int blank) const;
    int advance(int state, int token) const;
    bool empty() const { return states_.size() <= 1 || strength_ == 0; }
private:
    struct State {
        std::vector<std::pair<unsigned char, int>> chars;
        std::vector<std::pair<int, int>> tokens;
        int letters = 0;
        int max_word_length = 0;
        bool word_end = false;
    };
    int walk(int state, const std::string& piece) const;
    int edge(int state, int token) const;
    std::vector<State> states_;
    std::vector<bool> continuation_;
    std::vector<std::string> pieces_;
    float strength_;
    int minimum_prefix_;
};

extern thread_local const ContextBias* active_context_bias;
extern thread_local int context_changes;
class ContextScope {
public:
    explicit ContextScope(const ContextBias* graph);
    ~ContextScope();
private:
    const ContextBias* previous_;
};
} // namespace pk
