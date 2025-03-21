import random
import time

import requests
from prices.scrape.util import retry, split_price, split_size_and_unit, get_simplified_category

# {
#   // Metadata tracking information
#   "metadata": {
#     // Unique identifier for this product update iteration
#     "iterationCorrelationId": "61c6f645-b864-4b4b-aa05-48383272aaa2",
#     // When this product data was last modified
#     "lastModification": "2025-03-02T13:33:41",
#     // Base correlation ID (matches iteration ID in this case)
#     "correlationId": "61c6f645-b864-4b4b-aa05-48383272aaa2"
#   },
#
#   // UPC/product identifier
#   "productId": "00018000005017",
#
#   // Store keeping unit/inventory identifier (same as productId)
#   "sku": "00018000005017",
#
#   // Product display name
#   "name": "Pillsbury Cinnamon Rolls, Original Icing",
#
#   // Detailed product description
#   "description": "Slow down and savor the morning together with warm, freshly-baked Pillsbury Cinnamon Rolls. It's easy to make any day cinnamony sweet with Pillsbury's ready-to-bake dough and premade icing. These refrigerated cinnamon rolls make a great weekday breakfast or special holiday treat. This family favorite breakfast is ready in just minutes. Imagine the memories you'll make.\n\nThese decadent cinnamon rolls provide a sweet reason for your family to gather around the table. Simply heat the oven to 400° F (or 375° F for a nonstick pan), place the rolls in a greased round pan with the cinnamon top up, bake for 13–17 minutes or until golden brown, and spread the delicious icing on top. Nothing wakes up a day like an oven-fresh cinnamon roll.",
#
#   // Brand/manufacturer name
#   "brand": "Pillsbury",
#
#   // Price as numeric value
#   "priceNumeric": 4.99,
#
#   // Full price as numeric value (same as priceNumeric)
#   "wholePrice": 4.99,
#
#   // Formatted price with currency symbol
#   "price": "$4.99",
#
#   // Advertisement identifier
#   "adId": "display_jELqwtTmVQ_v9an4Gk5areZGTpoKEAoOMDAwMTgwMDAwMDUwMTcSABoMCMPdt74GENnbqMUDIgIIAQ==",
#
#   // Price per individual unit with formatted display
#   "pricePerUnit": "$0.62 each",
#
#   // Size unit information
#   "unitOfSize": {
#     // Unit abbreviation (none specified)
#     "abbreviation": "",
#     // Type of unit
#     "type": "each",
#     // Display label for the unit
#     "label": "Each",
#     // Quantity in package
#     "size": a8.0
#   },
#
#   // Measurement unit information
#   "unitOfMeasure": {
#     // Unit abbreviation (none specified)
#     "abbreviation": "",
#     // Type of unit
#     "type": "each",
#     // Display label for the unit
#     "label": "Each",
#     // Quantity for measurement
#     "size": 1.0
#   },
#
#   // Price unit information
#   "unitOfPrice": {
#     // Unit abbreviation (none specified)
#     "abbreviation": "",
#     // Type of unit
#     "type": "each",
#     // Display label for the unit
#     "label": "Each",
#     // Quantity for pricing
#     "size": 1.0
#   },
#
#   // Tax information (empty for this product)
#   "taxDetails": [],
#
#   // How the product is sold
#   "sellBy": "Each",
#
#   // Product attributes/flags
#   "attributes": {
#     // Whether product has alcohol restrictions
#     "alcohol Restricted": false,
#     // Whether product is gluten-free
#     "gluten Free": false,
#     // Whether product is organic
#     "organic": false,
#     // Whether product is pickup only (cannot be delivered)
#     "pickup Only": false,
#     // Whether product is eligible for SNAP benefits (Y=Yes)
#     "aurus SNAP Flag": "Y",
#     // Whether product is taxable (N=No)
#     "aurus Tax Flag": "N",
#     // Whether product is sold by weight (N=No)
#     "aurus Weighted Flag": "N",
#     // Bottle deposit amount (none for this product)
#     "aurus Bottle Deposit Amount": "0.00"
#   },
#
#   // Primary category classification
#   "defaultCategory": [
#     {
#       // Category unique identifier
#       "categoryId": "3bd8490e-430b-4f03-98f2-d67148df21e0",
#       // Retailer identifier code
#       "retailerId": "070306",
#       // Category name
#       "category": "Pastries & Pie Crusts",
#       // Full category path/hierarchy
#       "categoryBreadcrumb": "Grocery/Dairy & Eggs/Cookies & Dough/Pastries & Pie Crusts"
#     }
#   ],
#
#   // All categories product belongs to
#   "categories": [
#     {
#       "categoryId": "743e398c-8207-453e-a5a5-5399438abd50",
#       "retailerId": "Grocery",
#       "category": "Grocery",
#       "categoryBreadcrumb": "Grocery"
#     },
#     {
#       "categoryId": "6b5a02a1-6e51-4b89-923a-a2e14958fb2d",
#       "retailerId": "070000",
#       "category": "Dairy & Eggs",
#       "categoryBreadcrumb": "Grocery/Dairy & Eggs"
#     },
#     {
#       "categoryId": "0b248b72-c9bd-4460-a680-8a9a25b721ee",
#       "retailerId": "070300",
#       "category": "Cookies & Dough",
#       "categoryBreadcrumb": "Grocery/Dairy & Eggs/Cookies & Dough"
#     },
#     {
#       "categoryId": "3bd8490e-430b-4f03-98f2-d67148df21e0",
#       "retailerId": "070306",
#       "category": "Pastries & Pie Crusts",
#       "categoryBreadcrumb": "Grocery/Dairy & Eggs/Cookies & Dough/Pastries & Pie Crusts"
#     }
#   ],
#
#   // Whether product is marked as favorite by user
#   "isFavorite": false,
#
#   // Whether user has purchased this product before
#   "isPastPurchased": false,
#
#   // Product image URLs
#   "image": {
#     // Default image URL
#     "default": "https://images.cdn.cub.com/cell/4bccde20-630a-4f1e-a13a-a764e45e5786.jpeg",
#     // Small/cell view image URL
#     "cell": "https://images.cdn.cub.com/cell/4bccde20-630a-4f1e-a13a-a764e45e5786.jpeg",
#     // Detail view image URL
#     "details": "https://images.cdn.cub.com/detail/4bccde20-630a-4f1e-a13a-a764e45e5786.jpeg",
#     // Zoomed in image URL
#     "zoom": "https://images.cdn.cub.com/zoom/4bccde20-630a-4f1e-a13a-a764e45e5786.jpeg",
#     // Template URL for different sizes
#     "template": "https://images.cdn.cub.com/{size}/4bccde20-630a-4f1e-a13a-a764e45e5786.jpeg"
#   },
#
#   // Basic promotion information (none for this product)
#   "promotionInfo": [],
#
#   // Active promotions (none for this product)
#   "promotions": [],
#
#   // Points-based promotions (none for this product)
#   "pointsBasedPromotions": [],
#
#   // Count of all applicable promotions
#   "totalNumberOfPromotions": 0,
#
#   // Whether product is currently in stock
#   "available": true,
#
#   // Temporary price reduction information (none for this product)
#   "tprPrice": [],
#
#   // Source of the price (regular pricing vs. special/sale)
#   "priceSource": "regular",
#
#   // Whether product has configurable options
#   "isConfigurable": false
# }


# wget https://www.cub.com/sm/pickup/rsid/1650/ -O cub.html
# grep -oP 'href="/categories/\K[^"]+' cub.html | sed 's/.*-id-//' | sort | uniq > cub_categories.txt
category_ids = [
    "120000",  # Fruits & Vegetables
    "030000",   # Beverages
    "010000",   # Baby
    "070000",  # Dairy & Eggs
    "170000",  # Pantry
    "160000",  # Meat & Seafood
    "150000",  # Household Essentials
    "040000",  # Bread & Bakery
    "110000",  # Frozen
]


def scrape_cub_products(location_id: str):
    limit = 50
    product_skus = set()

    for category_id in category_ids:
        offset = 0

        while True:
            url = f"https://storefrontgateway.cub.com/api/stores/{location_id}/categories/{category_id}/search?take={limit}&skip={offset}&page={offset // limit + 1}&sort=relevance"

            with retry():
                response = requests.get(url)
                data = response.json()

            if "items" not in data or not data["items"]:
                break

            for item in data["items"]:
                sku = item.get("sku")
                if sku in product_skus:
                    continue

                name = item.get("name", "Unknown")

                size = "1.0 each"
                if "unitOfSize" in item and item["unitOfSize"]:
                    size_value = item["unitOfSize"].get("size", 1.0)
                    size_type = item["unitOfSize"].get("abbreviation") or item["unitOfSize"].get("type", "each")
                    size = f"{size_value} {size_type}"

                size, unit = split_size_and_unit(size)

                # Get unit information
                # unit = "each"
                # if "unitOfMeasure" in item and item["unitOfMeasure"]:
                #     unit = item["unitOfMeasure"].get("type", "each")

                # Get brand information
                brand = item.get("brand", "")

                # Get SNAP eligibility
                snap_eligible = False
                if "attributes" in item and item["attributes"]:
                    snap_flag = item["attributes"].get("aurus SNAP Flag", "N")
                    snap_eligible = (snap_flag == "Y")

                # Check availability
                available = item.get("available", True)

                price_str = None
                if "price" in item and item["price"]:
                    if isinstance(item["price"], str) and "avg/ea" in item["price"]:
                        price_str = item.get("pricePerUnit")
                    else:
                        price_str = item["price"]
                elif "priceNumeric" in item:
                    price_str = f"${item['priceNumeric']}"

                categories = item.get("categories", [])
                if categories:
                    category = categories[1].get("category")
                    category = get_simplified_category(category)
                else:
                    raise ValueError(f"Category not found for {sku}")

                if price_str:
                    price = split_price(price_str)
                    product_skus.add(sku)
                    product = {
                        'sku': sku,
                        'name': name,
                        'category': category,
                        'price': price,
                        'size': size,
                        'brand': brand,
                        'unit': unit,
                        'snap_eligible': snap_eligible,
                        'available': available
                    }
                    yield product

            if len(data["items"]) < limit:
                break

            offset += limit
