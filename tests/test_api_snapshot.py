from backend.app.main import app
from fastapi.testclient import TestClient


def test_health_and_lineup_snapshot():
    client = TestClient(app)
    assert client.get("/api/healthz").status_code == 200
    # Ensure lineup endpoint returns expected keys (after seed auto-inits)
    r = client.get("/api/lineup/optimal?week=1&objective=risk")
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"starters","bench","rationale"}

