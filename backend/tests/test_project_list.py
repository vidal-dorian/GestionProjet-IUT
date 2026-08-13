def test_list_projects_empty(client):
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert response.json() == []


def test_list_projects_returns_name_description_and_member_count(client):
    client.post("/api/projects", json={"name": "Site vitrine", "description": "Refonte du site"})
    client.post("/api/projects", json={"name": "App mobile"})

    response = client.get("/api/projects")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2

    by_name = {p["name"]: p for p in body}
    assert by_name["Site vitrine"]["description"] == "Refonte du site"
    assert by_name["Site vitrine"]["member_count"] == 0
    assert by_name["App mobile"]["description"] is None
    assert by_name["App mobile"]["member_count"] == 0
