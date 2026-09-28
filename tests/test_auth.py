from tests.conftest import auth


def test_registration_returns_user_without_password(client):
    response = client.post(
        "/auth/register", json={"email": "new@example.com", "password": "password123"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "user"
    assert "hashed_password" not in body
    assert "password" not in body


def test_duplicate_email_is_rejected(client, user_token):
    response = client.post(
        "/auth/register", json={"email": "user@example.com", "password": "password123"}
    )
    assert response.status_code == 409


def test_short_password_is_rejected(client):
    response = client.post("/auth/register", json={"email": "x@example.com", "password": "short"})
    assert response.status_code == 422


def test_wrong_password_and_unknown_email_give_the_same_error(client, user_token):
    wrong_password = client.post(
        "/auth/login", data={"username": "user@example.com", "password": "nope"}
    )
    unknown_email = client.post(
        "/auth/login", data={"username": "ghost@example.com", "password": "password123"}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


def test_protected_route_requires_a_token(client):
    assert client.get("/auth/me").status_code == 401


def test_invalid_token_is_rejected(client):
    assert client.get("/auth/me", headers=auth("not-a-real-token")).status_code == 401


