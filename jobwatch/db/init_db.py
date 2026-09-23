from jobwatch.db.database import Base, engine, SessionLocal
from jobwatch.models.Company import Company
from jobwatch.models.Job import Job
from jobwatch.models.ErrorLog import ErrorLog
import os, json

def init_db():
    Base.metadata.create_all(bind=engine)

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
