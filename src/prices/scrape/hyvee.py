import requests

from prices.scrape.util import retry, split_size_and_unit, get_simplified_category


def get_category_groups(store_id, category_id, aisle_id):
    url = 'https://www.hy-vee.com/aisles-online/api/graphql/two-legged/getCategoryGroups'

    headers = {
        'content-type': 'application/json',
        'origin': 'https://www.hy-vee.com',
        'referer': f'https://www.hy-vee.com/aisles-online/category/{category_id.lower()}',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    }

    data = {
        "operationName": "getCategoryGroups",
        "variables": {
            "input": {
                "aisleId": aisle_id,
                "categoryId": category_id,
                "storeId": int(store_id) if isinstance(store_id, str) else store_id
            }
        },
        "query": """query getCategoryGroups($input: CategoriesGroupsInput!) {
  categoriesGroups(input: $input) {
    responseId
    categoryId
    categoryName
    categoriesGroups {
      responseGroupId
      categoriesGroupId
      categoriesGroupName
      categoriesGroupProductImageUrl
      categoriesGroupChildCategories {
        childCategoryId
        childCategoryName
        __typename
      }
      categoriesGroupProducts {
        productId
        slotTypeId
        responseProductId
        shelfProductId
        isSponsored
        __typename
      }
      __typename
    }
    __typename
  }
}"""
    }

    with retry():
        response = requests.post(url, headers=headers, json=data)

    return response.json()

# {
#   // Root data object
#   "data": {
#     // Main product information object
#     "product": {
#       // Unique identifier for the product
#       "productId": "3002827",
#       // Size/quantity of the product
#       "size": "1 ct ",
#       // Information about available coupons (none available)
#       "couponProductV4": null,
#       // Detailed item information
#       "item": {
#         // Unique identifier for the specific item
#         "itemId": "a40d8f14-9c74-4e49-bb2b-ea9d0302e308",
#         // Short description of the product
#         "description": "OXO Tot Baby Block Frzr Cntnrs",
#         // Status of the item in the e-commerce system (available for purchase)
#         "ecommerceStatus": "ACTIVE",
#         // Retailer or source of the product
#         "source": "HYVEE",
#         // Array of product images
#         "images": [
#           {
#             // Unique identifier for the image
#             "imageId": "da4b0b7c-8cca-4d30-b44e-c2217daff75e",
#             // URL to the image
#             "url": "https://8e9d5b8b8dcb9208ef3f-01db2a53ae0368d03387780ee86ead55.ssl.cf2.rackcdn.com/0719812942030_CF_hyvee_default_large.jpeg",
#             // Indicates this is the main product image
#             "isPrimaryImage": true,
#             // GraphQL type name for this object
#             "__typename": "ItemImage"
#           }
#         ],
#         // Average weight of one unit (not applicable)
#         "unitAverageWeight": null,
#         // WIC (Women, Infants, and Children) program eligibility (not eligible)
#         "WicItems": null,
#         // GraphQL type name for this object
#         "__typename": "Item",
#         // Array of retail-specific item information
#         "retailItems": [
#           {
#             // Unique identifier for the retail item
#             "retailItemId": "341ed0d9-90d8-49dd-8317-0f0152491f0a",
#             // Base price of the product
#             "basePrice": 11.99,
#             // Quantity for the base price
#             "basePriceQuantity": 1,
#             // Unit of measure information
#             "soldByUnitOfMeasure": {
#               // Code for unit of measure (Count)
#               "code": "CT",
#               // Name of unit of measure
#               "name": "Count",
#               // GraphQL type name for this object
#               "__typename": "ItemUnitOfMeasure"
#             },
#             // Price displayed on the tag
#             "tagPrice": 11.99,
#             // Quantity for the tag price
#             "tagPriceQuantity": 1,
#             // Price displayed in e-commerce
#             "ecommerceTagPrice": 11.99,
#             // Quantity for e-commerce tag price
#             "ecommerceTagPriceQuantity": 1,
#             // Special price for members (none available)
#             "memberTagPrice": null,
#             // Quantity for member tag price (none available)
#             "memberTagPriceQuantity": null,
#             // GraphQL type name for this object
#             "__typename": "RetailItem"
#           }
#         ]
#       },
#       // GraphQL type name for this object
#       "__typename": "product"
#     },
#
#     // Store-specific product information
#     "storeProducts": {
#       // Array of store products
#       "storeProducts": [
#         {
#           // Unique identifier for store-specific product
#           "storeProductId": "52623631",
#           // Reference to the main product ID
#           "productId": 3002827,
#           // Unique identifier for the store
#           "storeId": 1759,
#           // Indicates if the product is on sale
#           "onSale": false,
#           // Indicates if the product qualifies for fuel saver program
#           "onFuelSaver": false,
#           // Indicates if the product is sold by weight
#           "isWeighted": false,
#           // Indicates if the product is alcoholic
#           "isAlcohol": false,
#           // Amount saved on fuel with purchase
#           "fuelSaver": 0,
#           // Current price
#           "price": 11.99,
#           // Quantity for the current price
#           "priceMultiple": 1,
#           // Base price
#           "basePrice": 11.99,
#           // Quantity for the base price
#           "basePriceMultiple": 1,
#           // Indicates if the tag price is lower than regular price
#           "isTagPriceLower": false,
#
#           // Department information
#           "department": {
#             // Unique identifier for the department
#             "departmentId": "68",
#             // GraphQL type name for this object
#             "__typename": "department",
#             // URL path for the department
#             "linkPath": "DP21838247",
#             // Name of the department
#             "name": "Baby"
#           },
#
#           // Additional descriptions for the store product (empty)
#           "storeProductDescriptions": [],
#           // Unique identifier for the subcategory
#           "subcategoryId": 8699,
#
#           // Department group information
#           "departmentGroup": {
#             // Unique identifier for the department group
#             "departmentGroupId": "8",
#             // URL path for the department group
#             "linkPath": "DG21838244",
#             // Name of the department group
#             "name": "Baby",
#             // GraphQL type name for this object
#             "__typename": "departmentGroup"
#           },
#
#           // Category information
#           "category": {
#             // Unique identifier for the category
#             "categoryId": "1700",
#             // Reference to the department ID
#             "departmentId": 68,
#             // URL path for the category
#             "linkPath": "CT21838257",
#             // Name of the category
#             "name": "Feeding & Pacifiers",
#
#             // Array of subcategories
#             "subcategories": [
#               {
#                 // Unique identifier for the subcategory
#                 "subcategoryId": "8699",
#                 // URL path for the subcategory
#                 "linkPath": "SC21838319",
#                 // Name of the subcategory
#                 "name": "Baby Feeding",
#                 // GraphQL type name for this object
#                 "__typename": "subcategory"
#               },
#               {
#                 // Unique identifier for another subcategory
#                 "subcategoryId": "12637",
#                 // URL path for the subcategory
#                 "linkPath": "SC23997899",
#                 // Name of the subcategory
#                 "name": "Pacifiers",
#                 // GraphQL type name for this object
#                 "__typename": "subcategory"
#               }
#             ],
#
#             // GraphQL type name for this object
#             "__typename": "category"
#           },
#
#           // Product variations information
#           "variations": [
#             {
#               // Type of variation
#               "name": "Count",
#               // Array of variation attributes
#               "variationsAttributes": [
#                 {
#                   // Specific variation value
#                   "name": "4 Count",
#                   // Products with this variation
#                   "variationsProducts": [
#                     {
#                       // Product ID for this variation
#                       "productId": 3002827,
#                       // Product information
#                       "product": {
#                         // Product ID
#                         "productId": "3002827",
#                         // Full product name
#                         "name": "OXO Tot Baby Blocks 6oz Freezer Storage Containers",
#                         // GraphQL type name for this object
#                         "__typename": "product"
#                       },
#                       // GraphQL type name for this object
#                       "__typename": "VariationsProduct"
#                     }
#                   ],
#                   // GraphQL type name for this object
#                   "__typename": "VariationsAttribute"
#                 }
#               ],
#               // GraphQL type name for this object
#               "__typename": "VariationsGroup"
#             }
#           ],
#
#           // GraphQL type name for this object
#           "__typename": "storeProduct"
#         }
#       ],
#
#       // GraphQL type name for this object
#       "__typename": "pageableStoreProducts"
#     }
#   }
# }

def get_hyvee_product(product_id, store_id):
    url = 'https://www.hy-vee.com/aisles-online/api/graphql/two-legged/getProductDetailsWithPrice'
    headers = {
        'content-type': 'application/json',
        'origin': 'https://www.hy-vee.com',
        'referer': f'https://www.hy-vee.com/aisles-online/p/{product_id}',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    }
    data = {
        "operationName": "getProductDetailsWithPrice",
        "variables": {
            "locationIds": ["266a52f4-0e7a-4729-bc6f-25c6ebaca111"],
            "retailItemEnabled": True,
            "targeted": False,
            "wicEnabled": True,
            "pickupLocationHasLocker": False,
            "productId": int(product_id) if isinstance(product_id, str) else product_id,
            "storeId": int(store_id) if isinstance(store_id, str) else store_id
        },
        "query": """query getProductDetailsWithPrice($locationIds: [ID!] = [], $retailItemEnabled: Boolean = false, $productId: Int!, $storeId: Int, $pickupLocationHasLocker: Boolean!, $targeted: Boolean = false, $wicEnabled: Boolean = false) {
  product(productId: $productId) {
    productId
    size
    item {
      itemId
      description
      ecommerceStatus
      source
      images {
        imageId
        url
        isPrimaryImage
        __typename
      }
      retailItems(locationIds: $locationIds) @include(if: $retailItemEnabled) {
        retailItemId
        basePrice
        basePriceQuantity
        tagPrice
        tagPriceQuantity
        memberTagPrice
        memberTagPriceQuantity
        __typename
      }
      __typename
    }
    __typename
  }
  storeProducts(where: {productId: $productId, storeId: $storeId, isActive: true}) {
    storeProducts {
      storeProductId
      productId
      storeId
      onSale
      onFuelSaver
      isWeighted
      isAlcohol
      fuelSaver
      price
      priceMultiple
      basePrice
      basePriceMultiple
      isTagPriceLower
      __typename
    }
    __typename
  }
}"""
    }

    with retry():
        response = requests.post(url, headers=headers, json=data)
    return response.json()


def get_all_products(store_id, category_id, aisle_id):
    categories = get_category_groups(store_id, category_id, aisle_id)

    if not categories or 'data' not in categories:
        raise ValueError(f"Failed to get category groups for {category_id}")


    # Process each category group
    category_groups = categories['data']['categoriesGroups']['categoriesGroups']
    for group in category_groups:
        group_name = group['categoriesGroupName']
        # results[group_name] = []

        # Process direct products in this group
        for product in group['categoriesGroupProducts']:
            product_id = int(product['productId'])
            product_details = get_hyvee_product(product_id, store_id)

            if product_details and 'data' in product_details:
                # Extract data from product_details
                product_data = product_details['data']['product']
                item_data = product_data.get('item', {})

                # Get store product info (for price and availability)
                store_products = product_details['data'].get('storeProducts', {}).get('storeProducts', [])
                store_product = store_products[0] if store_products else {}

                # Use department name as category
                category = ""
                if store_product and 'department' in store_product:
                    category = store_product['department'].get('name', '')
                    category = get_simplified_category(category)

                # Extract details
                sku = str(product_id)
                name = item_data.get('description', '')
                price = store_product.get('price', 0)
                size = product_data.get('size', '')
                size, unit = split_size_and_unit(size)

                # Brand extraction (often part of the product name)
                brand = ""
                # if ' ' in name:
                #     brand = name.split(' ')[0]  # Simple extraction - first word as brand

                # Unit of measure (from retail items if available)
                # unit = ""
                # if 'retailItems' in item_data and item_data['retailItems']:
                #     if 'soldByUnitOfMeasure' in item_data['retailItems'][0]:
                #         unit = item_data['retailItems'][0]['soldByUnitOfMeasure'].get('name', '')

                # SNAP eligibility (approximation - would need specific API data)
                snap_eligible = False  # Default value

                # Availability based on ecommerceStatus
                available = item_data.get('ecommerceStatus', '') == 'ACTIVE'

                product = {
                    'sku': sku,
                    'category': category,
                    'name': name,
                    'price': price,
                    'size': size,
                    'brand': brand,
                    'unit': unit,
                    'snap_eligible': snap_eligible,
                    'available': available
                }

                yield product

def scrape_hyvee_products(location_id: str):
    categories = [
        "BABY",
        "BAKERY",
        "BEVERAGES",
        "DAIRY",
        "DELI",
        "FROZEN",
        "FRESH_FRUITS_AND_VEGETABLES",
        "HEALTH_AND_BEAUTY",
        "HOUSEHOLD_AND_LAUNDRY",
        "MEAT_AND_SEAFOOD",
        "PANTRY",
        "PETS",
        "PREPARED_FOOD"
    ]

    # WTF is this?
    aisle_id = "b162d1a2fd29451c9ccb791be0cc2edd"

    seen_products = {}

    for category_id in categories:
        for product in get_all_products(location_id, category_id, aisle_id):
            if product["sku"] in seen_products.keys():
                print("DUPLICATE")
                print(product)
                print(seen_products[product["sku"]])
                continue
            seen_products[product["sku"]] = product
            yield product
