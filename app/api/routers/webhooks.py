from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import PaymentServiceDep
from app.exceptions import InvalidTransitionError
from app.schemas import WebhookBody


webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@webhook_router.post("/bank")
async def bank_webhook(body: WebhookBody, service: PaymentServiceDep):
    try:
        payment = await service.change_status(body.payment_id, body.status)
    except InvalidTransitionError:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "invalid transition"},
        )

    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "payment not found")
    return {"result": "ok"}