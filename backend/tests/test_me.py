def test_me_requires_auth(client):
    assert client.get("/api/me/favorites").status_code == 401


def test_favorites_crud(auth_client):
    assert auth_client.get("/api/me/favorites").json() == []

    res = auth_client.put("/api/me/favorites/m1", json={"title": "My Manga", "cover_url": "c"})
    assert res.status_code == 204
    # idempotente
    auth_client.put("/api/me/favorites/m1", json={"title": "My Manga", "cover_url": "c"})

    favs = auth_client.get("/api/me/favorites").json()
    assert [(f["manga_id"], f["title"]) for f in favs] == [("m1", "My Manga")]

    assert auth_client.delete("/api/me/favorites/m1").status_code == 204
    assert auth_client.get("/api/me/favorites").json() == []


def test_reading_progress(auth_client):
    assert auth_client.get("/api/me/progress/m1").json() is None

    auth_client.put("/api/me/progress/m1", json={"chapter_id": "c1", "chapter_number": "1"})
    auth_client.put("/api/me/progress/m1", json={"chapter_id": "c2", "chapter_number": "2"})

    assert auth_client.get("/api/me/progress/m1").json() == {
        "chapter_id": "c2",
        "chapter_number": "2",
    }
