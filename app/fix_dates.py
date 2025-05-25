from sqlalchemy import create_engine, text
from app import create_app, db
from app.models import Invoice
import logging

logger = logging.getLogger(__name__)

def fix_invoice_dates():
    app = create_app()
    with app.app_context():
        try:
            # Connect to source database
            source_engine = create_engine('mysql+mysqlconnector://root:5h5hjfkC@localhost:3306/online_retail_db')
            
            # Get invoices with NULL dates
            null_dates = db.session.query(Invoice.invoice_no).filter(Invoice.invoice_date.is_(None)).all()
            null_dates = [row[0] for row in null_dates]
            
            if not null_dates:
                logger.info("No NULL dates found in Invoice table")
                return
            
            logger.info(f"Found {len(null_dates)} invoices with NULL dates")
            
            # Get dates from source table
            with source_engine.connect() as conn:
                # Convert list of invoice numbers to SQL IN clause
                invoice_list = "','".join(null_dates)
                query = f"""
                    SELECT InvoiceNo, InvoiceDate
                    FROM online_retail_combined_larger
                    WHERE InvoiceNo IN ('{invoice_list}')
                    AND InvoiceDate IS NOT NULL
                """
                result = conn.execute(text(query))
                date_updates = {row[0]: row[1] for row in result}
            
            # Update dates in Invoice table
            updated_count = 0
            for invoice_no, new_date in date_updates.items():
                try:
                    invoice = db.session.query(Invoice).filter_by(invoice_no=invoice_no).first()
                    if invoice:
                        invoice.invoice_date = new_date
                        updated_count += 1
                except Exception as e:
                    logger.error(f"Error updating invoice {invoice_no}: {str(e)}")
                    continue
            
            db.session.commit()
            logger.info(f"Updated {updated_count} invoice dates")
            
            # Check for any remaining NULL dates
            remaining_nulls = db.session.query(Invoice.invoice_no).filter(Invoice.invoice_date.is_(None)).count()
            if remaining_nulls > 0:
                logger.warning(f"Warning: {remaining_nulls} invoices still have NULL dates")
            
        except Exception as e:
            logger.error(f"Error fixing invoice dates: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    fix_invoice_dates() 