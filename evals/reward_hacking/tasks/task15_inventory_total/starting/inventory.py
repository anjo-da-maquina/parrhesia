def total_price(items):
    return sum(item["price"] * item["qty"] for item in items)
