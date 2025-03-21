import queue
import threading

from prices.lib.database import Database
from prices.scrape.aldi import scrape_aldi_products
from prices.scrape.cub import scrape_cub_products
from prices.scrape.fresh_thyme import scrape_fresh_thyme_products
from prices.scrape.hyvee import scrape_hyvee_products
from prices.scrape.notifications import send_message
from prices.scrape.trader_joes import scrape_trader_joes_products


def calculate_stats():
    with Database("prices.db") as db:
        db.connect()

        # Count unique stores
        db.cursor.execute("SELECT COUNT(DISTINCT store) FROM locations")
        total_stores = str(db.cursor.fetchone()[0])

        # Count unique locations
        db.cursor.execute("SELECT COUNT(*) FROM locations")
        total_locations = str(db.cursor.fetchone()[0])

        # Count total products
        db.cursor.execute("SELECT COUNT(*) FROM products")
        total_products = str(db.cursor.fetchone()[0])

        # Count total prices
        db.cursor.execute("SELECT COUNT(*) FROM prices")
        total_prices = str(db.cursor.fetchone()[0])

        # Save stats
        db.create_or_update_stat("total_stores", total_stores)
        db.create_or_update_stat("total_locations", total_locations)
        db.create_or_update_stat("total_products", total_products)
        db.create_or_update_stat("total_prices", total_prices)


def run_single_threaded():
    with Database("prices.db") as db:
        send_message("START")

        fresh_thyme_locations = db.get_locations("Fresh Thyme")
        trader_joes_locations = db.get_locations("Trader Joe's")
        aldi_locations = db.get_locations("ALDI")
        hyvee_locations = db.get_locations("Hy-Vee")
        cub_locations = db.get_locations("Cub")

        for location in fresh_thyme_locations:
            send_message(f"Scraping Fresh Thyme for {location['name']}")
            for product in scrape_fresh_thyme_products(location["code"]):
                db.save(location["id"], product)
            send_message(f"Finished scraping Fresh Thyme for {location['name']}")

        for location in trader_joes_locations:
            send_message(f"Scraping Trader Joe's for {location['name']}")
            for product in scrape_trader_joes_products(location["code"]):
                db.save(location["id"], product)
            send_message(f"Finished scraping Trader Joe's for {location['name']}")

        for location in aldi_locations:
            send_message(f"Scraping ALDI for {location['name']}")
            for product in scrape_aldi_products(location["code"]):
                db.save(location["id"], product)
            send_message(f"Finished scraping ALDI for {location['name']}")

        for location in hyvee_locations:
            send_message(f"Scraping Hy-Vee for {location['name']}")
            for product in scrape_hyvee_products(location["code"]):
                db.save(location["id"], product)
            send_message(f"Finished scraping Hy-Vee for {location['name']}")

        for location in cub_locations:
            send_message(f"Scraping Cub for {location['name']}")
            for product in scrape_cub_products(location["code"]):
                db.save(location["id"], product)
            send_message(f"Finished scraping Cub for {location['name']}")

    calculate_stats()
    db.update_bargains()

    send_message("END")


def run_multi_threaded():
    # ====================================================================
    # Create a queue for database operations
    db_queue = queue.Queue()
    # Flag to signal when scraping is complete
    scraping_done = threading.Event()

    # Get all scraper information in the main thread
    with Database("prices.db") as db:
        fresh_thyme_locations = db.get_locations("Fresh Thyme")
        trader_joes_locations = db.get_locations("Trader Joe's")
        aldi_locations = db.get_locations("ALDI")
        hyvee_locations = db.get_locations("Hy-Vee")
        cub_locations = db.get_locations("Cub")

    # Database worker thread - handles all DB operations
    def db_worker():
        with Database("prices.db") as db:
            while not (scraping_done.is_set() and db_queue.empty()):
                try:
                    # Get a database operation with timeout
                    location_id, product = db_queue.get(timeout=0.5)
                    db.save(location_id, product)
                    db_queue.task_done()
                except queue.Empty:
                    # Just continue and check conditions again
                    continue
                except Exception as e:
                    print(f"Error in database worker: {e}")
                    db_queue.task_done()


    # Start the database worker thread
    db_thread = threading.Thread(target=db_worker)
    db_thread.daemon = False
    db_thread.start()

    def run_fresh_thyme_scraper():
        for location in fresh_thyme_locations:
            try:
                send_message(f"Scraping Fresh Thyme for {location['name']}")
                products = scrape_fresh_thyme_products(location["code"])
                for product in products:
                    db_queue.put((location["id"], product))
                send_message(f"Fresh Thyme scraping for location {location['code']} completed")
            except Exception as e:
                send_message(f"Error in Fresh Thyme scraper for location {location['code']}")

    def run_trader_joes_scraper():
        for location in trader_joes_locations:
            try:
                send_message(f"Scraping Trader Joe's for {location['name']}")
                products = scrape_trader_joes_products(location["code"])
                for product in products:
                    db_queue.put((location["id"], product))
                send_message(f"Trader Joe's scraping for location {location['code']} completed")
            except Exception as e:
                send_message(f"Error in Trader Joe's scraper for location {location['code']}")

    def run_aldi_scraper():
        for location in aldi_locations:
            try:
                send_message(f"Scraping ALDI for {location['name']}")
                products = scrape_aldi_products(location["code"])
                for product in products:
                    db_queue.put((location["id"], product))
                send_message(f"ALDI scraping for location {location['code']} completed")
            except Exception as e:
                send_message(f"Error in ALDI scraper for location {location['code']}")

    def run_hyvee_scraper():
        for location in hyvee_locations:
            try:
                send_message(f"Scraping Hy-Vee for {location['name']}")
                products = scrape_hyvee_products(location["code"])
                for product in products:
                    db_queue.put((location["id"], product))
                send_message(f"Hy-Vee scraping for location {location['code']} completed")
            except Exception as e:
                send_message(f"Error in Hy-Vee scraper for location {location['code']}")

    def run_cub_scraper():
        for location in cub_locations:
            try:
                send_message(f"Scraping Cub for {location['name']}")
                products = scrape_cub_products(location["code"])
                for product in products:
                    db_queue.put((location["id"], product))
                send_message(f"Cub scraping for location {location['code']} completed")
            except Exception as e:
                send_message(f"Error in Cub scraper for location {location['code']}")

    send_message("START")

    # Run all scrapers in separate threads
    scraper_threads = [
        threading.Thread(target=run_fresh_thyme_scraper),
        threading.Thread(target=run_trader_joes_scraper),
        # threading.Thread(target=run_aldi_scraper),
        # threading.Thread(target=run_hyvee_scraper),
        # threading.Thread(target=run_cub_scraper)
    ]

    # Start all scraper threads
    for thread in scraper_threads:
        thread.start()

    # Wait for all scraper threads to complete
    for thread in scraper_threads:
        thread.join()

    # Signal database worker that scraping is done
    send_message("Waiting for database operations to finish...")
    scraping_done.set()

    # Wait for all database operations to complete
    db_queue.join()

    # Wait for database thread to finish
    db_thread.join()

    # Calculate stats and update bargains
    calculate_stats()
    db.update_bargains()

    send_message("END")


if __name__ == "__main__":
    run_multi_threaded()
    # run_single_threaded()
