from flask import Blueprint, render_template, jsonify, request
from sqlalchemy import func, desc, case
from datetime import datetime, timedelta
from app import db
from app.models import Invoice, InvoiceItem, Product, Category, Customer

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/dashboard1')
def analytical_dashboard():
    """Analytical Dashboard for business analysts and data scientists"""
    # Get date range from request or default to last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get sales trends over time
    sales_trend = (
        db.session.query(
            func.date(Invoice.invoice_date).label('date'),
            func.sum(InvoiceItem.quantity * Product.price).label('total_sales')
        )
        .join(InvoiceItem, Invoice.invoice_no == InvoiceItem.invoice_no)
        .join(Product, InvoiceItem.product_id == Product.product_id)
        .filter(Invoice.invoice_date.between(start_date, end_date))
        .group_by(func.date(Invoice.invoice_date))
        .order_by('date')
        .all()
    )
    sales_trend = [dict(date=str(row.date), total_sales=float(row.total_sales)) for row in sales_trend]
    
    # Get top selling products
    top_products = db.session.query(
        Product.name.label('product_name'),
        func.sum(InvoiceItem.quantity).label('quantity')
    ).join(InvoiceItem).group_by(Product.product_id).order_by(
        desc('quantity')
    ).limit(10).all()
    top_products = [dict(product_name=row.product_name, quantity=int(row.quantity)) for row in top_products]
    
    # For now, provide empty lists for category_distribution and customer_segments
    category_distribution = []
    customer_segments = []
    
    return render_template('dashboard1.html',
                         sales_trend=sales_trend,
                         top_products=top_products,
                         category_distribution=category_distribution,
                         customer_segments=customer_segments,
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'),
                         categories=[]
                         )

@main.route('/dashboard2')
def operational_dashboard():
    """Minimal Operational Dashboard for debugging"""
    # Get recent invoices with customer names and total amount
    recent_invoices = db.session.query(
        Invoice.invoice_no,
        Invoice.invoice_date,
        Customer.name.label('customer_name'),
        func.sum(InvoiceItem.quantity * Product.price).label('total_amount')
    )\
    .join(Customer, Invoice.customer_id == Customer.customer_id)\
    .join(InvoiceItem, Invoice.invoice_no == InvoiceItem.invoice_no)\
    .join(Product, InvoiceItem.product_id == Product.product_id)\
    .group_by(Invoice.invoice_no, Invoice.invoice_date, Customer.name)\
    .order_by(Invoice.invoice_date.desc())\
    .limit(10).all()
    
    # Get daily metrics
    today = datetime.now().date()
    daily_metrics_raw = (
        db.session.query(
            func.count(Invoice.invoice_no).label('order_count'),
            func.sum(InvoiceItem.quantity * Product.price).label('total_sales'),
            func.avg(InvoiceItem.quantity * Product.price).label('average_order_value')
        )
        .join(InvoiceItem, Invoice.invoice_no == InvoiceItem.invoice_no)
        .join(Product, InvoiceItem.product_id == Product.product_id)
        .filter(func.date(Invoice.invoice_date) == today)
        .first()
    )
    # Patch: ensure no None values
    class Metrics:
        pass
    metrics = Metrics()
    metrics.order_count = daily_metrics_raw.order_count or 0
    metrics.total_sales = float(daily_metrics_raw.total_sales or 0)
    metrics.average_order_value = float(daily_metrics_raw.average_order_value or 0)
    # Get invoice status distribution (all completed in this case)
    status_distribution = [{'status': 'completed', 'count': metrics.order_count}]
    
    # For now, provide empty inventory_status
    inventory_status = []
    
    return render_template('dashboard2.html', 
        recent_orders=recent_invoices, 
        daily_metrics=metrics, 
        status_distribution=status_distribution, 
        inventory_status=inventory_status
    )

# API endpoints for dynamic data updates
@main.route('/api/sales-trend')
def get_sales_trend():
    days = int(request.args.get('days', 30))
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    sales_trend = (
        db.session.query(
            func.date(Invoice.invoice_date).label('date'),
            func.sum(InvoiceItem.quantity * Product.price).label('total_sales')
        )
        .join(InvoiceItem, Invoice.invoice_no == InvoiceItem.invoice_no)
        .join(Product, InvoiceItem.product_id == Product.product_id)
        .filter(Invoice.invoice_date.between(start_date, end_date))
        .group_by(func.date(Invoice.invoice_date))
        .order_by('date')
        .all()
    )
    
    return jsonify([{
        'date': str(record.date),
        'total_sales': float(record.total_sales)
    } for record in sales_trend])

@main.route('/api/operational-metrics')
def get_operational_metrics():
    today = datetime.now().date()
    
    # Get daily metrics
    daily_metrics = (
        db.session.query(
            func.count(Invoice.invoice_no).label('order_count'),
            func.sum(InvoiceItem.quantity * Product.price).label('total_sales'),
            func.avg(InvoiceItem.quantity * Product.price).label('average_order_value')
        )
        .join(InvoiceItem, Invoice.invoice_no == InvoiceItem.invoice_no)
        .join(Product, InvoiceItem.product_id == Product.product_id)
        .filter(func.date(Invoice.invoice_date) == today)
        .first()
    )
    
    # Get invoice status distribution (all completed in this case)
    status_distribution = [{'status': 'completed', 'count': daily_metrics.order_count or 0}]
    
    return jsonify({
        'order_count': daily_metrics.order_count or 0,
        'total_sales': float(daily_metrics.total_sales or 0),
        'average_order_value': float(daily_metrics.average_order_value or 0),
        'status_distribution': status_distribution
    }) 