import math
import random
import sqlite3
import threading
from datetime import datetime, timedelta


class Database:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.local = threading.local()

    def connect(self):
        # Check if this thread already has a connection
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            self.local.conn = sqlite3.connect(self.database_path)

            # Enable WAL mode
            # self.local.conn.execute("PRAGMA journal_mode=WAL")

            # Enable foreign keys
            self.local.conn.execute("PRAGMA foreign_keys=ON")

            self.local.cursor = self.local.conn.cursor()

            # Create tables if they don't exist
            self.local.cursor.execute('''
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

            self.local.cursor.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    zip TEXT NOT NULL,
                    UNIQUE(store, code)
                )
            ''')

            self.local.cursor.execute('''
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
            self.local.cursor.execute('''
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
            self.local.cursor.execute('''
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
            self.local.cursor.execute('''
                CREATE TABLE IF NOT EXISTS comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_on TEXT NOT NULL
                )
            ''')

            self.local.cursor.execute('''
                CREATE TABLE IF NOT EXISTS comparison_products (
                    comparison_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    PRIMARY KEY (comparison_id, product_id),
                    FOREIGN KEY (comparison_id) REFERENCES comparisons(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            ''')

            # New stats table with unique key
            self.local.cursor.execute('''
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            self.local.conn.commit()

    def close(self):
        if hasattr(self.local, 'conn') and self.local.conn:
            self.local.conn.close()
            self.local.conn = None
            self.local.cursor = None

    def create_or_update_stat(self, key: str, value: str) -> None:
        self.connect()
        self.local.cursor.execute(
            "INSERT INTO stats (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value)
        )
        self.local.conn.commit()

    def get_stats(self) -> dict[str, str]:
        self.connect()
        self.local.cursor.execute("SELECT key, value FROM stats")
        return dict(self.local.cursor.fetchall())

    def delete_all_stats(self) -> None:
        self.connect()
        self.local.cursor.execute("DELETE FROM stats")
        self.local.conn.commit()

    def create_location(self, store: str, name: str, code: str, zip: str) -> int:
        self.connect()

        self.local.cursor.execute('''
            INSERT INTO locations (store, code, name, zip)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(store, code) DO UPDATE SET
            name = excluded.name,
            zip = excluded.zip
        ''', (store, code, name, zip))

        self.local.cursor.execute('''
            SELECT id FROM locations WHERE store = ? AND code = ?
        ''', (store, code))

        location_id = self.local.cursor.fetchone()[0]
        self.local.conn.commit()

        return location_id

    def get_locations(self, store: str) -> list:
        self.connect()

        self.local.cursor.execute('''
            SELECT id, code, name, zip FROM locations WHERE store = ?
        ''', (store,))

        results = self.local.cursor.fetchall()
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
        self.local.cursor.execute("SELECT store FROM locations WHERE id = ?", (location_id,))
        location_data = self.local.cursor.fetchone()
        if not location_data:
            raise ValueError(f"Location with ID {location_id} not found")

        store = location_data[0]

        # Find or create product
        self.local.cursor.execute('''
            SELECT id, first_seen FROM products WHERE store = ? AND sku = ?
        ''', (store, data["sku"]))
        product = self.local.cursor.fetchone()

        if product:
            # Update existing product
            product_id = product[0]

            # If category is not in data, use a separate update query that doesn't include category
            if "category" not in data:
                self.local.cursor.execute('''
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
                self.local.cursor.execute('''
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

            self.local.cursor.execute('''
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
            product_id = self.local.cursor.lastrowid

        # Save price information with availability
        self.local.cursor.execute('''
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

        self.local.conn.commit()

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

        self.local.cursor.execute(full_query, params)
        rows = self.local.cursor.fetchall()

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
        self.local.cursor.execute("DELETE FROM bargain_locations")
        self.local.cursor.execute("DELETE FROM bargains")

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

        self.local.cursor.execute(product_query, (today, min_discount_percentage))
        bargain_products = self.local.cursor.fetchall()

        # Insert bargains
        inserted_count = 0

        for product_id, min_price, avg_price, discount_percentage in bargain_products:
            self.local.cursor.execute('''
                INSERT INTO bargains (product_id, avg_price, current_price, discount_percentage, date_identified)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, avg_price, min_price, discount_percentage, today))

            bargain_id = self.local.cursor.lastrowid
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

            self.local.cursor.execute(location_query, (product_id, today))
            locations = self.local.cursor.fetchall()

            for location_id, price in locations:
                self.local.cursor.execute('''
                    INSERT INTO bargain_locations (bargain_id, location_id, price)
                    VALUES (?, ?, ?)
                ''', (bargain_id, location_id, price))

        self.local.conn.commit()

        return inserted_count

    def get_bargains(self, limit: int = 50, offset: int = 0) -> list[dict]:
        self.connect()

        # First check if we have any bargains at all
        self.local.cursor.execute("SELECT COUNT(*) FROM bargains")
        bargain_count = self.local.cursor.fetchone()[0]
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

        self.local.cursor.execute(query, (limit, offset))
        rows = self.local.cursor.fetchall()

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

        self.local.cursor.execute(query, (store, sku))
        rows = self.local.cursor.fetchall()

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

        self.local.cursor.execute(query)
        rows = self.local.cursor.fetchall()

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

        self.local.cursor.execute(query, (comparison_id,))
        row = self.local.cursor.fetchone()

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
        '''

        self.local.cursor.execute(products_query, (comparison_id,))
        product_rows = self.local.cursor.fetchall()

        products = []
        for row in product_rows:
            product_id, store, sku, name, brand, size, unit, category, snap_eligible, last_seen, lowest_price, highest_price = row

            # Calculate unit price
            unit_price = lowest_price / size if lowest_price is not None and size is not None and size > 0 else None

            products.append({
                "id": product_id,
                "store": store,
                "sku": sku,
                "name": name,
                "brand": brand or "",
                "size": size,
                "unit": unit,
                "category": category,
                "snap_eligible": bool(snap_eligible),
                "last_updated": last_seen,
                "lowest_price": lowest_price,
                "highest_price": highest_price,
                "unit_price": unit_price
            })

        # Sort by unit price - simply put None values at the end
        products = sorted(products, key=lambda p: float('inf') if p["unit_price"] is None else p["unit_price"])

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
        self.local.cursor.execute('''
            INSERT INTO comparisons (title, created_on)
            VALUES (?, ?)
        ''', (title, created_on))

        comparison_id = self.local.cursor.lastrowid

        # Insert all product associations
        for product_id in product_ids:
            self.local.cursor.execute('''
                INSERT INTO comparison_products (comparison_id, product_id)
                VALUES (?, ?)
            ''', (comparison_id, product_id))

        self.local.conn.commit()
        return comparison_id

    def update_comparison(self, comparison_id: int, title: str = None, product_ids: list[int] = None) -> bool:
        self.connect()

        # Check if comparison exists
        self.local.cursor.execute("SELECT id FROM comparisons WHERE id = ?", (comparison_id,))
        if not self.local.cursor.fetchone():
            return False

        # Update title if provided
        if title is not None:
            self.local.cursor.execute('''
                UPDATE comparisons
                SET title = ?
                WHERE id = ?
            ''', (title, comparison_id))

        # Update products if provided
        if product_ids is not None:
            # Delete existing product associations
            self.local.cursor.execute('''
                DELETE FROM comparison_products
                WHERE comparison_id = ?
            ''', (comparison_id,))

            # Insert new product associations
            for product_id in product_ids:
                self.local.cursor.execute('''
                    INSERT INTO comparison_products (comparison_id, product_id)
                    VALUES (?, ?)
                ''', (comparison_id, product_id))

        self.local.conn.commit()
        return True

    def delete_comparison(self, comparison_id: int) -> bool:
        self.connect()

        # Check if comparison exists
        self.local.cursor.execute("SELECT id FROM comparisons WHERE id = ?", (comparison_id,))
        if not self.local.cursor.fetchone():
            return False

        # Delete the comparison (will cascade to comparison_products due to ON DELETE CASCADE)
        self.local.cursor.execute("DELETE FROM comparisons WHERE id = ?", (comparison_id,))

        self.local.conn.commit()
        return True

    def clear(self):
        self.connect()
        self.local.cursor.execute("DELETE FROM bargain_locations")
        self.local.cursor.execute("DELETE FROM bargains")
        self.local.cursor.execute("DELETE FROM prices")
        self.local.cursor.execute("DELETE FROM products")
        self.local.cursor.execute("DELETE FROM locations")
        self.local.conn.commit()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()