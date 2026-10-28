"""Read the inventory by default; --apply explicitly binds FAFIC without deleting data."""
import argparse
import uuid
from sqlalchemy import select
from app.core.database import SessionLocal
from app.modules.platform.models import Tenant, Environment, Assistant
from app.modules.platform.institution import setup_institution


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assistant-id", type=uuid.UUID)
    args = parser.parse_args()
    with SessionLocal() as database:
        for tenant in database.scalars(select(Tenant).order_by(Tenant.name)):
            print(f"Instituição: {tenant.name} ({tenant.id})")
            for environment in database.scalars(select(Environment).where(Environment.tenant_id == tenant.id)):
                print(f"  Ambiente: {environment.name}")
                for assistant in database.scalars(select(Assistant).where(Assistant.environment_id == environment.id)):
                    print(f"    Assistente: {assistant.name} — {assistant.id}")
        if args.apply:
            try:
                config = setup_institution(database, args.assistant_id)
                print(f"FAFIC configurada. Assistente: {config.assistant_id}")
            except ValueError as error:
                database.rollback()
                raise SystemExit(str(error))
        else:
            print("Somente leitura. Use --apply para configurar após revisar o inventário.")


if __name__ == "__main__":
    main()
