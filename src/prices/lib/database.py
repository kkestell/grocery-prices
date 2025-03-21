import math
import random
import sqlite3
from datetime import datetime, timedelta


class Database:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.conn = None
        self.cursor = None

    def connect(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.database_path)

            # Enable WAL mode
            # self.conn.execute("PRAGMA journal_mode=WAL")

            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys=ON")

            self.cursor = self.conn.cursor()

            # Create tables if they don't exist
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store TEXT NOT NULL,
                    sku TEXT NOT NULL,
                    name TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    size REAL NOT NULL,
                    unit TEXT NOT NULL,
                    category TEXT,
                    snap_eligible BOOLEAN NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    UNIQUE(store, sku)
                )
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    zip TEXT NOT NULL,
                    UNIQUE(store, code)
                )
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    location_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    price REAL NOT NULL,
                    available BOOLEAN NOT NULL,
                    UNIQUE(product_id, location_id, date),
                    FOREIGN KEY (product_id) REFERENCES products(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id)
                )
            ''')

            # New bargains table structure that associates with products instead of prices
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS bargains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    avg_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    discount_percentage REAL NOT NULL,
                    date_identified TEXT NOT NULL,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            ''')

            # New table to associate bargains with locations
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS bargain_locations (
                    bargain_id INTEGER NOT NULL,
                    location_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    PRIMARY KEY (bargain_id, location_id),
                    FOREIGN KEY (bargain_id) REFERENCES bargains(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id)
                )
            ''')

            # New tables for comparisons
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_on TEXT NOT NULL
                )
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS comparison_products (
                    comparison_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    PRIMARY KEY (comparison_id, product_id),
                    FOREIGN KEY (comparison_id) REFERENCES comparisons(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            ''')

            # New stats table with unique key
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def create_or_update_stat(self, key: str, value: str) -> None:
        self.connect()
        self.cursor.execute(
            "INSERT INTO stats (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value)
        )
        self.conn.commit()

    def get_stats(self) -> dict[str, str]:
        self.connect()
        self.cursor.execute("SELECT key, value FROM stats")
        return dict(self.cursor.fetchall())

    def delete_all_stats(self) -> None:
        self.connect()
        self.cursor.execute("DELETE FROM stats")
        self.conn.commit()

    def create_location(self, store: str, name: str, code: str, zip: str) -> int:
        self.connect()

        self.cursor.execute('''
            INSERT INTO locations (store, code, name, zip)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(store, code) DO UPDATE SET
            name = excluded.name,
            zip = excluded.zip
        ''', (store, code, name, zip))

        self.cursor.execute('''
            SELECT id FROM locations WHERE store = ? AND code = ?
        ''', (store, code))

        location_id = self.cursor.fetchone()[0]
        self.conn.commit()

        return location_id

    def get_locations(self, store: str) -> list:
        self.connect()

        self.cursor.execute('''
            SELECT id, code, name, zip FROM locations WHERE store = ?
        ''', (store,))

        results = self.cursor.fetchall()
        locations = []

        for row in results:
            id, code, name, zip = row
            locations.append({
                "id": id,
                "code": code,
                "name": name,
                "zip": zip
            })

        return locations

    def save(self, location_id: int, data: dict) -> None:
        self.connect()
        today = datetime.now().strftime("%Y-%m-%d")

        # Get the store from the location
        self.cursor.execute("SELECT store FROM locations WHERE id = ?", (location_id,))
        location_data = self.cursor.fetchone()
        if not location_data:
            raise ValueError(f"Location with ID {location_id} not found")

        store = location_data[0]

        # Find or create product
        self.cursor.execute('''
            SELECT id, first_seen FROM products WHERE store = ? AND sku = ?
        ''', (store, data["sku"]))
        product = self.cursor.fetchone()

        if product:
            # Update existing product
            product_id = product[0]

            # If category is not in data, use a separate update query that doesn't include category
            if "category" not in data:
                self.cursor.execute('''
                    UPDATE products SET
                    name = ?,
                    brand = ?,
                    size = ?,
                    unit = ?,
                    snap_eligible = ?,
                    last_seen = ?
                    WHERE id = ?
                ''', (data["name"],
                      data["brand"],
                      data["size"],
                      data["unit"],
                      data["snap_eligible"],
                      today,
                      product_id))
            else:
                self.cursor.execute('''
                    UPDATE products SET
                    name = ?,
                    brand = ?,
                    size = ?,
                    unit = ?,
                    category = ?,
                    snap_eligible = ?,
                    last_seen = ?
                    WHERE id = ?
                ''', (data["name"],
                      data["brand"],
                      data["size"],
                      data["unit"],
                      data["category"],
                      data["snap_eligible"],
                      today,
                      product_id))
        else:
            # Create new product - include category if available, otherwise use NULL
            category = data.get("category")  # Will be None if category isn't in data

            self.cursor.execute('''
                INSERT INTO products 
                (store, sku, name, brand, size, unit, category, snap_eligible, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (store,
                  data["sku"],
                  data["name"],
                  data["brand"],
                  data["size"],
                  data["unit"],
                  category,  # This will be None if category isn't in data
                  data["snap_eligible"],
                  today,
                  today))
            product_id = self.cursor.lastrowid

        # Save price information with availability
        self.cursor.execute('''
            INSERT INTO prices (product_id, location_id, date, price, available)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(product_id, location_id, date) DO UPDATE SET
            price = excluded.price,
            available = excluded.available
        ''', (product_id,
              location_id,
              today,
              data["price"],
              data["available"]))

        self.conn.commit()

        print(data)

    def search_products(self, query: str | None = None, snap: bool | None = None, store: str | None = None,
                        category: str | None = None, limit: int = 20, offset: int = 0) -> list[dict]:
        self.connect()

        # Base products selection
        base_query = """
            WITH product_selection AS (
                SELECT 
                    p.id,
                    p.store,
                    p.sku,
                    p.name,
                    p.brand,
                    p.size,
                    p.unit,
                    p.category,
                    p.snap_eligible,
                    p.last_seen
                FROM 
                    products p
                WHERE 
                    1=1
        """

        params = []

        # Add search conditions if query provided
        if query:
            base_query += " AND (p.sku = ? OR LOWER(p.name) LIKE LOWER(?) OR LOWER(p.brand) LIKE LOWER(?))"
            params.extend([query, f'%{query}%', f'%{query}%'])

        # Add SNAP eligibility filter if specified
        if snap is not None:
            base_query += " AND p.snap_eligible = ?"
            params.append(1 if snap else 0)  # Convert Python boolean to SQLite integer (1 for True, 0 for False)

        # Add store filter if specified
        if store:
            base_query += " AND p.store = ?"
            params.append(store)

        # Add category filter if specified
        if category:
            base_query += " AND p.category = ?"
            params.append(category)

        # Complete the CTE with limit, offset and prices
        full_query = base_query + """
                ORDER BY p.name ASC
                LIMIT ? OFFSET ?
            ),
            latest_prices AS (
                SELECT
                    pr.product_id,
                    pr.price,
                    pr.available,
                    ROW_NUMBER() OVER (
                        PARTITION BY pr.product_id
                        ORDER BY pr.price
                    ) AS price_rank,
                    COUNT(*) OVER (
                        PARTITION BY pr.product_id
                    ) AS price_count
                FROM 
                    prices pr
                JOIN
                    product_selection ps ON pr.product_id = ps.id
                JOIN
                    locations l ON pr.location_id = l.id
                WHERE
                    pr.date = ps.last_seen
            )
            SELECT
                ps.id,
                ps.store,
                ps.sku,
                ps.name,
                ps.brand,
                ps.size,
                ps.unit,
                ps.category,
                ps.snap_eligible,
                ps.last_seen,
                min_p.price AS lowest_price,
                max_p.price AS highest_price,
                min_p.available
            FROM
                product_selection ps
            LEFT JOIN
                latest_prices min_p ON ps.id = min_p.product_id AND min_p.price_rank = 1
            LEFT JOIN
                latest_prices max_p ON ps.id = max_p.product_id AND max_p.price_rank = max_p.price_count
        """

        params.extend([limit, offset])

        self.cursor.execute(full_query, params)
        rows = self.cursor.fetchall()

        results = []
        for row in rows:
            id, store, sku, name, brand, size, unit, category, snap_eligible, last_seen, lowest_price, highest_price, available = row

            product_data = {
                "id": id,
                "store": store,
                "sku": sku,
                "name": name,
                "brand": brand,
                "size": size,
                "unit": unit,
                "category": category,
                "snap_eligible": bool(snap_eligible),  # Convert from SQLite integer to Python boolean
                "last_updated": last_seen,
                "lowest_price": lowest_price,
                "highest_price": highest_price,
                "available": bool(available)  # Convert from SQLite integer to Python boolean
            }

            results.append(product_data)

        return results

    def update_bargains(self, min_discount_percentage: float = 10.0):
        self.connect()
        today = datetime.now().strftime("%Y-%m-%d")

        # Delete all existing bargains and bargain_locations
        self.cursor.execute("DELETE FROM bargain_locations")
        self.cursor.execute("DELETE FROM bargains")

        # First, identify product discounts with current prices below average
        product_query = '''
        WITH current_prices AS (
            -- Get current prices for all products
            SELECT 
                pr.product_id,
                pr.location_id,
                pr.price
            FROM 
                prices pr
            JOIN 
                products p ON pr.product_id = p.id
            WHERE 
                pr.date = ? AND pr.available = 1
        ),
        product_stats AS (
            -- Calculate min price and avg price per product
            SELECT 
                product_id,
                MIN(price) AS min_price,
                AVG(price) AS avg_price
            FROM 
                current_prices
            GROUP BY 
                product_id
        )
        -- Select products with discount percentage above threshold
        SELECT 
            product_id,
            min_price,
            avg_price,
            ((avg_price - min_price) / avg_price * 100) AS discount_percentage
        FROM 
            product_stats
        WHERE 
            avg_price > 0 AND
            ((avg_price - min_price) / avg_price * 100) >= ?
        '''

        self.cursor.execute(product_query, (today, min_discount_percentage))
        bargain_products = self.cursor.fetchall()

        # Insert bargains
        inserted_count = 0

        for product_id, min_price, avg_price, discount_percentage in bargain_products:
            self.cursor.execute('''
                INSERT INTO bargains (product_id, avg_price, current_price, discount_percentage, date_identified)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, avg_price, min_price, discount_percentage, today))

            bargain_id = self.cursor.lastrowid
            inserted_count += 1

            # Find all locations where this product is discounted
            location_query = '''
            SELECT 
                pr.location_id,
                pr.price
            FROM 
                prices pr
            WHERE 
                pr.product_id = ? AND 
                pr.date = ? AND 
                pr.available = 1
            '''

            self.cursor.execute(location_query, (product_id, today))
            locations = self.cursor.fetchall()

            for location_id, price in locations:
                self.cursor.execute('''
                    INSERT INTO bargain_locations (bargain_id, location_id, price)
                    VALUES (?, ?, ?)
                ''', (bargain_id, location_id, price))

        self.conn.commit()

        return inserted_count

    def get_bargains(self, limit: int = 50, offset: int = 0) -> list[dict]:
        self.connect()

        # First check if we have any bargains at all
        self.cursor.execute("SELECT COUNT(*) FROM bargains")
        bargain_count = self.cursor.fetchone()[0]
        print(f"Found {bargain_count} bargains in the database")

        if bargain_count == 0:
            return []

        query = '''
        SELECT 
            b.id AS bargain_id,
            p.store, 
            p.sku,
            p.name,
            p.brand,
            p.size,
            p.unit,
            p.category,
            b.avg_price,
            b.current_price,
            b.discount_percentage,
            b.date_identified,
            GROUP_CONCAT(l.name, ', ') AS locations
        FROM 
            bargains b
        JOIN 
            products p ON b.product_id = p.id
        JOIN 
            bargain_locations bl ON b.id = bl.bargain_id
        JOIN 
            locations l ON bl.location_id = l.id
        GROUP BY 
            b.id
        ORDER BY 
            b.discount_percentage DESC
        LIMIT ? OFFSET ?
        '''

        self.cursor.execute(query, (limit, offset))
        rows = self.cursor.fetchall()

        results = []
        for row in rows:
            bargain_id, store, sku, name, brand, size, unit, category, avg_price, current_price, discount_percentage, date_identified, locations = row

            bargain_data = {
                "bargain_id": bargain_id,
                "store": store,
                "sku": sku,
                "name": name,
                "brand": brand,
                "size": size,
                "unit": unit,
                "category": category,
                "locations": locations,
                "current_price": current_price,
                "avg_price": avg_price,
                "discount_percentage": round(discount_percentage, 2),
                "date_identified": date_identified
            }

            results.append(bargain_data)

        return results

    def get_prices(self, store: str, sku: str) -> list[dict]:
        self.connect()

        query = '''
        SELECT 
            p.store,
            pr.date,
            l.name AS location_name,
            l.zip AS location_zip,
            pr.price,
            pr.available
        FROM 
            prices pr
        JOIN 
            products p ON pr.product_id = p.id
        JOIN 
            locations l ON pr.location_id = l.id
        WHERE 
            p.store = ? AND p.sku = ?
        ORDER BY 
            pr.date DESC, l.name ASC
        '''

        self.cursor.execute(query, (store, sku))
        rows = self.cursor.fetchall()

        results = []
        for row in rows:
            store, date, location_name, location_zip, price, available = row

            price_data = {
                "store": store,
                "date": date,
                "location": location_name,
                "zip": location_zip,
                "price": price,
                "available": bool(available)
            }

            results.append(price_data)

        return results

    def list_comparisons(self) -> list[dict]:
        self.connect()

        query = '''
        SELECT 
            id, 
            title, 
            created_on
        FROM 
            comparisons
        ORDER BY 
            created_on DESC
        '''

        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        results = []
        for row in rows:
            comparison_id, title, created_on = row

            results.append({
                "id": comparison_id,
                "title": title,
                "created_on": created_on
            })

        return results

    def get_comparison(self, comparison_id: int) -> dict:
        self.connect()

        # Get the comparison details
        query = '''
        SELECT 
            id, 
            title, 
            created_on
        FROM 
            comparisons
        WHERE 
            id = ?
        '''

        self.cursor.execute(query, (comparison_id,))
        row = self.cursor.fetchone()

        if not row:
            return None

        comparison_id, title, created_on = row

        # Get all products in this comparison
        products_query = '''
        WITH comparison_product_ids AS (
            SELECT 
                cp.product_id
            FROM 
                comparison_products cp
            WHERE 
                cp.comparison_id = ?
        ),
        latest_prices AS (
            SELECT
                pr.product_id,
                pr.price,
                ROW_NUMBER() OVER (
                    PARTITION BY pr.product_id
                    ORDER BY pr.price
                ) AS price_rank,
                COUNT(*) OVER (
                    PARTITION BY pr.product_id
                ) AS price_count
            FROM 
                prices pr
            JOIN
                comparison_product_ids cpi ON pr.product_id = cpi.product_id
            JOIN
                products p ON pr.product_id = p.id
            JOIN
                locations l ON pr.location_id = l.id
            WHERE
                pr.date = p.last_seen
        )
        SELECT
            p.id,
            p.store,
            p.sku,
            p.name,
            p.brand,
            p.size,
            p.unit,
            p.category,
            p.snap_eligible,
            p.last_seen,
            min_p.price AS lowest_price,
            max_p.price AS highest_price
        FROM
            products p
        JOIN
            comparison_product_ids cpi ON p.id = cpi.product_id
        LEFT JOIN
            latest_prices min_p ON p.id = min_p.product_id AND min_p.price_rank = 1
        LEFT JOIN
            latest_prices max_p ON p.id = max_p.product_id AND max_p.price_rank = max_p.price_count
        ORDER BY
            p.store, p.name
        '''

        self.cursor.execute(products_query, (comparison_id,))
        product_rows = self.cursor.fetchall()

        products = []
        for row in product_rows:
            product_id, store, sku, name, brand, size, unit, category, snap_eligible, last_seen, lowest_price, highest_price = row

            # Size is now already a float, no need to parse it
            size_value = size  # Just use the size directly

            # Calculate unit price if we have both price and size
            unit_price = None
            if lowest_price is not None and size_value is not None and size_value > 0:
                unit_price = lowest_price / size_value

            products.append({
                "id": product_id,
                "store": store,
                "sku": sku,
                "name": name,
                "brand": brand,
                "size": size,
                "unit": unit,
                "category": category,
                "snap_eligible": bool(snap_eligible),
                "last_updated": last_seen,
                "lowest_price": lowest_price,
                "highest_price": highest_price,
                "unit_price": unit_price  # Add the unit price
            })

        # Construct the result
        result = {
            "id": comparison_id,
            "title": title,
            "created_on": created_on,
            "products": products
        }

        return result

    def create_comparison(self, title: str, product_ids: list[int]) -> int:
        self.connect()
        created_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert the comparison
        self.cursor.execute('''
            INSERT INTO comparisons (title, created_on)
            VALUES (?, ?)
        ''', (title, created_on))

        comparison_id = self.cursor.lastrowid

        # Insert all product associations
        for product_id in product_ids:
            self.cursor.execute('''
                INSERT INTO comparison_products (comparison_id, product_id)
                VALUES (?, ?)
            ''', (comparison_id, product_id))

        self.conn.commit()
        return comparison_id

    def update_comparison(self, comparison_id: int, title: str = None, product_ids: list[int] = None) -> bool:
        self.connect()

        # Check if comparison exists
        self.cursor.execute("SELECT id FROM comparisons WHERE id = ?", (comparison_id,))
        if not self.cursor.fetchone():
            return False

        # Update title if provided
        if title is not None:
            self.cursor.execute('''
                UPDATE comparisons
                SET title = ?
                WHERE id = ?
            ''', (title, comparison_id))

        # Update products if provided
        if product_ids is not None:
            # Delete existing product associations
            self.cursor.execute('''
                DELETE FROM comparison_products
                WHERE comparison_id = ?
            ''', (comparison_id,))

            # Insert new product associations
            for product_id in product_ids:
                self.cursor.execute('''
                    INSERT INTO comparison_products (comparison_id, product_id)
                    VALUES (?, ?)
                ''', (comparison_id, product_id))

        self.conn.commit()
        return True

    def delete_comparison(self, comparison_id: int) -> bool:
        self.connect()

        # Check if comparison exists
        self.cursor.execute("SELECT id FROM comparisons WHERE id = ?", (comparison_id,))
        if not self.cursor.fetchone():
            return False

        # Delete the comparison (will cascade to comparison_products due to ON DELETE CASCADE)
        self.cursor.execute("DELETE FROM comparisons WHERE id = ?", (comparison_id,))

        self.conn.commit()
        return True

    def seed(self, days: int = 60) -> tuple:
        self.connect()

        # Create locations
        locations = [
            self.create_location("Cub", "Minnetonka", "1001038", "55345"),
            self.create_location("Cub", "Plymouth", "1650", "55447"),
            self.create_location("Cub", "Maple Grove", "1600", "55311"),
            self.create_location("ALDI", "Medina, MN", "472-010", "55340"),
            self.create_location("ALDI", "Maple Grove, MN", "472-094", "55369"),
            self.create_location("ALDI", "Minnetonka, MN", "472-063", "55345"),
            self.create_location("Hy-Vee", "Plymouth", "1531", "55447")
        ]

        # Get store names from locations
        stores = list(set([l[0] for l in self.cursor.execute("SELECT store FROM locations").fetchall()]))

        # Product generation parameters
        store_brands = {
            "ALDI": ["Southern Grove", "Friendly Farms", "Simply Nature", "L'oven Fresh", "Kirkwood",
                     "Millville", "Clancy's", "Specially Selected", "Mama Cozzi's", "Barissimo", "None"],
            "Cub": ["Essential Everyday", "Butcher Shop", "General Mills", "Earthbound Farm", "Kemps",
                    "Tyson", "Coca-Cola", "Hunt's", "Nabisco", "Kellogg's", "None"],
            "Hy-Vee": ["Hy-Vee", "Full Circle", "Smart Chicken", "Jennie-O", "Chobani", "Barilla",
                       "Kellogg's", "Quaker", "Ore-Ida", "Blue Bunny", "None"]
        }

        categories = ["Produce", "Meat", "Dairy & Eggs", "Bakery", "Pantry", "Frozen",
                      "Beverages", "Snacks", "Breakfast", "Deli", "Seafood"]

        product_types = [
            "Milk", "Bread", "Eggs", "Apples", "Bananas", "Potatoes", "Carrots", "Chicken",
            "Beef", "Cheese", "Yogurt", "Cereal", "Pasta", "Sauce", "Rice", "Beans",
            "Juice", "Coffee", "Tea", "Frozen Vegetables", "Ice Cream", "Chips", "Crackers",
            "Cookies", "Soup", "Peanut Butter", "Jelly", "Oil", "Sugar", "Flour"
        ]

        descriptors = [
            "Organic", "Whole Grain", "Low Fat", "Fat Free", "Gluten Free", "Natural",
            "Fresh", "Frozen", "Sliced", "Diced", "Shredded", "Creamy", "Crunchy", "Sweet",
            "Original", "Homestyle", "Extra", "Premium", "Value Pack", "Family Size"
        ]

        units = ["oz", "lb", "count", "gallon", "pack", "each"]

        # Generate a product bank
        all_products = []
        product_count = 100  # Generate 100 products per store

        for store in stores:
            for i in range(product_count):
                # Generate SKU
                if store == "ALDI":
                    sku = f"00000000000{i + 10000}"[:16]
                elif store == "Cub":
                    sku = f"00{i + 50000}"[:14]
                else:  # Hy-Vee
                    sku = f"{i + 100000}"[:8]

                # Random product details
                product_type = random.choice(product_types)
                descriptor = random.choice(descriptors) if random.random() < 0.7 else ""
                brand = random.choice(store_brands[store])
                category = random.choice(categories)

                # Create name
                name = f"{descriptor} {product_type}".strip()

                # Random size and unit
                size = str(round(random.uniform(1, 24) * 4) / 4)  # Random size between 1-24 in 0.25 increments
                unit = random.choice(units)

                # SNAP eligibility (most food items are eligible)
                snap_eligible = random.random() < 0.9  # 90% of products are SNAP eligible

                # Create product
                product = {
                    "store": store,
                    "sku": sku,
                    "name": name,
                    "brand": brand,
                    "size": size,
                    "unit": unit,
                    "category": category,
                    "snap_eligible": snap_eligible
                }

                all_products.append(product)

        # Create a specific set of "bargain" products with guaranteed price differences
        bargain_products = random.sample(all_products, min(30, len(all_products) // 10))

        # Get today's date and calculate start date
        today = datetime.now()
        start_date = today - timedelta(days=days - 1)

        # Create a list of dates we'll use
        date_list = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

        # Set up dates for bargains - we want them to be recent
        recent_days = min(7, days)  # Last week or less
        recent_dates = date_list[-recent_days:]

        # Track product IDs
        product_ids = {}

        # Set up initial prices
        base_prices = {}

        # For each product, set a reasonable base price
        for product in all_products:
            # Generate a reasonable base price based on category and size
            size_num = float(product["size"])

            if "Meat" in product["category"] or "Seafood" in product["category"]:
                base_price = random.uniform(5, 15) * (size_num / 10 + 0.5)
            elif "Dairy" in product["category"]:
                base_price = random.uniform(2, 6) * (size_num / 10 + 0.5)
            elif "Produce" in product["category"]:
                base_price = random.uniform(1, 4) * (size_num / 10 + 0.5)
            elif "Frozen" in product["category"]:
                base_price = random.uniform(3, 8) * (size_num / 10 + 0.5)
            elif "Organic" in product["name"] or "Premium" in product["name"]:
                base_price = random.uniform(4, 10) * (size_num / 10 + 0.5)
            else:
                base_price = random.uniform(2, 5) * (size_num / 10 + 0.5)

            # Round to reasonable price ending
            base_price = round(base_price * 100 - random.choice([1, 5, 9])) / 100

            # Create a dictionary key from store and sku
            key = f"{product['store']}_{product['sku']}"
            base_prices[key] = base_price

        # Print some debug info about what we're doing
        print(f"Creating {len(bargain_products)} bargain products")
        print(f"Making them significantly cheaper at one location compared to others in recent dates")
        print(f"Recent dates: {recent_dates}")

        # Seed by date, working backward
        for date_str in date_list:
            # On each date, process each product
            for product in all_products:
                # Create a store-wide base price for this product on this date
                key = f"{product['store']}_{product['sku']}"
                base_price = base_prices[key]

                # 1. Regular price movement (small fluctuations)
                store_fluctuation = random.uniform(-0.2, 0.2)

                # 2. Seasonal trends (prices rise and fall over months)
                day_of_year = datetime.strptime(date_str, "%Y-%m-%d").timetuple().tm_yday
                seasonal_factor = 0.1 * math.sin(day_of_year / 365 * 2 * math.pi)

                # 3. Random sales (15% chance of a sale with larger discounts)
                sale_factor = 0.0
                if product not in bargain_products and random.random() < 0.15:
                    sale_factor = -random.uniform(0.15, 0.40)  # 15-40% discount

                # Special treatment for bargain products in recent dates
                is_bargain_product = product in bargain_products
                if is_bargain_product and date_str in recent_dates:
                    # Force a significant discount in the most recent dates
                    sale_factor = -random.uniform(0.25, 0.45)  # 25-45% discount

                # 4. Price increases over time (inflationary pressure)
                days_from_start = (datetime.strptime(date_str, "%Y-%m-%d") - start_date).days
                inflation_factor = days_from_start / 365 * 0.03  # ~3% annual inflation

                # Calculate the store-wide standard price for this product on this date
                store_price = base_price * (1 + store_fluctuation + seasonal_factor + sale_factor + inflation_factor)
                store_price = round(store_price * 100) / 100  # Round to nearest cent

                # Skip some combinations to create variety in the data
                if random.random() < 0.05:  # 5% chance to skip this product/date combination
                    continue

                # Get all locations for this product's store
                store_locations = [loc_id for loc_id, store, _, _, _ in
                                   [(row[0], row[1], row[2], row[3], row[4])
                                    for row in self.cursor.execute(
                                       "SELECT id, store, code, name, zip FROM locations WHERE store = ?",
                                       (product["store"],)).fetchall()]]

                # For each store location
                for loc_id in store_locations:
                    # Determine if product is available (90% chance of being available)
                    available = random.random() < 0.9

                    if not available:
                        continue

                    # Start with the store-wide price
                    price = store_price

                    # Apply location-specific variations for bargain products
                    # Much more aggressive location-based pricing for bargain products in recent dates
                    if is_bargain_product and date_str in recent_dates:
                        # Ensure significant price differences BETWEEN LOCATIONS on the SAME DAY
                        # This is what the bargain detection algorithm specifically looks for
                        if loc_id == store_locations[0]:  # First location gets a big discount
                            location_factor = -0.3  # 30% cheaper at this location
                        else:
                            location_factor = 0.05  # 5% more expensive at other locations

                        price = price * (1 + location_factor)
                        price = round(price * 100) / 100  # Round to nearest cent
                    # Normal location variations for other products
                    elif random.random() < 0.15:
                        location_factor = random.choice([-0.05, 0.05])
                        price = price * (1 + location_factor)
                        price = round(price * 100) / 100  # Round to nearest cent

                    # Ensure price is reasonable (never goes below a minimum threshold)
                    min_price = base_price * 0.6  # Never less than 60% of base price
                    price = max(price, min_price)

                    # Create or get product ID
                    product_key = f"{product['store']}_{product['sku']}"
                    if product_key not in product_ids:
                        # Need to insert the product first
                        self.cursor.execute('''
                            INSERT INTO products 
                            (store, sku, name, brand, size, unit, category, snap_eligible, first_seen, last_seen)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            product["store"],
                            product["sku"],
                            product["name"],
                            product["brand"],
                            product["size"],
                            product["unit"],
                            product["category"],
                            product["snap_eligible"],
                            date_str,
                            date_str
                        ))

                        # Get the product ID
                        self.cursor.execute('''
                            SELECT id FROM products WHERE store = ? AND sku = ?
                        ''', (product["store"], product["sku"]))

                        product_ids[product_key] = self.cursor.fetchone()[0]

                    # Save the price information
                    self.cursor.execute('''
                        INSERT INTO prices (product_id, location_id, date, price, available)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(product_id, location_id, date) DO UPDATE SET
                        price = excluded.price,
                        available = excluded.available
                    ''', (
                        product_ids[product_key],
                        loc_id,
                        date_str,
                        price,
                        available
                    ))

                    # Debug output for the most recent date
                    if date_str == date_list[-1] and product["sku"] == "0000000000010000":
                        self.cursor.execute('''
                            SELECT l.name, pr.price
                            FROM prices pr
                            JOIN locations l ON pr.location_id = l.id
                            WHERE pr.product_id = ? AND pr.date = ?
                        ''', (product_ids[product_key], date_str))

                        debug_prices = self.cursor.fetchall()
                        print(f"DEBUG: SKU {product['sku']} prices for {date_str}:")
                        for loc_name, price in debug_prices:
                            print(f"  - {loc_name}: ${price:.2f}")

                    # Debug output for the price range calculation
                    if product["sku"] == "0000000000010000" and date_str == date_list[-1]:
                        self.cursor.execute('''
                            SELECT 
                                MIN(pr.price) AS min_price,
                                MAX(pr.price) AS max_price
                            FROM 
                                prices pr
                            WHERE 
                                pr.product_id = ? AND pr.date = ?
                        ''', (product_ids[product_key], date_str))

                        min_price, max_price = self.cursor.fetchone()
                        print(
                            f"DEBUG: Price range for SKU {product['sku']} on {date_str}: ${min_price:.2f} - ${max_price:.2f}")

                    # Update last_seen date for the product
                    self.cursor.execute('''
                        UPDATE products
                        SET last_seen = ?
                        WHERE id = ?
                    ''', (date_str, product_ids[product_key]))

        # Commit all changes
        self.conn.commit()

        # Check the logic used by the search_products method, which populates the product table display
        print("\nDEBUG: Checking how search_products calculates price ranges...")
        test_product_sku = "0000000000010000"
        self.cursor.execute("SELECT id FROM products WHERE sku = ?", (test_product_sku,))
        test_id = self.cursor.fetchone()

        if test_id:
            test_id = test_id[0]
            self.cursor.execute('''
                SELECT pr.date, pr.location_id, pr.price 
                FROM prices pr 
                WHERE pr.product_id = ? 
                ORDER BY pr.date DESC
            ''', (test_id,))

            price_history = self.cursor.fetchall()
            print(f"DEBUG: Price history for product {test_product_sku} (latest first):")

            latest_date = None
            latest_prices = []

            for date, loc_id, price in price_history:
                if latest_date is None:
                    latest_date = date

                if date == latest_date:
                    latest_prices.append(price)

                print(f"  - Date: {date}, Location ID: {loc_id}, Price: ${price:.2f}")

            if latest_prices:
                print(
                    f"DEBUG: Latest prices (date {latest_date}): ${min(latest_prices):.2f} - ${max(latest_prices):.2f}")

        # Update bargains based on the seeded data with a lower threshold
        bargain_count = self.update_bargains(min_discount_percentage=8.0)

        # Force one more cleanup pass with a very low threshold to ensure we get some bargains
        if bargain_count == 0:
            print("No bargains found with regular threshold, trying with a lower threshold...")
            bargain_count = self.update_bargains(min_discount_percentage=5.0)

        # Return the number of products, price points, and bargains created
        return len(product_ids), self.cursor.execute("SELECT COUNT(*) FROM prices").fetchone()[0], bargain_count

    def clear(self):
        self.connect()
        self.cursor.execute("DELETE FROM bargain_locations")
        self.cursor.execute("DELETE FROM bargains")
        self.cursor.execute("DELETE FROM prices")
        self.cursor.execute("DELETE FROM products")
        self.cursor.execute("DELETE FROM locations")
        self.conn.commit()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()