from src.routers.prompts import list_prompt_sets
from src.config import load_config
from src.database.engine import Database
from src.database.repository import Repository

db = Database(load_config().postgres)
session = db.get_sync_session()
repo = Repository(session)

try:
    print(list_prompt_sets(repo))
except Exception as e:
    import traceback
    traceback.print_exc()
