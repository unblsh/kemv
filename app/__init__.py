from flask import Flask
from config import Config
import logging
from sqlalchemy import text
from app.extensions import db

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    # Test database connection
    with app.app_context():
        try:
            # Try to execute a simple query
            db.session.execute(text('SELECT 1'))
            logger.info('Database connection successful!')
            
            # Log database tables
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f'Available tables: {tables}')
            
            # Import models here to avoid circular imports
            from app.models import Customer, Product, Category, Invoice, InvoiceLine, Stock
            
            # Test a basic query on each model
            for model in [Customer, Product, Category, Invoice, InvoiceLine, Stock]:
                count = db.session.query(model).count()
                logger.info(f'Table {model.__tablename__}: {count} records')
                
        except Exception as e:
            logger.error(f'Database connection failed: {str(e)}')
            raise
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    return app 