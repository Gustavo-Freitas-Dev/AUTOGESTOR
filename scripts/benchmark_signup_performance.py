import argparse
import json
import statistics
import time
import uuid
from dataclasses import dataclass

import httpx


@dataclass
class Attempt:
    idx: int
    status: int
    total_ms: float
    ttfb_ms: float | None
    server_timing: dict[str, float]
    request_id: str | None


def parse_server_timing(value: str | None) -> dict[str, float]:
    if not value:
        return {}
    metrics: dict[str, float] = {}
    for part in value.split(","):
        tokens = [item.strip() for item in part.split(";") if item.strip()]
        if not tokens:
            continue
        name = tokens[0]
        dur = None
        for token in tokens[1:]:
            if token.startswith("dur="):
                try:
                    dur = float(token.split("=", 1)[1])
                except ValueError:
                    dur = None
        if dur is not None:
            metrics[name] = dur
    return metrics


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


def one_attempt(client: httpx.Client, base_url: str, idx: int) -> Attempt:
    email = f"perf_{idx}_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"nome": "Perf Runner", "email": email, "senha": "SenhaForte!123"}

    t0 = time.perf_counter()
    with client.stream("POST", f"{base_url}/auth/cadastro", json=payload) as response:
        first_chunk_at = None
        for chunk in response.iter_bytes():
            if chunk and first_chunk_at is None:
                first_chunk_at = time.perf_counter()
            # Consome o corpo inteiro no mesmo iterator para evitar StreamConsumed.
            continue
        total_ms = (time.perf_counter() - t0) * 1000

        ttfb_ms = None
        if first_chunk_at is not None:
            ttfb_ms = (first_chunk_at - t0) * 1000

        return Attempt(
            idx=idx,
            status=response.status_code,
            total_ms=total_ms,
            ttfb_ms=ttfb_ms,
            server_timing=parse_server_timing(response.headers.get("server-timing")),
            request_id=response.headers.get("x-request-id"),
        )


def summarize(attempts: list[Attempt]) -> dict:
    totals = [a.total_ms for a in attempts]
    ttfb_values = [a.ttfb_ms for a in attempts if a.ttfb_ms is not None]
    warm = attempts[1:] if len(attempts) > 1 else attempts
    warm_totals = [a.total_ms for a in warm]

    return {
        "first_attempt_ms": attempts[0].total_ms if attempts else None,
        "second_attempt_ms": attempts[1].total_ms if len(attempts) > 1 else None,
        "five_attempts_ms": totals,
        "mean_ms": statistics.mean(totals) if totals else 0.0,
        "median_ms": statistics.median(totals) if totals else 0.0,
        "p95_ms": percentile(totals, 0.95),
        "min_ms": min(totals) if totals else 0.0,
        "max_ms": max(totals) if totals else 0.0,
        "warm_mean_ms": statistics.mean(warm_totals) if warm_totals else 0.0,
        "errors": sum(1 for a in attempts if a.status >= 400),
        "ttfb_mean_ms": statistics.mean(ttfb_values) if ttfb_values else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark controlado do cadastro")
    parser.add_argument("--base-url", default="http://127.0.0.1:8002")
    parser.add_argument("--attempts", type=int, default=5)
    args = parser.parse_args()

    attempts: list[Attempt] = []
    with httpx.Client(timeout=30.0) as client:
        for idx in range(1, args.attempts + 1):
            attempts.append(one_attempt(client, args.base_url.rstrip("/"), idx))

    output = {
        "summary": summarize(attempts),
        "attempts": [
            {
                "idx": a.idx,
                "status": a.status,
                "total_ms": a.total_ms,
                "ttfb_ms": a.ttfb_ms,
                "request_id": a.request_id,
                "server_timing": a.server_timing,
            }
            for a in attempts
        ],
        "note": "Para medir nova tentativa apos inatividade, execute este script novamente depois do periodo desejado.",
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
