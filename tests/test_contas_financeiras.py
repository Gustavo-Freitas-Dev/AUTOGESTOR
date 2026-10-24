from conftest import cadastrar


def pessoal(client, headers):
    return next(e["id"] for e in client.get("/espacos", headers=headers).json() if e["tipo"] == "PESSOAL")


def test_conta_saldo_e_movimento(client):
    _, h = cadastrar(client, "Conta", "conta_v2@example.com")
    e = pessoal(client, h)
    r = client.post(f"/espacos/{e}/contas/", headers=h, json={
        "nome": "Banco", "tipo": "BANCO", "ambiente": "PESSOAL", "saldo_inicial": "100.00"
    })
    assert r.status_code == 201, r.text
    conta = r.json()["id"]
    m = client.post(f"/espacos/{e}/movimentacoes/", headers=h, json={
        "tipo": "GASTO", "categoria": "Mercado", "valor": "25.00",
        "data": "2026-10-16", "conta_id": conta
    })
    assert m.status_code == 200, m.text
    assert m.json()["conta_id"] == conta
    saldos = client.get(f"/espacos/{e}/contas/", headers=h)
    assert saldos.status_code == 200, saldos.text
    assert saldos.json()[0]["saldo_atual"] == "75.00"


def test_conta_de_outro_espaco_rejeitada(client, dois_usuarios):
    (_, ha), (_, hb) = dois_usuarios
    ea, eb = pessoal(client, ha), pessoal(client, hb)
    conta = client.post(f"/espacos/{ea}/contas/", headers=ha, json={
        "nome": "Banco", "tipo": "BANCO", "ambiente": "PESSOAL"
    }).json()["id"]
    r = client.post(f"/espacos/{eb}/movimentacoes/", headers=hb, json={
        "tipo": "GANHO", "categoria": "Teste", "valor": "10.00",
        "data": "2026-10-16", "conta_id": conta
    })
    assert r.status_code == 422, r.text


def test_lancamento_legado_sem_conta(client):
    _, h = cadastrar(client, "Legado", "legado_v2@example.com")
    e = pessoal(client, h)
    r = client.post(f"/espacos/{e}/movimentacoes/", headers=h, json={
        "tipo": "GANHO", "categoria": "Salario", "valor": "50.00",
        "data": "2026-10-16"
    })
    assert r.status_code == 200, r.text
    assert r.json()["conta_id"] is None
