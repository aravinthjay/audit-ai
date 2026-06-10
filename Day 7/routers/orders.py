"""
routers/orders.py — Order Endpoints
=====================================
Full CRUD + status-patch + summary extension.
"""

from typing import List,Optional
status:Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/orders", tags=["Orders"])


# ── CREATE ──────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order",
)
def create_order(
    payload: OrderCreate,
    repo: OrderRepository = Depends(get_repository),
) -> OrderResponse:
    """
    Accepts a deeply nested `OrderCreate` body:
    - **customer** → name, email, phone, shipping_address (nested)
    - **items[]**  → each item embeds a full **product** object
    - **payment_method** enum
    - **notes** (optional)

    Returns an `OrderResponse` which *extends* the stored order with a
    computed **summary** block (subtotal, discounts, grand total, item count).
    """
    order = Order(**payload.model_dump())
    saved = repo.save(order)
    return OrderResponse.from_order(saved)


# ── READ ALL ────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[OrderResponse],
    summary="List all orders",
)
@router.get("/", response_model=List[OrderResponse])
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sort_by: Literal["created_at", "grand_total"] = "created_at",
    repo: OrderRepository = Depends(get_repository)
):
    orders = repo.list_all()

    # sorting
    if sort_by == "grand_total":
        orders.sort(
            key=lambda o: OrderResponse.from_order(o).summary.grand_total,
            reverse=True
        )
    else:
        orders.sort(
            key=lambda o: o.created_at,
            reverse=True
        )

    # pagination
    orders = orders[skip:skip + limit]

    return [
        OrderResponse.from_order(order)
        for order in orders
    ]


# ── READ ONE ────────────────────────────────────────────────────────────────

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get a single order by ID",
)
def get_order(
    order_id: UUID,
    repo: OrderRepository = Depends(get_repository),
) -> OrderResponse:
    order = repo.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found.",
        )
    return OrderResponse.from_order(order)


# ── UPDATE STATUS (PATCH) ────────────────────────────────────────────────────

@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status",
)
def update_order_status(
    order_id: UUID,
    new_status: OrderStatus,
    repo: OrderRepository = Depends(get_repository),
) -> OrderResponse:
    """
    Extension task: PATCH only the `status` field.
    Demonstrates partial update without re-validating the whole body.
    """
    order = repo.update_status(order_id, new_status)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found.",
        )
    return OrderResponse.from_order(order)


# ── DELETE ──────────────────────────────────────────────────────────────────

@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel / delete an order",
)
def delete_order(
    order_id: UUID,
    repo: OrderRepository = Depends(get_repository),
) -> None:
    if not repo.delete(order_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found.",
        )