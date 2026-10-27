#ifdef NDEBUG
#undef NDEBUG
#endif
#include "context_bias.hpp"
#include <cassert>
#include <iostream>

int main() {
    const std::vector<std::string> pieces = {"\xe2\x96\x81Jos", "selin", "lin", "ser", ".", "\xe2\x96\x81le"};
    pk::ContextBias graph(pieces, "Josselin\n", .5f, 3);
    int state = graph.advance(0, 0);
    float scores[] = {-9, 1.8f, .1f, 2.f, 3.f, 4.f, 5.f};
    assert(graph.select(state, scores, 7, 3, 6) == 1);
    assert(graph.select(0, scores, 7, 3, 6) == 3);  // no model prefix
    assert(graph.select(state, scores, 7, 6, 6) == 6);  // blank cannot be changed
    assert(graph.select(state, scores, 7, 4, 6) == 4);  // punctuation cannot be changed
    assert(graph.select(state, scores, 7, 5, 6) == 5);  // word boundary cannot be changed
    scores[3] = 3.f;
    assert(graph.select(state, scores, 7, 3, 6) == 3);  // strong acoustic winner
    assert(graph.advance(state, 3) == 0);
    state = graph.advance(state, 1);
    assert(graph.select(state, scores, 7, 3, 6) == 3);  // complete name cannot force extensions
    pk::ContextBias disabled(pieces, "Josselin", 0, 3);
    assert(disabled.select(disabled.advance(0, 0), scores, 7, 3, 6) == 3);
    // Two initial characters are insufficient to distinguish Maïlys / Maëlys.
    const std::vector<std::string> accent_pieces = {"\xe2\x96\x81Ma", "\xc3\xaflys", "\xc3\xablys"};
    pk::ContextBias guarded(accent_pieces, "Ma\xc3\xablys", 2, 3);
    const float accent_scores[] = {-9, 2, 1, -10};
    assert(guarded.select(guarded.advance(0, 0), accent_scores, 4, 1, 3) == 1);
    pk::ContextBias permissive(accent_pieces, "Ma\xc3\xablys", 2, 2);
    assert(permissive.select(permissive.advance(0, 0), accent_scores, 4, 1, 3) == 2);
    const std::vector<std::string> suffix_pieces = {"\xe2\x96\x81" "Arm", "ande", "and"};
    pk::ContextBias preserve_suffix(suffix_pieces, "Armand", 2, 3);
    assert(preserve_suffix.select(preserve_suffix.advance(0, 0), accent_scores, 4, 1, 3) == 1);
    // A shorter intermediate BPE piece may still lead to a longer correct name.
    const std::vector<std::string> partial_pieces = {"\xe2\x96\x81" "B\xc3\xa9r", "\xc3\xa9ny", "\xc3\xa9n", "ice"};
    pk::ContextBias allow_completion(partial_pieces, "B\xc3\xa9r\xc3\xa9nice", 2, 3);
    const float partial_scores[] = {-9, 2, 1, -9, -10};
    assert(allow_completion.select(allow_completion.advance(0, 0), partial_scores, 5, 1, 4) == 2);
    std::cout << "Context gating, blank/boundary protection and zero-strength parity passed\n";
}
