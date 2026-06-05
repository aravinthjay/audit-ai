"""
main.py — FastAPI Application Entry Point
==========================================
Run:  uvicorn main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

#from routers.orders import router as orders_router

app = FastAPI(
    title="Order Management API",
    description=(
        "End-to-end FastAPI demo with **nested Pydantic models** and the "
        "**extension response pattern**.\n\n"
        "| Layer | Model |\n"
        "|---|---|\n"
        "| Leaf | `Address`, `Product` |\n"
        "| Composed | `OrderItem` (→ Product), `Customer` (→ Address) |\n"
        "| Top-level | `OrderCreate`, `Order` |\n"
        "| Extension | `OrderResponse` (→ Order + computed `summary`) |"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["Health"])
def health() -> dict:
    return {"status": "ok", "message": "Order Management API is running 🚀"}

"""
main.py — FastAPI Application Entry Point
==========================================
Run:  uvicorn main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.orders import router as orders_router

app = FastAPI(
    title="Order Management API",
    description=(
        "End-to-end FastAPI demo with **nested Pydantic models** and the "
        "**extension response pattern**.\n\n"
        "| Layer | Model |\n"
        "|---|---|\n"
        "| Leaf | `Address`, `Product` |\n"
        "| Composed | `OrderItem` (→ Product), `Customer` (→ Address) |\n"
        "| Top-level | `OrderCreate`, `Order` |\n"
        "| Extension | `OrderResponse` (→ Order + computed `summary`) |"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders_router)


@app.get("/", tags=["Health"])
def health() -> dict:
    return {"status": "ok", "message": "Order Management API is running 🚀"}