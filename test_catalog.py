import asyncio
from decimal import Decimal

from sqlalchemy import select

from bot import (
    INITIAL_PRODUCTS,
    PRICE_CATALOG,
    Base,
    Product,
    ProductVariant,
    StoreSetting,
    async_session_maker,
    complete_price_variants,
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
        variants = (await session.execute(select(ProductVariant))).scalars().all()
        by_name = {product.name: product for product in products}
        expected = {name for names in INITIAL_PRODUCTS.values() for name in names}
        assert expected <= by_name.keys()
        assert set(PRICE_CATALOG) <= by_name.keys()

        for name, price_variants in PRICE_CATALOG.items():
            assert by_name[name].price == Decimal(complete_price_variants(name, price_variants)[0][1])
            product_variants = [row for row in variants if row.product_id == by_name[name].id]
            assert [row.name for row in product_variants] == ["1 Día", "3 Días", "7 Días", "15 Días", "30 Días", "Permanente"]
            assert all(row.stock == 5 for row in product_variants)
            assert by_name[name].stock == 30
            assert by_name[name].is_active

        assert products
        assert await session.get(StoreSetting, "initial_inventory_all_products_stock_5_v3")

        selected = next(row for row in variants if row.name == "7 Días")
        selected.stock = 2
        product = await session.get(Product, selected.product_id)
        product.stock = 27
        await session.commit()
        await seed_initial_products(session)
        persisted_variant = await session.get(ProductVariant, selected.id)
        assert persisted_variant.stock == 2

    print("CATALOG_OK")


if __name__ == "__main__":
    asyncio.run(main())
