from datetime import datetime
from app.extensions import db

class Country(db.Model):
    __tablename__ = 'country'
    
    country_id = db.Column('CountryID', db.Integer, primary_key=True, autoincrement=True)
    country_name = db.Column('CountryName', db.String(100), unique=True)
    
    # Relationships
    customers = db.relationship('Customer', backref='country', lazy=True)

class Customer(db.Model):
    __tablename__ = 'customer'
    
    customer_id = db.Column('CustomerID', db.Integer, primary_key=True)
    country_id = db.Column('CountryID', db.Integer, db.ForeignKey('country.CountryID'))
    
    # Relationships
    invoices = db.relationship('Invoice', backref='customer', lazy=True)

class Product(db.Model):
    __tablename__ = 'product'
    
    product_id = db.Column('ProductID', db.Integer, primary_key=True, autoincrement=True)
    stock_code = db.Column('StockCode', db.String(20), unique=True, nullable=False)
    description = db.Column('Description', db.Text)
    
    # Relationships
    invoice_lines = db.relationship('InvoiceLine', backref='product', lazy=True)
    stock = db.relationship('Stock', backref='product', lazy=True, uselist=False)

class Category(db.Model):
    __tablename__ = 'Category'
    
    category_id = db.Column('CategoryID', db.Integer, primary_key=True, autoincrement=True)
    category_name = db.Column('CategoryName', db.String(255), nullable=False)
    stock_code = db.Column('StockCode', db.Text)

class Invoice(db.Model):
    __tablename__ = 'invoice'
    
    invoice_no = db.Column('InvoiceNo', db.String(20), primary_key=True)
    invoice_date = db.Column('InvoiceDate', db.DateTime)
    customer_id = db.Column('CustomerID', db.Integer, db.ForeignKey('customer.CustomerID'))
    
    # Relationships
    invoice_lines = db.relationship('InvoiceLine', backref='invoice', lazy=True)
    
    # @property
    # def total_amount(self):
    #     return sum(line.line_total for line in self.invoice_lines)

class InvoiceLine(db.Model):
    __tablename__ = 'invoice_line'
    
    invoice_line_id = db.Column('InvoiceLineID', db.Integer, primary_key=True, autoincrement=True)
    invoice_no = db.Column('InvoiceNo', db.String(20), db.ForeignKey('invoice.InvoiceNo'), nullable=False)
    product_id = db.Column('ProductID', db.Integer, db.ForeignKey('product.ProductID'), nullable=False)
    quantity = db.Column('Quantity', db.Integer)
    unit_price = db.Column('UnitPrice', db.Numeric(10, 2))
    
    @property
    def line_total(self):
        if self.quantity is not None and self.unit_price is not None:
            return float(self.quantity * self.unit_price)
        return 0.0

class Stock(db.Model):
    __tablename__ = 'Stock'
    
    product_id = db.Column('ProductID', db.String(20), db.ForeignKey('product.StockCode'), primary_key=True)
    quantity_in_stock = db.Column('QuantityInStock', db.Integer, nullable=False, default=0) 