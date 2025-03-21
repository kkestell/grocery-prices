import requests
import re
from typing import Generator, Any
from prices.scrape.util import retry, split_price, split_size_and_unit, get_simplified_category, normalize_units


def scrape_fresh_thyme_products(store_id: str = "508") -> Generator[dict[str, Any], None, None]:
    headers = {
        "accept": "application/json",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }

    # Explicitly defined categories from the provided HTML
    categories = [
        ("69298", "Supplements"),
        ("69288", "OTC Internal"),
        ("69292", "Baby & Kids"),
        ("69235", "Vitamins and Minerals"),
        ("69237", "Multivitamins"),
        ("69238", "Single Vitamins"),
        ("69239", "Minerals"),
        ("69245", "Digestive Health"),
        ("69246", "Probiotics"),
        ("69247", "Enzymes"),
        ("69266", "Digestive Aids"),
        ("69225", "Wellness"),
        ("69228", "Superfoods & Greens"),
        ("69229", "Calcium & Joint Health"),
        ("69231", "Heart Health"),
        ("69232", "Antioxidants"),
        ("69233", "Women's & Men's Health"),
        ("69234", "Children's Health"),
        ("69297", "Children's Vitamins"),
        ("69296", "Children's Supplements"),
        ("69227", "Nutritional Oils"),
        ("69286", "Plant Oils"),
        ("69285", "Fish Oils"),
        ("69267", "CBD"),
        ("69240", "Protein and Fitness"),
        ("69283", "Collagen"),
        ("69241", "Protein Powders & Shakes"),
        ("69243", "Amino Acids"),
        ("69244", "Weight Loss & Diet"),
        ("69242", "Sports Nutrition"),
        ("69248", "Herbs & Natural Remedies"),
        ("69249", "Mood & Sleep"),
        ("69250", "Seasonal Wellness & Immune"),
        ("69251", "Homeopathy"),
        ("69230", "Herbs"),
        ("69252", "Cleanse & Detox"),
        ("12994", "Bakery"),
        ("68949", "Tortillas & Flat Bread"),
        ("68950", "Breakfast Bakery"),
        ("68951", "Bread"),
        ("68952", "Bakery Desserts"),
        ("68953", "Buns & Rolls"),
        ("13003", "Frozen"),
        ("69014", "Frozen Pizza & Meals"),
        ("69006", "Vegan & Vegetarian"),
        ("69008", "Breads & Doughs"),
        ("69009", "Appetizers & Sides"),
        ("69010", "Breakfast"),
        ("69011", "Produce"),
        ("69013", "Dessert, Ice Cream & Ice"),
        ("69016", "Meat & Seafood"),
        ("13004", "Produce"),
        ("69019", "Fresh Herbs"),
        ("69020", "Fresh Vegetables"),
        ("69021", "Packaged Vegetables & Fruits"),
        ("69022", "Fresh Fruits"),
        ("69047", "Floral"),
        ("69137", "Fresh Juice"),
        ("13007", "Meat & Seafood"),
        ("69025", "Packaged Poultry"),
        ("69026", "Seafood"),
        ("69027", "All Natural Meat"),
        ("69028", "All Natural Poultry"),
        ("69029", "Packaged Seafood"),
        ("69030", "Hot Dogs, Bacon & Sausage"),
        ("69031", "Packaged Meat"),
        ("69136", "All Natural Pork")
    ]

    processed_skus = set()

    for category_id, category_name in categories:
        page = 1
        page_size = 48
        skip = 0

        while True:
            url = f"https://storefrontgateway.freshthyme.com/api/stores/{store_id}/categories/{category_id}/search?take={page_size}&skip={skip}&page={page}"

            with retry():
                response = requests.get(url, headers=headers)

            if response.status_code != 200:
                break

            data = response.json()

            if not data.get('items'):
                break

            products = data.get('items', [])

            for product in products:
                sku = product.get('sku')

                if not sku or sku in processed_skus:
                    continue

                processed_skus.add(sku)

                name = product.get('name', '').strip()

                price = None
                if product.get('priceNumeric') is not None:
                    price = float(product.get('priceNumeric'))

                size = None
                unit = None
                if 'unitOfSize' in product:
                    unit_of_size = product['unitOfSize']
                    size = unit_of_size.get('size')
                    unit = normalize_units(unit_of_size.get('abbreviation', ''))

                if not unit:
                    unit = 'ea'

                brand = product.get('brand', '')
                available = product.get('available', False)
                snap_eligible = False

                if product.get('defaultCategory') and len(product['defaultCategory']) > 0:
                    raw_category = product['defaultCategory'][0].get('category', category_name)
                    category = get_simplified_category(raw_category)
                else:
                    category = get_simplified_category(category_name)

                product_info = {
                    'sku': sku,
                    'name': name,
                    'price': price,
                    'size': size,
                    'brand': brand,
                    'unit': unit,
                    'snap_eligible': snap_eligible,
                    'available': available,
                    'category': category
                }

                yield product_info

            if len(products) < page_size or data.get('total', 0) <= skip + len(products):
                break

            page += 1
            skip += page_size