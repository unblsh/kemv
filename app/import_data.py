import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from app import create_app, db
from app.models import Customer, Product, Category, Invoice, InvoiceLine, Stock, Country
import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

def import_data():
    app = create_app()
    with app.app_context():
        try:
            # Connect to source database
            source_engine = create_engine('mysql+mysqlconnector://root:5h5hjfkC@localhost:3306/online_retail_db')
            
            # Read data from source table
            with source_engine.connect() as conn:
                # Get unique countries
                countries_df = pd.read_sql("""
                    SELECT DISTINCT Country
                    FROM online_retail_combined_larger
                    WHERE Country IS NOT NULL
                """, conn)
                
                # Get unique customers with their countries
                customers_df = pd.read_sql("""
                    SELECT DISTINCT CustomerID, Country
                    FROM online_retail_combined_larger
                    WHERE CustomerID IS NOT NULL AND Country IS NOT NULL
                """, conn)
                
                # Get unique products and categories
                products_df = pd.read_sql("""
                    SELECT DISTINCT ProductID, StockCode, Description, Category
                    FROM online_retail_combined_larger
                    WHERE ProductID IS NOT NULL
                """, conn)
                
                # Get invoice data
                invoices_df = pd.read_sql("""
                    SELECT DISTINCT InvoiceNo, InvoiceDate, CustomerID
                    FROM online_retail_combined_larger
                    WHERE InvoiceNo IS NOT NULL AND InvoiceDate IS NOT NULL
                """, conn)
                
                # Get invoice lines
                invoice_lines_df = pd.read_sql("""
                    SELECT InvoiceNo, ProductID, Quantity, UnitPrice, Quantity * UnitPrice as LineTotal
                    FROM online_retail_combined_larger
                    WHERE InvoiceNo IS NOT NULL AND ProductID IS NOT NULL
                """, conn)
            
            # Import countries
            country_map = {}
            for _, row in countries_df.iterrows():
                country = Country(country_name=row['Country'])
                db.session.merge(country)
                db.session.flush()  # Get the country_id
                country_map[row['Country']] = country.country_id
            db.session.commit()
            logger.info(f"Imported {len(countries_df)} countries")
            
            # Import customers
            for _, row in customers_df.iterrows():
                customer = Customer(
                    customer_id=int(row['CustomerID']),
                    country_id=country_map[row['Country']]
                )
                db.session.merge(customer)
            db.session.commit()
            logger.info(f"Imported {len(customers_df)} customers")
            
            # Import categories
            categories = {}
            for _, row in products_df.iterrows():
                if pd.notna(row['Category']):
                    category = Category(
                        category_name=row['Category'],
                        stock_code=row['StockCode']
                    )
                    db.session.merge(category)
                    db.session.flush()  # Get the category_id
                    categories[row['StockCode']] = category.category_id
            db.session.commit()
            logger.info(f"Imported {len(categories)} categories")
            
            # Import products
            for _, row in products_df.iterrows():
                product = Product(
                    product_id=int(row['ProductID']),
                    stock_code=row['StockCode'],
                    description=row['Description']
                )
                db.session.merge(product)
            db.session.commit()
            logger.info(f"Imported {len(products_df)} products")
            
            # Import invoices
            for _, row in invoices_df.iterrows():
                invoice = Invoice(
                    invoice_no=row['InvoiceNo'],
                    invoice_date=row['InvoiceDate'],
                    customer_id=int(row['CustomerID']) if pd.notna(row['CustomerID']) else None
                )
                db.session.merge(invoice)
            db.session.commit()
            logger.info(f"Imported {len(invoices_df)} invoices")
            
            # Import invoice lines
            for _, row in invoice_lines_df.iterrows():
                invoice_line = InvoiceLine(
                    invoice_no=row['InvoiceNo'],
                    product_id=int(row['ProductID']),
                    quantity=int(row['Quantity']),
                    unit_price=float(row['UnitPrice'])
                )
                db.session.merge(invoice_line)
            db.session.commit()
            logger.info(f"Imported {len(invoice_lines_df)} invoice lines")
            
            # Initialize stock levels
            stock_levels = (
                db.session.query(
                    InvoiceLine.product_id,
                    func.sum(InvoiceLine.quantity).label('total_sold')
                )
                .group_by(InvoiceLine.product_id)
                .all()
            )
            
            for product_id, total_sold in stock_levels:
                stock = Stock(
                    product_id=product_id,
                    quantity_in_stock=int(total_sold * 1.5)  # Initial stock is 1.5x max daily sales
                )
                db.session.merge(stock)
            db.session.commit()
            logger.info(f"Initialized stock levels for {len(stock_levels)} products")
            
            logger.info("Data import completed successfully")
            
        except Exception as e:
            logger.error(f"Error during data import: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    import_data() 