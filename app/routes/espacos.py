from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.auth_dependencies import obter_usuario_atual
from app.database.dependencies import get_db
from app.models.enums import PapelMembro, TipoEspaco
from app.models.membro_espaco import MembroEspaco
from app.models.usuario_model import Usuario
from app.schemas.espaco_schemas import (
    AtualizarEspaco,
    CodigoRegenerado,
    CriarEspacoCompartilhado,
    EntrarEspaco,
    EspacoDetalhe,
    EspacoResumo,
    MembroResposta,
)
from app.services.espaco_service import (
    criar_espaco_compartilhado,
    entrar_por_codigo,
    listar_espacos,
    regenerar_codigo,
    serializar_espaco,
    verificar_acesso_espaco,
    verificar_administrador,
)

router = APIRouter(prefix="/espacos", tags=["Espaços financeiros"])


@router.get("", response_model=list[EspacoResumo])
def listar(db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    return listar_espacos(db, usuario.id)


@router.get("/{espaco_id}", response_model=EspacoDetalhe)
def detalhar(espaco_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    membro = verificar_acesso_espaco(usuario.id, espaco_id, db)
    return serializar_espaco(db, membro.espaco, membro)


@router.post("/compartilhados", response_model=EspacoDetalhe, status_code=status.HTTP_201_CREATED)
def criar(dado: CriarEspacoCompartilhado, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    espaco = criar_espaco_compartilhado(db, usuario.id, dado.nome, dado.limite_membros)
    membro = verificar_acesso_espaco(usuario.id, espaco.id, db)
    return serializar_espaco(db, espaco, membro)


@router.post("/entrar", response_model=EspacoDetalhe)
def entrar(dado: EntrarEspaco, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    espaco = entrar_por_codigo(db, usuario.id, dado.codigo)
    membro = verificar_acesso_espaco(usuario.id, espaco.id, db)
    return serializar_espaco(db, espaco, membro)


@router.patch("/{espaco_id}", response_model=EspacoDetalhe)
def atualizar(espaco_id: int, dado: AtualizarEspaco, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    membro = verificar_administrador(usuario.id, espaco_id, db)
    membro.espaco.nome = dado.nome.strip()
    if dado.codigo_ativo is not None:
        if membro.espaco.tipo == TipoEspaco.PESSOAL and dado.codigo_ativo:
            raise HTTPException(status_code=400, detail="Espaços pessoais não podem ativar código de acesso.")
        membro.espaco.codigo_ativo = dado.codigo_ativo
    if dado.limite_membros is not None:
        if membro.espaco.tipo == TipoEspaco.PESSOAL:
            raise HTTPException(status_code=400, detail="O espaço pessoal possui somente um membro.")
        quantidade = db.query(MembroEspaco).filter_by(espaco_id=espaco_id).count()
        if dado.limite_membros < quantidade:
            raise HTTPException(status_code=400, detail="O limite não pode ser menor que a quantidade atual de membros.")
        membro.espaco.limite_membros = dado.limite_membros
    db.commit()
    db.refresh(membro.espaco)
    return serializar_espaco(db, membro.espaco, membro)


@router.delete("/{espaco_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(espaco_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    membro = verificar_administrador(usuario.id, espaco_id, db)
    if membro.espaco.tipo == TipoEspaco.PESSOAL:
        raise HTTPException(status_code=400, detail="O espaço pessoal não pode ser excluído.")
    db.delete(membro.espaco)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{espaco_id}/regenerar-codigo", response_model=CodigoRegenerado)
def regenerar(espaco_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    membro = verificar_administrador(usuario.id, espaco_id, db)
    codigo = regenerar_codigo(db, membro.espaco)
    return {"espaco_id": espaco_id, "codigo_acesso": codigo}


@router.get("/{espaco_id}/membros", response_model=list[MembroResposta])
def membros(espaco_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    vinculos = db.query(MembroEspaco).filter_by(espaco_id=espaco_id).all()
    return [{"usuario_id": v.usuario_id, "nome": v.usuario.nome, "email": v.usuario.email, "papel": v.papel, "entrou_em": v.entrou_em} for v in vinculos]


@router.delete("/{espaco_id}/membros/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_membro(espaco_id: int, usuario_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    administrador = verificar_administrador(usuario.id, espaco_id, db)
    alvo = db.query(MembroEspaco).filter_by(espaco_id=espaco_id, usuario_id=usuario_id).first()
    if not alvo:
        raise HTTPException(status_code=404, detail="Membro não encontrado.")
    if administrador.espaco.tipo == TipoEspaco.PESSOAL or alvo.papel == PapelMembro.DONO:
        raise HTTPException(status_code=400, detail="O dono do espaço pessoal não pode ser removido.")
    if alvo.usuario_id == usuario.id and alvo.papel == PapelMembro.ADMIN:
        raise HTTPException(status_code=400, detail="O administrador não pode remover a si mesmo.")
    db.delete(alvo)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
