from __future__ import annotations

import ctypes
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from oqs_transport.local_rag import DEFAULT_GENERATION_MODEL, DEFAULT_OLLAMA_URL, generate_prompt_with_ollama, ollama_available  # noqa: E402


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _memory_status() -> dict[str, float]:
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    gib = 1024**3
    return {
        "ram_total_gib": round(status.ullTotalPhys / gib, 2),
        "ram_available_gib": round(status.ullAvailPhys / gib, 2),
        "pagefile_available_gib": round(status.ullAvailPageFile / gib, 2),
        "memory_load_percent": int(status.dwMemoryLoad),
    }


def _nvidia_smi() -> dict[str, object]:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=10,
        ).strip()
    except Exception as exc:  # noqa: BLE001 - diagnostic script should report environment failure.
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    if not output:
        return {"available": False, "error": "nvidia-smi returned no GPUs"}
    name, total, used, free, util, temp = [part.strip() for part in output.split(",", maxsplit=5)]
    return {
        "available": True,
        "name": name,
        "vram_total_mib": int(total),
        "vram_used_mib": int(used),
        "vram_free_mib": int(free),
        "gpu_util_percent": int(util),
        "temperature_c": int(temp),
    }


def _ollama_json(path: str) -> object:
    with urllib.request.urlopen(f"{DEFAULT_OLLAMA_URL}{path}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    report: dict[str, object] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu_logical_threads": os.cpu_count(),
        "memory": _memory_status(),
        "gpu": _nvidia_smi(),
        "ollama_available": ollama_available(),
    }
    if report["ollama_available"]:
        report["ollama_models"] = _ollama_json("/api/tags")
        report["ollama_loaded"] = _ollama_json("/api/ps")
        start = time.perf_counter()
        try:
            response = generate_prompt_with_ollama(
                prompt="Responda em uma frase curta: dephasing é perda de fase.",
                model=DEFAULT_GENERATION_MODEL,
                options={
                    "num_ctx": 512,
                    "num_predict": 48,
                    "num_gpu": 0,
                    "num_thread": 4,
                    "num_batch": 32,
                    "temperature": 0.1,
                },
                keep_alive="0s",
                timeout_s=240,
            )
            report["cpu_generation_test"] = {
                "ok": True,
                "duration_s": round(time.perf_counter() - start, 2),
                "response": response,
            }
        except Exception as exc:  # noqa: BLE001 - health report should capture failures.
            report["cpu_generation_test"] = {
                "ok": False,
                "duration_s": round(time.perf_counter() - start, 2),
                "error": f"{type(exc).__name__}: {exc}",
            }

    memory = dict(report["memory"])
    gpu = dict(report["gpu"])
    report["recommendation"] = {
        "best_profile": "stable" if float(memory["ram_available_gib"]) >= 6.0 else "game",
        "use_gpu_generation": bool(gpu.get("available")) and int(gpu.get("vram_free_mib", 0)) >= 6000,
        "play_lol_while_generating": "not recommended for ranked/serious matches; use --no-generate or --profile game",
        "reason": "qwen2.5:7b is stable on CPU here, but it is slow and uses several GB of RAM; GTX 1650 4 GB is too small for stable 7B GPU generation.",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

