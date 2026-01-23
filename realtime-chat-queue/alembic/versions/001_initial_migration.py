"""Initial migration - create messages and deliveries tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('message_id', sa.String(100), nullable=False, unique=True),
        sa.Column('chat_id', sa.String(100), nullable=False),
        sa.Column('sender_id', sa.String(100), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_messages_message_id', 'messages', ['message_id'])
    op.create_index('ix_messages_chat_id', 'messages', ['chat_id'])
    op.create_index('ix_messages_sender_id', 'messages', ['sender_id'])
    op.create_index('ix_messages_status', 'messages', ['status'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])
    
    op.create_table(
        'message_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('message_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['message_id'], ['messages.message_id'], ),
    )
    op.create_index('ix_message_deliveries_message_id', 'message_deliveries', ['message_id'])
    op.create_index('ix_message_deliveries_user_id', 'message_deliveries', ['user_id'])
    op.create_index('idx_message_user', 'message_deliveries', ['message_id', 'user_id'], unique=True)
    op.create_index('idx_user_status', 'message_deliveries', ['user_id', 'status'])


def downgrade() -> None:
    op.drop_index('idx_user_status', table_name='message_deliveries')
    op.drop_index('idx_message_user', table_name='message_deliveries')
    op.drop_index('ix_message_deliveries_user_id', table_name='message_deliveries')
    op.drop_index('ix_message_deliveries_message_id', table_name='message_deliveries')
    op.drop_table('message_deliveries')
    
    op.drop_index('ix_messages_created_at', table_name='messages')
    op.drop_index('ix_messages_status', table_name='messages')
    op.drop_index('ix_messages_sender_id', table_name='messages')
    op.drop_index('ix_messages_chat_id', table_name='messages')
    op.drop_index('ix_messages_message_id', table_name='messages')
    op.drop_table('messages')
