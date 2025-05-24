from datetime import datetime
from app import db

class Customer(db.Model):
    __tablename__ = 'Customer'
    
    customer_id = db.Column('CustomerID', db.Integer, primary_key=True)
    name = db.Column('CustomerName', db.String(255))
    country_code = db.Column('CountryCode', db.String(10))
    
    # Relationships
    invoices = db.relationship('Invoice', backref='customer', lazy=True)

class Product(db.Model):
    __tablename__ = 'Product'
    
    product_id = db.Column('ProductID', db.Integer, primary_key=True)
    name = db.Column('ProductName', db.String(100), nullable=False)
    price = db.Column('UnitPrice', db.Float, nullable=False)
    
    # Relationships
    invoice_items = db.relationship('InvoiceItem', backref='product', lazy=True)

class Category(db.Model):
    __tablename__ = 'Category'
    
    category_id = db.Column('CategoryID', db.Integer, primary_key=True)
    name = db.Column('CategoryName', db.String(255), nullable=False)

class Invoice(db.Model):
    __tablename__ = 'Invoice'
    
    invoice_no = db.Column('InvoiceNo', db.String(20), primary_key=True)
    invoice_date = db.Column('InvoiceDate', db.DateTime, nullable=False)
    customer_id = db.Column('CustomerID', db.Integer, db.ForeignKey('Customer.CustomerID'))
    
    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)
    
    @property
    def total_amount(self):
        return sum(item.quantity * item.unit_price for item in self.items)

class InvoiceItem(db.Model):
    __tablename__ = 'Invoice_Item'
    
    invoice_item_id = db.Column('InvoiceItemID', db.Integer, primary_key=True, autoincrement=True)
    invoice_no = db.Column('InvoiceNo', db.String(20), db.ForeignKey('Invoice.InvoiceNo'))
    product_id = db.Column('ProductID', db.Integer, db.ForeignKey('Product.ProductID'))
    quantity = db.Column('Quantity', db.Integer, nullable=False)
    
    @property
    def unit_price(self):
        return self.product.price if self.product else 0
    
    @property
    def subtotal(self):
        return self.quantity * self.unit_price 