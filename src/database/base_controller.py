from pathlib import Path
import aiosqlite
import logging

logger = logging.getLogger(__name__)

class BaseController:
    def __init__(self, db_path: str = "data/app.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
    async def execute(self, query: str, params: tuple = None) -> bool:
        """执行SQL语句"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(query, params or ())
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Database error: {e}")
            return False
            
    async def fetch_one(self, query: str, params: tuple = None) -> dict:
        """获取单条记录"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params or ()) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Database error: {e}")
            return None
            
    async def fetch_all(self, query: str, params: tuple = None) -> list:
        """获取多条记录"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params or ()) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Database error: {e}")
            return [] 