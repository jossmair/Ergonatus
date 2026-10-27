import subprocess
import sys
from uuid import uuid4
from fortinatus.windows import SingleInstance


def test_one_mutex_across_distinct_processes():
    name = "Local\\Fortinatus-test-" + uuid4().hex
    first = SingleInstance(name)
    assert first.acquire()
    try:
        code = "from fortinatus.windows import SingleInstance;import sys;g=SingleInstance(sys.argv[1]);print(int(g.acquire()));g.close()"
        result = subprocess.run([sys.executable, "-c", code, name], capture_output=True, text=True, timeout=5)
        assert result.returncode == 0
        assert result.stdout.strip() == "0"
    finally:
        first.close()
    second = SingleInstance(name)
    try:
        assert second.acquire()
    finally:
        second.close()


def test_closing_an_extra_launcher_does_not_release_the_first_lock():
    name = "Local\\Fortinatus-test-" + uuid4().hex
    first, duplicate, third = [SingleInstance(name) for _ in range(3)]
    try:
        assert first.acquire()
        assert not duplicate.acquire()
        duplicate.close()
        assert not third.acquire()
    finally:
        first.close()
        duplicate.close()
        third.close()
