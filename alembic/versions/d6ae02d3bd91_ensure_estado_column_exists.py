"""ensure_estado_column_exists

Revision ID: d6ae02d3bd91
Revises: b5c6d7e8f9g0
Create Date: 2026-09-16 12:11:46.464665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd6ae02d3bd91'
down_revision: Union[str, None] = 'b5c6d7e8f9g0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Verificar si la columna estado ya existe, si no, agregarla
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('usuarios')]
    
    if 'estado' not in columns:
        # El ENUM ya existe (creado previamente), solo agregamos la columna
        op.add_column('usuarios', 
            sa.Column('estado', 
                      sa.Enum('ACTIVO', 'INACTIVO', 'BLOQUEADO', name='estadousuario'),
                      nullable=False,
                      server_default='ACTIVO')
        )
        print("✓ Columna 'estado' agregada a tabla 'usuarios'")
    else:
        print("✓ Columna 'estado' ya existe en tabla 'usuarios'")


def downgrade() -> None:
    # Verificar si la columna existe antes de eliminarla
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('usuarios')]
    
    if 'estado' in columns:
        op.drop_column('usuarios', 'estado')
        print("✓ Columna 'estado' eliminada de tabla 'usuarios'")