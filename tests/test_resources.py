from tests.conftest import auth


def test_normal_user_cannot_create_a_resource(client, user_token):
    response = client.post("/resources", json={"name": "Room B"}, headers=auth(user_token))
    assert response.status_code == 403


def test_admin_can_create_a_resource(client, admin_token):
    response = client.post("/resources", json={"name": "Room B"}, headers=auth(admin_token))
    assert response.status_code == 201
    assert response.json()["slot_minutes"] == 60


def test_duplicate_resource_name_is_rejected(client, admin_token, resource_id):
    response = client.post("/resources", json={"name": "Room A"}, headers=auth(admin_token))
    assert response.status_code == 409


def test_patch_only_changes_supplied_fields(client, admin_token, resource_id):
    response = client.patch(
        f"/resources/{resource_id}",
        json={"description": "Seats 10"},
        headers=auth(admin_token),
    )

    body = response.json()
    assert body["description"] == "Seats 10"
    assert body["name"] == "Room A"


def test_delete_deactivates_instead_of_removing(client, admin_token, resource_id):
    assert client.delete(f"/resources/{resource_id}", headers=auth(admin_token)).status_code == 204

    active = client.get("/resources", headers=auth(admin_token)).json()
    assert active == []

    everything = client.get(
        "/resources", params={"include_inactive": True}, headers=auth(admin_token)
    ).json()
    assert len(everything) == 1
    assert everything[0]["is_active"] is False


