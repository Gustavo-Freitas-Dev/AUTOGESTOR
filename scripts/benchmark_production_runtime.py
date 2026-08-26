import argparse
import json
import statistics
import time
import uuid
from dataclasses import dataclass

import httpx


@dataclass
class Sample:
    name: str
    status: int
    total_ms: float
    body_len: int


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


def timed_request(client: httpx.Client, method: str, url: str, **kwargs) -> Sample:
    t0 = time.perf_counter()
    resp = client.request(method, url, **kwargs)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return Sample(name=url, status=resp.status_code, total_ms=elapsed_ms, body_len=len(resp.content))


def measure_series(client: httpx.Client, label: str, method: str, url: str, *, n: int = 5, **kwargs) -> list[Sample]:
    samples = []
    for _ in range(n):
        samples.append(timed_request(client, method, url, **kwargs))
    return samples


def summarize(samples: list[Sample]) -> dict:
    totals = [s.total_ms for s in samples]
    return {
        "count": len(samples),
        "min_ms": min(totals),
        "max_ms": max(totals),
        "mean_ms": statistics.mean(totals),
        "median_ms": statistics.median(totals),
        "p95_ms": percentile(totals, 0.95),
        "errors": sum(1 for s in samples if s.status >= 400),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://autogestor-api.vercel.app")
    parser.add_argument("--email-prefix", default="perf")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    email = f"{args.email_prefix}_{uuid.uuid4().hex[:10]}@example.com"
    senha = "SenhaForte!123"

    with httpx.Client(timeout=30.0) as client:
        health = measure_series(client, "health", "GET", f"{base_url}/health", n=5)
        signup_start = time.perf_counter()
        signup_resp = client.post(f"{base_url}/auth/cadastro", json={"nome": "Perf Prod", "email": email, "senha": senha})
        signup_ms = (time.perf_counter() - signup_start) * 1000

        login_start = time.perf_counter()
        login_resp = client.post(f"{base_url}/auth/login", json={"email": email, "senha": senha})
        login_ms = (time.perf_counter() - login_start) * 1000
        login_body = login_resp.json()
        token = login_body["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        espacos_resp = client.get(f"{base_url}/espacos", headers=headers)
        espacos = espacos_resp.json()
        pessoal = next(item for item in espacos if item["tipo"] == "PESSOAL")
        espaco_id = pessoal["id"]

        mov_create_payload = {"tipo": "GASTO", "categoria": "Perf", "descricao": "Benchmark", "valor": 99.5, "data": "2026-08-25"}
        mov_create_start = time.perf_counter()
        mov_create_resp = client.post(f"{base_url}/espacos/{espaco_id}/movimentacoes/", json=mov_create_payload, headers=headers)
        mov_create_ms = (time.perf_counter() - mov_create_start) * 1000
        mov_id = mov_create_resp.json()["id"]

        mov_update_payload = {"tipo": "GASTO", "categoria": "Perf", "descricao": "Benchmark ajustado", "valor": 101.25, "data": "2026-08-25"}
        mov_update_start = time.perf_counter()
        mov_update_resp = client.put(f"{base_url}/espacos/{espaco_id}/movimentacoes/{mov_id}", json=mov_update_payload, headers=headers)
        mov_update_ms = (time.perf_counter() - mov_update_start) * 1000

        mov_list = measure_series(client, "mov_list", "GET", f"{base_url}/espacos/{espaco_id}/movimentacoes/", n=5, headers=headers)
        dashboard = measure_series(client, "dashboard", "GET", f"{base_url}/espacos/{espaco_id}/dashboard/resumo", n=5, headers=headers)
        auth_me = measure_series(client, "auth_me", "GET", f"{base_url}/auth/me", n=5, headers=headers)

        report = {
            "base_url": base_url,
            "email": email,
            "signup": {"status": signup_resp.status_code, "ms": signup_ms, "body_len": len(signup_resp.content)},
            "login": {"status": login_resp.status_code, "ms": login_ms, "body_len": len(login_resp.content)},
            "mov_create": {"status": mov_create_resp.status_code, "ms": mov_create_ms, "body_len": len(mov_create_resp.content)},
            "mov_update": {"status": mov_update_resp.status_code, "ms": mov_update_ms, "body_len": len(mov_update_resp.content)},
            "health_series": [{"status": s.status, "ms": s.total_ms, "body_len": s.body_len} for s in health],
            "auth_me_series": [{"status": s.status, "ms": s.total_ms, "body_len": s.body_len} for s in auth_me],
            "mov_list_series": [{"status": s.status, "ms": s.total_ms, "body_len": s.body_len} for s in mov_list],
            "dashboard_series": [{"status": s.status, "ms": s.total_ms, "body_len": s.body_len} for s in dashboard],
            "summary": {
                "health": summarize(health),
                "auth_me": summarize(auth_me),
                "mov_list": summarize(mov_list),
                "dashboard": summarize(dashboard),
            },
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
