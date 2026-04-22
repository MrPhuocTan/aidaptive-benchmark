from src.config import load_config
from src.database.engine import Database
config = load_config()
db = Database(config.postgres)
db.create_tables()
print("Tables created.")
