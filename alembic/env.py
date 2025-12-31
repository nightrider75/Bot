import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env", override=False)

src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from bot.config import settings

# Import all models to ensure they are registered with the Base metadata
from bot.models.asset import PlatformAsset  # noqa: F401
from bot.models.assistant_mappings import AssistantMapping  # noqa: F401
from bot.models.bot_models import (  # noqa: F401
    Bot,
    BotUserData,
    Config,
    FunctionMapping,
    Node,
)
from bot.models.chat import Base
from bot.models.conversation_details import (
    ConversationDetails,  # noqa: F401
)


def _get_database_url() -> str:
    """Prefer explicit Alembic/SQLAlchemy vars before falling back to store settings."""
    return (
        os.environ.get("ALEMBIC_DATABASE_URL")
        or os.environ.get("SQLALCHEMY_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or settings.sync_database_url
    )


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override the static URL defined in alembic.ini so runtime config is used.
config.set_main_option("sqlalchemy.url", _get_database_url())

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    pass
    # fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
