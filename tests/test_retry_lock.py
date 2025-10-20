from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path


def load_module(module_name: str, relative_path: str):
    base = Path(__file__).resolve().parent.parent
    module_path = base / relative_path
    if str(module_path.parent) not in sys.path:
        sys.path.insert(0, str(module_path.parent))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


retry_module = load_module("funkbr_retry", "code/utils/retry.py")


def test_retry_with_backoff_eventually_succeeds() -> None:
    calls = {"count": 0}
    waits: list[float] = []

    def sleeper(seconds: float) -> None:
        waits.append(seconds)

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("fail")
        return "ok"

    result = retry_module.retry_with_backoff(
        flaky,
        max_tries=4,
        base=0.1,
        cap=0.5,
        jitter=False,
        sleep=sleeper,
        retry_exceptions=(ValueError,),
    )

    assert result == "ok"
    assert waits == [0.1, 0.2]


def test_retry_with_backoff_exhausts() -> None:
    def always_fail() -> None:
        raise ValueError("nope")

    try:
        retry_module.retry_with_backoff(
            always_fail,
            max_tries=2,
            base=0.05,
            cap=0.1,
            jitter=False,
            sleep=lambda _: None,
            retry_exceptions=(ValueError,),
        )
    except retry_module.RetryError as exc:
        assert "exhausted" in str(exc)
    else:
        raise AssertionError("expected RetryError")


def test_with_lock_prevents_parallel_execution(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parent.parent / "scripts" / "with_lock.sh"
    lock = tmp_path / "resource.lock"

    env = {**os.environ, "LOCK_WAIT_SECS": "0"}

    proc1 = subprocess.Popen(
        [
            str(script),
            str(lock),
            "--",
            sys.executable,
            "-c",
            "import time; time.sleep(0.3)",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(0.05)
    proc2 = subprocess.run(
        [str(script), str(lock), "--", sys.executable, "-c", "print('second')"],
        env=env,
        capture_output=True,
        text=True,
    )
    proc1.wait()

    assert proc2.returncode == 75
    assert "busy" in proc2.stderr
