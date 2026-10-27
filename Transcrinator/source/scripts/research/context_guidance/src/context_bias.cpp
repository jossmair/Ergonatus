#include "context_bias.hpp"
#include <algorithm>
#include <cmath>
#include <sstream>
#include <stdexcept>

namespace pk {
thread_local const ContextBias* active_context_bias = nullptr;
thread_local int context_changes = 0;
static const std::string space = "\xe2\x96\x81";

ContextBias::ContextBias(const std::vector<std::string>& pieces, const std::string& lines,
                         float strength, int minimum_prefix)
    : pieces_(pieces), strength_(strength), minimum_prefix_(minimum_prefix) {
    if (!std::isfinite(strength) || strength < 0 || strength > 2 || minimum_prefix < 2 || minimum_prefix > 8)
        throw std::invalid_argument("invalid context bias parameters");
    if (lines.size() > 32768 || pieces.size() > 65536)
        throw std::invalid_argument("context vocabulary too large");
    states_.push_back(State{});
    std::istringstream input(lines);
    std::string phrase;
    while (std::getline(input, phrase)) {
        if (phrase.empty()) continue;
        std::string encoded = space;
        for (unsigned char c : phrase) encoded += c == ' ' ? space : std::string(1, (char)c);
        int state = 0, letters = 0, word_length = 0;
        for (size_t i = 0; i < encoded.size(); ++i) {
            unsigned char c = (unsigned char)encoded[i];
            if (encoded.compare(i, space.size(), space) == 0) {
                if (i > 0) states_[state].word_end = true;
                letters = 0;
                const size_t start = i + space.size();
                size_t end = encoded.find(space, start);
                if (end == std::string::npos) end = encoded.size();
                word_length = 0;
                for (size_t p = start; p < end; ++p)
                    if (((unsigned char)encoded[p] & 0xc0) != 0x80) ++word_length;
            }
            else if ((c & 0xc0) != 0x80) ++letters;
            int next = -1;
            for (const auto& link : states_[state].chars) if (link.first == c) { next = link.second; break; }
            if (next < 0) {
                if (states_.size() >= 8192) throw std::invalid_argument("context graph too large");
                next = (int)states_.size();
                states_[state].chars.push_back({c, next});
                states_.push_back(State{});
                states_.back().letters = letters;
            }
            state = next;
            states_[state].max_word_length = std::max(states_[state].max_word_length, word_length);
        }
        states_[state].word_end = true;
    }
    continuation_.reserve(pieces.size());
    for (const auto& piece : pieces) {
        unsigned char c = piece.empty() ? 0 : (unsigned char)piece[0];
        continuation_.push_back(!piece.empty() && piece.find(space) == std::string::npos
            && piece.find_first_of(".,;:!?") == std::string::npos
            && (c >= 128 || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')));
    }
    // Sparse transitions: store only tokens that advance an actual name prefix.
    // This happens at configuration time, never at an audio callback.
    for (size_t state = 0; state < states_.size(); ++state) {
        for (size_t token = 0; token < pieces.size(); ++token) {
            if (pieces[token].empty() || pieces[token][0] == '<' || pieces[token][0] == '[') continue;
            int next = walk((int)state, pieces[token]);
            if (next >= 0) states_[state].tokens.push_back({(int)token, next});
        }
    }
}

int ContextBias::walk(int state, const std::string& piece) const {
    for (unsigned char c : piece) {
        int next = -1;
        for (const auto& link : states_[state].chars) if (link.first == c) { next = link.second; break; }
        if (next < 0) return -1;
        state = next;
    }
    return state;
}

int ContextBias::edge(int state, int token) const {
    const auto& links = states_[state].tokens;
    auto found = std::lower_bound(links.begin(), links.end(), token,
        [](const auto& link, int value) { return link.first < value; });
    return found != links.end() && found->first == token ? found->second : -1;
}

int ContextBias::advance(int state, int token) const {
    int next = edge(state, token);
    if (next < 0) next = edge(0, token);
    return next < 0 ? 0 : next;
}

int ContextBias::select(int state, const float* logits, int count, int best, int blank) const {
    // Never turn silence, punctuation or a new word into a dictionary completion.
    // A dictionary prefix must already have been supplied by the acoustic model.
    if (best < 0 || best >= count || best >= (int)continuation_.size() || best == blank || state <= 0 || strength_ == 0
        || states_[state].letters < minimum_prefix_ || !continuation_[best]
        || !std::isfinite(logits[best])) return best;
    int chosen = best;
    float score = logits[best];
    int heard_length = states_[state].letters;
    for (unsigned char c : pieces_[best]) if ((c & 0xc0) != 0x80) ++heard_length;
    for (const auto& link : states_[state].tokens) {
        int token = link.first;
        if (token >= count || token == blank || !continuation_[token] || !std::isfinite(logits[token])) continue;
        // Keep finer BPE segmentation possible, but never finish a dictionary
        // word before the characters already supplied by the acoustic winner.
        if (token != best) {
            const auto& destination = states_[link.second];
            if (destination.max_word_length < heard_length
                || (destination.word_end && destination.letters < heard_length)) continue;
        }
        float candidate = logits[token] + strength_;
        if (candidate > score) { score = candidate; chosen = token; }
    }
    return chosen;
}

ContextScope::ContextScope(const ContextBias* graph) : previous_(active_context_bias) {
    active_context_bias = graph && !graph->empty() ? graph : nullptr;
    context_changes = 0;
}
ContextScope::~ContextScope() { active_context_bias = previous_; }
} // namespace pk
