from conftest import cadastrar


def espaco_pessoal(client, headers):
    resposta = client.get("/espacos", headers=headers)
    assert resposta.status_code == 200
    return next(e for e in resposta.json() if e["tipo"] == "PESSOAL")


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


def test_nao_autenticado_recebe_401(client):
    assert client.get("/espacos").status_code == 401


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


def test_membro_compartilha_movimentos_e_nao_membro_recebe_403(client, dois_usuarios):
    (_, ha), (_, hb) = dois_usuarios
    espaco = criar_compartilhado(client, ha)
    client.post("/espacos/entrar", json={"codigo": espaco["codigo_acesso"]}, headers=hb)
    criada = client.post(f"/espacos/{espaco['id']}/movimentacoes/", json=movimento(), headers=ha)
    assert criada.status_code == 200
    assert len(client.get(f"/espacos/{espaco['id']}/movimentacoes/", headers=hb).json()) == 1
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
