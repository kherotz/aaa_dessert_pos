from flask import Flask, render_template, request, jsonify
import sqlite3
import datetime

app = Flask(__name__)
DB_NAME = "desserts.db"

def init_db():
    """Initialize database tables with default dessert items."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 1. Items / Stock Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                cost_price REAL NOT NULL,
                sale_price REAL NOT NULL,
                stock INTEGER NOT NULL
            )
        """)
        
        # 2. Sales History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_amount REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        # 3. Listahan ng Utang (Debt Ledger) Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                item_details TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'Unpaid',
                date TEXT NOT NULL
            )
        """)
        
        # Seed initial dessert items if table is empty
        cursor.execute("SELECT COUNT(*) FROM items")
        if cursor.fetchone()[0] == 0:
            initial_items = [
                ("Mango Graham Tub (Medium)", "Graham Cakes", 75.0, 120.0, 24),
                ("Choco Fudge Graham", "Graham Cakes", 80.0, 130.0, 13),
                ("Graham Balls (Box of 10)", "Bites & Treats", 25.0, 50.0, 4),
                ("Classic Leche Flan", "Specialty Desserts", 90.0, 150.0, 13),
                ("Graham Balls Solo Piece", "Bites & Treats", 4.0, 10.0, 30),
                ("Buko Pandan Salad Tub", "Specialty Desserts", 70.0, 110.0, 8),
            ]
            cursor.executemany(
                "INSERT INTO items (name, category, cost_price, sale_price, stock) VALUES (?, ?, ?, ?, ?)",
                initial_items
            )
        conn.commit()

# --- Page Route ---
@app.route("/")
def index():
    return render_template("index.html")

# --- API Endpoints ---

@app.route("/api/items", methods=["GET"])
def get_items():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        items = conn.execute("SELECT * FROM items ORDER BY id DESC").fetchall()
        return jsonify([dict(item) for item in items])

@app.route("/api/items", methods=["POST"])
def add_item():
    data = request.json
    name = data.get("name")
    category = data.get("category", "Graham Cakes")
    cost_price = float(data.get("cost_price", 0))
    sale_price = float(data.get("sale_price", 0))
    stock = int(data.get("stock", 0))
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO items (name, category, cost_price, sale_price, stock) VALUES (?, ?, ?, ?, ?)",
            (name, category, cost_price, sale_price, stock)
        )
        conn.commit()
    return jsonify({"success": True, "message": "Item saved successfully!"})

@app.route("/api/items/<int:item_id>/restock", methods=["POST"])
def restock_item(item_id):
    data = request.json
    qty = int(data.get("quantity", 0))
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE items SET stock = stock + ? WHERE id = ?", (qty, item_id))
        conn.commit()
    return jsonify({"success": True})

@app.route("/api/checkout", methods=["POST"])
def checkout():
    data = request.json
    cart = data.get("cart", [])
    now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        for item in cart:
            item_id = item["id"]
            qty = item["quantity"]
            price = item["sale_price"]
            total = qty * price
            
            # Check availability
            cursor.execute("SELECT stock FROM items WHERE id = ?", (item_id,))
            current_stock = cursor.fetchone()[0]
            if current_stock < qty:
                return jsonify({"success": False, "error": f"Insufficient stock for {item['name']}"}), 400
            
            # Deduct stock
            cursor.execute("UPDATE items SET stock = stock - ? WHERE id = ?", (qty, item_id))
            
            # Record sale
            cursor.execute(
                "INSERT INTO sales (item_name, quantity, unit_price, total_amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                (item["name"], qty, price, total, now)
            )
        conn.commit()
    return jsonify({"success": True, "message": "Transaction completed!"})

@app.route("/api/debts", methods=["GET"])
def get_debts():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        debts = conn.execute("SELECT * FROM debts ORDER BY id DESC").fetchall()
        return jsonify([dict(d) for d in debts])

@app.route("/api/debts", methods=["POST"])
def add_debt():
    data = request.json
    customer = data.get("customer_name")
    details = data.get("item_details")
    amount = float(data.get("amount", 0))
    date = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO debts (customer_name, item_details, amount, status, date) VALUES (?, ?, ?, 'Unpaid', ?)",
            (customer, details, amount, date)
        )
        conn.commit()
    return jsonify({"success": True})

@app.route("/api/debts/<int:debt_id>/pay", methods=["POST"])
def pay_debt(debt_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE debts SET status = 'Paid' WHERE id = ?", (debt_id,))
        conn.commit()
    return jsonify({"success": True})

@app.route("/api/sales", methods=["GET"])
def get_sales():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        sales = conn.execute("SELECT * FROM sales ORDER BY id DESC LIMIT 50").fetchall()
        return jsonify([dict(s) for s in sales])

if __name__ == "__main__":
    init_db()
    print("🍓 Server running at http://127.0.0.1:5000/")
    app.run(debug=True, port=5000)