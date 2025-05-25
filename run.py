import sys
from app import create_app, db
from app.import_data import import_data

app = create_app()

if __name__ == '__main__':
    import sys
    if '--print-invoice-dates' in sys.argv:
        from app.models import Invoice
        with app.app_context():
            dates = set(str(i.invoice_date) for i in db.session.query(Invoice).all())
            for d in sorted(dates):
                print(d)
        sys.exit(0)
    elif '--import-data' in sys.argv:
        with app.app_context():
            print("Starting data import...")
            try:
                import_data()
                print("Data import completed.")
            except Exception as e:
                print(f"Data import failed: {e}")
        sys.exit(0)
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()
    app.run(debug=True, host='127.0.0.1', port=5001) 