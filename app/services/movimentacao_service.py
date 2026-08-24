from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import Select, asc, desc, select
from sqlalchemy.orm import Session

from app.models.movimentacao import Movimentacao
from app.schemas.movimentacao_schemas import AtualizarMovimentacao, CriarMovimentacao


def service_criar_movimentacao(
    db: Session,
    dado: CriarMovimentacao,
    usuario_id: int,
    espaco_id: int,
) -> Movimentacao:
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


def _apply_filters(
    stmt: Select[tuple[Movimentacao]],
    tipo: str | None,
    categoria: str | None,
    descricao: str | None,
    data_inicio: date | None,
    data_fim: date | None,
) -> Select[tuple[Movimentacao]]:
    if tipo:
        stmt = stmt.where(Movimentacao.tipo == tipo)
    if categoria:
        stmt = stmt.where(Movimentacao.categoria.ilike(f"%{categoria.strip()}%"))
    if descricao:
        stmt = stmt.where(Movimentacao.descricao.ilike(f"%{descricao.strip()}%"))
    if data_inicio:
        stmt = stmt.where(Movimentacao.data >= data_inicio)
    if data_fim:
        stmt = stmt.where(Movimentacao.data <= data_fim)
    return stmt


def _apply_ordering(stmt: Select[tuple[Movimentacao]], ordenar_por: str, ordem: str) -> Select[tuple[Movimentacao]]:
    direcao = desc if ordem == "desc" else asc
    if ordenar_por == "valor":
        return stmt.order_by(direcao(Movimentacao.valor), desc(Movimentacao.id))
    return stmt.order_by(direcao(Movimentacao.data), desc(Movimentacao.id))


def service_listar_movimentacoes(
    db: Session,
    espaco_id: int,
    tipo: str | None = None,
    categoria: str | None = None,
    descricao: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    ordenar_por: str = "data",
    ordem: str = "desc",
    limite: int = 100,
    offset: int = 0,
) -> list[Movimentacao]:
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data inicial nao pode ser maior que a data final.",
        )

    stmt = select(Movimentacao).where(Movimentacao.espaco_id == espaco_id)
    stmt = _apply_filters(stmt, tipo, categoria, descricao, data_inicio, data_fim)
    stmt = _apply_ordering(stmt, ordenar_por, ordem)
    stmt = stmt.offset(offset).limit(limite)

    return list(db.execute(stmt).scalars().all())


def service_atualizar_movimentacao(
    db: Session,
    id: int,
    dado: AtualizarMovimentacao,
    espaco_id: int,
) -> dict[str, str | Movimentacao]:
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


def service_deletar_movimentacao(db: Session, id: int, espaco_id: int) -> dict[str, str]:
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


def service_resumo_por_categoria(
    db: Session,
    espaco_id: int,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> list[dict[str, Decimal | str]]:
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data inicial nao pode ser maior que a data final.",
        )

    stmt = select(
        Movimentacao.categoria,
        Movimentacao.tipo,
        Movimentacao.valor,
    ).where(Movimentacao.espaco_id == espaco_id)

    if data_inicio:
        stmt = stmt.where(Movimentacao.data >= data_inicio)
    if data_fim:
        stmt = stmt.where(Movimentacao.data <= data_fim)

    agregados: dict[str, Decimal] = {}
    for categoria, tipo, valor in db.execute(stmt).all():
        atual = agregados.get(categoria, Decimal("0.00"))
        if str(tipo) == "GASTO":
            agregados[categoria] = atual - Decimal(valor)
        else:
            agregados[categoria] = atual + Decimal(valor)

    return [
        {"categoria": categoria, "total": total.quantize(Decimal("0.01"))}
        for categoria, total in sorted(agregados.items(), key=lambda item: item[1], reverse=True)
    ]
