from decimal import Decimal

from app.models.usuario_model import Usuario
from app.services.espaco_service import criar_espaco_compartilhado, entrar_por_codigo
from tests.conftest import cadastrar


def _mov(client, headers, espaco_id, tipo, valor, data, categoria="Teste"):
    resposta = client.post(
        f"/espacos/{espaco_id}/movimentacoes/",
        headers=headers,
        json={"tipo": tipo, "valor": valor, "data": data, "categoria": categoria},
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_resumo_mensal_exclui_primeiro_dia_do_mes_seguinte(client, db):
    _, headers = cadastrar(client, "Teste", "mensal@example.com")
    usuario = db.query(Usuario).filter_by(email="mensal@example.com").one()
    espaco_id = usuario.membros_espacos[0].espaco_id
    _mov(client, headers, espaco_id, "GANHO", "100.00", "2026-10-31")
    _mov(client, headers, espaco_id, "GASTO", "40.00", "2026-11-01")
    resposta = client.get(
        f"/espacos/{espaco_id}/dashboard/resumo-mensal?ano=2026&mes=10",
        headers=headers,
    )
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert Decimal(str(dados["total_ganhos"])) == Decimal("100.00")
    assert Decimal(str(dados["total_gastos"])) == Decimal("0.00")
    assert dados["quantidade_movimentacoes"] == 1


def test_membro_visualiza_extrato_compartilhado_sem_editar_movimento_alheio(client, db):
    _, headers_a = cadastrar(client, "Ana", "ana.shared@example.com")
    _, headers_b = cadastrar(client, "Bruno", "bruno.shared@example.com")
    ana = db.query(Usuario).filter_by(email="ana.shared@example.com").one()
    bruno = db.query(Usuario).filter_by(email="bruno.shared@example.com").one()
    espaco = criar_espaco_compartilhado(db, ana.id, "Casa")
    entrar_por_codigo(db, bruno.id, espaco.codigo_acesso)
    movimento = _mov(client, headers_a, espaco.id, "GASTO", "25.00", "2026-10-10")
    resposta = client.get(f"/espacos/{espaco.id}/movimentacoes/", headers=headers_b)
    assert resposta.status_code == 200, resposta.text
    assert any(item["id"] == movimento["id"] for item in resposta.json())
    categorias = client.get(
        f"/espacos/{espaco.id}/movimentacoes/resumo-por-categoria", headers=headers_b
    )
    assert categorias.status_code == 200, categorias.text
    assert any(item["categoria"] == "Teste" for item in categorias.json())
    edicao = client.put(
        f"/espacos/{espaco.id}/movimentacoes/{movimento['id']}",
        headers=headers_b,
        json={"tipo": "GASTO", "valor": "99.00", "data": "2026-10-10", "categoria": "Teste"},
    )
    assert edicao.status_code == 403
