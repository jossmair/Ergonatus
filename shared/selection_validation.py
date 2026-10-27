"""Compatibility helpers for the existing Redactor UIA reader, reused read-only."""
import hashlib
def fingerprint(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def splice_text(original,start,end,selected,replacement):
    if type(start) is not int or type(end) is not int or not 0<=start<=end<=len(original) or original[start:end]!=selected:raise ValueError('La sélection a changé.')
    return original[:start]+replacement+original[end:]

def read_uia_selection(expected):
    from shared.selection_accessibility import Accessibility
    bridge=Accessibility()
    try:
        target=bridge.capture(expected)
        if not target.selected:raise ValueError('Aucun texte sélectionné. Collez le texte dans le logiciel si besoin.')
        return target.selected
    finally:bridge.close()
