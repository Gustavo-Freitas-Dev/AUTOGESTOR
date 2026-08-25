from conftest import cadastrar


def espaco_pessoal(client, headers):
    resposta = client.get("/espacos", headers=headers)
    assert resposta.status_code == 200
    return next(e for e in resposta.json() if e["tipo"] == "PESSOAL")


def test_healthcheck(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def criar_compartilhado(client, headers, nome="Casa", limite=5):
    resposta = client.post("/espacos/compartilhados", json={"nome": nome, "limite_membros": limite}, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def movimento(valor=100, tipo="GANHO"):
    return {"tipo": tipo, "categoria": "Teste", "descricao": "Registro", "valor": valor, "data": "2026-08-05"}


def test_cadastro_cria_usuario_espaco_pessoal_e_dono(client):
    usuario, headers = cadastrar(client, "Ana", "ana@example.com")
    assert usuario["usuario"]["email"] == "ana@example.com"
    espacos = client.get("/espacos", headers=headers).json()
    assert len(espacos) == 1
    assert espacos[0]["tipo"] == "PESSOAL"
    assert espacos[0]["papel"] == "DONO"
    membros = client.get(f"/espacos/{espacos[0]['id']}/membros", headers=headers).json()
    assert len(membros) == 1
    assert membros[0]["usuario_id"] == usuario["usuario"]["id"]


def test_obter_usuario_atual(client):
    usuario, headers = cadastrar(client, "Ana", "ana_me@example.com")
    resposta = client.get("/auth/me", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["email"] == usuario["usuario"]["email"]


def test_usuario_pode_excluir_propria_conta(client):
    usuario, headers = cadastrar(client, "Ana", "ana_excluir@example.com")

    resposta = client.request(
        "DELETE",
        "/auth/me",
        json={"senha_atual": "senha123"},
        headers=headers,
    )
    assert resposta.status_code == 200
    assert resposta.json()["message"] == "Conta excluída com sucesso."

    resposta_me = client.get("/auth/me", headers=headers)
    assert resposta_me.status_code == 401

    resposta_login = client.post(
        "/auth/login",
        json={"email": usuario["usuario"]["email"], "senha": "senha123"},
    )
    assert resposta_login.status_code == 401


def test_excluir_conta_exige_senha_atual_valida(client):
    _, headers = cadastrar(client, "Ana", "ana_excluir_invalida@example.com")

    resposta = client.request(
        "DELETE",
        "/auth/me",
        json={"senha_atual": "senha-errada"},
        headers=headers,
    )
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "Senha atual incorreta."

    resposta_me = client.get("/auth/me", headers=headers)
    assert resposta_me.status_code == 200


def test_nao_autenticado_recebe_401(client):
    assert client.get("/espacos").status_code == 401


def test_token_invalido_recebe_401(client):
    headers = {"Authorization": "Bearer token-invalido"}
    resposta = client.get("/espacos", headers=headers)
    assert resposta.status_code == 401


def test_outro_usuario_nao_acessa_pessoal(client, dois_usuarios):
    (_, ha), (_, hb) = dois_usuarios
    pessoal = espaco_pessoal(client, ha)
    assert client.get(f"/espacos/{pessoal['id']}", headers=hb).status_code == 403
    assert client.get(f"/espacos/{pessoal['id']}/movimentacoes/", headers=hb).status_code == 403


def test_criar_compartilhado_e_entrar_com_codigo(client, dois_usuarios):
    (_, ha), (_, hb) = dois_usuarios
    espaco = criar_compartilhado(client, ha)
    assert len(espaco["codigo_acesso"]) == 8
    entrada = client.post("/espacos/entrar", json={"codigo": espaco["codigo_acesso"].lower()}, headers=hb)
    assert entrada.status_code == 200
    assert entrada.json()["papel"] == "MEMBRO"
    assert len(client.get(f"/espacos/{espaco['id']}/membros", headers=ha).json()) == 2


def test_codigo_invalido_duplicidade_e_limite(client, dois_usuarios):
    (_, ha), (_, hb) = dois_usuarios
    assert client.post("/espacos/entrar", json={"codigo": "XXXXXXXX"}, headers=hb).status_code == 404
    espaco = criar_compartilhado(client, ha, limite=2)
    codigo = espaco["codigo_acesso"]
    assert client.post("/espacos/entrar", json={"codigo": codigo}, headers=ha).status_code == 409
    assert client.post("/espacos/entrar", json={"codigo": codigo}, headers=hb).status_code == 200
    _, hc = cadastrar(client, "Caio", "caio@example.com")
    assert client.post("/espacos/entrar", json={"codigo": codigo}, headers=hc).status_code == 409


def test_membro_ve_apenas_as_proprias_movimentacoes_no_compartilhado(client, dois_usuarios):
    (_, ha), (_, hb) = dois_usuarios
    espaco = criar_compartilhado(client, ha)
    client.post("/espacos/entrar", json={"codigo": espaco["codigo_acesso"]}, headers=hb)
    criada = client.post(f"/espacos/{espaco['id']}/movimentacoes/", json=movimento(), headers=ha)
    assert criada.status_code == 200

    lista_b = client.get(f"/espacos/{espaco['id']}/movimentacoes/", headers=hb)
    assert lista_b.status_code == 200
    assert lista_b.json() == []

    leitura_cruzada = client.get(
        f"/espacos/{espaco['id']}/movimentacoes/{criada.json()['id']}",
        headers=hb,
    )
    assert leitura_cruzada.status_code == 404

    _, hc = cadastrar(client, "Caio", "caio2@example.com")
    assert client.get(f"/espacos/{espaco['id']}/movimentacoes/", headers=hc).status_code == 403


def test_movimentacoes_filtradas_e_id_sem_acesso_cruzado(client, dois_usuarios):
    (_, ha), (_, hb) = dois_usuarios
    pa, pb = espaco_pessoal(client, ha), espaco_pessoal(client, hb)
    criada = client.post(f"/espacos/{pa['id']}/movimentacoes/", json=movimento(), headers=ha).json()
    assert client.get(f"/espacos/{pb['id']}/movimentacoes/", headers=hb).json() == []
    assert client.get(f"/espacos/{pb['id']}/movimentacoes/{criada['id']}", headers=hb).status_code == 404
    assert client.get(f"/espacos/{pa['id']}/movimentacoes/", headers=hb).status_code == 403


def test_regenerar_invalida_codigo_antigo(client, dois_usuarios):
    (_, ha), (_, hb) = dois_usuarios
    espaco = criar_compartilhado(client, ha)
    antigo = espaco["codigo_acesso"]
    resposta = client.post(f"/espacos/{espaco['id']}/regenerar-codigo", headers=ha)
    assert resposta.status_code == 200
    novo = resposta.json()["codigo_acesso"]
    assert novo != antigo
    assert client.post("/espacos/entrar", json={"codigo": antigo}, headers=hb).status_code == 404
    assert client.post("/espacos/entrar", json={"codigo": novo}, headers=hb).status_code == 200


def test_membro_sem_permissao_administrativa(client, dois_usuarios):
    (_, ha), (_, hb) = dois_usuarios
    espaco = criar_compartilhado(client, ha)
    client.post("/espacos/entrar", json={"codigo": espaco["codigo_acesso"]}, headers=hb)
    assert client.patch(f"/espacos/{espaco['id']}", json={"nome": "Novo"}, headers=hb).status_code == 403
    assert client.post(f"/espacos/{espaco['id']}/regenerar-codigo", headers=hb).status_code == 403


def test_espaco_pessoal_nao_pode_ser_excluido(client):
    _, headers = cadastrar(client, "Ana", "ana3@example.com")
    pessoal = espaco_pessoal(client, headers)
    assert client.delete(f"/espacos/{pessoal['id']}", headers=headers).status_code == 400


def test_dono_edita_nome_do_pessoal_e_admin_edita_compartilhado(client):
    _, headers = cadastrar(client, "Ana", "ana5@example.com")
    pessoal = espaco_pessoal(client, headers)
    resposta = client.patch(f"/espacos/{pessoal['id']}", json={"nome": "Minhas finanças"}, headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Minhas finanças"
    compartilhado = criar_compartilhado(client, headers)
    resposta = client.patch(
        f"/espacos/{compartilhado['id']}",
        json={"nome": "Casa nova", "codigo_ativo": False, "limite_membros": 10}, headers=headers,
    )
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Casa nova"
    assert resposta.json()["codigo_ativo"] is False
    assert resposta.json()["limite_membros"] == 10


def test_limite_configuravel_validado(client):
    _, headers = cadastrar(client, "Ana", "ana6@example.com")
    assert client.post("/espacos/compartilhados", json={"nome": "Inválido", "limite_membros": 21}, headers=headers).status_code == 422
    espaco = criar_compartilhado(client, headers, limite=7)
    assert espaco["limite_membros"] == 7


def test_administrador_exclui_espaco_compartilhado(client):
    _, headers = cadastrar(client, "Ana", "ana4@example.com")
    espaco = criar_compartilhado(client, headers, "Temporário")
    client.post(f"/espacos/{espaco['id']}/movimentacoes/", json=movimento(), headers=headers)
    assert client.delete(f"/espacos/{espaco['id']}", headers=headers).status_code == 204
    assert client.get(f"/espacos/{espaco['id']}", headers=headers).status_code == 403


def test_dashboard_isolado_por_espaco(client, dois_usuarios):
    (_, ha), (_, hb) = dois_usuarios
    pa, pb = espaco_pessoal(client, ha), espaco_pessoal(client, hb)
    client.post(f"/espacos/{pa['id']}/movimentacoes/", json=movimento(150), headers=ha)
    client.post(f"/espacos/{pb['id']}/movimentacoes/", json=movimento(999), headers=hb)
    resumo = client.get(f"/espacos/{pa['id']}/dashboard/resumo", headers=ha).json()
    assert float(resumo["Saldo"]) == 150


def test_filtros_ordenacao_e_paginacao_movimentacoes(client):
    _, headers = cadastrar(client, "Ana", "ana_filtros@example.com")
    espaco = espaco_pessoal(client, headers)

    payloads = [
        {"tipo": "GANHO", "categoria": "Salario", "descricao": "Agosto", "valor": 3000, "data": "2026-08-01"},
        {"tipo": "GASTO", "categoria": "Mercado", "descricao": "Compra", "valor": 250, "data": "2026-08-02"},
        {"tipo": "GASTO", "categoria": "Transporte", "descricao": "Uber", "valor": 40, "data": "2026-08-03"},
    ]
    for payload in payloads:
        resposta = client.post(f"/espacos/{espaco['id']}/movimentacoes/", json=payload, headers=headers)
        assert resposta.status_code == 200

    resposta = client.get(
        f"/espacos/{espaco['id']}/movimentacoes/?tipo=GASTO&categoria=mercado",
        headers=headers,
    )
    assert resposta.status_code == 200
    dados = resposta.json()
    assert len(dados) == 1
    assert dados[0]["categoria"] == "Mercado"

    resposta = client.get(
        f"/espacos/{espaco['id']}/movimentacoes/?ordenar_por=valor&ordem=asc&limite=1&offset=0",
        headers=headers,
    )
    assert resposta.status_code == 200
    dados = resposta.json()
    assert len(dados) == 1
    assert float(dados[0]["valor"]) == 40.0


def test_periodo_invertido_retorna_400(client):
    _, headers = cadastrar(client, "Ana", "ana_periodo@example.com")
    espaco = espaco_pessoal(client, headers)

    resposta = client.get(
        f"/espacos/{espaco['id']}/movimentacoes/?data_inicio=2026-08-10&data_fim=2026-08-01",
        headers=headers,
    )
    assert resposta.status_code == 400

    resposta = client.get(
        f"/espacos/{espaco['id']}/dashboard/periodo?data_inicio=2026-08-10&data_fim=2026-08-01",
        headers=headers,
    )
    assert resposta.status_code == 400


def test_resumo_por_categoria(client):
    _, headers = cadastrar(client, "Ana", "ana_resumo@example.com")
    espaco = espaco_pessoal(client, headers)
    client.post(f"/espacos/{espaco['id']}/movimentacoes/", json=movimento(400, "GANHO"), headers=headers)
    client.post(
        f"/espacos/{espaco['id']}/movimentacoes/",
        json={"tipo": "GASTO", "categoria": "Alimentacao", "descricao": "Mercado", "valor": 100, "data": "2026-08-05"},
        headers=headers,
    )

    resposta = client.get(f"/espacos/{espaco['id']}/movimentacoes/resumo-por-categoria", headers=headers)
    assert resposta.status_code == 200
    categorias = {item["categoria"]: item["total"] for item in resposta.json()}
    assert "Teste" in categorias
    assert "Alimentacao" in categorias
