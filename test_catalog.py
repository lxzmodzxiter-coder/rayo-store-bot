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

        threshold = Decimal("10.00")
        high_price = [product for product in products if product.price >= threshold]
        low_price = [product for product in products if product.price < threshold]
        assert high_price and low_price
        assert all(product.stock == 5 and product.is_active for product in high_price)
        assert all(product.stock == 0 and not product.is_active for product in low_price)
        assert await session.get(StoreSetting, "initial_inventory_price_ge_10_v2")

        # Una nueva siembra no debe reponer ventas ni sobrescribir cambios
        # manuales después de que la política de activación quedó marcada.
        sold = high_price[0]
        sold.stock = 3
        manually_changed = low_price[0]
        manually_changed.stock = 4
        manually_changed.is_active = True
        await session.commit()

        await seed_initial_products(session)
        persisted_sold = await session.get(Product, sold.id)
        persisted_low = await session.get(Product, manually_changed.id)
        assert persisted_sold.stock == 3
        assert persisted_sold.is_active is True
        assert persisted_low.stock == 4
        assert persisted_low.is_active is True

        # Si una base ya usaba la política v1, el cambio al umbral no repone
        # el stock caro, pero sí retira el stock de los productos inferiores.
        marker = await session.get(StoreSetting, "initial_inventory_price_ge_10_v2")
        await session.delete(marker)
        session.add(StoreSetting(key="initial_inventory_5_v1", value="5"))
        sold.stock = 2
        sold.is_active = True
        manually_changed.stock = 4
        manually_changed.is_active = True
        await session.commit()
        await seed_initial_products(session)
        migrated_sold = await session.get(Product, sold.id)
        migrated_low = await session.get(Product, manually_changed.id)
        assert migrated_sold.stock == 2
        assert migrated_sold.is_active is True
        assert migrated_low.stock == 0
        assert migrated_low.is_active is False

    print("CATALOG_OK")


if __name__ == "__main__":
    asyncio.run(main())

