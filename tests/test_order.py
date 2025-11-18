import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"  # API Gateway

def test_create_order(order_client, register_user):
    _, token = register_user()

    r = order_client.post(
        "/v1/orders",
        json={"items": ["apple", "milk"]},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert r.status_code == 201
    assert r.json()["success"] is True
    assert "id" in r.json()["data"]


def test_get_own_order(order_client, register_user):
    user_id, token = register_user()

    r = order_client.post(
        "/v1/orders",
        json={"items": ["tea"]},
        headers={"Authorization": f"Bearer {token}"}
    )
    order_id = r.json()["data"]["id"]
    r = order_client.get(
        f"/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert r.json()["success"] is True
    assert r.json()["data"]["id"] == order_id


def test_get_my_orders_pagination(order_client, register_user):
    _, token = register_user("paginator@test.com")

    for i in range(3):
        order_client.post(
            "/v1/orders",
            json={"items": [f"item{i}"]},
            headers={"Authorization": f"Bearer {token}"}
        )

    r = order_client.get(
        "/v1/orders?page=1&limit=2",
        headers={"Authorization": f"Bearer {token}"}
    )
    data = r.json()["data"]

    assert len(data["orders"]) == 2
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["limit"] == 2


def test_update_other_user_order_forbidden(order_client, register_user):
    _, token1 = register_user("o1@test.com")
    r = order_client.post(
        "/v1/orders",
        json={"items": ["x"]},
        headers={"Authorization": f"Bearer {token1}"}
    )
    order_id = r.json()["data"]["id"]

    _, token2 = register_user("o2@test.com")

    r = order_client.put(
        f"/v1/orders/{order_id}",
        json={"items": ["hacked"]},
        headers={"Authorization": f"Bearer {token2}"}
    )

    assert r.status_code == 403


def test_cancel_own_order(order_client, register_user):
    _, token = register_user("cancel@test.com")

    r = order_client.post(
        "/v1/orders",
        json={"items": ["pizza"]},
        headers={"Authorization": f"Bearer {token}"}
    )
    order_id = r.json()["data"]["id"]

    r = order_client.delete(
        f"/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert r.json()["success"] is True
    assert r.json()["data"]["status"] == "cancelled"

    r = order_client.put(
        f"/v1/orders/{order_id}",
        json={"items": ["new"]},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert r.status_code == 400