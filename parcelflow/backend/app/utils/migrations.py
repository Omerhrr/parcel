"""
Database Migration Utilities
ParcelFlow - Multi-tenant Logistics Platform

Handles schema migrations for SQLite databases.
"""
from sqlalchemy import text, inspect
from app.database import engine
import logging

logger = logging.getLogger(__name__)


def get_table_columns(table_name: str) -> list:
    """Get list of column names for a table"""
    inspector = inspect(engine)
    try:
        columns = inspector.get_columns(table_name)
        return [col['name'] for col in columns]
    except Exception:
        return []


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    if not table_exists(table_name):
        return False
    columns = get_table_columns(table_name)
    return column_name in columns


def add_column_if_not_exists(table_name: str, column_name: str, column_type: str, default_value=None):
    """Add a column to a table if it doesn't exist"""
    if not table_exists(table_name):
        logger.info(f"Table {table_name} does not exist, skipping column {column_name}")
        return False

    if column_exists(table_name, column_name):
        logger.info(f"Column {column_name} already exists in {table_name}")
        return False

    try:
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        if default_value is not None:
            sql += f" DEFAULT {default_value}"

        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()

        logger.info(f"Added column {column_name} to {table_name}")
        return True
    except Exception as e:
        logger.error(f"Error adding column {column_name} to {table_name}: {e}")
        return False


def create_table_if_not_exists(table_name: str, create_sql: str):
    """Create a table if it doesn't exist"""
    if table_exists(table_name):
        logger.info(f"Table {table_name} already exists")
        return False

    try:
        with engine.connect() as conn:
            conn.execute(text(create_sql))
            conn.commit()
        logger.info(f"Created table {table_name}")
        return True
    except Exception as e:
        logger.error(f"Error creating table {table_name}: {e}")
        return False


def run_migrations():
    """Run all pending migrations"""
    logger.info("Running database migrations...")

    migrations_run = 0

    # Migration 1: Add GPS coordinates to waybills table
    if add_column_if_not_exists('waybills', 'pickup_latitude', 'VARCHAR(20)'):
        migrations_run += 1

    if add_column_if_not_exists('waybills', 'pickup_longitude', 'VARCHAR(20)'):
        migrations_run += 1

    if add_column_if_not_exists('waybills', 'delivery_latitude', 'VARCHAR(20)'):
        migrations_run += 1

    if add_column_if_not_exists('waybills', 'delivery_longitude', 'VARCHAR(20)'):
        migrations_run += 1

    # Migration 2: Add extra_data column to audit_logs (renamed from metadata)
    if add_column_if_not_exists('audit_logs', 'extra_data', 'TEXT'):
        migrations_run += 1

    # Migration 3: Add notes column to branches if missing
    if add_column_if_not_exists('branches', 'notes', 'TEXT'):
        migrations_run += 1

    # Migration 4: Add missing columns to dispatches table
    if add_column_if_not_exists('dispatches', 'completed_at', 'VARCHAR(50)'):
        migrations_run += 1

    if add_column_if_not_exists('dispatches', 'dispatched_at', 'VARCHAR(50)'):
        migrations_run += 1

    if add_column_if_not_exists('dispatches', 'estimated_delivery', 'VARCHAR(50)'):
        migrations_run += 1

    if add_column_if_not_exists('dispatches', 'attempt_count', 'INTEGER DEFAULT 0'):
        migrations_run += 1

    if add_column_if_not_exists('dispatches', 'last_attempt_at', 'VARCHAR(50)'):
        migrations_run += 1

    if add_column_if_not_exists('dispatches', 'route_notes', 'TEXT'):
        migrations_run += 1

    if add_column_if_not_exists('dispatches', 'distance_km', 'NUMERIC(10, 2)'):
        migrations_run += 1

    if add_column_if_not_exists('dispatches', 'failure_reason', 'TEXT'):
        migrations_run += 1

    # Migration 5: Add missing columns to delivery_confirmations table
    if add_column_if_not_exists('delivery_confirmations', 'receiver_signature_svg', 'TEXT'):
        migrations_run += 1

    if add_column_if_not_exists('delivery_confirmations', 'receiver_signature', 'TEXT'):
        migrations_run += 1

    if add_column_if_not_exists('delivery_confirmations', 'proof_photo_url', 'VARCHAR(500)'):
        migrations_run += 1

    if add_column_if_not_exists('delivery_confirmations', 'delivery_latitude', 'VARCHAR(20)'):
        migrations_run += 1

    if add_column_if_not_exists('delivery_confirmations', 'delivery_longitude', 'VARCHAR(20)'):
        migrations_run += 1

    if add_column_if_not_exists('delivery_confirmations', 'cod_collected', 'INTEGER DEFAULT 0'):
        migrations_run += 1

    if add_column_if_not_exists('delivery_confirmations', 'cod_amount', 'NUMERIC(12, 2) DEFAULT 0'):
        migrations_run += 1

    if add_column_if_not_exists('delivery_confirmations', 'payment_method', 'VARCHAR(50)'):
        migrations_run += 1

    if add_column_if_not_exists('delivery_confirmations', 'receiver_id_type', 'VARCHAR(50)'):
        migrations_run += 1

    if add_column_if_not_exists('delivery_confirmations', 'receiver_id_number', 'VARCHAR(100)'):
        migrations_run += 1

    # Migration 6: Create deliveries table if it doesn't exist
    deliveries_table_sql = """
    CREATE TABLE deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,
        branch_id INTEGER,
        waybill_id INTEGER,
        agent_id INTEGER,
        delivered_at VARCHAR(50),
        status VARCHAR(20) DEFAULT 'delivered',
        cod_collected INTEGER DEFAULT 0,
        cod_amount NUMERIC(12, 2) DEFAULT 0,
        receiver_name VARCHAR(255),
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
        FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL,
        FOREIGN KEY (waybill_id) REFERENCES waybills(id) ON DELETE CASCADE,
        FOREIGN KEY (agent_id) REFERENCES logistic_agents(id) ON DELETE SET NULL
    )
    """
    if create_table_if_not_exists('deliveries', deliveries_table_sql):
        migrations_run += 1

    # Migration 6: Create agent_remittances table if it doesn't exist
    agent_remittances_table_sql = """
    CREATE TABLE agent_remittances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,
        agent_id INTEGER,
        amount NUMERIC(12, 2) NOT NULL,
        period_start VARCHAR(50),
        period_end VARCHAR(50),
        collected_at VARCHAR(50),
        remitted_at VARCHAR(50),
        status VARCHAR(20) DEFAULT 'pending',
        payment_method VARCHAR(50),
        payment_reference VARCHAR(255),
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
        FOREIGN KEY (agent_id) REFERENCES logistic_agents(id) ON DELETE SET NULL
    )
    """
    if create_table_if_not_exists('agent_remittances', agent_remittances_table_sql):
        migrations_run += 1

    # Migration 7: Create indexes for faster queries
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_deliveries_business_id ON deliveries(business_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_deliveries_agent_id ON deliveries(agent_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_deliveries_waybill_id ON deliveries(waybill_id)"))
            conn.commit()
        logger.info("Created indexes on deliveries table")
    except Exception as e:
        logger.debug(f"Index creation skipped (may already exist): {e}")

    # Migration 8: Add pricing_type to products table
    if add_column_if_not_exists('products', 'pricing_type', "VARCHAR(20) DEFAULT 'fixed'"):
        migrations_run += 1

    # Migration 9: Create product_prices table for pricing matrix
    product_prices_table_sql = """
    CREATE TABLE product_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        min_quantity INTEGER DEFAULT 1 NOT NULL,
        max_quantity INTEGER,
        price NUMERIC(12, 2) DEFAULT 0,
        total_price NUMERIC(12, 2),
        is_buy_x_get_y INTEGER DEFAULT 0,
        buy_quantity INTEGER,
        get_quantity INTEGER,
        label VARCHAR(255),
        priority INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    )
    """
    if create_table_if_not_exists('product_prices', product_prices_table_sql):
        migrations_run += 1

    # Create index on product_prices
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_product_prices_product_id ON product_prices(product_id)"))
            conn.commit()
    except Exception as e:
        logger.debug(f"Index creation skipped: {e}")

    # Migration 10: Add remittance fields to orders table
    if add_column_if_not_exists('orders', 'vendor_id', 'INTEGER'):
        migrations_run += 1

    if add_column_if_not_exists('orders', 'remittance_fee', 'NUMERIC(12, 2) DEFAULT 0'):
        migrations_run += 1

    if add_column_if_not_exists('orders', 'vendor_amount', 'NUMERIC(12, 2) DEFAULT 0'):
        migrations_run += 1

    if add_column_if_not_exists('orders', 'remittance_status', "VARCHAR(20) DEFAULT 'pending'"):
        migrations_run += 1

    if add_column_if_not_exists('orders', 'remitted_at', 'VARCHAR(50)'):
        migrations_run += 1

    if add_column_if_not_exists('orders', 'remittance_id', 'INTEGER'):
        migrations_run += 1

    # Migration 11: Add vendor_id to inventory table
    if add_column_if_not_exists('inventory', 'vendor_id', 'INTEGER'):
        migrations_run += 1

    # Create indexes for orders and inventory vendor_id
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_orders_vendor_id ON orders(vendor_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inventory_vendor_id ON inventory(vendor_id)"))
            conn.commit()
    except Exception as e:
        logger.debug(f"Index creation skipped: {e}")

    # Migration 12: Add remittance_fee to vendors table
    if add_column_if_not_exists('vendors', 'remittance_fee', 'NUMERIC(12, 2) DEFAULT 0'):
        migrations_run += 1

    logger.info(f"Completed {migrations_run} migrations")
    return migrations_run


def check_database_schema():
    """Check and report on database schema"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    logger.info("Database schema check:")
    for table in tables:
        columns = inspector.get_columns(table)
        logger.info(f"  Table '{table}': {[col['name'] for col in columns]}")

    return tables
