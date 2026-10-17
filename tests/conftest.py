"""Tests run against a real FalkorDB. Set CLAIMPATH_TEST_FALKORDB=host:port to use yours, otherwise
a throwaway FalkorDB server is started from the falkordblite wheel on a free port."""
import os, shutil, socket, subprocess, sys, tempfile, time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture(scope="session")
def falkordb_server():
    ext = os.environ.get("CLAIMPATH_TEST_FALKORDB")
    if ext:
        host, port = ext.split(":"); yield host, int(port); return
    import redislite
    binp = os.path.join(os.path.dirname(redislite.__file__), "bin")
    port, d = free_port(), tempfile.mkdtemp()
    proc = subprocess.Popen([os.path.join(binp, "redis-server"), "--port", str(port), "--loadmodule",
                             os.path.join(binp, "falkordb.so"), "--dir", d, "--save", ""],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import redis
    for _ in range(50):
        try:
            redis.Redis(port=port).ping(); break
        except Exception:
            time.sleep(0.1)
    yield "127.0.0.1", port
    proc.terminate(); proc.wait(); shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def client(falkordb_server, monkeypatch):
    host, port = falkordb_server
    monkeypatch.setenv("FALKORDB_HOST", host); monkeypatch.setenv("FALKORDB_PORT", str(port))
    monkeypatch.setenv("CLAIMPATH_GRAPH", "claimpath_test")
    import importlib, seed, app as appmod
    importlib.reload(seed); importlib.reload(appmod)
    seed.seed()
    from fastapi.testclient import TestClient
    return TestClient(appmod.app)
