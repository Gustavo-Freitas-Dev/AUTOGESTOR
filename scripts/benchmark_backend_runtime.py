import json
import statistics
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.database.base import Base  # noqa: E402
from app.database.dependencies import get_db  # noqa: E402
from app.models.espaco_financeiro import EspacoFinanceiro  # noqa: E402, F401
from app.models.membro_espaco import MembroEspaco  # noqa: E402, F401
from app.models.movimentacao import Movimentacao  # noqa: E402, F401
from app.models.password_reset_token import PasswordResetToken  # noqa: E402, F401
from app.models.usuario_model import Usuario  # noqa: E402, F401
from main import app  # noqa: E402


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def measure(client: TestClient, method: str, url: str, *, headers=None, json_body=None) -> dict:
    t0 = time.perf_counter()
    response = client.request(method, url, headers=headers, json=json_body)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "method": method,
        "url": url,
        "status": response.status_code,
        "total_ms": round(elapsed_ms, 2),
        "body_len": len(response.content),
    }


def main() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionTest = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionTest()

    query_count = {"value": 0}

    @event.listens_for(engine, "before_cursor_execute")
    def _count_queries(*_args, **_kwargs):
        query_count["value"] += 1

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            signup = measure(
                client,
                "POST",
                "/auth/cadastro",
                json_body={"nome": "Ana", "email": "ana@example.com", "senha": "Senha123!"},
            )
            token = client.post(
                "/auth/login",
                json={"email": "ana@example.com", "senha": "Senha123!"},
            ).json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            espacos = client.get("/espacos", headers=headers).json()
            pessoal = next(item for item in espacos if item["tipo"] == "PESSOAL")
            espaco_id = pessoal["id"]

            for payload in [
                {"tipo": "GANHO", "categoria": "Salario", "descricao": "Agosto", "valor": 3000, "data": "2026-08-01"},
                {"tipo": "GASTO", "categoria": "Mercado", "descricao": "Compra", "valor": 250, "data": "2026-08-02"},
                {"tipo": "GASTO", "categoria": "Transporte", "descricao": "Uber", "valor": 40, "data": "2026-08-03"},
            ]:
                client.post(f"/espacos/{espaco_id}/movimentacoes/", json=payload, headers=headers)

            samples = {
                "health": measure(client, "GET", "/health"),
                "health_db": measure(client, "GET", "/health", headers=headers),
                "auth_me": measure(client, "GET", "/auth/me", headers=headers),
                "espacos": measure(client, "GET", "/espacos", headers=headers),
                "mov_list": measure(client, "GET", f"/espacos/{espaco_id}/movimentacoes/", headers=headers),
                "dashboard_resumo": measure(client, "GET", f"/espacos/{espaco_id}/dashboard/resumo", headers=headers),
                "login": measure(client, "POST", "/auth/login", json_body={"email": "ana@example.com", "senha": "Senha123!"}),
                "mov_create": measure(
                    client,
                    "POST",
                    f"/espacos/{espaco_id}/movimentacoes/",
                    headers=headers,
                    json_body={"tipo": "GASTO", "categoria": "Internet", "descricao": "Plano", "valor": 120, "data": "2026-08-04"},
                ),
                "mov_update": measure(
                    client,
                    "PUT",
                    f"/espacos/{espaco_id}/movimentacoes/1",
                    headers=headers,
                    json_body={"tipo": "GANHO", "categoria": "Salario", "descricao": "Agosto ajustado", "valor": 3100, "data": "2026-08-01"},
                ),
            }

            values = [item["total_ms"] for item in samples.values()]
            result = {
                "summary": {
                    "count": len(samples),
                    "min_ms": min(values),
                    "max_ms": max(values),
                    "mean_ms": statistics.mean(values),
                    "median_ms": statistics.median(values),
                    "p95_ms": percentile(values, 0.95),
                    "errors": sum(1 for item in samples.values() if item["status"] >= 400),
                    "queries_total": query_count["value"],
                },
                "samples": samples,
                "signup_first_measure": signup,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        app.dependency_overrides.clear()
        session.close()


if __name__ == "__main__":
    main()
