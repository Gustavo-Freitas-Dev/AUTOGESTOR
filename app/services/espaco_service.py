import secrets
import string

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import PapelMembro, TipoEspaco
from app.models.espaco_financeiro import EspacoFinanceiro
from app.models.membro_espaco import MembroEspaco
from app.models.usuario_model import Usuario

ALFABETO_CODIGO = string.ascii_uppercase + string.digits
TAMANHO_CODIGO = 8
PAPEIS_ADMINISTRATIVOS = {PapelMembro.DONO, PapelMembro.ADMIN}


def gerar_codigo_unico(db: Session) -> str:
    for _ in range(20):
        codigo = "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(TAMANHO_CODIGO))
        existe = db.query(EspacoFinanceiro.id).filter(func.upper(EspacoFinanceiro.codigo_acesso) == codigo).first()
        if not existe:
            return codigo
    raise HTTPException(status_code=500, detail="Não foi possível gerar um código de acesso.")


def verificar_acesso_espaco(usuario_id: int, espaco_id: int, db: Session) -> MembroEspaco:
    membro = db.query(MembroEspaco).filter(
        MembroEspaco.usuario_id == usuario_id,
        MembroEspaco.espaco_id == espaco_id,
    ).first()
    if not membro:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não possui acesso a este espaço.")
    return membro


def verificar_administrador(usuario_id: int, espaco_id: int, db: Session) -> MembroEspaco:
    membro = verificar_acesso_espaco(usuario_id, espaco_id, db)
    if membro.papel not in PAPEIS_ADMINISTRATIVOS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administradores podem realizar esta ação.")
    return membro


def criar_espaco_pessoal(db: Session, usuario: Usuario) -> EspacoFinanceiro:
    espaco = EspacoFinanceiro(
        nome="Meu espaço",
        tipo=TipoEspaco.PESSOAL,
        codigo_acesso=None,
        codigo_ativo=False,
        limite_membros=1,
        criado_por_id=usuario.id,
    )
    db.add(espaco)
    db.flush()
    db.add(MembroEspaco(usuario_id=usuario.id, espaco_id=espaco.id, papel=PapelMembro.DONO))
    db.flush()
    return espaco


def criar_espaco_compartilhado(db: Session, usuario_id: int, nome: str, limite_membros: int = 5) -> EspacoFinanceiro:
    espaco = EspacoFinanceiro(
        nome=nome.strip(), tipo=TipoEspaco.COMPARTILHADO,
        codigo_acesso=gerar_codigo_unico(db), codigo_ativo=True,
        limite_membros=limite_membros, criado_por_id=usuario_id,
    )
    db.add(espaco)
    db.flush()
    db.add(MembroEspaco(usuario_id=usuario_id, espaco_id=espaco.id, papel=PapelMembro.ADMIN))
    db.commit()
    db.refresh(espaco)
    return espaco


def entrar_por_codigo(db: Session, usuario_id: int, codigo: str) -> EspacoFinanceiro:
    normalizado = codigo.strip().upper()
    espaco = db.query(EspacoFinanceiro).filter(func.upper(EspacoFinanceiro.codigo_acesso) == normalizado).first()
    if not espaco:
        raise HTTPException(status_code=404, detail="Código de acesso inválido.")
    if espaco.tipo != TipoEspaco.COMPARTILHADO:
        raise HTTPException(status_code=400, detail="Não é possível entrar em um espaço pessoal.")
    if not espaco.codigo_ativo:
        raise HTTPException(status_code=400, detail="Este código de acesso está desativado.")
    if db.query(MembroEspaco).filter_by(usuario_id=usuario_id, espaco_id=espaco.id).first():
        raise HTTPException(status_code=409, detail="Você já participa deste espaço.")
    quantidade = db.query(MembroEspaco).filter_by(espaco_id=espaco.id).count()
    if quantidade >= espaco.limite_membros:
        raise HTTPException(status_code=409, detail="O espaço atingiu o limite de membros.")
    db.add(MembroEspaco(usuario_id=usuario_id, espaco_id=espaco.id, papel=PapelMembro.MEMBRO))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Você já participa deste espaço.")
    db.refresh(espaco)
    return espaco


def listar_espacos(db: Session, usuario_id: int) -> list[dict]:
    vinculos = db.query(MembroEspaco).filter_by(usuario_id=usuario_id).all()
    return [serializar_espaco(db, vinculo.espaco, vinculo) for vinculo in vinculos]


def serializar_espaco(db: Session, espaco: EspacoFinanceiro, membro: MembroEspaco) -> dict:
    administrador = membro.papel in PAPEIS_ADMINISTRATIVOS
    return {
        "id": espaco.id, "nome": espaco.nome, "tipo": espaco.tipo,
        "papel": membro.papel,
        "quantidade_membros": db.query(MembroEspaco).filter_by(espaco_id=espaco.id).count(),
        "codigo_acesso": espaco.codigo_acesso if administrador else None,
        "codigo_ativo": espaco.codigo_ativo,
        "limite_membros": espaco.limite_membros,
        "criado_por_id": espaco.criado_por_id, "criado_em": espaco.criado_em,
    }


def regenerar_codigo(db: Session, espaco: EspacoFinanceiro) -> str:
    if espaco.tipo != TipoEspaco.COMPARTILHADO:
        raise HTTPException(status_code=400, detail="Espaços pessoais não possuem código de acesso.")
    espaco.codigo_acesso = gerar_codigo_unico(db)
    espaco.codigo_ativo = True
    db.commit()
    return espaco.codigo_acesso
