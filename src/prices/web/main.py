from flask import Flask, render_template, request, jsonify, redirect, url_for

from prices.lib.constants import CATEGORIES
from prices.lib.database import Database

app = Flask(__name__)
db = Database("prices.db")


@app.route("/")
def index():
    stats = db.get_stats()
    return render_template("index.html", stats=stats)


@app.route("/comparisons")
def list_comparisons():
    comparisons = db.list_comparisons()

    # Enhance each comparison with additional data
    for comparison in comparisons:
        # Get full comparison data to access products
        full_comparison = db.get_comparison(comparison["id"])

        if not full_comparison or not full_comparison["products"]:
            comparison["best_value_product"] = None
            comparison["unit"] = None
            comparison["savings"] = None
            continue

        # Calculate unit prices for each product
        for product in full_comparison["products"]:
            size_value = product["size"]

            if product["lowest_price"] is not None and size_value > 0:
                product["unit_price"] = product["lowest_price"] / size_value
            else:
                product["unit_price"] = None

        # Find best value product
        best_value_product = None
        lowest_unit_price = None

        for product in full_comparison["products"]:
            if product["unit_price"] is not None:
                if lowest_unit_price is None or product["unit_price"] < lowest_unit_price:
                    lowest_unit_price = product["unit_price"]
                    best_value_product = product

        # Find second best product to calculate savings
        second_best_price = None
        for product in full_comparison["products"]:
            if product["unit_price"] is not None and product != best_value_product:
                if second_best_price is None or product["unit_price"] < second_best_price:
                    second_best_price = product["unit_price"]

        # Calculate savings (difference between best and second best)
        savings = None
        if lowest_unit_price is not None and second_best_price is not None:
            savings = lowest_unit_price - second_best_price

        # Add the calculated data to the comparison
        comparison["best_value_product"] = best_value_product
        comparison["unit"] = full_comparison["products"][0]["unit"] if full_comparison["products"] else None
        comparison["savings"] = savings

    return render_template("comparisons/index.html", comparisons=comparisons)


@app.route("/comparisons/<int:comparison_id>")
def show_comparison(comparison_id):
    comparison = db.get_comparison(comparison_id)
    if not comparison:
        return "Comparison not found", 404

    # Calculate unit prices for each product
    for product in comparison["products"]:
        # Size is now directly a numeric value from the database
        size_value = product["size"]

        # Calculate price per unit size
        if product["lowest_price"] is not None and size_value > 0:
            product["unit_price"] = product["lowest_price"] / size_value
        else:
            product["unit_price"] = None

    # Find the best value product (lowest price per unit)
    best_value_product = None
    lowest_unit_price = None

    if comparison["products"]:
        for product in comparison["products"]:
            if product["unit_price"] is not None:
                if lowest_unit_price is None or product["unit_price"] < lowest_unit_price:
                    lowest_unit_price = product["unit_price"]
                    best_value_product = product

    # Also find the product with the lowest absolute price
    lowest_price_product = None
    lowest_price = None

    if comparison["products"]:
        for product in comparison["products"]:
            if product["lowest_price"] is not None:
                if lowest_price is None or product["lowest_price"] < lowest_price:
                    lowest_price = product["lowest_price"]
                    lowest_price_product = product

    return render_template(
        "comparisons/show.html",
        comparison=comparison,
        lowest_price=lowest_price,
        best_value_product=best_value_product,
        lowest_price_product=lowest_price_product,
        unit=comparison["products"][0]["unit"] if comparison["products"] else None
    )

@app.route("/comparisons/new")
def new_comparison():
    return render_template("comparisons/new.html", categories=sorted(CATEGORIES))


@app.route("/compare")
def compare():
    return render_template("compare/index.html")


@app.route("/products")
def products():
    return render_template("products/index.html", categories=sorted(CATEGORIES))


@app.route("/bargains")
def bargains():
    return render_template("bargains/index.html")


@app.route("/price-history/<store>/<sku>")
def price_history(store, sku):
    return render_template("price_history/index.html", store=store, sku=sku)


@app.route("/api/products")
def get_products():
    query = request.args.get("q")
    snap = request.args.get("snap")
    store = request.args.get("store")
    category = request.args.get("category")

    if snap == "1":
        snap = True
    elif snap == "0":
        snap = False
    else:
        snap = None

    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))

    products = db.search_products(query, snap, store, category, limit, offset)
    return jsonify(products)


@app.route("/api/bargains")
def get_bargains():
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    bargains = db.get_bargains(limit, offset)
    return jsonify(bargains)


@app.route("/api/price-history/<store>/<sku>")
def get_price_history(store, sku):
    prices = db.get_prices(store, sku)

    products = db.search_products(query=sku)
    product = next((p for p in products if p["store"] == store and p["sku"] == sku), None)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    dates = {}
    for price in prices:
        date = price["date"]
        if date not in dates:
            dates[date] = []
        dates[date].append(price)

    result = {
        "product": product,
        "price_history": [
            {
                "date": date,
                "prices": date_prices,
                "min_price": min(p["price"] for p in date_prices),
                "max_price": max(p["price"] for p in date_prices),
                "avg_price": sum(p["price"] for p in date_prices) / len(date_prices),
                "location_count": len(date_prices),
                "available_count": sum(1 for p in date_prices if p["available"])
            }
            for date, date_prices in sorted(dates.items(), reverse=True)
        ]
    }

    return jsonify(result)


@app.route("/api/comparisons", methods=["GET"])
def get_comparisons():
    comparisons = db.list_comparisons()
    return jsonify(comparisons)


@app.route("/api/comparisons/<int:comparison_id>", methods=["GET"])
def get_comparison(comparison_id):
    comparison = db.get_comparison(comparison_id)
    if not comparison:
        return jsonify({"error": "Comparison not found"}), 404
    return jsonify(comparison)


@app.route("/api/comparisons", methods=["POST"])
def create_comparison():
    data = request.json

    if not data or "title" not in data or "product_ids" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    title = data["title"]
    product_ids = data["product_ids"]

    if not title.strip():
        return jsonify({"error": "Title cannot be empty"}), 400

    if not product_ids or not isinstance(product_ids, list) or len(product_ids) == 0:
        return jsonify({"error": "At least one product is required"}), 400

    try:
        comparison_id = db.create_comparison(title, product_ids)
        return jsonify({"id": comparison_id, "title": title}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/comparisons/<int:comparison_id>", methods=["PUT"])
def update_comparison(comparison_id):
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    title = data.get("title")
    product_ids = data.get("product_ids")

    if not db.update_comparison(comparison_id, title, product_ids):
        return jsonify({"error": "Comparison not found"}), 404

    return jsonify({"success": True})


@app.route("/api/comparisons/<int:comparison_id>", methods=["DELETE"])
def delete_comparison(comparison_id):
    if not db.delete_comparison(comparison_id):
        return jsonify({"error": "Comparison not found"}), 404

    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True)