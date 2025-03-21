import time
from contextlib import contextmanager


@contextmanager
def retry():
   attempt = 0
   while True:
       attempt += 1
       try:
           time.sleep(0.5)
           yield
           break
       except Exception as e:
           if attempt >= 3:
               raise e
           delay = min(1.0 * (2 ** (attempt - 1)), 60.0)
           time.sleep(delay)


def normalize_units(unit: str) -> str:
    unit = unit.lower().strip()
    if not unit:
        return unit
    if unit in ["ounce", "ounces"]:
        return "oz"
    if unit in ["pound", "pounds"]:
        return "lb"
    if unit in ["gallon", "gallons"]:
        return "gal"
    if unit in ["quart", "quarts"]:
        return "qt"
    if unit in ["pint", "pints"]:
        return "pt"
    if unit in ["liter", "liters"]:
        return "L"
    if unit in ["milliliter", "milliliters"]:
        return "ml"
    if unit in ["gram", "grams"]:
        return "g"
    if unit in ["inch", "inches"]:
        return "in"
    if unit in ["foot", "feet"]:
        return "ft"
    if unit in ["dozen", "dozens"]:
        return "dz"
    if unit in ["floz", "fl oz"]:
        return "fl oz"
    return unit
def split_size_and_unit(size_str: str) -> tuple[float, str]:
    if not size_str:
        return 0.0, ""
    # Handle approximate sizes by removing the ~ symbol
    clean_size = size_str.rstrip(".,").replace("avg. ", "").replace("~", "").strip()

    # Clean up the string by removing common packaging terms
    packaging_terms = [
        " Pack", " Cans", " Package", " Loaf", " Plastic Bottle", " Bottle", " Bottles",
        " Bag", " Carton", " Canister", " Container", " Box", " Pouch", " Carded Pk",
        " Tray", " Loaves", " Aluminum Bottles", " Plastic Bottles", " Can", " Zip Pak",
        " Plastic Tub", " Aseptic Carton", " Chunk", " Brick", " Shrinkwrap",
        " Resealable Bag", " Wrapper", " Cup/Tub", " Tub", " Cylinder", " Packages",
        " Shrinkwrapped", " Gable Top", " Jar", " Sleeve", " Stand Up Bag", " Tube"
    ]

    for suffix in packaging_terms:
        if clean_size.endswith(suffix):
            clean_size = clean_size[:-len(suffix)].strip()

    # Check for "X x Y unit" format (e.g., "8 x 3 oz")
    if " x " in clean_size:
        parts = clean_size.split(" x ", 1)
        try:
            quantity = float(parts[0].strip())
            size_parts = parts[1].strip().split(" ", 1)
            if len(size_parts) > 0 and size_parts[0].replace('.', '', 1).isdigit():
                item_size = float(size_parts[0])
                # Calculate total size (quantity * individual size)
                size_value = quantity * item_size
                # Get the unit from the remainder
                remaining = size_parts[1] if len(size_parts) > 1 else ""
            else:
                # Handle case where the second part doesn't start with a number
                size_value = quantity
                remaining = parts[1].strip()
        except (ValueError, IndexError):
            # Fall back to standard parsing if "x" format parsing fails
            size_value = None
            remaining = clean_size
    else:
        # Standard parsing for non "x" format
        size_value = None
        numeric_part = ""
        i = 0
        while i < len(clean_size) and (clean_size[i].isdigit() or clean_size[i] == '.'):
            numeric_part += clean_size[i]
            i += 1

        try:
            if numeric_part:
                size_value = float(numeric_part)
        except ValueError:
            size_value = None

        # Remaining part after the number (potential unit)
        remaining = clean_size[len(numeric_part):].strip() if numeric_part else clean_size

    # Known units mapping
    unit_mappings = {
        "ea": ["ea", "each", "ct"],
        "fl oz": ["fl oz", "floz"],
        "oz": ["oz"],
        "gal": ["gal"],
        "lb": ["lb"],
        "pk": ["pk"],
        "ft": ["ft"],
        "L": ["l"],
        "pt": ["pt"],
        "qt": ["qt"],
        "g": ["g"],
        "in": ["in"],
        "dz": ["dz"],
        "ml": ["ml"],
    }

    # Handle unit/package format (e.g., "lb/package")
    if "/" in remaining:
        unit_parts = remaining.split("/", 1)
        remaining = unit_parts[0].strip().lower()

    # Determine the unit
    unit = ""
    for standard_unit, variations in unit_mappings.items():
        for variation in variations:
            if remaining.startswith(variation) and (
                    len(remaining) == len(variation) or
                    not remaining[len(variation)].isalpha()
            ):
                unit = standard_unit
                break
        if unit:
            break

    # If no standard unit was found, use the remaining text as the unit
    if not unit and remaining:
        unit = remaining

    return size_value, unit

def split_price(price: str) -> float:
    price = price.rstrip(".")
    price = price.rstrip("est")

    if "/" in price:
        price = price.split("/")[0]

    price = price.lstrip("$")
    price = price.strip()
    price = float(price)

    return price


mapping = {
    "Baby & Child": [
        "Baby",
        "Baby Items",
        "Baby & Kids"
    ],

    "Bakery & Bread": [
        "Bakery",
        "Breads & Cakes",
        "Bread & Bakery",
        "Tortillas & Flatbreads",
        "Loaves, Rolls, Buns",
        "Sliced Bread",
        "Bagels",
        "Sweet Stuff",
        "Bakery Desserts",
        "Breakfast Bakery",
        "Buns & Rolls",
        "Bakery & Bread",
        "Tortillas & Flat Bread",
        "Bread",
        "Breads & Doughs"
    ],

    "Beverages": [
        "Water",
        "Tea & Hot Chocolate",
        "Soft Drinks",
        "Sports & Energy Drinks",
        "Juices",
        "Coffee",
        "Drink Mixes & Water Enhancers",
        "Nutritional Drinks",
        "Beverages",
        "Frozen Juices",
        "Water (Sparkling & Still)",
        "Coffee & Tea",
        "Juices & More",
        "Sodas & Mixers",
        "Non-Dairy Bev",
        "Fresh Juice"
    ],

    "Dairy & Eggs": [
        "Dairy, Cheese & Eggs",
        "Dairy & Eggs",
        "Milk & Cream",
        "Yogurt, etc.",
        "Butter",
        "Eggs",
        "Slices, Shreds, Crumbles",
        "Wedges, Wheels, Loaves, Logs",
        "Cream and Creamy Cheeses"
    ],

    "Deli & Prepared Foods": [
        "Prepared Foods",
        "Delicatessen",
        "Deli",
        "Deli & Prepared Food",
        "Custom Orders",
        "Packaged Meals & Sides",
        "Wraps, Burritos & Sandwiches",
        "Salads, Soups & Sides",
        "Entrées & Center of Plate",
        "Soup, Chili & Meals",
        "Dip/Spread"
    ],

    "Frozen Foods": [
        "Ice Cream, Desserts & Toppings",
        "Frozen Meat Substitutes",
        "Frozen Fruits & Vegetables",
        "Frozen Pizza",
        "Frozen Meals & Entrees",
        "Frozen Meat & Seafood",
        "Ice",
        "Frozen Foods",
        "Frozen",
        "Appetizers",
        "Cool Desserts",
        "Fruit & Vegetables",
        "Entrées & Sides",
        "Frozen Pizza & Meals",
        "Appetizers & Sides",
        "Dessert, Ice Cream & Ice"
    ],

    "Meat & Seafood": [
        "Meat & Seafood",
        "Fresh Meat & Seafood",
        "Chicken & Turkey",
        "Fish & Seafood",
        "Beef, Pork & Lamb",
        "Plant-based Protein",
        "Hot Dogs, Bacon & Sausage",
        "Packaged Poultry",
        "Seafood",
        "All Natural Poultry",
        "Packaged Meat",
        "All Natural Pork",
        "All Natural Meat",
        "Packaged Seafood",
        "Vegan & Vegetarian"
    ],

    "Pantry & Dry Goods": [
        "Bulk Foods",
        "Canned & Jarred Foods",
        "Breakfast Foods",
        "Cooking & Baking",
        "Pantry Essentials",
        "Breakfast & Cereals",
        "Pantry",
        "International Foods",
        "Grains & Pasta",
        "Condiments & Salad Dressing",
        "Spices",
        "For Baking & Cooking",
        "Oils & Vinegars",
        "Condiments",
        "Dressing & Seasoning",
        "Salsa & Hot Sauce",
        "BBQ, Pasta, Simmer",
        "Nut Butters & Fruit Spreads",
        "Pastas & Grains",
        "Honeys, Syrups & Nectars",
        "Cereals",
        "Packaged Fish, Meat, Fruit & Veg",
        "Packaged Vegetables & Fruits",
        "Breakfast"
    ],

    "Produce": [
        "Produce",
        "Fresh Produce",
        "Fruits & Vegetables",
        "Fruits",
        "Veggies",
        "Fresh Vegetables",
        "Fresh Herbs",
        "Fresh Fruits"
    ],

    "Snacks & Desserts": [
        "Snack Foods",
        "Snacks",
        "Candy",
        "Candy & Chocolate",
        "Candies & Cookies",
        "Snacks & Sweets",
        "Nuts, Dried Fruits, Seeds",
        "Bars, Jerky &… Surprises",
        "Packaged for Snacking",
        "Chips, Crackers & Crunchy Bites"
    ],

    "Household & Personal Care": [
        "Laundry & Cleaning",
        "Health Care",
        "Vitamins & Supplements",
        "Paper & Plastic",
        "Personal Care",
        "Household Supplies",
        "Household Essentials",
        "Beauty Care",
        "Hardware & Auto",
        "Kitchen & Dining",
        "Clothing",
        "Reading",
        "For the Face & Body",
        "Nutritional Supplements",
        "Fish Oils",
        "Digestive Aids",
        "Mood & Sleep",
        "Seasonal Wellness & Immune",
        "Homeopathy",
        "Children's Vitamins",
        "Weight Loss & Diet",
        "Children's Health",
        "Children's Supplements",
        "Single Vitamins",
        "Cleanse & Detox",
        "Women's & Men's Health",
        "Amino Acids",
        "Minerals",
        "Sports Nutrition",
        "Antioxidants",
        "Herbs",
        "CBD",
        "Protein Powders & Shakes",
        "Calcium & Joint Health",
        "Plant Oils",
        "Superfoods & Greens",
        "Probiotics",
        "Heart Health",
        "Collagen",
        "OTC Internal",
        "Multivitamins",
        "Enzymes"
    ],

    "Seasonal & Special": [
        "Featured",
        "Mother's Day",
        "Healthy Living",
        "ALDI Finds",
        "BBQ & Picnic",
        "Game Day",
        "Valentine's Day",
        "Easter",
        "Fall Products",
        "College & Dorm Room",
        "Grilling",
        "Floral",
        "Flowers & Plants",
        "Plants",
        "Bouquets"
    ],

    "Alcohol & Tobacco": [
        "Beer, Wine & Spirits",
        "Tobacco",
        "Wine, Beer & Liquor"
    ],

    "Pet Supplies": [
        "Pet Supplies",
        "Pet",
        "Pet Stuff"
    ],

    "Miscellaneous": [
        "Unknown",
        "Products"
    ]
}

all_categories = set()
def get_simplified_category(original_category):
    for simplified, originals in mapping.items():
        if original_category in originals:
            return simplified
    all_categories.add(original_category)
    # write all_categories to a file
    with open("/home/kyle/Documents/all_categories.txt", "w") as f:
        for category in all_categories:
            f.write(category + "\n")
    return "Miscellaneous"