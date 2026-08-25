# ruff: noqa: E402

import json
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SASession

import app.routes.auth as auth_routes
from main import app


class StageRecorder:
    def __init__(self) -> None:
        self.current_request_id: str | None = None
        self.by_request: dict[str, dict[str, float]] = {}

    def begin(self) -> str:
        req_id = str(uuid.uuid4())
        self.current_request_id = req_id
        self.by_request[req_id] = defaultdict(float)
        self.by_request[req_id]["flush_count"] = 0
        return req_id

    def end(self) -> dict[str, float]:
        if not self.current_request_id:
            return {}
        data = dict(self.by_request.get(self.current_request_id, {}))
        self.current_request_id = None
        return data

    def add_ms(self, key: str, elapsed_s: float) -> None:
        if not self.current_request_id:
            return
        self.by_request[self.current_request_id][key] += elapsed_s * 1000

    def incr(self, key: str) -> None:
        if not self.current_request_id:
            return
        self.by_request[self.current_request_id][key] += 1


recorder = StageRecorder()

orig_busca = auth_routes.buscar_usuario_por_email
orig_hash = auth_routes.hash_senha
orig_token = auth_routes.criar_access_token
orig_flush = SASession.flush
orig_commit = SASession.commit
orig_refresh = SASession.refresh


def wrapped_busca(db, email):
    metrics = recorder.by_request.get(recorder.current_request_id or "", {})
    if "connection_ms" not in metrics:
        t0 = time.perf_counter()
        db.connection()
        recorder.add_ms("connection_ms", time.perf_counter() - t0)

    t1 = time.perf_counter()
    result = orig_busca(db, email)
    recorder.add_ms("email_lookup_ms", time.perf_counter() - t1)
    return result


def wrapped_hash(senha: str):
    t0 = time.perf_counter()
    result = orig_hash(senha)
    recorder.add_ms("password_hash_ms", time.perf_counter() - t0)
    return result


def wrapped_token(dados: dict):
    t0 = time.perf_counter()
    result = orig_token(dados)
    recorder.add_ms("token_ms", time.perf_counter() - t0)
    return result


def wrapped_flush(self, *args, **kwargs):
    t0 = time.perf_counter()
    result = orig_flush(self, *args, **kwargs)
    recorder.add_ms("flush_ms", time.perf_counter() - t0)
    recorder.incr("flush_count")
    return result


def wrapped_commit(self, *args, **kwargs):
    t0 = time.perf_counter()
    result = orig_commit(self, *args, **kwargs)
    recorder.add_ms("commit_ms", time.perf_counter() - t0)
    return result


def wrapped_refresh(self, *args, **kwargs):
    t0 = time.perf_counter()
    result = orig_refresh(self, *args, **kwargs)
    recorder.add_ms("refresh_ms", time.perf_counter() - t0)
    return result


def run_attempt(client: TestClient, idx: int) -> dict[str, float]:
    req_id = recorder.begin()
    email = f"perf_user_{idx}_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"nome": "Perf User", "email": email, "senha": "SenhaForte!123"}

    t0 = time.perf_counter()
    response = client.post("/auth/cadastro", json=payload)
    total_ms = (time.perf_counter() - t0) * 1000

    data = recorder.end()
    data["request_id"] = req_id
    data["http_status"] = response.status_code
    data["endpoint_total_ms"] = total_ms
    return data


def summarize(samples: list[dict[str, float]]) -> dict:
    warm = samples[1:] if len(samples) > 1 else samples

    def avg(key: str, group: list[dict[str, float]]) -> float:
        values = [float(item.get(key, 0.0)) for item in group]
        return sum(values) / len(values) if values else 0.0

    keys = [
        "connection_ms",
        "email_lookup_ms",
        "password_hash_ms",
        "flush_ms",
        "commit_ms",
        "refresh_ms",
        "token_ms",
        "endpoint_total_ms",
    ]

    return {
        "first": {k: float(samples[0].get(k, 0.0)) for k in keys} if samples else {},
        "warm_avg": {k: avg(k, warm) for k in keys},
        "attempts": samples,
    }


def main() -> None:
    auth_routes.buscar_usuario_por_email = wrapped_busca
    auth_routes.hash_senha = wrapped_hash
    auth_routes.criar_access_token = wrapped_token
    SASession.flush = wrapped_flush
    SASession.commit = wrapped_commit
    SASession.refresh = wrapped_refresh

    try:
        attempts = []
        with TestClient(app) as client:
            for i in range(1, 6):
                attempts.append(run_attempt(client, i))

        print(json.dumps(summarize(attempts), indent=2))
    finally:
        auth_routes.buscar_usuario_por_email = orig_busca
        auth_routes.hash_senha = orig_hash
        auth_routes.criar_access_token = orig_token
        SASession.flush = orig_flush
        SASession.commit = orig_commit
        SASession.refresh = orig_refresh


if __name__ == "__main__":
    main()
