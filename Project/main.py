from fastapi import FastAPI, Query, Response, status
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# ================= DATA =================
items = [
    {"id":1,"name":"Tomato","price":40,"unit":"kg","category":"Vegetable","in_stock":True},
    {"id":2,"name":"Apple","price":120,"unit":"kg","category":"Fruit","in_stock":True},
    {"id":3,"name":"Milk","price":50,"unit":"litre","category":"Dairy","in_stock":True},
    {"id":4,"name":"Rice","price":60,"unit":"kg","category":"Grain","in_stock":False},
    {"id":5,"name":"Eggs","price":80,"unit":"dozen","category":"Dairy","in_stock":True},
    {"id":6,"name":"Potato","price":30,"unit":"kg","category":"Vegetable","in_stock":True},
]

orders = []
order_counter = 1
cart = []

# ================= MODELS =================

class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=50)
    delivery_address: str = Field(..., min_length=10)
    delivery_slot: str = "Morning"
    bulk_order: bool = False

class NewItem(BaseModel):
    name: str = Field(..., min_length=2)
    price: int = Field(..., gt=0)
    unit: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    in_stock: bool = True

class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str
    delivery_slot: str

# ================= HELPERS =================

def find_item(item_id):
    return next((i for i in items if i["id"] == item_id), None)

def calculate_order_total(price, quantity, delivery_slot, bulk):
    total = price * quantity
    original = total

    if bulk and quantity >= 10:
        total *= 0.92  # 8% discount

    if delivery_slot == "Morning":
        total += 40
    elif delivery_slot == "Evening":
        total += 60

    return int(original), int(total)

def filter_items_logic(category=None, max_price=None, unit=None, in_stock=None):
    result = items

    if category is not None:
        result = [i for i in result if i["category"] == category]

    if max_price is not None:
        result = [i for i in result if i["price"] <= max_price]

    if unit is not None:
        result = [i for i in result if i["unit"] == unit]

    if in_stock is not None:
        result = [i for i in result if i["in_stock"] == in_stock]

    return result

# ================= DAY 1 =================

@app.get("/")
def home():
    return {"message": "Welcome to FreshMart Grocery"}

@app.get("/items")
def get_items():
    return {
        "items": items,
        "total": len(items),
        "in_stock_count": len([i for i in items if i["in_stock"]])
    }

@app.get("/items/summary")
def summary():
    categories = {}
    for i in items:
        categories[i["category"]] = categories.get(i["category"], 0) + 1

    return {
        "total": len(items),
        "in_stock": len([i for i in items if i["in_stock"]]),
        "out_of_stock": len([i for i in items if not i["in_stock"]]),
        "categories": categories
    }

@app.get("/orders")
def get_orders():
    return {"orders": orders, "total": len(orders)}

# ================= FILTER =================

@app.get("/items/filter")
def filter_items(category:str=None,max_price:int=None,unit:str=None,in_stock:bool=None):
    result = filter_items_logic(category,max_price,unit,in_stock)
    return {"items": result}

# ================= SEARCH / SORT / PAGE =================

@app.get("/items/search")
def search(keyword:str):
    res=[i for i in items if keyword.lower() in i["name"].lower() or keyword.lower() in i["category"].lower()]
    return {"results":res,"total_found":len(res)}

@app.get("/items/sort")
def sort_items(sort_by:str="price",order:str="asc"):
    if sort_by not in ["price","name","category"]:
        return {"error":"Invalid field"}
    reverse=True if order=="desc" else False
    return {"items":sorted(items,key=lambda x:x[sort_by],reverse=reverse)}

@app.get("/items/page")
def paginate(page:int=1,limit:int=4):
    start=(page-1)*limit
    end=start+limit
    total_pages=(len(items)+limit-1)//limit
    return {"page":page,"total_pages":total_pages,"data":items[start:end]}

# ================= CRUD =================
@app.post("/orders")
def place_order(data: OrderRequest):
    global order_counter

    item = find_item(data.item_id)

    if not item:
        return {"error": "Item not found"}

    if not item["in_stock"]:
        return {"error": "Item out of stock"}

    original, final = calculate_order_total(
        item["price"],
        data.quantity,
        data.delivery_slot,
        data.bulk_order
    )

    order = {
        "order_id": order_counter,
        "item_id": data.item_id,
        "item_name": item["name"],
        "quantity": data.quantity,
        "unit": item["unit"],
        "delivery_slot": data.delivery_slot,
        "original_price": original,
        "final_price": final,
        "status": "confirmed"
    }

    orders.append(order)
    order_counter += 1

    return order

@app.post("/items")
def add_item(item:NewItem,response:Response):
    if any(i["name"].lower()==item.name.lower() for i in items):
        response.status_code=400
        return {"error":"Duplicate item"}

    new=item.dict()
    new["id"]=len(items)+1
    items.append(new)

    response.status_code=201
    return {"item":new}

@app.get("/orders/search")
def search_orders(keyword: str):
    res = [o for o in orders if keyword.lower() in o["customer"].lower()]
    return {"results": res}

@app.get("/orders/sort")
def sort_orders():
    return {"orders": sorted(orders, key=lambda x: x["total_cost"])}

@app.get("/orders/page")
def paginate_orders(page: int = 1, limit: int = 2):
    start = (page - 1) * limit
    end = start + limit
    return {"data": orders[start:end]}

@app.put("/items/{item_id}")
def update(item_id:int,price:int=None,in_stock:bool=None):
    item=find_item(item_id)
    if not item:
        return {"error":"Item not found"}

    if price is not None:
        item["price"]=price
    if in_stock is not None:
        item["in_stock"]=in_stock

    return item

@app.delete("/items/{item_id}")
def delete(item_id:int):
    item=find_item(item_id)
    if not item:
        return {"error":"Item not found"}

    if any(o["item_id"]==item_id for o in orders):
        return {"error":"Item has active orders"}

    items.remove(item)
    return {"message":"Deleted"}

# ================= CART =================

@app.post("/cart/add")
def add_to_cart(item_id:int=Query(...),quantity:int=1):
    item=find_item(item_id)

    if not item:
        return {"error":"Not found"}
    if not item["in_stock"]:
        return {"error":"Out of stock"}

    for c in cart:
        if c["item_id"]==item_id:
            c["quantity"]+=quantity
            return {"message":"Updated"}

    cart.append({"item_id":item_id,"quantity":quantity})
    return {"message":"Added"}

@app.get("/cart")
def view_cart():
    total=0
    detailed=[]
    for c in cart:
        item=find_item(c["item_id"])
        sub=item["price"]*c["quantity"]
        total+=sub
        detailed.append({"name":item["name"],"subtotal":sub})

    return {"cart":detailed,"grand_total":total}

@app.delete("/cart/{item_id}")
def remove_cart(item_id:int):
    for c in cart:
        if c["item_id"]==item_id:
            cart.remove(c)
            return {"message":"Removed"}
    return {"error":"Not found"}

@app.post("/cart/checkout")
def checkout(data:CheckoutRequest,response:Response):
    global order_counter

    if not cart:
        response.status_code=400
        return {"error":"Cart empty"}

    placed=[]
    total=0

    for c in cart:
        item=find_item(c["item_id"])
        orig,final=calculate_order_total(item["price"],c["quantity"],data.delivery_slot,False)

        order={
            "order_id":order_counter,
            "item_id":c["item_id"],
            "customer":data.customer_name,
            "total_cost":final
        }

        orders.append(order)
        placed.append(order)
        total+=final
        order_counter+=1

    cart.clear()
    response.status_code=201
    return {"orders":placed,"grand_total":total}

# ================= BROWSE =================

@app.get("/items/browse")
def browse(keyword:str=None,category:str=None,in_stock:bool=None,sort_by:str=None,order:str="asc",page:int=1,limit:int=4):
    result=items

    if keyword:
        result=[i for i in result if keyword.lower() in i["name"].lower()]

    if category:
        result=[i for i in result if i["category"]==category]

    if in_stock is not None:
        result=[i for i in result if i["in_stock"]==in_stock]

    if sort_by:
        reverse=True if order=="desc" else False
        result=sorted(result,key=lambda x:x[sort_by],reverse=reverse)

    start=(page-1)*limit
    end=start+limit

    return {"results":result[start:end]}

# ================= LAST =================

@app.get("/items/{item_id}")
def get_item(item_id:int):
    item=find_item(item_id)
    if not item:
        return {"error":"Not found"}
    return item