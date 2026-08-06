from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.models.movimentacao import Movimentacao
from app.schemas.movimentacao_schemas import (
    CriarMovimentacao,
    AtualizarMovimentacao
)


def service_criar_movimentacao(db: Session, dado: CriarMovimentacao, usuario_id: int, espaco_id: int):
    """
    MUDANÇA: agora recebe usuario_id e grava ele na movimentação
    criada. Sem isso, o registro ficaria "órfão" (sem dono),
    e voltaria a aparecer pra todo mundo.
    """
    movimentacao = Movimentacao(
        espaco_id=espaco_id,
        criado_por_id=usuario_id,
        tipo=dado.tipo,
        categoria=dado.categoria,
        descricao=dado.descricao,
        valor=dado.valor,
        data=dado.data
    )

    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)

    return movimentacao


def service_listar_movimentacoes(db: Session, espaco_id: int):
    """
    MUDANÇA PRINCIPAL: antes fazia .all() — trazia TUDO, de TODOS
    os usuários, sempre. Agora filtra por Movimentacao.usuario_id,
    então cada usuário só vê o que é dele.
    """
    return (
        db.query(Movimentacao)
        .filter(Movimentacao.espaco_id == espaco_id)
        .all()
    )


def service_atualizar_movimentacao(db: Session, id: int, dado: AtualizarMovimentacao, espaco_id: int):
    """
    MUDANÇA: o filtro agora exige id E usuario_id batendo juntos.
    Isso impede que o Usuário A edite uma movimentação que
    pertence ao Usuário B, mesmo sabendo o ID dela (ex: tentando
    na mão pela URL/Swagger). Sem essa segunda condição, qualquer
    pessoa logada poderia editar dados de qualquer outra.
    """
    movimentacao = (
        db.query(Movimentacao)
        .filter(Movimentacao.id == id, Movimentacao.espaco_id == espaco_id)
        .first()
    )

    if not movimentacao:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")

    movimentacao.tipo = dado.tipo
    movimentacao.categoria = dado.categoria
    movimentacao.descricao = dado.descricao
    movimentacao.valor = dado.valor
    movimentacao.data = dado.data

    db.commit()
    db.refresh(movimentacao)

    return {
        "message": "Movimentação atualizada com sucesso",
        "movimentacao": movimentacao
    }


def service_deletar_movimentacao(db: Session, id: int, espaco_id: int):
    """
    Mesma proteção do update: só deleta se a movimentação
    pertencer ao usuário que está fazendo a requisição.
    """
    movimentacao = (
        db.query(Movimentacao)
        .filter(Movimentacao.id == id, Movimentacao.espaco_id == espaco_id)
        .first()
    )

    if not movimentacao:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")

    db.delete(movimentacao)
    db.commit()

    return {
        "message": "Movimentação deletada com sucesso"
    }


def service_buscar_id(db: Session, id: int, espaco_id: int):
    """
    Mesma proteção: busca por id, mas só dentro das movimentações
    daquele usuário.
    """
    movimentacao = (
        db.query(Movimentacao)
        .filter(Movimentacao.id == id, Movimentacao.espaco_id == espaco_id)
        .first()
    )

    if not movimentacao:
        raise HTTPException(
            status_code=404,
            detail="Movimentação não encontrada"
        )

    return movimentacao
