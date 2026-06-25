from fastapi import APIRouter, Depends, HTTPException
from app.schemas.gastos_schemas import CriarGastos, AtualizarGastos
from app.services.gastos_service import criar_gasto
from app.database.dependencies import get_db
from app.schemas.gastos_schemas import CriarGastos
from sqlalchemy.orm import Session
from app.models.gastos import Gasto

router = APIRouter(prefix='/gastos', tags=['Gastos'])

@router.post('/',
    summary='Cadastra um novo gasto',
    description='Rota para cadastrar um novo gasto ao banco de dados'
)
def criar(
    dado: CriarGastos,
    db: Session = Depends(get_db)
):
    return criar_gasto(db, dado)

@router.get('/',
    summary='Vizualizar os gastos',
    description='Retorna todos os gatos cadastrados no banco de dados'
)
def view_gastos(
    db: Session = Depends(get_db)
):
    return db.query(Gasto).all()

@router.put('/{id}',
    summary='Atualizar gastos',
    description='Rota para atualizar um gasto cadastrado no banco de dados.'
)
def update_gastos(id: int, dado: AtualizarGastos, db: Session = Depends(get_db)):

    gasto = db.query(Gasto).filter(Gasto.id == id).first()

    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto não encontrado")

    gasto.categoria = dado.categoria
    gasto.descricao = dado.descricao
    gasto.valor = dado.valor

    db.commit()
    db.refresh(gasto)

    return {"message": "Gasto atualizado com sucesso", "gasto": gasto}

@router.delete('/{id}',
    summary='Deleta um gasto',
    description='Rota para deletar um gasto cadastrado no banco de dados.'
)
def delete_gasto(id: int, db: Session = Depends(get_db)):

    gasto = db.query(Gasto).filter(Gasto.id == id).first()

    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto não encontrado")

    db.delete(gasto)
    db.commit()

    return {"message": "Gasto deletado com sucesso"}