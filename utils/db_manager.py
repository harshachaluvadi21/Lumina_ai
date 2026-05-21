import os
import sqlite3
import datetime
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import config

class DatabaseManager:
    def __init__(self):
        self.use_mongodb = False
        self.mongo_client = None
        self.mongo_db = None
        
        # Try to initialize MongoDB if URI is configured
        if config.is_mongodb_configured():
            try:
                # Set a short timeout so it doesn't hang if MongoDB is offline
                self.mongo_client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=3000)
                # Trigger a connection test
                self.mongo_client.admin.command('ping')
                self.mongo_db = self.mongo_client[config.MONGODB_DATABASE]
                self.use_mongodb = True
                print("Successfully connected to MongoDB Cluster.")
            except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
                print(f"MongoDB connection failed: {e}. Falling back to SQLite local storage.")
                self.use_mongodb = False
        else:
            print("MongoDB not configured in .env. Using SQLite local storage.")
            
        if not self.use_mongodb:
            self._init_sqlite()

    def _init_sqlite(self):
        """Initializes SQLite database tables if using local storage."""
        conn = sqlite3.connect(config.SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_path_or_link TEXT,
                word_count INTEGER DEFAULT 0,
                uploaded_at TEXT NOT NULL
            )
        """)
        
        # Create analytics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                document_id TEXT,
                action_type TEXT NOT NULL,
                duration_seconds INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()

    # --- User Methods ---
    
    def create_user(self, username, email, password_hash) -> str:
        """Creates a new user and returns their user ID."""
        now = datetime.datetime.utcnow().isoformat()
        
        if self.use_mongodb:
            user_doc = {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "created_at": datetime.datetime.utcnow()
            }
            res = self.mongo_db.users.insert_one(user_doc)
            return str(res.inserted_id)
        else:
            user_id = str(ObjectId())  # Use MongoDB style IDs for uniformity
            conn = sqlite3.connect(config.SQLITE_DB_PATH)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (id, username, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, email, password_hash, now)
                )
                conn.commit()
                return user_id
            except sqlite3.IntegrityError as e:
                conn.close()
                raise ValueError("Username or Email already exists.") from e
            finally:
                conn.close()

    def get_user_by_username(self, username) -> dict:
        """Retrieves a user by username."""
        if self.use_mongodb:
            user = self.mongo_db.users.find_one({"username": username})
            if user:
                user["_id"] = str(user["_id"])
            return user
        else:
            conn = sqlite3.connect(config.SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            conn.close()
            if row:
                user = dict(row)
                user["_id"] = user["id"] # Map SQLite primary key to uniform '_id' key
                return user
            return None

    def get_user_by_email(self, email) -> dict:
        """Retrieves a user by email."""
        if self.use_mongodb:
            user = self.mongo_db.users.find_one({"email": email})
            if user:
                user["_id"] = str(user["_id"])
            return user
        else:
            conn = sqlite3.connect(config.SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            conn.close()
            if row:
                user = dict(row)
                user["_id"] = user["id"]
                return user
            return None

    # --- Document Management Methods ---
    
    def add_document(self, user_id, title, source_type, source_path_or_link, word_count=0) -> str:
        """Logs metadata of a new uploaded document."""
        now = datetime.datetime.utcnow()
        
        if self.use_mongodb:
            doc = {
                "user_id": user_id,
                "title": title,
                "source_type": source_type,
                "source_path_or_link": source_path_or_link,
                "word_count": word_count,
                "uploaded_at": now
            }
            res = self.mongo_db.documents.insert_one(doc)
            return str(res.inserted_id)
        else:
            doc_id = str(ObjectId())
            conn = sqlite3.connect(config.SQLITE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO documents (id, user_id, title, source_type, source_path_or_link, word_count, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (doc_id, user_id, title, source_type, source_path_or_link, word_count, now.isoformat())
            )
            conn.commit()
            conn.close()
            return doc_id

    def get_user_documents(self, user_id) -> list:
        """Gets all documents uploaded by a specific user."""
        if self.use_mongodb:
            docs = list(self.mongo_db.documents.find({"user_id": user_id}).sort("uploaded_at", -1))
            for d in docs:
                d["_id"] = str(d["_id"])
            return docs
        else:
            conn = sqlite3.connect(config.SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC", (user_id,))
            rows = cursor.fetchall()
            conn.close()
            
            docs = []
            for r in rows:
                d = dict(r)
                d["_id"] = d["id"]
                docs.append(d)
            return docs

    def delete_document(self, user_id, document_id) -> bool:
        """Deletes a document logging and vector dependencies must be cleaned separately."""
        if self.use_mongodb:
            res = self.mongo_db.documents.delete_one({"_id": ObjectId(document_id), "user_id": user_id})
            return res.deleted_count > 0
        else:
            conn = sqlite3.connect(config.SQLITE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id))
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted

    # --- Study Analytics & Heatmap Methods ---
    
    def log_analytics(self, user_id, document_id, action_type, duration_seconds=0):
        """Logs a user learning activity."""
        now = datetime.datetime.utcnow()
        
        if self.use_mongodb:
            activity = {
                "user_id": user_id,
                "document_id": document_id,
                "action_type": action_type,
                "duration_seconds": duration_seconds,
                "timestamp": now
            }
            self.mongo_db.analytics.insert_one(activity)
        else:
            activity_id = str(ObjectId())
            conn = sqlite3.connect(config.SQLITE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO analytics (id, user_id, document_id, action_type, duration_seconds, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (activity_id, user_id, document_id, action_type, duration_seconds, now.isoformat())
            )
            conn.commit()
            conn.close()

    def get_user_analytics_summary(self, user_id) -> dict:
        """Returns statistics for building the modern AI Study Dashboard."""
        if self.use_mongodb:
            # Query counts
            total_documents = self.mongo_db.documents.count_documents({"user_id": user_id})
            activities = list(self.mongo_db.analytics.find({"user_id": user_id}))
        else:
            conn = sqlite3.connect(config.SQLITE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents WHERE user_id = ?", (user_id,))
            total_documents = cursor.fetchone()[0]
            
            cursor.execute("SELECT id, user_id, document_id, action_type, duration_seconds, timestamp FROM analytics WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            activities = [{"action_type": r[3], "duration_seconds": r[4], "timestamp": r[5]} for r in rows]
            conn.close()
            
        # Compute summaries
        total_actions = len(activities)
        total_study_seconds = sum(act.get("duration_seconds", 0) for act in activities)
        
        action_counts = {}
        for act in activities:
            atype = act.get("action_type", "view")
            action_counts[atype] = action_counts.get(atype, 0) + 1
            
        return {
            "total_documents": total_documents,
            "total_study_minutes": round(total_study_seconds / 60, 1),
            "total_interactions": total_actions,
            "actions_by_type": action_counts
        }

    def get_user_heatmap_data(self, user_id) -> dict:
        """Returns a dict of { 'YYYY-MM-DD': interaction_count } for rendering the study heatmap grid."""
        heatmap_data = {}
        
        if self.use_mongodb:
            activities = list(self.mongo_db.analytics.find({"user_id": user_id}))
            for act in activities:
                dt = act.get("timestamp")
                if isinstance(dt, datetime.datetime):
                    date_str = dt.strftime("%Y-%m-%d")
                else:
                    date_str = str(dt)[:10]
                heatmap_data[date_str] = heatmap_data.get(date_str, 0) + 1
        else:
            conn = sqlite3.connect(config.SQLITE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp FROM analytics WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            conn.close()
            
            for r in rows:
                date_str = r[0][:10]  # First 10 chars represent YYYY-MM-DD
                heatmap_data[date_str] = heatmap_data.get(date_str, 0) + 1
                
        return heatmap_data

# Global instance
db = DatabaseManager()
