from datetime import datetime
from app.extensions import db

class Customer(db.Model):
    __tablename__ = 'Customer'
    
    customer_id = db.Column('CustomerID', db.Integer, primary_key=True)
    name = db.Column('Name', db.String(100))
    country = db.Column('Country', db.String(100))
    segment = db.Column('Segment', db.String(50))
    
    # Relationships
    invoices = db.relationship('Invoice', backref='customer', lazy=True)

class Product(db.Model):
    __tablename__ = 'Product'
    
    product_id = db.Column('ProductID', db.Integer, primary_key=True)
    product_name = db.Column('ProductName', db.String(100), nullable=False)
    category_id = db.Column('CategoryID', db.Integer, db.ForeignKey('Category.CategoryID'))
    
    # Relationships
    invoice_lines = db.relationship('InvoiceLine', backref='product', lazy=True)
    category = db.relationship('Category', backref='products', lazy=True)
    stock = db.relationship('Stock', backref='product', lazy=True, uselist=False)

class Category(db.Model):
    __tablename__ = 'Category'
    
    category_id = db.Column('CategoryID', db.Integer, primary_key=True)
    category_name = db.Column('CategoryName', db.String(255), nullable=False)

class Invoice(db.Model):
    __tablename__ = 'Invoice'
    
    invoice_no = db.Column('InvoiceNo', db.String(20), primary_key=True)
    invoice_date = db.Column('InvoiceDate', db.DateTime, nullable=False)
    customer_id = db.Column('CustomerID', db.Integer, db.ForeignKey('Customer.CustomerID'))
    
    # Relationships
    invoice_lines = db.relationship('InvoiceLine', backref='invoice', lazy=True)
    
    @property
    def total_amount(self):
        return sum(line.line_total for line in self.invoice_lines)

class InvoiceLine(db.Model):
    __tablename__ = 'InvoiceLine'
    
    invoice_line_id = db.Column('InvoiceLineID', db.Integer, primary_key=True)
    invoice_no = db.Column('InvoiceNo', db.String(20), db.ForeignKey('Invoice.InvoiceNo'))
    product_id = db.Column('ProductID', db.Integer, db.ForeignKey('Product.ProductID'))
    quantity = db.Column('Quantity', db.Integer, nullable=False)
    unit_price = db.Column('UnitPrice', db.Float, nullable=False)
    line_total = db.Column('LineTotal', db.Float, nullable=False)

class Stock(db.Model):
    __tablename__ = 'Stock'
    
    product_id = db.Column('ProductID', db.Integer, db.ForeignKey('Product.ProductID'), primary_key=True)
    quantity_in_stock = db.Column('QuantityInStock', db.Integer, nullable=False, default=0) 