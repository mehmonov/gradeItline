# 10-dars: Database (SQLAlchemy)

## Dars maqsadi

Ushbu dars oxirida o'quvchi:
- SQLAlchemy ORM nima ekanini tushunadi
- Model, schema va CRUD qatlamlarini ajratib yozadi
- FastAPI bilan SQLAlchemy ni ulab ishlata oladi
- `User` va `Post` orasidagi relationship ni sozlay oladi
- Filtrlash va qidiruv so'rovlarini yozadi

## Dars rejasi (50-70 daqiqa)

1. Nazariya: ORM va SQLAlchemy asoslari
2. Loyiha strukturasini yaratish
3. `database.py` orqali ulanish sozlash
4. `models.py` da jadvallar va relationship
5. `schemas.py` da Pydantic modellar
6. `crud.py` da amaliy operatsiyalar
7. `main.py` da endpointlar
8. Qidiruv va filter misollari
9. Mustaqil topshiriqlar

---

## SQLAlchemy nima?

SQLAlchemy — Python uchun eng mashhur ORM kutubxona. ORM yordamida SQL yozmasdan ham database bilan Python obyektlari orqali ishlash mumkin.

Oddiy fikr:
- SQL jadvallari <-> Python klasslar
- SQL qatorlari <-> Python obyektlar

---

## O'rnatish

```bash
pip install sqlalchemy
```

SQLite uchun qo'shimcha paket kerak emas. PostgreSQL ishlatsangiz:

```bash
pip install psycopg2-binary
```

FastAPI bilan to'liq ishlatish uchun odatda:

```bash
pip install fastapi uvicorn sqlalchemy pydantic[email]
```

---

## Loyiha strukturasi

```text
project/
├── main.py
├── database.py
├── models.py
├── schemas.py
└── crud.py
```

---

## `database.py` - Database sozlash

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite (lokal fayl)
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

# PostgreSQL uchun:
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/dbname"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Faqat SQLite uchun
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

### Tushuntirish

1. `create_engine()` database ga ulanish yaratadi
2. `SessionLocal` sessiya (transaction) yaratish factory si
3. `Base` barcha modellar uchun asosiy klass
4. `check_same_thread=False` faqat SQLite da kerak bo'ladi

---

## `models.py` - Database modellari

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    posts = relationship("Post", back_populates="author", cascade="all, delete")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(String, nullable=False)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    author = relationship("User", back_populates="posts")
```

### Column turlari

| SQLAlchemy | Python | SQL |
| --- | --- | --- |
| Integer | int | INTEGER |
| String | str | VARCHAR |
| Float | float | FLOAT |
| Boolean | bool | BOOLEAN |
| DateTime | datetime | DATETIME |
| Text | str | TEXT |

### Column parametrlari

- `primary_key=True` - asosiy kalit
- `index=True` - qidiruvni tezlashtiradi
- `unique=True` - takrorlanmas qiymat
- `default=value` - boshlang'ich qiymat
- `nullable=False` - bo'sh bo'lishi mumkin emas

### Relationship tushuntirish

- `User.posts` -> bir foydalanuvchining ko'p posti bo'lishi mumkin (`one-to-many`)
- `Post.author` -> har bir post bitta muallifga tegishli
- `back_populates` -> ikki tomondan bog'lanishni sinxron qiladi

---

## `schemas.py` - Pydantic modellari

```python
from datetime import datetime
from typing import List
from pydantic import BaseModel, EmailStr, ConfigDict


class PostBase(BaseModel):
    title: str
    content: str


class PostCreate(PostBase):
    pass


class Post(PostBase):
    id: int
    published: bool
    created_at: datetime
    author_id: int

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    posts: List[Post] = []

    model_config = ConfigDict(from_attributes=True)
```

### `from_attributes=True` nima qiladi?

SQLAlchemy obyektini avtomatik ravishda Pydantic modelga o'girish imkonini beradi.

---

## `crud.py` - Database operatsiyalari

```python
from sqlalchemy.orm import Session
from models import User, Post
from schemas import UserCreate, PostCreate


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate):
    hashed_password = f"hashed_{user.password}"  # Real loyihada passlib/bcrypt ishlating
    db_user = User(email=user.email, name=user.name, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False


def get_posts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Post).offset(skip).limit(limit).all()


def create_post(db: Session, post: PostCreate, user_id: int):
    db_post = Post(**post.model_dump(), author_id=user_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def get_user_posts(db: Session, user_id: int):
    return db.query(Post).filter(Post.author_id == user_id).all()
```

### Query metodlari

- `query(Model)` - so'rov boshlash
- `filter(condition)` - filtrlash
- `first()` - birinchi natija yoki `None`
- `all()` - barcha natijalar (`list`)
- `offset(n)` - `n` ta yozuvni o'tkazib yuborish
- `limit(n)` - `n` ta yozuv olish
- `count()` - natija soni

### Session operatsiyalari

- `db.add(obj)` - yangi obyekt qo'shish
- `db.commit()` - o'zgarishni saqlash
- `db.refresh(obj)` - bazadagi yangi holatni qayta o'qish
- `db.delete(obj)` - obyektni o'chirish

---

## `main.py` - FastAPI ilova

```python
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
import models
import schemas
import crud


Base.metadata.create_all(bind=engine)
app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email allaqachon ro'yxatdan o'tgan")
    return crud.create_user(db=db, user=user)


@app.get("/users", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return db_user


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    success = crud.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return {"message": "O'chirildi"}


@app.post("/users/{user_id}/posts", response_model=schemas.Post)
def create_post(user_id: int, post: schemas.PostCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return crud.create_post(db=db, post=post, user_id=user_id)


@app.get("/posts", response_model=List[schemas.Post])
def read_posts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_posts(db, skip=skip, limit=limit)


@app.get("/users/{user_id}/posts", response_model=List[schemas.Post])
def read_user_posts(user_id: int, db: Session = Depends(get_db)):
    return crud.get_user_posts(db, user_id=user_id)
```

### `Base.metadata.create_all()`

Bu qator modellar asosida jadvallarni yaratadi. Jadval allaqachon mavjud bo'lsa, qayta yaratmaydi.

---

## Filtrlash va qidirish

```python
from sqlalchemy import or_
from sqlalchemy.orm import Session
from models import User


def search_users(db: Session, query: str):
    return db.query(User).filter(
        or_(
            User.name.contains(query),
            User.email.contains(query),
        )
    ).all()


def get_active_users(db: Session):
    return db.query(User).filter(User.is_active.is_(True)).all()


def get_users_with_posts(db: Session):
    return db.query(User).filter(User.posts.any()).all()
```

### Filter operatorlari

- `==`, `!=` - teng / teng emas
- `>`, `<`, `>=`, `<=` - taqqoslash
- `.contains()` - ichida bor
- `.startswith()` - bilan boshlanadi
- `.endswith()` - bilan tugaydi
- `.in_([list])` - ro'yxat ichida bor
- `or_()`, `and_()` - mantiqiy operatorlar

---

## Darsda jonli demo (o'qituvchi uchun)

1. `uvicorn main:app --reload` ishga tushiring
2. `http://127.0.0.1:8000/docs` ga kiring
3. Bitta user yarating (`POST /users`)
4. O'sha userga 2 ta post qo'shing (`POST /users/{user_id}/posts`)
5. `/users`, `/posts`, `/users/{id}/posts` endpointlarini ketma-ket chaqiring
6. `delete` endpoint bilan userni o'chirib, natijani ko'rsating

---

## Tez-tez uchraydigan xatolar

- `db.commit()` ni unutish -> o'zgarishlar saqlanmaydi
- `db.refresh(obj)` qilmaslik -> `id` yoki yangi qiymatlar ko'rinmasligi mumkin
- SQLite da `check_same_thread=False` bermaslik -> thread xatolari
- Schema da `from_attributes=True` bo'lmasa `response_model` xatolik berishi mumkin
- `password` ni plain text saqlash -> xavfsizlik xatosi

---

## Topshiriqlar

### Topshiriq 1

`Product` modeli yarating:
- `id`, `name`, `price`, `stock`, `category`, `created_at`
- To'liq CRUD funksiyalar yozing
- `GET /products` endpointini filter bilan qo'llab-quvvatlang

### Topshiriq 2

`Order` va `OrderItem` modellari yarating:
- `Order`: `id`, `user_id`, `total`, `status`, `created_at`
- `OrderItem`: `id`, `order_id`, `product_id`, `quantity`, `price`
- Relationshiplarni to'g'ri sozlang:
  - `Order.items`
  - `OrderItem.order`

### Topshiriq 3

Qidiruv endpoint yozing:

`GET /products/search?q=telefon&min_price=100&max_price=1000&category=phone`

Shartlar:
- `q` bo'yicha `name` dan qidirish
- `min_price` / `max_price` oralig'ida filter
- `category` bo'yicha filter
- bo'sh parametrlar berilmasa, ularga filter qo'llanmasin

---

## Mini savol-javob

1. `SessionLocal` va `engine` farqi nima?
2. `relationship()` nima uchun kerak?
3. `commit()` va `refresh()` qachon ishlatiladi?
4. Nega `schemas.py` alohida faylda yoziladi?

---

## Qisqa xulosa

SQLAlchemy orqali:
- model bilan jadval tuzamiz
- session bilan transaction boshqaramiz
- CRUD bilan ma'lumotni boshqaramiz
- FastAPI bilan endpoint orqali tashqi dunyoga chiqaramiz

Bu arxitektura keyingi darslarda authentication, migration va production database ga o'tishni osonlashtiradi.
