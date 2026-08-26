import asyncio
from decimal import Decimal
from sqlalchemy import select
from bot import Base, Product, async_session_maker, engine

# Precios más altos combinados de EZTEAM, JOEL MODS y el bot anterior.
HIGHEST_PRICES = {
    "PRÓXY ANDROID": [("1 Día", "2.00"), ("3 Días", "3.00"), ("7 Días", "7.00"), ("30 Días", "12.00")],
    "DRIP CLIENT": [("1 Día", "3.00"), ("3 Días", "5.00"), ("7 Días", "7.00"), ("15 Días", "10.00"), ("31 Días", "15.00")],
    "BR MODS MÓVIL - ROOT": [("1 Día", "2.00"), ("7 Días", "7.00"), ("30 Días", "12.00")],
    "PATO TEAM": [("3 Días", "3.00"), ("7 Días", "8.00"), ("15 Días", "6.00"), ("30 Días", "15.00")],
    "CUBAN MODS": [("1 Día", "2.00"), ("7 Días", "7.00"), ("30 Días", "12.00")],
    "HG CHEATS": [("1 Día", "3.00"), ("10 Días", "10.00"), ("30 Días", "25.00")],
    "PROXY MENÚ": [("1 Día", "0.70"), ("10 Días", "8.00")],
    "PROYECTO HOLOGRAMA VIP": [("30 Días", "9.90"), ("Permanente", "29.90")],
    "PROXY POTATSO": [("1 Día", "2.00"), ("7 Días", "4.00"), ("30 Días", "18.00"), ("Keis Ilimitadas", "25.00")],
    "CERTIFICADO IPHONE": [("360 Días", "10.00")],
    "E-Sign": [("360 Días", "10.00")],
    "FLOURITE": [("1 Día", "5.00"), ("7 Días", "15.00"), ("30 Días", "31.00"), ("Permanente", "100.00")],
    "BYPASS UID": [("30 Días", "10.00"), ("Permanente", "40.00")],
    "BR MODS PC": [("1 Día", "3.00"), ("10 Días", "7.00"), ("30 Días", "15.00")],
    "AIMKILL PC": [("1 Día", "3.00"), ("7 Días", "7.00"), ("30 Días", "15.00"), ("365 Días", "30.00")], # Bypass XG
    "NUMEROS VIRTUALES (Para WhatsApp)": [("Acceso", "10.00")],
    "PLATAFORMA STREAMING": [("Acceso", "25.00")],
}

def price_variants_text(variants: list[tuple[str, str]]) -> str:
    return ", ".join([f"{dur} | ${price}" for dur, price in variants])

async def update_prices():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_maker() as session:
        products = (await session.execute(select(Product))).scalars().all()
        for product in products:
            if product.name in HIGHEST_PRICES:
                variants = HIGHEST_PRICES[product.name]
                product.description = price_variants_text(variants)
                product.price = Decimal(variants[0][1])
                print(f"Updated {product.name} to {product.price}")
        await session.commit()

if __name__ == "__main__":
    asyncio.run(update_prices())
