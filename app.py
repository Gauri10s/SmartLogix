import os
from functools import wraps
from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-key-change-me")

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "smartlogix")
    )

def query_db(sql, params=(), one=False, commit=False):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        result = cursor.fetchone() if one else cursor.fetchall()
        if commit:
            conn.commit()
        return result
    finally:
        cursor.close()
        conn.close()

def execute_db(sql, params=()):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@app.context_processor
def inject_globals():
    return {"current_user": session.get("name"), "current_role": session.get("role")}

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter your name, a valid email and a password of at least 6 characters.", "danger")
            return render_template("register.html")
        try:
            execute_db(
                "INSERT INTO users (name,email,password_hash,role) VALUES (%s,%s,%s,'customer')",
                (name, email, generate_password_hash(password))
            )
            flash("Account created. You can now sign in.", "success")
            return redirect(url_for("login"))
        except Error:
            flash("That email may already be registered. Please try another.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query_db("SELECT * FROM users WHERE email=%s", (email,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], role=user["role"])
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    role = session["role"]
    if role == "customer":
        orders = query_db("SELECT * FROM orders WHERE customer_id=%s ORDER BY created_at DESC LIMIT 6", (session["user_id"],))
        products = query_db("SELECT * FROM products ORDER BY name LIMIT 4")
        total_orders = query_db("SELECT COUNT(*) AS n FROM orders WHERE customer_id=%s", (session["user_id"],), one=True)["n"]
        return render_template("customer_dashboard.html", orders=orders, products=products, total_orders=total_orders)
    if role == "warehouse":
        orders = query_db("SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id=o.customer_id WHERE o.status IN ('Placed','Confirmed','Packing','Ready for Dispatch') ORDER BY o.created_at")
        return render_template("warehouse.html", orders=orders)
    if role == "delivery":
        orders = query_db("SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id=o.customer_id WHERE o.delivery_person_id=%s ORDER BY o.created_at DESC", (session["user_id"],))
        return render_template("delivery.html", orders=orders)
    stats = {
        "orders": query_db("SELECT COUNT(*) AS n FROM orders", one=True)["n"],
        "products": query_db("SELECT COUNT(*) AS n FROM products", one=True)["n"],
        "customers": query_db("SELECT COUNT(*) AS n FROM users WHERE role='customer'", one=True)["n"],
        "delayed": query_db("SELECT COUNT(*) AS n FROM orders WHERE status NOT IN ('Delivered','Cancelled') AND created_at < NOW() - INTERVAL 3 DAY", one=True)["n"]
    }
    recent = query_db("SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id=o.customer_id ORDER BY o.created_at DESC LIMIT 7")
    low_stock = query_db("SELECT * FROM products WHERE stock <= low_stock_threshold ORDER BY stock ASC")
    return render_template("admin_dashboard.html", stats=stats, recent=recent, low_stock=low_stock)

@app.route("/products")
@login_required
def products():
    items = query_db("SELECT * FROM products ORDER BY name")
    return render_template("products.html", products=items)

@app.route("/products/add", methods=["POST"])
@roles_required("admin", "warehouse")
def add_product():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    try:
        price = float(request.form.get("price", "0"))
        stock = int(request.form.get("stock", "0"))
        threshold = int(request.form.get("threshold", "5"))
        if not name or price < 0 or stock < 0 or threshold < 0:
            raise ValueError()
        execute_db("INSERT INTO products (name,description,price,stock,low_stock_threshold) VALUES (%s,%s,%s,%s,%s)",
                   (name, description, price, stock, threshold))
        flash("Product added successfully.", "success")
    except (ValueError, Error):
        flash("Please enter valid product details.", "danger")
    return redirect(url_for("products"))

@app.route("/products/<int:product_id>/stock", methods=["POST"])
@roles_required("admin", "warehouse")
def update_stock(product_id):
    try:
        stock = int(request.form.get("stock", "-1"))
        if stock < 0:
            raise ValueError()
        execute_db("UPDATE products SET stock=%s WHERE id=%s", (stock, product_id))
        flash("Inventory updated.", "success")
    except ValueError:
        flash("Stock must be a non-negative whole number.", "danger")
    return redirect(url_for("products"))

@app.route("/cart/add/<int:product_id>", methods=["POST"])
@roles_required("customer")
def add_to_cart(product_id):
    product = query_db("SELECT * FROM products WHERE id=%s", (product_id,), one=True)
    if not product or product["stock"] < 1:
        flash("This product is currently out of stock.", "warning")
    else:
        cart = session.get("cart", {})
        key = str(product_id)
        cart[key] = min(int(cart.get(key, 0)) + 1, product["stock"])
        session["cart"] = cart
        flash("Added to your cart.", "success")
    return redirect(url_for("products"))

@app.route("/cart")
@roles_required("customer")
def cart():
    cart_data = []
    total = Decimal("0.00")
    for pid, qty in session.get("cart", {}).items():
        p = query_db("SELECT * FROM products WHERE id=%s", (int(pid),), one=True)
        if p:
            subtotal = Decimal(str(p["price"])) * int(qty)
            total += subtotal
            cart_data.append({"product": p, "quantity": qty, "subtotal": subtotal})
    return render_template("cart.html", cart=cart_data, total=total)

@app.route("/checkout", methods=["POST"])
@roles_required("customer")
def checkout():
    address = request.form.get("address", "").strip()
    cart_items = session.get("cart", {})
    if not address or not cart_items:
        flash("Add items to your cart and enter a delivery address.", "warning")
        return redirect(url_for("cart"))
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        total = Decimal("0.00")
        lines = []
        for pid, qty in cart_items.items():
            cur.execute("SELECT * FROM products WHERE id=%s FOR UPDATE", (int(pid),))
            p = cur.fetchone()
            qty = int(qty)
            if not p or p["stock"] < qty:
                raise ValueError("Insufficient stock for one or more products.")
            total += Decimal(str(p["price"])) * qty
            lines.append((p, qty))
        cur.execute("INSERT INTO orders (customer_id,total,delivery_address,status) VALUES (%s,%s,%s,'Placed')",
                    (session["user_id"], total, address))
        order_id = cur.lastrowid
        for p, qty in lines:
            cur.execute("INSERT INTO order_items (order_id,product_id,quantity,unit_price) VALUES (%s,%s,%s,%s)",
                        (order_id, p["id"], qty, p["price"]))
            cur.execute("UPDATE products SET stock=stock-%s WHERE id=%s", (qty, p["id"]))
        cur.execute("INSERT INTO status_history (order_id,status,note,changed_by) VALUES (%s,'Placed','Order created',%s)",
                    (order_id, session["user_id"]))
        conn.commit()
        session["cart"] = {}
        flash(f"Order #{order_id} placed successfully.", "success")
    except (ValueError, Error) as exc:
        conn.rollback()
        flash(str(exc) if isinstance(exc, ValueError) else "Could not place the order. Please try again.", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("orders"))

@app.route("/orders")
@login_required
def orders():
    if session["role"] == "customer":
        data = query_db("SELECT * FROM orders WHERE customer_id=%s ORDER BY created_at DESC", (session["user_id"],))
    elif session["role"] == "delivery":
        data = query_db("SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id=o.customer_id WHERE o.delivery_person_id=%s ORDER BY o.created_at DESC", (session["user_id"],))
    else:
        data = query_db("SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id=o.customer_id ORDER BY o.created_at DESC")
    return render_template("orders.html", orders=data)

@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = query_db("SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id=o.customer_id WHERE o.id=%s", (order_id,), one=True)
    if not order:
        flash("Order not found.", "warning")
        return redirect(url_for("orders"))
    if session["role"] == "customer" and order["customer_id"] != session["user_id"]:
        flash("You cannot view this order.", "danger")
        return redirect(url_for("orders"))
    if session["role"] == "delivery" and order["delivery_person_id"] != session["user_id"]:
        flash("This order is not assigned to you.", "danger")
        return redirect(url_for("orders"))
    items = query_db("SELECT oi.*, p.name FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE oi.order_id=%s", (order_id,))
    history = query_db("SELECT * FROM status_history WHERE order_id=%s ORDER BY changed_at", (order_id,))
    delivery_people = query_db("SELECT id,name FROM users WHERE role='delivery' ORDER BY name") if session["role"] == "admin" else []
    return render_template("order_detail.html", order=order, items=items, history=history,
                           delivery_people=delivery_people,
                           can_update=session["role"] in ("admin", "warehouse", "delivery"))

@app.route("/orders/<int:order_id>/status", methods=["POST"])
@roles_required("admin", "warehouse", "delivery")
def update_order_status(order_id):
    status = request.form.get("status")
    allowed = ["Confirmed", "Packing", "Ready for Dispatch", "Dispatched", "In Transit", "Out for Delivery", "Delivered", "Cancelled"]
    order = query_db("SELECT * FROM orders WHERE id=%s", (order_id,), one=True)
    if not order or status not in allowed:
        flash("Invalid order or status.", "danger")
        return redirect(url_for("orders"))
    if session["role"] == "delivery" and order["delivery_person_id"] != session["user_id"]:
        flash("This order is not assigned to you.", "danger")
        return redirect(url_for("orders"))
    execute_db("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))
    execute_db("INSERT INTO status_history (order_id,status,note,changed_by) VALUES (%s,%s,%s,%s)",
               (order_id, status, "Status updated", session["user_id"]))
    flash("Order status updated.", "success")
    return redirect(url_for("order_detail", order_id=order_id))

@app.route("/orders/<int:order_id>/assign", methods=["POST"])
@roles_required("admin")
def assign_delivery(order_id):
    person_id = request.form.get("delivery_person_id")
    person = query_db("SELECT id FROM users WHERE id=%s AND role='delivery'", (person_id,), one=True)
    if not person:
        flash("Select a valid delivery person.", "danger")
    else:
        execute_db("UPDATE orders SET delivery_person_id=%s WHERE id=%s", (person_id, order_id))
        flash("Delivery assigned.", "success")
    return redirect(url_for("order_detail", order_id=order_id))

@app.route("/team")
@roles_required("admin")
def team():
    people = query_db("SELECT id,name,email,role,created_at FROM users ORDER BY role,name")
    return render_template("team.html", people=people)

@app.route("/team/<int:user_id>/role", methods=["POST"])
@roles_required("admin")
def change_role(user_id):
    role = request.form.get("role")
    if role not in ("customer", "warehouse", "delivery", "admin"):
        flash("Invalid role.", "danger")
    else:
        execute_db("UPDATE users SET role=%s WHERE id=%s", (role, user_id))
        flash("User role updated.", "success")
    return redirect(url_for("team"))

@app.route("/analytics")
@roles_required("admin")
def analytics():
    status_rows = query_db("SELECT status,COUNT(*) AS count FROM orders GROUP BY status")
    revenue_rows = query_db("SELECT DATE(created_at) AS day, SUM(total) AS revenue FROM orders WHERE created_at >= CURDATE() - INTERVAL 6 DAY GROUP BY DATE(created_at) ORDER BY day")
    return render_template("analytics.html", status_rows=status_rows, revenue_rows=revenue_rows)

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)
