"""Sample FastAPI application for testing route discovery."""
from fastapi import FastAPI, Depends, APIRouter, HTTPException
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


def get_current_user():
    pass


def get_db():
    pass


# Direct app routes
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/login")
async def login(username: str, password: str):
    return {"token": "abc"}


# Router with prefix
router = APIRouter(prefix="/api/v1")


@router.get("/items", tags=["items"])
async def list_items(skip: int = 0, limit: int = 10, db=Depends(get_db)):
    return []


@router.get("/items/{item_id}", tags=["items"], response_model=Item)
async def get_item(item_id: int):
    return {"name": "test", "price": 1.0}


@router.post("/items", tags=["items"])
async def create_item(item: Item, user=Depends(get_current_user)):
    return item


@router.put("/items/{item_id}", tags=["items"])
async def update_item(item_id: int, item: Item, user=Depends(get_current_user)):
    return item


@router.delete("/items/{item_id}", tags=["items"])
async def delete_item(item_id: int, user=Depends(get_current_user)):
    return {"ok": True}


# Users router
users_router = APIRouter(prefix="/api/v1/users")


@users_router.get("/")
async def list_users():
    return []


@users_router.get("/{user_id}")
async def get_user(user_id: int):
    return {}


app.include_router(router)
app.include_router(users_router)
