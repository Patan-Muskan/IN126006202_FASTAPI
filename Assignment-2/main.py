from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI()

# Products list
products = [
    {'id':1,'name':'Wireless Mouse','price':499,'category':'Electronics','in_stock':True},
    {'id':2,'name':'Notebook','price':99,'category':'Stationery','in_stock':True},
    {'id':3,'name':'USB Hub','price':799,'category':'Electronics','in_stock':False},
    {'id':4,'name':'Pen Set','price':49,'category':'Stationery','in_stock':True},
]

# -------------------------------
# Endpoint 0
# -------------------------------
@app.get("/")
def home():
    return {"message": "FastAPI Is Working"}


# -------------------------------
# Q1 - Filter Products
# -------------------------------
@app.get("/products/filter")
def filter_products(min_price: int = None, max_price: int = None, category: str = None):

    filtered = products

    # filter by category
    if category:
        filtered = [p for p in filtered if p["category"].lower() == category.lower()]

    # filter by minimum price
    if min_price is not None:
        filtered = [p for p in filtered if p["price"] >= min_price]

    # filter by maximum price
    if max_price is not None:
        filtered = [p for p in filtered if p["price"] <= max_price]

    return {
        "filtered_products": filtered,
        "count": len(filtered)
    }


# -------------------------------
# Q2 - Get only name and price
# -------------------------------
@app.get("/products/{product_id}/price")
def get_product_price(product_id: int):

    product = next((p for p in products if p["id"] == product_id), None)

    if product is None:
        return {"error": "Product not found"}

    return {
        "name": product["name"],
        "price": product["price"]
    }


# -------------------------------
# Feedback storage
# -------------------------------
feedback = []


# -------------------------------
# Customer Feedback Model
# -------------------------------
class CustomerFeedback(BaseModel):
    customer_name: str = Field(..., min_length=2)
    product_id: int = Field(..., gt=0)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=300)


# -------------------------------
# Q3 - Submit Feedback
# -------------------------------
@app.post("/feedback")
def submit_feedback(data: CustomerFeedback):

    feedback_data = data.model_dump()

    feedback.append(feedback_data)

    return {
        "message": "Feedback submitted successfully",
        "feedback": feedback_data,
        "total_feedback": len(feedback)
    }


# -------------------------------
# Q4 - Product Summary
# -------------------------------
@app.get("/products/summary")
def product_summary():

    total_products = len(products)

    in_stock_count = len([p for p in products if p["in_stock"]])

    out_of_stock_count = len([p for p in products if not p["in_stock"]])

    most_expensive_product = max(products, key=lambda p: p["price"])

    cheapest_product = min(products, key=lambda p: p["price"])

    # maintain order of categories
    categories = []
    for p in products:
        if p["category"] not in categories:
            categories.append(p["category"])

    return {
        "total_products": total_products,
        "in_stock_count": in_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "most_expensive": {
            "name": most_expensive_product["name"],
            "price": most_expensive_product["price"]
        },
        "cheapest": {
            "name": cheapest_product["name"],
            "price": cheapest_product["price"]
        },
        "categories": categories
    }


# -------------------------------
# Order Item Model
# -------------------------------
class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., ge=1, le=50)


# -------------------------------
# Bulk Order Model
# -------------------------------
class BulkOrder(BaseModel):
    company_name: str = Field(..., min_length=2)
    contact_email: str = Field(..., min_length=5)
    items: List[OrderItem] = Field(..., min_items=1)


# -------------------------------
# Q5 - Bulk Order Endpoint
# -------------------------------
@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):

    confirmed = []
    failed = []
    grand_total = 0

    for item in order.items:

        product = next((p for p in products if p["id"] == item.product_id), None)

        if product is None:
            failed.append({
                "product_id": item.product_id,
                "reason": "Product not found"
            })
            continue

        if not product["in_stock"]:
            failed.append({
                "product_id": item.product_id,
                "reason": f'{product["name"]} is out of stock'
            })
            continue

        subtotal = product["price"] * item.quantity
        grand_total += subtotal

        confirmed.append({
            "product": product["name"],
            "qty": item.quantity,
            "subtotal": subtotal
        })

    return {
        "company": order.company_name,
        "confirmed": confirmed,
        "failed": failed,
        "grand_total": grand_total
    }


# -------------------------------
# Orders storage
# -------------------------------
orders = []
order_counter = 1


# -------------------------------
# Order Model for bonus task
# -------------------------------
class Order(BaseModel):
    product_id: int
    quantity: int


# -------------------------------
# BONUS - Create Order
# -------------------------------
@app.post("/orders")
def create_order(order: Order):

    global order_counter

    new_order = {
        "order_id": order_counter,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "status": "pending"
    }

    orders.append(new_order)

    order_counter += 1

    return {
        "message": "Order placed successfully",
        "order": new_order
    }


# -------------------------------
# BONUS - Get Order
# -------------------------------
@app.get("/orders/{order_id}")
def get_order(order_id: int):

    order = next((o for o in orders if o["order_id"] == order_id), None)

    if order is None:
        return {"error": "Order not found"}

    return order


# -------------------------------
# BONUS - Confirm Order
# -------------------------------
@app.patch("/orders/{order_id}/confirm")
def confirm_order(order_id: int):

    order = next((o for o in orders if o["order_id"] == order_id), None)

    if order is None:
        return {"error": "Order not found"}

    order["status"] = "confirmed"

    return {
        "message": "Order confirmed",
        "order": order
    }