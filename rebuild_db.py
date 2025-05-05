from app import create_app
from models import db
import os
import sqlite3
from datetime import datetime

def backup_database():
    """Create a backup of the current database"""
    source_path = 'instance/finance.db'
    backup_path = f'instance/finance_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    
    try:
        # Check if the source database exists
        if os.path.exists(source_path):
            # Create connection to the source database
            conn = sqlite3.connect(source_path)
            
            # Create a backup
            with sqlite3.connect(backup_path) as backup:
                conn.backup(backup)
            
            conn.close()
            print(f"Backup created at {backup_path}")
            return True
        else:
            print(f"Source database {source_path} does not exist. No backup needed.")
            return False
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False

def rebuild_database():
    """Rebuild the database with the current schema (without Family table)"""
    try:
        # Create application context
        app = create_app()
        
        with app.app_context():
            # Remove the existing database file if it exists
            if os.path.exists('instance/finance.db'):
                try:
                    os.remove('instance/finance.db')
                    print("Removed old database file")
                except Exception as e:
                    print(f"Could not remove old database file: {e}")
                    return False
            
            # Create all tables based on current models
            db.create_all()
            print("Database rebuilt successfully with new schema")
            return True
    except Exception as e:
        print(f"Error rebuilding database: {e}")
        return False

if __name__ == "__main__":
    print("Starting database rebuild process...")
    
    # Backup the current database
    backup_success = backup_database()
    if backup_success:
        print("Database backup successful")
    
    # Rebuild the database
    rebuild_success = rebuild_database()
    if rebuild_success:
        print("Database rebuild successful")
    
    print("Database rebuild process completed")