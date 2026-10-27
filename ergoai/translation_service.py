"""Local translation host sharing Redactor's installed model and loader."""
import hashlib,os,time
from shared.domain import app_data
from shared.translation import LANGUAGES
from ergoai.proofreading_service import Proofreader,MODEL,serve as serve_host


def endpoint():
    from ergoai.proofreading_service import endpoint as shared_endpoint
    return shared_endpoint()


def messages(text,source,target):
    if source not in LANGUAGES or target not in LANGUAGES:raise ValueError('Choisissez les deux langues.')
    prompt=(f'Translate the user text from {LANGUAGES[source][1]} into {LANGUAGES[target][1]} '
        f'as literally as natural {LANGUAGES[target][1]} permits. Preserve every object and quantity exactly. '
        f'Output only the {LANGUAGES[target][1]} translation.')
    return [dict(role='system',content=prompt),dict(role='user',content=text)]


class Translator(Proofreader):
    def translate(self,text,source,target,cancel):
        conversation=messages(text,source,target)
        if cancel.is_set():raise ValueError('Traduction annulée.')
        if source==target:return dict(text=text,model=MODEL,seconds=0)
        self.load();self.engine.stop.clear();self.last=time.monotonic();started=self.last;chunks=[];finish='stop'
        if cancel.is_set():raise ValueError('Traduction annulée.')
        iterator=self.engine.llm.create_chat_completion(messages=conversation,stream=True,
            max_tokens=min(2048,max(256,len(text)*2)),temperature=0,repeat_penalty=1.0)
        try:
            for item in iterator:
                if cancel.is_set():raise ValueError('Traduction annulée.')
                choice=item['choices'][0];chunks.append(choice.get('delta',{}).get('content') or '');finish=choice.get('finish_reason') or finish
        finally:
            if hasattr(iterator,'close'):iterator.close()
            self.last=time.monotonic()
        output=''.join(chunks).strip()
        if not output or finish=='length':raise ValueError('Traduction incomplète. Essayez un passage plus court.')
        if '<think>' in output:raise ValueError('Le moteur n’a pas fourni une traduction utilisable.')
        return dict(text=output,model=MODEL,seconds=round(time.monotonic()-started,3))


def serve():
    # Both operations share one queue and one resident model in the same host.
    serve_host()
