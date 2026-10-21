import unicodedata
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.auth_dependencies import obter_usuario_atual
from app.database.dependencies import get_db
from app.models.categoria import Categoria
from app.models.usuario_model import Usuario
from app.services.espaco_service import verificar_acesso_espaco

router = APIRouter(prefix="/espacos/{espaco_id}/categorias", tags=["Categorias"])

def normalizar(nome: str) -> str:
    return unicodedata.normalize("NFC", " ".join(nome.split())).casefold()

class CategoriaEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=80)

class CategoriaSaida(BaseModel):
    id: int
    nome: str
    model_config = {"from_attributes": True}

@router.get("/", response_model=list[CategoriaSaida])
def listar(espaco_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return sorted(db.query(Categoria).filter_by(espaco_id=espaco_id).all(), key=lambda c: c.nome.casefold())

@router.post("/", response_model=CategoriaSaida, status_code=status.HTTP_201_CREATED)
def criar(espaco_id: int, dados: CategoriaEntrada, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    nome = " ".join(dados.nome.split())
    if not nome or len(nome) > 80:
        raise HTTPException(status_code=422, detail="Informe um nome de categoria válido.")
    categoria = Categoria(espaco_id=espaco_id, nome=nome, nome_normalizado=normalizar(nome))
    db.add(categoria)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Esta categoria já existe.")
    db.refresh(categoria)
    return categoria

@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(espaco_id: int, categoria_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    categoria = db.query(Categoria).filter_by(id=categoria_id, espaco_id=espaco_id).first()
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    db.delete(categoria)
    db.commit()
    # Movimentações mantêm sua categoria textual e não são excluídas.
