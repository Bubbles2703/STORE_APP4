import os, shutil
from fastapi import Request, Form, Depends, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models import Product, Cart, Order, OrderItem
from auth import get_current_user
from database import get_db

templates = Jinja2Templates(directory="templates")

def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    products = db.query(Product).all() if user.role != "admin" else db.query(Product).all()
    return templates.TemplateResponse("index.html", {"request": request, "products": products, "user": user})

def add_product(request: Request, name: str = Form(...), price: float = Form(...), quantity: int = Form(...),
                image: UploadFile = File(None), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse("/login", status_code=302)
    image_path = None
    if image:
        os.makedirs("static/images", exist_ok=True)
        path = f"static/images/{image.filename}"
        with open(path, "wb") as f:
            shutil.copyfileobj(image.file, f)
        image_path = f"images/{image.filename}"
    product = Product(name=name, price=price, quantity=quantity, image_path=image_path, owner_id=user.id)
    db.add(product)
    db.commit()
    return RedirectResponse("/", status_code=302)

def edit_product_form(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403)
    product = db.query(Product).get(product_id)
    return templates.TemplateResponse("edit_product.html", {"request": request, "product": product, "user": user})


def update_product(
        request: Request,
        product_id: int,
        name: str = Form(...),
        price: float = Form(...),
        quantity: int = Form(...),
        description: str = Form(None),
        image: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403)

    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    product.name = name
    product.price = price
    product.quantity = quantity
    product.description = description

    if image and image.filename:
        os.makedirs("static/images", exist_ok=True)
        filename = image.filename
        image_path = f"static/images/{filename}"

        # 💡 открываем именно путь к файлу
        with open(image_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        # сохраняем относительный путь
        product.image_path = f"images/{filename}"

    db.commit()
    return RedirectResponse("/", status_code=302)


def delete_product(request: Request, product_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    product = db.query(Product).filter(Product.id == product_id).first()
    if product and (user.role == "admin" or product.owner_id == user.id):
        db.delete(product)
        db.commit()
    return RedirectResponse("/", status_code=302)

def view_cart(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    items = db.query(Cart).filter_by(user_id=user.id).all()
    cart_products = []
    total = 0
    for item in items:
        subtotal = item.product.price * item.quantity
        total += subtotal
        cart_products.append({"product": item.product, "quantity": item.quantity, "subtotal": subtotal})
    return templates.TemplateResponse("cart.html", {"request": request, "cart_products": cart_products, "user": user, "total": total})

def add_to_cart(request: Request, product_id: int, quantity: int = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or product.quantity < quantity:
        return RedirectResponse("/", status_code=302)
    item = db.query(Cart).filter_by(user_id=user.id, product_id=product_id).first()
    if item:
        item.quantity += quantity
    else:
        db.add(Cart(user_id=user.id, product_id=product_id, quantity=quantity))
    db.commit()
    return RedirectResponse("/cart", status_code=302)

def clear_cart(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    db.query(Cart).filter_by(user_id=user.id).delete()
    db.commit()
    return RedirectResponse("/cart", status_code=302)

def create_order(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    cart_items = db.query(Cart).filter_by(user_id=user.id).all()
    if not cart_items:
        return RedirectResponse("/cart", status_code=302)
    order = Order(user_id=user.id)
    db.add(order)
    db.commit()
    for item in cart_items:
        db.add(OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity, price=item.product.price))
        item.product.quantity -= item.quantity
    db.query(Cart).filter_by(user_id=user.id).delete()
    db.commit()
    return RedirectResponse("/orders", status_code=302)

def read_orders(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    orders = db.query(Order).filter_by(user_id=user.id).all()
    for order in orders:
        order.total_price = sum(item.price * item.quantity for item in order.items)
    return templates.TemplateResponse("orders.html", {"request": request, "orders": orders, "user": user})

def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403)
    from models import User
    users = db.query(User).all()
    return templates.TemplateResponse("admin_users_orders.html", {"request": request, "users": users, "user": user})
