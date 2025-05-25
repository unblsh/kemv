from app import create_app, db

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
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()
    app.run(debug=True, host='127.0.0.1', port=5001) 