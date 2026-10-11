import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app as fastapi_app
from app.main import lifespan
from app.models import PaymentModel, PromoModel, TariffModel

BASIC_EMAIL = "user@example.com"

PAYMENT_RESPONSE_KEYS = {
    "id",
    "status",
    "tariff_id",
    "amount",
    "discount",
    "method",
    "installment_months",
    "schedule",
    "email",
    "created_at",
}


async def create_payment(client, **overrides):
    payload = {
        "tariff_id": "standard",
        "email": BASIC_EMAIL,
        "method": "card",
    }
    payload.update(overrides)
    return await client.post("/payments", json=payload)


async def test_create_payment_without_promo(client):
    response = await create_payment(client)

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == PAYMENT_RESPONSE_KEYS
    assert body["status"] == "pending"
    assert body["amount"] == 1_990_000
    assert body["discount"] == 0
    assert body["method"] == "card"
    assert body["schedule"] is None


async def test_create_payment_with_promo_applies_discount(client):
    response = await create_payment(client, promo_code="KVITTO10")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["discount"] == 199_000
    assert body["amount"] == 1_990_000 - 199_000


async def test_create_payment_with_lowercase_promo_is_case_insensitive(client):
    response = await create_payment(client, promo_code="kvitto10")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["discount"] == 199_000
    assert body["amount"] == 1_990_000 - 199_000


async def test_create_payment_with_unknown_promo_returns_422(client):
    response = await create_payment(client, promo_code="NOPE")

    assert response.status_code == 422, response.text


@pytest.mark.parametrize("months", [3, 6, 12])
async def test_installment_schedule_sums_to_amount(client, months):
    response = await create_payment(
        client, method="installment", installment_months=months
    )

    assert response.status_code == 201, response.text
    body = response.json()
    schedule = body["schedule"]

    assert body["installment_months"] == months
    assert len(schedule) == months
    assert all(part > 0 for part in schedule)
    assert sum(schedule) == body["amount"]


async def test_installment_schedule_matches_spec_example(client):
    response = await create_payment(
        client, method="installment", installment_months=3
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["amount"] == 1_990_000
    assert body["schedule"] == [663_334, 663_333, 663_333]


async def test_idempotency_key_does_not_create_second_payment(client, session):
    headers = {"Idempotency-Key": "test-key-123"}

    first = await client.post(
        "/payments",
        json={"tariff_id": "standard", "email": BASIC_EMAIL, "method": "card"},
        headers=headers,
    )
    second = await client.post(
        "/payments",
        json={"tariff_id": "standard", "email": BASIC_EMAIL, "method": "card"},
        headers=headers,
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]
    assert set(second.json()) == PAYMENT_RESPONSE_KEYS

    count = await session.scalar(select(func.count()).select_from(PaymentModel))
    assert count == 1


async def test_forbidden_transition_returns_409_and_keeps_status(client):
    created = await create_payment(client)
    payment_id = created.json()["id"]

    response = await client.post(
        "/webhooks/bank", json={"payment_id": payment_id, "status": "refunded"}
    )

    assert response.status_code == 409, response.text

    current = await client.get(f"/payments/{payment_id}")
    assert current.json()["status"] == "pending"


async def test_allowed_transition_changes_status(client):
    created = await create_payment(client)
    payment_id = created.json()["id"]

    response = await client.post(
        "/webhooks/bank", json={"payment_id": payment_id, "status": "succeeded"}
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"result": "ok"}

    current = await client.get(f"/payments/{payment_id}")
    assert current.json()["status"] == "succeeded"


async def test_get_unknown_payment_returns_404(client):
    response = await client.get(f"/payments/{uuid.uuid4()}")

    assert response.status_code == 404


async def test_startup_seeds_default_tariffs_and_promo(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        await session.execute(
            text("TRUNCATE payments, promos, tariffs RESTART IDENTITY CASCADE")
        )
        await session.commit()

    async with lifespan(fastapi_app):
        pass

    async with factory() as session:
        promo = await session.scalar(
            select(PromoModel).where(PromoModel.code == "KVITTO10")
        )
        assert promo is not None
        assert promo.percent == 10

        tariffs = (await session.scalars(select(TariffModel))).all()
        assert {t.id for t in tariffs} == {"basic", "standard", "premium"}

        seeded_twice = await session.scalars(select(TariffModel))
        assert len(list(seeded_twice)) == 3
