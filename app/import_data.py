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
            
            # Read all data from the source table
            with source_engine.connect() as conn:
                source_data_df = pd.read_sql("""
                    SELECT *
                    FROM online_retail_source
                """, conn)

            logger.info(f"Read {len(source_data_df)} rows from online_retail_source")

            # Debug: Print columns and exit to diagnose column name issue
            # print("Debug - Columns in source_data_df: {}".format(source_data_df.columns.tolist()))
            # import sys
            # sys.exit(0)

            if source_data_df.empty:
                logger.warning("Source data table is empty. Skipping import.")
                return # Exit if no data to import

            # Find the actual column names in a case-insensitive way, stripping whitespace
            column_mapping = {}
            # Removed 'CategoryName' as it is not present in the DataFrame read by pandas
            required_columns = [
                'Country', 'CustomerID', 'StockCode', 'Description',
                'InvoiceNo', 'InvoiceDate', 'Quantity', 'UnitPrice'
            ]
            source_columns = source_data_df.columns.tolist()

            for req_col in required_columns:
                found_col = None
                for src_col in source_columns:
                    # Flexible matching for column names, handle specific known differences
                    if req_col.lower() == 'invoiceno'.lower() and src_col.strip().lower() == 'invoice'.lower():
                         found_col = src_col
                         break # Found specific mapping for Invoice
                    elif req_col.lower() == 'unitprice'.lower() and src_col.strip().lower() == 'price'.lower():
                         found_col = src_col
                         break # Found specific mapping for UnitPrice
                    # General flexible match for other columns if not already found by specific mapping
                    elif src_col.strip().lower() == req_col.lower():
                        found_col = src_col
                        break # Found general match

                if found_col:
                    # Map the required logical name to the actual column name found in the DataFrame
                    column_mapping[req_col] = found_col
                else:
                    # If a required column is still not found, raise error
                    raise KeyError(f"Required column '{req_col}' not found in source data.")

            logger.info(f"Column mapping: {column_mapping}")

            # Clear existing data in application tables (excluding Category for now, as we'll merge)
            db.session.execute(text('SET FOREIGN_KEY_CHECKS=0'))
            db.session.query(InvoiceLine).delete()
            db.session.query(Invoice).delete()
            db.session.query(Stock).delete()
            db.session.query(Product).delete()
            db.session.query(Customer).delete()
            db.session.query(Country).delete()
            # Clear categories that might have been created with NULL stock_codes previously
            # Keep existing categories if they have stock codes, as we're not re-creating them based on source CategoryName
            # db.session.query(Category).filter(Category.stock_code.is_(None)).delete()
            db.session.commit()
            db.session.execute(text('SET FOREIGN_KEY_CHECKS=1'))
            logger.info("Cleared existing data in application tables.")

            # --- Import Data into Application Tables ---

            # Import countries
            # Use found column name for selection
            countries_df = source_data_df[source_data_df[column_mapping['Country']].notna()][[column_mapping['Country']]].drop_duplicates().reset_index(drop=True)
            country_map = {}
            for _, row in countries_df.iterrows():
                country_name = row[column_mapping['Country']]
                country = Country(country_name=country_name)
                db.session.add(country)
                db.session.flush() # To get the generated country_id
                country_map[country_name] = country.country_id
            db.session.commit()
            logger.info(f"Imported {len(countries_df)} countries")

            # Import customers and build customer_map (CustomerID to application customer_id)
            # Use found column names for selection
            customers_df = source_data_df[source_data_df[column_mapping['CustomerID']].notna()][[column_mapping['CustomerID'], column_mapping['Country']]].drop_duplicates(subset=[column_mapping['CustomerID']]).reset_index(drop=True)
            customer_map = {}
            for _, row in customers_df.iterrows():
                 customer_id_source = int(row[column_mapping['CustomerID']])
                 country_name = row[column_mapping['Country']]
                 if country_name in country_map:
                    customer = Customer(
                        customer_id=customer_id_source,
                        country_id=country_map[country_name]
                    )
                    db.session.add(customer)
                    # Assuming customer_id in source is unique and matches app customer_id for now
                    customer_map[customer_id_source] = customer_id_source
                 else:
                     logger.warning(f"Skipping row due to missing country mapping for country: {country_name}")

            db.session.commit()
            logger.info(f"Imported {len(customer_map)} customers")

            # Import products and build product_map (StockCode to ProductID)
            # Use found column names for selection
            products_df = source_data_df[source_data_df[column_mapping['StockCode']].notna()][[column_mapping['StockCode'], column_mapping['Description']]].drop_duplicates(subset=[column_mapping['StockCode']]).reset_index(drop=True)
            product_map = {}
            for i, (_, row) in enumerate(products_df.iterrows()):
                stock_code = row[column_mapping['StockCode']]
                description = row[column_mapping['Description']] if pd.notna(row[column_mapping['Description']]) else 'No Description'
                product = Product(
                    # Generate ProductID since it's not in source table columns
                    # Using i + 1 as a simple unique integer ID
                    product_id=i + 1, 
                    stock_code=stock_code,
                    description=description
                )
                db.session.add(product)
                product_map[stock_code] = product.product_id
            db.session.commit()
            logger.info(f"Imported {len(product_map)} products")

            # Import categories based on Product Descriptions and Stock Codes
            # Define category keywords
            category_keywords = {
                'Home Decor': ['DECOR', 'DECORATION', 'BAUBLE', 'HEART', 'GLASS', 'METAL', 'DOOR', 'WALL', 'FRAME', 'MIRROR', 'CUSHION', 'CANDLE'],
                'Stationery': ['PENCIL', 'PEN', 'NOTEBOOK', 'PAPER', 'TAPE', 'CHAR', 'ENVELOPE', 'CARD', 'STICKER', 'LABEL', 'BOOK', 'DIARY'],
                'Toys': ['TOY', 'GAME', 'PUZZLE', 'DOLL', 'BEAR', 'BALL', 'BLOCK', 'TRAIN', 'CAR', 'ANIMAL', 'PLUSH'],
                'Accessories': ['BAG', 'PURSE', 'WALLET', 'SCARF', 'HAT', 'GLOVE', 'BELT', 'JEWEL', 'BRACELET', 'NECKLACE', 'RING', 'WATCH'],
                'Seasonal': ['CHRISTMAS', 'EASTER', 'HALLOWEEN', 'VALENTINE', 'SANTA', 'EGG', 'PUMPKIN', 'HEART', 'TREE', 'STAR', 'SNOW']
            }

            # Create a mapping from StockCode to determined CategoryName using products_df
            stock_code_to_category_name = {}
            # Use found column names for access
            for _, row in products_df.iterrows(): # Use the products_df created above
                 stock_code = row[column_mapping['StockCode']]
                 description = row[column_mapping['Description']] if pd.notna(row[column_mapping['Description']]) else ''
                 assigned = False
                 for category, keywords in category_keywords.items():
                     if any(keyword in description.upper() for keyword in keywords):
                         stock_code_to_category_name[stock_code] = category
                         assigned = True
                         break
                 if not assigned:
                     # Default to 'Accessories' if no category matches
                     stock_code_to_category_name[stock_code] = 'Accessories'

            # Import categories - one entry per unique StockCode assigned a category
            categories_added_count = 0
            # Use a set to track added stock_codes to avoid duplicates
            added_stock_codes = set()
            for stock_code, category_name in stock_code_to_category_name.items():
                 if stock_code not in added_stock_codes:
                    category = Category(
                        # CategoryID is auto-incremented
                        category_name=category_name,
                        stock_code=stock_code
                    )
                    db.session.add(category)
                    added_stock_codes.add(stock_code)
                    categories_added_count += 1

            db.session.commit()
            logger.info(f"Imported {categories_added_count} categories with stock code mappings")

            # Import invoices and build invoice_map (InvoiceNo to application invoice_no)
            # Use found column names for selection
            invoices_df = source_data_df[source_data_df[column_mapping['InvoiceNo']].notna()][[column_mapping['InvoiceNo'], column_mapping['InvoiceDate'], column_mapping['CustomerID']]].drop_duplicates(subset=[column_mapping['InvoiceNo']]).reset_index(drop=True)

            invoice_map = {}
            # Assuming invoice_no in source is unique and matches app invoice_no for now
            # Use found column names for access
            for _, row in invoices_df.iterrows():
                invoice_no = row[column_mapping['InvoiceNo']]

                if pd.notna(row[column_mapping['InvoiceDate']]):
                    try:
                        # Attempt to parse date, handle potential errors
                        invoice_date = pd.to_datetime(row[column_mapping['InvoiceDate']])
                    except ValueError:
                        logger.warning(f"Skipping invoice {invoice_no} due to invalid date format: {row[column_mapping['InvoiceDate']]}")
                        continue # Skip this invoice if date is invalid

                    # Check if CustomerID exists in our imported customers
                    customer_id_source = int(row[column_mapping['CustomerID']]) if pd.notna(row[column_mapping['CustomerID']]) else None
                    if customer_id_source is not None and customer_id_source in customer_map:
                        invoice = Invoice(
                            invoice_no=invoice_no,
                            invoice_date=invoice_date,
                            customer_id=customer_id_source # Use the customer_id directly from source
                        )
                        db.session.add(invoice)
                        invoice_map[invoice_no] = invoice_no # Assuming invoice_no is unique and matches
                    else:
                        logger.warning(f"Skipping invoice {invoice_no} due to missing or invalid customer ID: {row[column_mapping['CustomerID']]}")

            db.session.commit()
            logger.info(f"Imported {len(invoice_map)} invoices")

            # Import invoice lines
            invoice_lines_added_count = 0
            # Filter out rows with missing required data before iterating
            # Use found column names for filtering
            filtered_invoice_lines_df = source_data_df[
                source_data_df[column_mapping['InvoiceNo']].notna() &
                source_data_df[column_mapping['StockCode']].notna() &
                source_data_df[column_mapping['Quantity']].notna() &
                source_data_df[column_mapping['UnitPrice']].notna()
            ]
            # Use found column names for access
            for _, row in filtered_invoice_lines_df.iterrows():
                invoice_no = row[column_mapping['InvoiceNo']]
                stock_code = row[column_mapping['StockCode']]
                quantity = row[column_mapping['Quantity']]
                unit_price = row[column_mapping['UnitPrice']]

                # Ensure invoice and product exist in our imported data
                if invoice_no in invoice_map and stock_code in product_map:
                    # Map StockCode to ProductID
                    product_id = product_map[stock_code]

                    invoice_line = InvoiceLine(
                        invoice_no=invoice_no,
                        product_id=product_id,
                        quantity=int(quantity),
                        unit_price=float(unit_price)
                    )
                    db.session.add(invoice_line)
                    invoice_lines_added_count += 1
                else:
                    logger.warning(f"Skipping invoice line (InvoiceNo: {invoice_no}, StockCode: {stock_code}) due to missing invoice or product.")

            db.session.commit()
            logger.info(f"Imported {invoice_lines_added_count} invoice lines")

            # Initialize stock levels (can be done after importing invoice lines)
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
                    quantity_in_stock=int(total_sold) # Simple initial stock based on total sold
                )
                # Use merge in case a product already had a stock entry
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