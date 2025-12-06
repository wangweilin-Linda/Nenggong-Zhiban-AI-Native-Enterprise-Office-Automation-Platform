"""create workflow tables

Revision ID: 003
Revises: 002
Create Date: 2024-03-21 10:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # 创建工作流设计表
    op.create_table(
        'workflow_designs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('workflow_config', postgresql.JSONB(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建工作流设计版本表
    op.create_table(
        'workflow_design_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_design_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('workflow_config', postgresql.JSONB(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workflow_design_id'], ['workflow_designs.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workflow_design_id', 'version', name='uix_workflow_design_version')
    )

    # 创建工作流实例表
    op.create_table(
        'workflow_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_design_id', sa.Integer(), nullable=False),
        sa.Column('workflow_design_version', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('current_node', sa.String(length=100), nullable=True),
        sa.Column('form_data', postgresql.JSONB(), nullable=True),
        sa.Column('initiator_id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=True),
        sa.Column('business_type', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workflow_design_id'], ['workflow_designs.id'], ),
        sa.ForeignKeyConstraint(['initiator_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建审批记录表
    op.create_table(
        'approval_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_instance_id', sa.Integer(), nullable=False),
        sa.Column('node_name', sa.String(length=100), nullable=False),
        sa.Column('operator_id', sa.Integer(), nullable=False),
        sa.Column('operation', sa.String(length=50), nullable=False),
        sa.Column('comment', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workflow_instance_id'], ['workflow_instances.id'], ),
        sa.ForeignKeyConstraint(['operator_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('approval_records')
    op.drop_table('workflow_instances')
    op.drop_table('workflow_design_versions')
    op.drop_table('workflow_designs') 