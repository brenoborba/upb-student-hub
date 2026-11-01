def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_user_and_auth(client):
    r = client.post("/api/users", json={"email": "a@b.c"})
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "a@b.c"
    assert "api_key" in data
    api_key = data["api_key"]

    # Missing key -> 401
    assert client.get(f"/api/users/{data['id']}/assignments").status_code == 401

    # Valid key -> 200, empty list
    r = client.get(f"/api/users/{data['id']}/assignments", headers={"X-API-Key": api_key})
    assert r.status_code == 200
    assert r.json() == []


def test_cross_user_forbidden(client):
    a = client.post("/api/users", json={"email": "a@x.com"}).json()
    b = client.post("/api/users", json={"email": "b@x.com"}).json()

    r = client.get(f"/api/users/{a['id']}/assignments", headers={"X-API-Key": b["api_key"]})
    assert r.status_code == 403


def test_set_sakai_credentials(client, db):
    from backend.app.models import SakaiCredential

    user = client.post("/api/users", json={"email": "c@d.e"}).json()
    h = {"X-API-Key": user["api_key"]}

    r = client.put(
        f"/api/users/{user['id']}/sakai-credentials",
        json={"username": "u@ipb.pt", "password": "pw"},
        headers=h,
    )
    assert r.status_code == 204

    cred = db.query(SakaiCredential).filter_by(user_id=user["id"]).one()
    assert cred.username == "u@ipb.pt"
    assert cred.password_enc != "pw"  # stored encrypted


def test_sync_requires_credentials(client):
    user = client.post("/api/users", json={"email": "e@f.g"}).json()
    h = {"X-API-Key": user["api_key"]}

    r = client.post(f"/api/users/{user['id']}/sync", headers=h)
    assert r.status_code == 400
