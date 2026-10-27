import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

import psutil


def run(command, timeout=10):
    try:
        return subprocess.run(
            command, capture_output=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


@dataclass
class Hardware:
    cpu: str
    cores: int
    ram_total: int
    ram_available: int
    gpus: list = field(default_factory=list)
    wsl2: bool = False
    vulkan_loader: bool = False

    def as_dict(self):
        return asdict(self)


def detect(quick=False):
    memory = psutil.virtual_memory()
    hw = Hardware(platform.processor(), psutil.cpu_count(logical=False) or 1, memory.total, memory.available)
    system = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"
    hw.vulkan_loader = (system / "vulkan-1.dll").exists()
    if quick:
        hw.pending_detection=True
        return hw
    smi = shutil.which("nvidia-smi") or str(system / "nvidia-smi.exe")
    result = run(
        [smi, "--query-gpu=name,memory.total,memory.free,compute_cap", "--format=csv,noheader,nounits"]
    )
    if result and result.returncode == 0:
        for line in result.stdout.decode(errors="replace").splitlines():
            try:
                name, total, free, capability = [x.strip() for x in line.split(",")]
                hw.gpus.append(
                    {
                        "name": name,
                        "vram_mb": int(total),
                        "free_mb": int(free),
                        "cuda_capability": float(capability),
                        "vendor": "NVIDIA",
                    }
                )
            except ValueError:
                pass
    command = "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress"
    result = run(["powershell.exe", "-NoProfile", "-Command", command])
    if result and result.returncode == 0:
        try:
            names = json.loads(result.stdout.decode(errors="replace"))
            for name in names if isinstance(names, list) else [names]:
                if not any(g["name"] == name for g in hw.gpus):
                    hw.gpus.append({"name": name, "vram_mb": None, "vendor": "autre"})
        except ValueError:
            pass
    hw.vulkan_loader = (system / "vulkan-1.dll").exists()
    return hw
