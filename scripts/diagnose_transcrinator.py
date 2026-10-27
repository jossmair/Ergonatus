from pathlib import Path
import sys,os,tempfile,asyncio,time,json,multiprocessing
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Transcrinator/source'))
async def diagnose():
    from app.core.settings import Settings
    from app.core.device_detector import detect
    from app.services.engine_manager import EngineManager
    os.environ.update(TRANSCRI_BUNDLE=str(ROOT/'ergoai/transcription'),TRANSCRI_DATA=tempfile.mkdtemp(prefix='transcri-load-'),PYTHONPATH=str(ROOT/'Transcrinator/source'))
    start=time.monotonic();hw=await asyncio.to_thread(detect);print('hardware',json.dumps(hw.as_dict()),flush=True)
    manager=EngineManager(hw)
    try:
        engine=await manager.prepare(Settings());print('READY',engine.backend,round(time.monotonic()-start,2),flush=True)
    except Exception:
        import traceback;traceback.print_exc();raise
    finally:await manager.close()
if __name__=='__main__':
    multiprocessing.freeze_support();asyncio.run(diagnose())
