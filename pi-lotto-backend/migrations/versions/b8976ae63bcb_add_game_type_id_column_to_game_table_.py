"""Add game_type_id column to game table fix

Revision ID: b8976ae63bcb
Revises: 93aa37f1a93d
Create Date: 2024-05-06 21:40:25.758124

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8976ae63bcb'
down_revision = '93aa37f1a93d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('game', schema=None) as batch_op:
        batch_op.add_column(sa.Column('game_type_id', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('name', sa.String(length=100), nullable=False))
        batch_op.add_column(sa.Column('entry_fee', sa.Float(), nullable=False))
        batch_op.add_column(sa.Column('winner_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('max_players', sa.Integer(), nullable=False))
        batch_op.create_foreign_key('uq_game_user', 'user', ['winner_id'], ['id'])
        batch_op.create_foreign_key('uq_game_game_type', 'game_type', ['game_type_id'], ['id'])
        batch_op.drop_column('num_players')
        batch_op.drop_column('game_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('game', schema=None) as batch_op:
        batch_op.add_column(sa.Column('game_id', sa.VARCHAR(length=100), nullable=False))
        batch_op.add_column(sa.Column('num_players', sa.INTEGER(), nullable=False))
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('max_players')
        batch_op.drop_column('winner_id')
        batch_op.drop_column('entry_fee')
        batch_op.drop_column('name')
        batch_op.drop_column('game_type_id')

    # ### end Alembic commands ###
