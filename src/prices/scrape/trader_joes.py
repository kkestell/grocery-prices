import requests
import json
from typing import Generator, Any
from prices.scrape.util import retry, split_price, split_size_and_unit, get_simplified_category, normalize_units


def scrape_trader_joes_products(store_id: str = "713") -> Generator[dict[str, Any], None, None]:
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    }

    categories_query = """
    {
      categoryList(filters: null) {
        id
        level
        name
        path
        url_key
        product_count
        children {
          id
          level
          name
          path
          url_key
          product_count
          children {
            id
            level
            name
            path
            url_key
            product_count
            children {
              id
              level
              name
              path
              url_key
              product_count
              children {
                id
                level
                name
                path
                url_key
                product_count
                __typename
              }
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
    }
    """

    with retry():
        categories_response = requests.post(
            'https://www.traderjoes.com/api/graphql',
            headers=headers,
            json={"query": categories_query}
        )

    if categories_response.status_code != 200:
        return

    categories_data = categories_response.json()

    def extract_categories_with_products(categories):
        result = []
        for category in categories:
            if category.get('product_count', 0) > 0:
                result.append({
                    'id': category['id'],
                    'name': category['name']
                })

            if category.get('children'):
                result.extend(extract_categories_with_products(category['children']))

        return result

    try:
        all_categories = extract_categories_with_products(categories_data['data']['categoryList'])
    except KeyError as e:
        return

    processed_skus = set()
    total_products = 0

    for i, category_info in enumerate(all_categories):
        category_id = category_info['id']
        category_name = category_info['name']

        page = 1
        page_size = 50
        category_products = 0

        while True:
            products_query = """
            query SearchProducts($categoryId: String, $currentPage: Int, $pageSize: Int, $storeCode: String = "713", $availability: String = "1", $published: String = "1") {
              products(
                filter: {store_code: {eq: $storeCode}, published: {eq: $published}, availability: {match: $availability}, category_id: {eq: $categoryId}}
                sort: {popularity: DESC}
                currentPage: $currentPage
                pageSize: $pageSize
              ) {
                items {
                  sku
                  item_title
                  category_hierarchy {
                    id
                    name
                    __typename
                  }
                  sales_size
                  sales_uom_description
                  price_range {
                    minimum_price {
                      final_price {
                        currency
                        value
                        __typename
                      }
                      __typename
                    }
                    __typename
                  }
                  retail_price
                  item_characteristics
                  __typename
                }
                total_count
                pageInfo: page_info {
                  currentPage: current_page
                  totalPages: total_pages
                  __typename
                }
                __typename
              }
            }
            """

            variables = {
                "storeCode": store_id,
                "availability": "1",
                "published": "1",
                "categoryId": str(category_id),
                "currentPage": page,
                "pageSize": page_size
            }

            with retry():
                products_response = requests.post(
                    'https://www.traderjoes.com/api/graphql',
                    headers=headers,
                    json={"operationName": "SearchProducts", "variables": variables, "query": products_query}
                )

            if products_response.status_code != 200:
                break

            products_data = products_response.json()

            try:
                products = products_data['data']['products']['items']

                # If the server returned no products, break
                if not products:
                    break

                for product in products:
                    sku = product['sku']

                    if sku in processed_skus:
                        continue

                    processed_skus.add(sku)

                    name = product['item_title'].strip()

                    price = None
                    if product.get('price_range') and product['price_range']['minimum_price']['final_price']['value']:
                        price = product['price_range']['minimum_price']['final_price']['value']
                    elif product.get('retail_price'):
                        try:
                            price = float(product['retail_price'])
                        except (ValueError, TypeError):
                            price = None

                    raw_size = str(product.get('sales_size', ''))
                    size, unit = split_size_and_unit(raw_size)
                    if not unit and product.get('sales_uom_description'):
                        unit = normalize_units(product.get('sales_uom_description', ''))

                    brand = "Trader Joe's"
                    available = True
                    snap_eligible = False

                    if product.get('category_hierarchy'):
                        hierarchy = product['category_hierarchy']
                        raw_category = hierarchy[-1]['name'] if hierarchy else category_name
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

                    total_products += 1
                    category_products += 1
                    yield product_info

                page_info = products_data['data']['products']['pageInfo']
                if page_info['currentPage'] >= page_info['totalPages']:
                    break

                page += 1

            except KeyError as e:
                break