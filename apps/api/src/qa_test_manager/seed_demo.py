from __future__ import annotations

from os import environ

from sqlalchemy import select

from qa_test_manager.database import DEFAULT_DATABASE_URL, SessionLocal
from qa_test_manager.models import (
    Project,
    ProjectMember,
    TestCase,
    TestOrigin,
    TestPriority,
    TestResult,
    TestStep,
    TestType,
    User,
    UserRole,
)
from qa_test_manager.security import hash_password


def seed_demo() -> None:
    database_url = environ.get("QA_TEST_MANAGER_DATABASE_URL", DEFAULT_DATABASE_URL)
    password = environ.get("QA_TEST_MANAGER_DEMO_PASSWORD", "")
    if environ.get("QA_TEST_MANAGER_ALLOW_DEMO_SEED") != "1":
        raise SystemExit("Defina QA_TEST_MANAGER_ALLOW_DEMO_SEED=1 para autorizar o seed.")
    if "demo" not in database_url.lower() and "e2e" not in database_url.lower():
        raise SystemExit("O seed só pode usar uma base cujo nome contenha demo ou e2e.")
    if len(password) < 12:
        raise SystemExit("Defina QA_TEST_MANAGER_DEMO_PASSWORD com pelo menos 12 caracteres.")

    with SessionLocal() as database:
        existing_emails = set(database.scalars(select(User.email)))
        demo_emails = {
            "admin.demo@example.com",
            "tester.demo@example.com",
            "dev.demo@example.com",
        }
        if existing_emails:
            if existing_emails == demo_emails:
                print("Dados fictícios de demonstração já existem.")
                return
            raise SystemExit("A base de demonstração contém utilizadores não reconhecidos.")
        users = [
            User(
                name="Admin Demo",
                email="admin.demo@example.com",
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            ),
            User(
                name="Tester Demo",
                email="tester.demo@example.com",
                password_hash=hash_password(password),
                role=UserRole.TESTER,
            ),
            User(
                name="Dev Demo",
                email="dev.demo@example.com",
                password_hash=hash_password(password),
                role=UserRole.DEV,
            ),
        ]
        project = Project(
            name="Portal de demonstração",
            description="Dados inteiramente fictícios para o roteiro local.",
        )
        database.add_all([*users, project])
        database.flush()
        database.add_all(
            [
                ProjectMember(project_id=project.id, user_id=users[1].id),
                ProjectMember(project_id=project.id, user_id=users[2].id),
                TestCase(
                    project_id=project.id,
                    case_number="CT001",
                    execution_order=1,
                    priority=TestPriority.HIGH,
                    requirement="RF-DEMO-001",
                    test_type=TestType.FUNCTIONAL_POSITIVE,
                    title="Autenticação com credenciais válidas",
                    test_data="Utilizador fictício ativo",
                    description="Validar o acesso ao portal de demonstração.",
                    preconditions="Utilizador ativo e página de login disponível.",
                    expected_result="A sessão é iniciada.",
                    final_result=TestResult.NOT_EXECUTED,
                    origin=TestOrigin.MANUAL,
                    steps=[
                        TestStep(
                            position=1,
                            action="Submeter credenciais válidas",
                            expected_result="Sessão iniciada",
                        )
                    ],
                ),
            ]
        )
        project.next_case_sequence = 2
        database.commit()
    print("Dados fictícios de demonstração criados.")


if __name__ == "__main__":
    seed_demo()
