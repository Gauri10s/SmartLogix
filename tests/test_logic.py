
import pytest
from app import app
from werkzeug.security import generate_password_hash, check_password_hash


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    with app.test_client() as client:
        yield client


def login_user(client, role="customer", user_id=1):
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["name"] = "Test User"
        session["role"] = role


# ---------------- AUTHENTICATION TESTS ----------------

def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign in to your workspace" in response.data


def test_register_page_loads(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Join SmartLogix" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.location


def test_register_success(client, monkeypatch):
    saved = {}

    def fake_execute(sql, params):
        saved["sql"] = sql
        saved["params"] = params
        return 1

    monkeypatch.setattr("app.execute_db", fake_execute)

    response = client.post("/register", data={
        "name": "Test Customer",
        "email": "TEST@GMAIL.COM",
        "password": "password123"
    })

    assert response.status_code == 302
    assert "/login" in response.location
    assert saved["params"][1] == "test@gmail.com"
    assert check_password_hash(saved["params"][2], "password123")
    assert "'customer'" in saved["sql"]


def test_register_rejects_short_password(client, monkeypatch):
    def should_not_execute(*args):
        pytest.fail("Database should not be called")

    monkeypatch.setattr("app.execute_db", should_not_execute)

    response = client.post("/register", data={
        "name": "Test User",
        "email": "test@gmail.com",
        "password": "123"
    })

    assert response.status_code == 200
    assert b"at least 6 characters" in response.data


def test_login_success(client, monkeypatch):
    user = {
        "id": 1,
        "name": "Test User",
        "email": "test@gmail.com",
        "password_hash": generate_password_hash("password123"),
        "role": "customer"
    }

    monkeypatch.setattr("app.query_db", lambda *args, **kwargs: user)

    response = client.post("/login", data={
        "email": "TEST@GMAIL.COM",
        "password": "password123"
    })

    assert response.status_code == 302
    assert "/dashboard" in response.location

    with client.session_transaction() as session:
        assert session["user_id"] == 1
        assert session["role"] == "customer"


def test_login_rejects_wrong_password(client, monkeypatch):
    user = {
        "id": 1,
        "name": "Test User",
        "email": "test@gmail.com",
        "password_hash": generate_password_hash("password123"),
        "role": "customer"
    }

    monkeypatch.setattr("app.query_db", lambda *args, **kwargs: user)

    response = client.post("/login", data={
        "email": "test@gmail.com",
        "password": "wrongpassword"
    })

    assert response.status_code == 200
    assert b"Incorrect email or password" in response.data


def test_logout_clears_session(client):
    login_user(client)

    response = client.get("/logout")

    assert response.status_code == 302
    assert "/login" in response.location

    with client.session_transaction() as session:
        assert "user_id" not in session


# ---------------- ROLE PERMISSION TESTS ----------------

def test_admin_page_requires_admin(client):
    login_user(client, role="customer")

    response = client.get("/analytics")

    assert response.status_code == 302
    assert "/dashboard" in response.location


def test_team_page_requires_admin(client):
    login_user(client, role="warehouse")

    response = client.get("/team")

    assert response.status_code == 302
    assert "/dashboard" in response.location


def test_customer_cannot_add_products(client):
    login_user(client, role="customer")

    response = client.post("/products/add", data={
        "name": "Headphones",
        "price": "1499",
        "stock": "10",
        "threshold": "5"
    })

    assert response.status_code == 302
    assert "/dashboard" in response.location


# ---------------- INVENTORY TESTS ----------------

def test_admin_can_add_product(client, monkeypatch):
    saved = {}

    def fake_execute(sql, params):
        saved["params"] = params
        return 1

    monkeypatch.setattr("app.execute_db", fake_execute)
    login_user(client, role="admin")

    response = client.post("/products/add", data={
        "name": "Wireless Headphones",
        "description": "Bluetooth headphones",
        "price": "1499",
        "stock": "20",
        "threshold": "5"
    })

    assert response.status_code == 302
    assert saved["params"][0] == "Wireless Headphones"
    assert saved["params"][2] == 1499.0
    assert saved["params"][3] == 20


def test_product_rejects_negative_stock(client, monkeypatch):
    def should_not_execute(*args):
        pytest.fail("Invalid product should not be inserted")

    monkeypatch.setattr("app.execute_db", should_not_execute)
    login_user(client, role="admin")

    response = client.post("/products/add", data={
        "name": "Headphones",
        "price": "1499",
        "stock": "-5",
        "threshold": "5"
    })

    assert response.status_code == 302


# ---------------- CART TESTS ----------------

def test_customer_can_add_product_to_cart(client, monkeypatch):
    product = {
        "id": 10,
        "name": "Wireless Mouse",
        "stock": 10,
        "price": 699
    }

    monkeypatch.setattr("app.query_db", lambda *args, **kwargs: product)
    login_user(client, role="customer")

    response = client.post("/cart/add/10")

    assert response.status_code == 302

    with client.session_transaction() as session:
        assert session["cart"]["10"] == 1


def test_out_of_stock_product_not_added(client, monkeypatch):
    product = {
        "id": 10,
        "name": "Wireless Mouse",
        "stock": 0,
        "price": 699
    }

    monkeypatch.setattr("app.query_db", lambda *args, **kwargs: product)
    login_user(client, role="customer")

    response = client.post("/cart/add/10")

    assert response.status_code == 302

    with client.session_transaction() as session:
        assert "cart" not in session


# ---------------- ORDER ACCESS TESTS ----------------

def test_customer_cannot_view_another_customers_order(client, monkeypatch):
    order = {
        "id": 50,
        "customer_id": 2,
        "delivery_person_id": 3
    }

    monkeypatch.setattr("app.query_db", lambda *args, **kwargs: order)
    login_user(client, role="customer", user_id=1)

    response = client.get("/orders/50")

    assert response.status_code == 302
    assert "/orders" in response.location


def test_delivery_person_cannot_update_unassigned_order(client, monkeypatch):
    order = {
        "id": 50,
        "customer_id": 2,
        "delivery_person_id": 3,
        "status": "Placed"
    }

    monkeypatch.setattr("app.query_db", lambda *args, **kwargs: order)
    login_user(client, role="delivery", user_id=4)

    response = client.post("/orders/50/status", data={
        "status": "Delivered"
    })

    assert response.status_code == 302
    assert "/orders" in response.location
