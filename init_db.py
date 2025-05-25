import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text, MetaData

def init_db():
    app = create_app()
    with app.app_context():
        # Get the database engine
        engine = db.engine
        
        # Get all table names
        metadata = MetaData()
        metadata.reflect(bind=engine)
        table_names = metadata.tables.keys()
        
        # Temporarily disable foreign key checks and drop tables
        with engine.connect() as conn:
            # Disable foreign key checks
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            conn.commit()
            
            # Drop tables in reverse order of dependencies
            for table_name in reversed(list(table_names)):
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
                    print(f"Dropped table: {table_name}")
                except Exception as e:
                    print(f"Error dropping table {table_name}: {str(e)}")
            conn.commit()
            
            # Re-enable foreign key checks
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
            conn.commit()
        
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    init_db() 