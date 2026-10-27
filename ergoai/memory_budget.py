"""Release only idle sibling models; never cancel another application's work."""
import json
from multiprocessing.connection import Client


def release_idle_peer(own_address):
    from ergoai.service import endpoint,authkey
    from ergoai.proofreading_service import endpoint as proofreading_endpoint
    for address in (endpoint(),proofreading_endpoint()):
        if address==own_address:continue
        try:
            with Client(address,family='AF_PIPE',authkey=authkey()) as connection:
                connection.send_bytes(json.dumps({'op':'release_idle'}).encode())
                if connection.poll(2):connection.recv_bytes(4096)
        except (OSError,EOFError,ValueError):pass


def idle_timeout():
    import psutil
    return 20 if psutil.virtual_memory().available<2*1024**3 else 90


def release_if_idle(model_lock,jobs,unload):
    if not model_lock.acquire(blocking=False):return False
    try:
        if not jobs.empty():return False
        unload();return True
    finally:model_lock.release()
