import asyncio
import httpx
import uuid
async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://127.0.0.1:8000/api/v1/payments/",
            headers={"Authorization": "Bearer test", "idempotency-key": str(uuid.uuid4())},
            json={"amount": 10.0, "currency": "usd", "payment_method": "pm_card_visa", "sender_id": "u1", "receiver_id": "u2"})
        print(resp.json())
asyncio.run(main())
