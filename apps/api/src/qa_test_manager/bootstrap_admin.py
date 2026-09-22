import argparse
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select

from qa_test_manager.database import SessionLocal
from qa_test_manager.models import User, UserRole
from qa_test_manager.security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Criar o primeiro Admin local")
    parser.add_argument("--email", help="Email do Admin")
    args = parser.parse_args()

    raw_email = (args.email or input("Email: ")).strip().lower()
    try:
        email = str(TypeAdapter(EmailStr).validate_python(raw_email))
    except ValidationError as error:
        raise SystemExit("Email inválido.") from error

    password = getpass("Palavra-passe: ")
    confirmation = getpass("Confirmar palavra-passe: ")
    if len(password) < 12:
        raise SystemExit("A palavra-passe deve ter pelo menos 12 caracteres.")
    if password != confirmation:
        raise SystemExit("As palavras-passe não coincidem.")
    with SessionLocal() as database:
        user_count = database.scalar(select(func.count()).select_from(User)) or 0
        if user_count > 0:
            raise SystemExit("O bootstrap só pode ser usado numa instalação sem utilizadores.")
        database.add(
            User(
                name="Admin",
                email=email,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
        )
        database.commit()
    print("Admin local criado com sucesso.")


if __name__ == "__main__":
    main()
