from flask import Flask, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)

app.config["SECRET_KEY"] = "secureshop-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///secureshop.db"

db = SQLAlchemy(app)
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


# -------------------------
# DATABASE MODELS
# -------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(300))


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)


# -------------------------
# HOME
# -------------------------

@app.route("/")
def home():
    return """
    <h1>SecureShop</h1>
    <p>Welcome to SecureShop</p>

    <a href="/register">Register</a><br>
    <a href="/login">Login</a><br>
    <a href="/products">Products</a><br>
    <a href="/cart">Cart</a><br>
    <a href="/orders">Order History</a><br>
    <a href="/profile">My Profile</a><br>
    <a href="/admin">Admin Area</a>
    """


# -------------------------
# REGISTER
# -------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            return "Username already exists"

        user = User(
            username=username,
            password=password
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return """
    <h1>Register</h1>

    <form method="POST">

        Username:
        <input name="username">

        <br><br>

        Password:
        <input type="password" name="password">

        <br><br>

        <button type="submit">Register</button>

    </form>

    <a href="/">Home</a>
    """


# -------------------------
# LOGIN
# -------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(
            username=username,
            password=password
        ).first()

        if user:

            session["user_id"] = user.id
            session["username"] = user.username
            session["is_admin"] = user.is_admin

            return redirect("/")

        return "Invalid username or password"

    return """
    <h1>Login</h1>

    <form method="POST">

        Username:
        <input name="username">

        <br><br>

        Password:
        <input type="password" name="password">

        <br><br>

        <button type="submit">Login</button>

    </form>

    <a href="/">Home</a>
    """


# -------------------------
# LOGOUT
# -------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# -------------------------
# PRODUCTS
# -------------------------

@app.route("/products")
def products():

    search = request.args.get("search", "")

    if search:

        # INTENTIONALLY VULNERABLE FOR LAB
        query = text("SELECT * FROM product WHERE name LIKE :search")
        products = db.session.execute(
        query,
    {"search": f"%{search}%"}
   ).fetchall()
    else:

        products = Product.query.all()

    html = "<h1>Products</h1>"

    html += """
    <form method="GET">

        Search:
        <input name="search">

        <button type="submit">Search</button>

    </form>
    """

    for product in products:

        html += f"""
        <hr>

        <h2>{product.name}</h2>

        <p>Price: ₹{product.price}</p>

        <p>{product.description}</p>

        <a href="/product/{product.id}">
            View Product
        </a>
        """

    html += '<br><br><a href="/">Home</a>'

    return html


# -------------------------
# PRODUCT DETAILS
# -------------------------

@app.route("/product/<int:product_id>")
def product(product_id):

    product = Product.query.get(product_id)

    if not product:
        return "Product not found"

    return f"""
    <h1>{product.name}</h1>

    <p>Price: ₹{product.price}</p>

    <p>{product.description}</p>

    <form method="POST" action="/cart/add/{product.id}">

        Quantity:
        <input name="quantity" value="1">

        <button type="submit">
            Add to Cart
        </button>

    </form>

    <br>

    <a href="/products">Products</a>
    """


# -------------------------
# CART
# -------------------------

@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_cart(product_id):

    product = Product.query.get(product_id)

    if not product:
        return "Product not found"

    quantity = int(request.form.get("quantity", 1))

    cart = session.get("cart", [])

    cart.append({
        "product_id": product.id,
        "name": product.name,
        "price": product.price,
        "quantity": quantity
    })

    session["cart"] = cart

    return redirect("/cart")


@app.route("/cart")
def cart():

    cart = session.get("cart", [])

    html = "<h1>Shopping Cart</h1>"

    total = 0

    for item in cart:

        item_total = item["price"] * item["quantity"]

        total += item_total

        html += f"""
        <p>
        {item["name"]}
        × {item["quantity"]}
        = ₹{item_total}
        </p>
        """

    html += f"<h2>Total: ₹{total}</h2>"

    if cart:

        html += """
        <form method="POST" action="/checkout">
            <button type="submit">
                Place Order
            </button>
        </form>
        """

    html += '<br><a href="/products">Continue Shopping</a>'

    return html


# -------------------------
# CHECKOUT
# -------------------------

@app.route("/checkout", methods=["POST"])
def checkout():

    if "user_id" not in session:
        return redirect("/login")

    cart = session.get("cart", [])

    for item in cart:

        order = Order(
            user_id=session["user_id"],
            product_name=item["name"],
            quantity=item["quantity"],
            total=item["price"] * item["quantity"]
        )

        db.session.add(order)

    db.session.commit()

    session["cart"] = []

    return redirect("/orders")


# -------------------------
# PROFILE
# -------------------------
# -------------------------
# PROFILE
# -------------------------
@app.route("/profile/<int:user_id>")
def profile_by_id(user_id):
    if "user_id" not in session:
        return redirect("/login")

    if user_id != session["user_id"]:
        return "Access denied", 403

    user = User.query.get(user_id)

    if not user:
        return "User not found"

    return f"""
    <h1>User Profile</h1>
    <p>User ID: {user.id}</p>
    <p>Username: {user.username}</p>
    """


# -------------------------
# INTENTIONALLY VULNERABLE IDOR
# -------------------------


@app.route("/profile/<int:user_id>")
@app.route("/orders")
def orders():

    if "user_id" not in session:
        return redirect("/login")

    orders = Order.query.filter_by(
        user_id=session["user_id"]
    ).all()

    html = "<h1>Order History</h1>"

    for order in orders:

        html += f"""
        <p>
        Order #{order.id}
        - {order.product_name}
        - Quantity: {order.quantity}
        - Total: ₹{order.total}
        </p>
        """

    return html


# -------------------------
# ADMIN AREA
# -------------------------

@app.route("/admin")
def admin():

    if not session.get("is_admin"):
        return "Admin access required"

    products = Product.query.all()
    users = User.query.all()

    html = "<h1>Admin Area</h1>"

    html += "<h2>Users</h2>"

    for user in users:

        html += f"""
        <p>
        ID: {user.id}
        Username: {user.username}
        Admin: {user.is_admin}
        </p>
        """

    html += "<h2>Products</h2>"

    for product in products:

        html += f"""
        <p>
        {product.id} -
        {product.name} -
        ₹{product.price}
        </p>
        """

    html += """
    <h2>Add Product</h2>

    <form method="POST" action="/admin/product/add">

        Name:
        <input name="name">

        <br><br>

        Price:
        <input name="price">

        <br><br>

        Description:
        <input name="description">

        <br><br>

        <button type="submit">
            Add Product
        </button>

    </form>
    """

    return html


@app.route("/admin/product/add", methods=["POST"])
def add_product():

    if not session.get("is_admin"):
        return "Admin access required"

    product = Product(
        name=request.form["name"],
        price=float(request.form["price"]),
        description=request.form["description"]
    )

    db.session.add(product)
    db.session.commit()

    return redirect("/admin")


# -------------------------
# DATABASE INITIALIZATION
# -------------------------

with app.app_context():

    db.create_all()

    if User.query.count() == 0:

        admin = User(
            username="admin",
            password="admin123",
            is_admin=True
        )

        user = User(
            username="testuser",
            password="test123",
            is_admin=False
        )

        db.session.add(admin)
        db.session.add(user)

    if Product.query.count() == 0:

        db.session.add(
            Product(
                name="Laptop",
                price=55000,
                description="High performance laptop"
            )
        )

        db.session.add(
            Product(
                name="Phone",
                price=25000,
                description="Smartphone"
            )
        )

        db.session.add(
            Product(
                name="Headphones",
                price=3000,
                description="Wireless headphones"
            )
        )

    db.session.commit()


# -------------------------
# RUN APPLICATION
# -------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=8080,
        debug=False
    )