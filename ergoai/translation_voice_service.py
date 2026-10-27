"""Independent multilingual Piper host; preserves the existing French host."""
from ergoai.voice_service import main as serve
from ergoai.service import endpoint as ai_endpoint
from ergoai.translation_voices import VOICES

def endpoint():return ai_endpoint().replace('Ergonatus.AI.v1.','Ergonatus.TranslationVoice.v1.')

def main():serve(endpoint,VOICES)
