from sqlalchemy import inspect, text

from jobwatch.db.database import Base, engine, SessionLocal, sync_company_id_sequence
from jobwatch.models.Company import Company
from jobwatch.models.Job import Job
from jobwatch.models.ErrorLog import ErrorLog
import os, json

def init_db():
    Base.metadata.create_all(bind=engine)
    # The standalone schema has no Alembic runner, so upgrade legacy rows here.
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("LOCK TABLE company IN ACCESS EXCLUSIVE MODE"))
        columns = {column["name"] for column in inspect(connection).get_columns("company")}
        if "api_url" in columns:
            if connection.dialect.name == "postgresql":
                if "api_config" not in columns:
                    connection.execute(text("ALTER TABLE company ADD COLUMN api_config JSONB NOT NULL DEFAULT '{}'::jsonb"))
                connection.execute(text(
                    "UPDATE company SET api_config = jsonb_build_object('url', api_url) || api_config "
                    "WHERE api_url IS NOT NULL"
                ))
            else:
                if "api_config" not in columns:
                    connection.execute(text("ALTER TABLE company ADD COLUMN api_config JSON NOT NULL DEFAULT '{}'"))
                connection.execute(text(
                    "UPDATE company SET api_config = json_insert(api_config, '$.url', api_url) "
                    "WHERE api_url IS NOT NULL"
                ))
            connection.execute(text("ALTER TABLE company DROP COLUMN api_url"))
        if "has_api" in columns:
            connection.execute(text("ALTER TABLE company DROP COLUMN has_api"))

def insert_initial_companies():
    db = SessionLocal()
    try:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "initial_data", "companies.json")
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return

        with open(filepath) as f:
            companies = json.load(f)
            for company in companies:
                exists = db.query(Company).filter_by(company_name=company["company_name"]).first()
                if not exists:
                    db.add(Company(**company))
        db.flush()
        sync_company_id_sequence(db)
        db.commit()
        print("Companies inserted successfully.")
    except Exception as e:
        db.rollback()
        print("Error inserting companies:", e)
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    insert_initial_companies()
