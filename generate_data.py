import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

regions = ["North", "South", "East", "West"]
categories = ["Electronics", "Clothing", "Food & Beverage", "Home & Garden", "Sports"]
products = {
    "Electronics": ["Laptop", "Smartphone", "Tablet", "Headphones", "Smart Watch"],
    "Clothing": ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Dress"],
    "Food & Beverage": ["Coffee Beans", "Protein Bar", "Green Tea", "Energy Drink", "Snack Mix"],
    "Home & Garden": ["Plant Pot", "LED Lamp", "Throw Pillow", "Wall Art", "Candle Set"],
    "Sports": ["Yoga Mat", "Dumbbell", "Running Shoes", "Water Bottle", "Jump Rope"],
}
sales_reps = ["Alice Johnson", "Bob Smith", "Carol White", "David Lee", "Eva Martinez",
              "Frank Chen", "Grace Kim", "Henry Brown"]

rows = []
start_date = datetime(2023, 1, 1)
for _ in range(1000):
    category = random.choice(categories)
    product = random.choice(products[category])
    region = random.choice(regions)
    rep = random.choice(sales_reps)
    date = start_date + timedelta(days=random.randint(0, 730))
    quantity = random.randint(1, 50)
    unit_price = round(random.uniform(10, 500), 2)
    discount = round(random.choice([0, 0, 0, 0.05, 0.1, 0.15, 0.2]), 2)
    revenue = round(quantity * unit_price * (1 - discount), 2)
    cost = round(revenue * random.uniform(0.4, 0.7), 2)
    profit = round(revenue - cost, 2)

    rows.append({
        "date": date.strftime("%Y-%m-%d"),
        "region": region,
        "category": category,
        "product": product,
        "sales_rep": rep,
        "quantity": quantity,
        "unit_price": unit_price,
        "discount": discount,
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
    })

df = pd.DataFrame(rows)
df.to_csv("sales_data.csv", index=False)
print(f"Generated {len(df)} rows → sales_data.csv")
print(df.head())
