from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import Base, engine
import auth, api

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Auth
app.get("/login")(auth.login_page)
app.post("/login")(auth.login)
app.get("/logout")(auth.logout)
app.post("/register")(auth.register)

# Products & Views
app.get("/")(api.index)
app.post("/add")(api.add_product)
app.post("/delete/{product_id}")(api.delete_product)

# Cart
app.get("/cart")(api.view_cart)
app.post("/cart/add/{product_id}")(api.add_to_cart)
app.post("/cart/clear")(api.clear_cart)

# Orders
app.post("/orders/create")(api.create_order)
app.get("/orders")(api.read_orders)
