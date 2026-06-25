from sqlalchemy.orm import Session
from app.models.gastos import Gasto

def criar_gasto(db: Session, dado):
    gasto = Gasto(
        categoria=dado.categoria.value,
        descricao=dado.descricao,
        valor=dado.valor
    )

    db.add(gasto)
    db.commit()
    db.refresh(gasto)

    return gasto