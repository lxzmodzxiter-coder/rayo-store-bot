import asyncio
from decimal import Decimal

from sqlalchemy import select

from bot import (
    INITIAL_PRODUCTS,
    PRICE_CATALOG,
    Base,
    Product,
    async_session_maker,
    engine,
    seed_initial_products,
)


async def main():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        await seed_initial_products(session)
        products = (await session.execute(select(Product))).scalars().all()
        by_name = {product.name: product for product in products}
        expected = {name for names in INITIAL_PRODUCTS.values() for name in names}
        assert expected <= by_name.keys()
        assert set(PRICE_CATALOG) <= by_name.keys()
        for name, variants in PRICE_CATALOG.items():
            assert by_name[name].price == Decimal(variants[0][1])
        for product in products:
            assert product.stock == 0
            assert product.is_active is False

    print("CATALOG_OK")


if __name__ == "__main__":
    asyncio.run(main())

