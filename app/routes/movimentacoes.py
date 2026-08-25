from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.auth_dependencies import obter_usuario_atual
from app.database.dependencies import get_db
from app.models.usuario_model import Usuario  # ← novo import (tipo do usuário)
from app.schemas.movimentacao_schemas import (
    AtualizarMovimentacao,
    CriarMovimentacao,
    MovimentacaoResposta,
)
from app.services.espaco_service import verificar_acesso_espaco
from app.services.movimentacao_service import (
    service_atualizar_movimentacao,
    service_buscar_id,
    service_criar_movimentacao,
    service_deletar_movimentacao,
    service_listar_movimentacoes,
    service_resumo_por_categoria,
)

router = APIRouter(prefix="/espacos/{espaco_id}/movimentacoes", tags=["Movimentações"])


@router.post(
    "/",
    summary="Cadastra uma nova movimentação",
    description="Rota para cadastrar uma nova movimentação no banco de dados, vinculada ao usuário logado"
)
def criar(
    espaco_id: int,
    dado: CriarMovimentacao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),   # ← exige login
) -> MovimentacaoResposta:
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_criar_movimentacao(db, dado, usuario.id, espaco_id)


@router.get(
    "/",
    summary="Visualizar movimentações",
    description="Retorna apenas as movimentações do usuário logado"
)
def view(
    espaco_id: int,
    tipo: Literal["GANHO", "GASTO"] | None = Query(default=None),
    categoria: str | None = Query(default=None, min_length=1, max_length=80),
    descricao: str | None = Query(default=None, min_length=1, max_length=255),
    data_inicio: date | None = None,
    data_fim: date | None = None,
    ordenar_por: Literal["data", "valor"] = "data",
    ordem: Literal["asc", "desc"] = "desc",
    limite: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),   # ← exige login
) -> list[MovimentacaoResposta]:
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_listar_movimentacoes(
        db,
        espaco_id,
        tipo=tipo,
        categoria=categoria,
        descricao=descricao,
        data_inicio=data_inicio,
        data_fim=data_fim,
        ordenar_por=ordenar_por,
        ordem=ordem,
        limite=limite,
        offset=offset,
    )


@router.put(
    "/{id}",
    summary="Atualizar movimentação",
    description="Atualiza uma movimentação, desde que pertença ao usuário logado"
)
def update(
    espaco_id: int,
    id: int,
    dado: AtualizarMovimentacao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),   # ← exige login
) -> dict:
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_atualizar_movimentacao(db, id, dado, espaco_id, usuario.id)


@router.delete(
    "/{id}",
    summary="Deletar movimentação",
    description="Deleta uma movimentação, desde que pertença ao usuário logado"
)
def delete(
    espaco_id: int,
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),   # ← exige login
) -> dict[str, str]:
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_deletar_movimentacao(db, id, espaco_id)


@router.get(
    "/resumo-por-categoria",
    summary="Resumo financeiro por categoria",
    description="Retorna os totais liquidos por categoria no periodo informado.",
)
def resumo_por_categoria(
    espaco_id: int,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
) -> list[dict[str, str | float]]:
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    dados = service_resumo_por_categoria(db, espaco_id, data_inicio=data_inicio, data_fim=data_fim)
    return [{"categoria": item["categoria"], "total": float(item["total"])} for item in dados]


@router.get(
    "/{id}",
    summary='Busca movimentação pelo ID',
    description='Busca a movimentação pelo ID, desde que pertença ao usuário logado'
)
def buscar_id(
    espaco_id: int,
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),   # ← exige login
) -> MovimentacaoResposta:
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_buscar_id(db, id, espaco_id)
