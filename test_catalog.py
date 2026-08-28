import asyncio
from decimal import Decimal

from sqlalchemy import select

from bot import (
    INITIAL_PRODUCTS,
    PRICE_CATALOG,
    Base,
    Product,
    StoreSetting,
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

        assert products
        assert all(product.stock == 5 and product.is_active for product in products)
        assert await session.get(StoreSetting, "initial_inventory_all_products_stock_5_v3")

        sold = products[0]
        sold.sales_count = 1
        sold.stock = 3
        untouched = products[1]
        untouched.stock = 2
        untouched.is_active = False
        await session.commit()

        await seed_initial_products(session)
        persisted_sold = await session.get(Product, sold.id)
        persisted_untouched = await session.get(Product, untouched.id)
        assert persisted_sold.stock == 3
        assert persisted_sold.is_active is True
        assert persisted_untouched.stock == 2
        assert persisted_untouched.is_active is False

        # Una activación posterior no repone ni reactiva productos que ya se vendieron.
        marker = await session.get(StoreSetting, "initial_inventory_all_products_stock_5_v3")
        await session.delete(marker)
        untouched.sales_count = 0
        untouched.stock = 0
        untouched.is_active = False
        sold.stock = 1
        sold.is_active = True
        await session.commit()
        await seed_initial_products(session)
        migrated_sold = await session.get(Product, sold.id)
        migrated_untouched = await session.get(Product, untouched.id)
        assert migrated_sold.stock == 1
        assert migrated_sold.is_active is True
        assert migrated_untouched.stock == 5
        assert migrated_untouched.is_active is True

    print("CATALOG_OK")


if __name__ == "__main__":
    asyncio.run(main())

