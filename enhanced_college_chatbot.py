import sqlite3
import json
import hashlib
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import bcrypt

class EnhancedDatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with user management tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Create chat_sessions table (renamed from sessions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Update messages table to include user_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                user_id TEXT,
                message_type TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Update user preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                preferences TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Create user_sessions table for login session management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_user(self, username: str, email: str, password: str) -> Dict:
        """Create a new user account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute(
                'SELECT user_id FROM users WHERE username = ? OR email = ?',
                (username, email)
            )
            if cursor.fetchone():
                return {'success': False, 'error': 'Username or email already exists'}
            
            # Create new user
            user_id = str(uuid.uuid4())
            password_hash = self.hash_password(password)
            
            cursor.execute(
                'INSERT INTO users (user_id, username, email, password_hash) VALUES (?, ?, ?, ?)',
                (user_id, username, email, password_hash)
            )
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'user_id': user_id,
                'username': username,
                'email': email
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def authenticate_user(self, username: str, password: str) -> Dict:
        """Authenticate user login"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT user_id, username, email, password_hash FROM users WHERE username = ? AND is_active = TRUE',
                (username,)
            )
            user = cursor.fetchone()
            
            if not user or not self.verify_password(password, user[3]):
                return {'success': False, 'error': 'Invalid username or password'}
            
            # Create session token
            session_token = str(uuid.uuid4())
            expires_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # You might want to add actual expiration logic
            
            cursor.execute(
                'INSERT INTO user_sessions (session_token, user_id, expires_at) VALUES (?, ?, datetime("now", "+7 days"))',
                (session_token, user[0])
            )
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'user_id': user[0],
                'username': user[1],
                'email': user[2],
                'session_token': session_token
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify_session_token(self, session_token: str) -> Dict:
        """Verify if session token is valid"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT us.user_id, u.username, u.email 
                FROM user_sessions us 
                JOIN users u ON us.user_id = u.user_id 
                WHERE us.session_token = ? AND us.is_active = TRUE 
                AND us.expires_at > datetime('now')
            ''', (session_token,))
            
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return {
                    'success': True,
                    'user_id': user[0],
                    'username': user[1],
                    'email': user[2]
                }
            else:
                return {'success': False, 'error': 'Invalid or expired session'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def logout_user(self, session_token: str) -> bool:
        """Logout user by deactivating session token"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE user_sessions SET is_active = FALSE WHERE session_token = ?',
                (session_token,)
            )
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def create_chat_session(self, user_id: str, title: str = 'New Chat') -> str:
        """Create a new chat session for a user"""
        session_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO chat_sessions (session_id, user_id, title) VALUES (?, ?, ?)',
            (session_id, user_id, title)
        )
        conn.commit()
        conn.close()
        return session_id
    
    def get_user_chat_sessions(self, user_id: str) -> List[Dict]:
        """Get all chat sessions for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_id, title, created_at, updated_at,
                   (SELECT COUNT(*) FROM messages WHERE session_id = cs.session_id) as message_count
            FROM chat_sessions cs 
            WHERE user_id = ? AND is_active = TRUE 
            ORDER BY updated_at DESC
        ''', (user_id,))
        
        sessions = cursor.fetchall()
        conn.close()
        
        return [
            {
                'session_id': session[0],
                'title': session[1],
                'created_at': session[2],
                'updated_at': session[3],
                'message_count': session[4]
            }
            for session in sessions
        ]
    
    def update_chat_title(self, session_id: str, title: str):
        """Update chat session title"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?',
            (title, session_id)
        )
        conn.commit()
        conn.close()
    
    def delete_chat_session(self, session_id: str, user_id: str) -> bool:
        """Delete (deactivate) a chat session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE chat_sessions SET is_active = FALSE WHERE session_id = ? AND user_id = ?',
                (session_id, user_id)
            )
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def save_message(self, session_id: str, user_id: str, message_type: str, content: str):
        """Save a message to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO messages (session_id, user_id, message_type, content) VALUES (?, ?, ?, ?)',
            (session_id, user_id, message_type, content)
        )
        cursor.execute(
            'UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?',
            (session_id,)
        )
        conn.commit()
        conn.close()
    
    def get_session_messages(self, session_id: str, user_id: str) -> List[Dict]:
        """Retrieve all messages for a session (with user verification)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.message_type, m.content, m.timestamp 
            FROM messages m
            JOIN chat_sessions cs ON m.session_id = cs.session_id
            WHERE m.session_id = ? AND cs.user_id = ? 
            ORDER BY m.timestamp
        ''', (session_id, user_id))
        messages = cursor.fetchall()
        conn.close()
        
        return [
            {
                'type': msg[0],
                'content': msg[1],
                'timestamp': msg[2]
            }
            for msg in messages
        ]
    
    def save_preferences(self, session_id: str, user_id: str, preferences: dict):
        """Save user preferences for a specific session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO user_preferences (session_id, user_id, preferences) VALUES (?, ?, ?)',
            (session_id, user_id, json.dumps(preferences))
        )
        conn.commit()
        conn.close()
    
    def get_preferences(self, session_id: str, user_id: str) -> dict:
        """Get user preferences for a specific session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT preferences FROM user_preferences WHERE session_id = ? AND user_id = ?',
            (session_id, user_id)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return {}
    
    def verify_session_ownership(self, session_id: str, user_id: str) -> bool:
        """Verify if a session belongs to a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT session_id FROM chat_sessions WHERE session_id = ? AND user_id = ? AND is_active = TRUE',
            (session_id, user_id)
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None