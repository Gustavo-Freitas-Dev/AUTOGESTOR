import json
import statistics
import time
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8002"


def one_attempt(client: httpx.Client, idx: int) -> dict:
    email = f"http_perf_{idx}_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"nome": "Perf HTTP", "email": email, "senha": "SenhaForte!123"}

    t0 = time.perf_counter()
    req = client.build_request("POST", f"{BASE_URL}/auth/cadastro", json=payload)
    resp = client.send(req)
    total_ms = (time.perf_counter() - t0) * 1000

    return {
        "attempt": idx,
        "status": resp.status_code,
        "total_ms": total_ms,
        "content_length": len(resp.content),
    }


def main() -> None:
    samples = []
    with httpx.Client(timeout=30.0) as client:
        for i in range(1, 6):
            samples.append(one_attempt(client, i))

    durations = [item["total_ms"] for item in samples]
    result = {
        "attempts": samples,
        "summary": {
            "count": len(samples),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "mean_ms": statistics.mean(durations),
            "median_ms": statistics.median(durations),
            "p95_ms": statistics.quantiles(durations, n=100)[94] if len(durations) >= 2 else durations[0],
            "errors": sum(1 for item in samples if item["status"] >= 400),
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
