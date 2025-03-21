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


# def run_multi_threaded():
#     # ====================================================================
#     # Create a queue for database operations
#     db_queue = queue.Queue()
#     # Flag to signal when scraping is complete
#     scraping_done = threading.Event()
#
#     # Get all scraper information in the main thread
#     with Database("prices.db") as db:
#         aldi_locations = db.get_locations("ALDI")
#         hyvee_locations = db.get_locations("Hy-Vee")
#         cub_locations = db.get_locations("Cub")
#
#
#     # Database worker thread - handles all DB operations
#     def db_worker():
#         with Database("prices.db") as db:
#             while not (scraping_done.is_set() and db_queue.empty()):
#                 try:
#                     # Get a database operation with timeout
#                     location_id, product = db_queue.get(timeout=0.5)
#                     db.save(location_id, product)
#                     db_queue.task_done()
#                 except queue.Empty:
#                     # Just continue and check conditions again
#                     continue
#                 except Exception as e:
#                     print(f"Error in database worker: {e}")
#                     db_queue.task_done()
#
#
#     # Start the database worker thread
#     db_thread = threading.Thread(target=db_worker)
#     db_thread.daemon = False
#     db_thread.start()
#
#     # Individual scraper functions
#     def run_aldi_scraper():
#         if not aldi_locations:
#             print("No ALDI locations found")
#             return
#
#         location = aldi_locations[0]  # Take first location as in original code
#         try:
#             products = scrape_aldi_products(location["code"])
#             for product in products:
#                 db_queue.put((location["id"], product))
#             print(f"ALDI scraping for location {location['code']} completed")
#         except Exception as e:
#             print(f"Error in ALDI scraper: {e}")
#
#
#     def run_hyvee_scraper():
#         if not hyvee_locations:
#             print("No Hy-Vee locations found")
#             return
#
#         location = hyvee_locations[0]  # Take first location as in original code
#         try:
#             products = scrape_hyvee_products(location["code"])
#             for product in products:
#                 db_queue.put((location["id"], product))
#             print(f"Hy-Vee scraping for location {location['code']} completed")
#         except Exception as e:
#             print(f"Error in Hy-Vee scraper: {e}")
#
#
#     def run_cub_scraper():
#         if not cub_locations:
#             print("No Cub locations found")
#             return
#
#         location = cub_locations[0]  # Take first location as in original code
#         try:
#             products = scrape_cub_products(location["code"])
#             for product in products:
#                 db_queue.put((location["id"], product))
#             print(f"Cub scraping for location {location['code']} completed")
#         except Exception as e:
#             print(f"Error in Cub scraper: {e}")
#
#
#     print("Starting scraping process...")
#     send_message("START")
#
#     # Run all scrapers in separate threads
#     scraper_threads = [
#         threading.Thread(target=run_aldi_scraper),
#         threading.Thread(target=run_hyvee_scraper),
#         threading.Thread(target=run_cub_scraper)
#     ]
#
#     # Start all scraper threads
#     for thread in scraper_threads:
#         thread.start()
#
#     # Wait for all scraper threads to complete
#     for thread in scraper_threads:
#         thread.join()
#
#     # Signal database worker that scraping is done
#     print("All scraping completed, waiting for database operations to finish...")
#     scraping_done.set()
#
#     # Wait for all database operations to complete
#     db_queue.join()
#
#     # Wait for database thread to finish
#     db_thread.join()
#
#     print("All operations completed")
#     send_message("END")


if __name__ == "__main__":
    # calculate_stats()
    # run_multi_threaded()
    run_single_threaded()

# if __name__ == "__main__":
#     with Database("prices.db") as db:
#         # ====================================================================
#         # db.seed()
#         # db.update_bargains()
#         # sys.exit(0)
#         # ====================================================================
#
#         # ====================================================================
#         # db.migrate()
#         # sys.exit(0)
#         # ====================================================================
#
#         # ====================================================================
#         # db.create_location("Cub", "Minnetonka", "1001038", "55345")
#         # db.create_location("Cub", "Plymouth", "1650", "55447")
#         # db.create_location("Cub", "Maple Grove", "1600", "55311")
#         # db.create_location("ALDI", "Medina, MN", "472-010", "55340")
#         # db.create_location("ALDI", "Maple Grove, MN", "472-094", "55369")
#         # db.create_location("ALDI", "Minnetonka, MN", "472-063", "55345")
#         # db.create_location("Hy-Vee", "Plymouth", "1531", "55447")
#         # sys.exit(0)
#         # ====================================================================
#
#         # ====================================================================
#         # db.update_bargains()
#         # sys.exit(0)
#         # ====================================================================
#
#         def scrape_aldi():
#             for location in db.get_locations("ALDI"):
#                 for product in scrape_aldi_products(location["code"]):
#                     db.save(location["id"], product)
#                 break
#
#         def scrape_hyvee():
#             for location in db.get_locations("Hy-Vee"):
#                 for product in scrape_hyvee_products(location["code"]):
#                     db.save(location["id"], product)
#                 break
#
#         def scrape_cub():
#             for location in db.get_locations("Cub"):
#                 for product in scrape_cub_products(location["code"]):
#                     db.save(location["id"], product)
#                 break
#
#         send_message("START")
#
#         scrape_aldi()
#         scrape_cub()
#         scrape_hyvee()
#
#         send_message("END")
