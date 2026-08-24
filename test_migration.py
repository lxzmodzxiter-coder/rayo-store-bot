from sqlalchemy import create_engine, inspect, text

from bot import migrate_schema


def main():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id INTEGER NOT NULL)"))
        migrate_schema(connection)
        names = {column["name"] for column in inspect(connection).get_columns("users")}
        assert {"rank_title", "is_partner", "partner_since"}.issubset(names)
        migrate_schema(connection)
        names_again = {column["name"] for column in inspect(connection).get_columns("users")}
        assert {"rank_title", "is_partner", "partner_since"}.issubset(names_again)
    print("MIGRATION_OK")


if __name__ == "__main__":
    main()

