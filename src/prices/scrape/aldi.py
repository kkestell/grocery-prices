from logging import Logger

import requests
from prices.scrape.util import retry, split_price, split_size_and_unit, get_simplified_category


# {
#   // Universal product code or SKU identifier
#   "sku": "0000000000000005",
#
#   // Product display name
#   "name": "Original Kettle Chips, 8 oz",
#
#   // Brand/manufacturer name
#   "brandName": "Clancy's",
#
#   // URL-friendly version of product name for web links
#   "urlSlugText": "clancy-s-original-kettle-chips-8-oz",
#
#   // Age restriction status (none for this product)
#   "ageRestriction": null,
#
#   // Alcohol content indicator (none for this product)
#   "alcohol": null,
#
#   // Product discontinuation status
#   "discontinued": false,
#
#   // Additional information about discontinuation (not applicable)
#   "discontinuedNote": null,
#
#   // Indicator if product cannot be purchased
#   "notForSale": false,
#
#   // Explanation why product can't be purchased (not applicable)
#   "notForSaleReason": null,
#
#   // Minimum quantity that can be purchased
#   "quantityMin": 1,
#
#   // Maximum quantity that can be purchased in a single order
#   "quantityMax": 99,
#
#   // Increment value for quantity selection
#   "quantityInterval": 1,
#
#   // Default quantity shown in shopping interface
#   "quantityDefault": 1,
#
#   // Unit of measurement for quantity
#   "quantityUnit": "each",
#
#   // Type of weight measurement system used
#   "weightType": "0",
#
#   // Product size/weight as displayed to customer
#   "sellingSize": "8 oz",
#
#   // Date when product will be available (not applicable)
#   "onSaleDateDisplay": null,
#
#   // Price information
#   "price": {
#     // Price in cents (2.15 USD)
#     "amount": 215,
#
#     // Relevant price used for calculations (same as amount)
#     "amountRelevant": 215,
#
#     // Formatted display of relevant price
#     "amountRelevantDisplay": "$2.15",
#
#     // Bottle/container deposit fee (none for this product)
#     "bottleDeposit": 0,
#
#     // Formatted display of bottle deposit
#     "bottleDepositDisplay": "$0.00",
#
#     // Unit price, likely price per ounce (27 cents)
#     "comparison": 27,
#
#     // Formatted unit price display (not provided)
#     "comparisonDisplay": null,
#
#     // Currency code (USD)
#     "currencyCode": "USD",
#
#     // Currency symbol ($)
#     "currencySymbol": "$",
#
#     // Price per unit measure (not applicable)
#     "perUnit": null,
#
#     // Formatted display of per unit price
#     "perUnitDisplay": null,
#
#     // Previous/sale price comparison (not applicable)
#     "wasPriceDisplay": null
#   },
#
#   // Country-specific product information
#   "countryExtensions": {
#     // Indicates product is eligible for SNAP benefits (food stamps) in the US
#     "usSnapEligible": true
#   },
#
#   // Product images and assets
#   "assets": [
#     {
#       // Front image URL template
#       "url": "https://dm.cms.aldi.cx/is/image/prod1amer/product/jpg/scaleWidth/{width}/1413ebde-2063-4587-8cd3-e5fb61dfe010/{slug}",
#
#       // Maximum image width available
#       "maxWidth": 1000,
#
#       // Maximum image height available
#       "maxHeight": 1000,
#
#       // MIME type of the image
#       "mimeType": "image/*",
#
#       // Asset type code (FR01 likely means "Front view")
#       "assetType": "FR01"
#     },
#     {
#       // Back image URL template
#       "url": "https://dm.cms.aldi.cx/is/image/prod1amer/product/jpg/scaleWidth/{width}/e8f7d5b4-cd1c-496b-99a2-faed672af682/{slug}",
#
#       // Maximum image width available
#       "maxWidth": 1000,
#
#       // Maximum image height available
#       "maxHeight": 1000,
#
#       // MIME type of the image
#       "mimeType": "image/*",
#
#       // Asset type code (BA01 likely means "Back view")
#       "assetType": "BA01"
#     }
#   ]
# }

def scrape_aldi_products(store_id: str, quick: bool = False):
    limit = 30
    offset = 0

    while True:
        url = f"https://api.aldi.us/v3/product-search?currency=USD&serviceType=pickup&limit={limit}&offset={offset}&sort=relevance&servicePoint={store_id}"

        with retry():
            response = requests.get(url)

        if response.status_code != 200:
            break

        data = response.json()["data"]
        products = 0

        for item in data:
            name = " ".join(item["name"].split())
            sku = item["sku"]
            price = split_price(item["price"]["comparisonDisplay"] or item["price"]["amountRelevantDisplay"])
            size, unit = split_size_and_unit(item.get("sellingSize"))
            brand = item.get("brandName") or "ALDI"
            snap_eligible = item.get("countryExtensions", {}).get("usSnapEligible", False)
            available = not (item.get("discontinued", False) or item.get("notForSale", False))

            category = "Unknown"
            if not quick:
                with retry():
                    detail_response = requests.get(f"https://api.aldi.us/v2/products/{sku}?servicePoint={store_id}&serviceType=pickup")

                if detail_response.status_code == 200:
                    detail_data = detail_response.json()["data"]

                    categories = detail_data.get("categories", [])
                    if categories:
                        category = categories[0].get("name")
                        category = get_simplified_category(category)

            if name == "#N/A":
                name = item.get("urlSlugText", None)
                if name:
                    name = name.replace("-", " ").title()
                print(item)
                # print(detail_data)
                print(name)
                print("====================================")

            product = {
                'sku': sku,
                'name': name,
                'price': price,
                'size': size,
                'brand': brand,
                'unit': unit,
                'snap_eligible': snap_eligible,
                'available': available
            }

            if not quick:
                product['category'] = category

            products += 1

            yield product

        if not products:
            break

        offset += limit
