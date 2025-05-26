from fastapi import Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from models import User
from database import get_db

templates = Jinja2Templates(directory="templates")

def get_current_user(request: Request, db: Session):
    user_id = request.cookies.get("user_id")
    return db.query(User).filter(User.id == int(user_id)).first() if user_id else None

def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not bcrypt.verify(password, user.password):
        return RedirectResponse("/login", status_code=302)
    response = RedirectResponse("/", status_code=302)
    response.set_cookie("user_id", str(user.id))
    return response

def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("user_id")
    return response

def register(username: str = Form(...), password: str = Form(...), role: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == username).first():
        return RedirectResponse("/login", status_code=302)
    hashed = bcrypt.hash(password)
    user = User(username=username, password=hashed, role=role, is_admin=(role == "admin"))
    db.add(user)
    db.commit()
    return RedirectResponse("/login", status_code=302)