from flask import Blueprint, render_template, jsonify, request
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app import db
from app.models import Invoice, InvoiceItem, Product, Category, Customer

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('base.html')

@main.route('/dashboard1')
def analytical_dashboard():
    """Analytical Dashboard for business analysts and data scientists"""
    # Get date range from request or default to last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get sales trends over time
    sales_trend = db.session.query(
        func.date(Invoice.invoice_date).label('date'),
        func.sum(Invoice.total_amount).label('total_sales')
    ).filter(
        Invoice.invoice_date.between(start_date, end_date)
    ).group_by(
        func.date(Invoice.invoice_date)
    ).order_by('date').all()
    
    # Get top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(InvoiceItem.quantity).label('total_quantity')
    ).join(InvoiceItem).group_by(Product.product_id).order_by(
        desc('total_quantity')
    ).limit(10).all()
    
    # Get category distribution
    category_distribution = db.session.query(
        Category.name,
        func.count(Product.product_id).label('product_count')
    ).join(Product).group_by(Category.category_id).all()
    
    # Get customer segments based on invoice count
    customer_segments = db.session.query(
        func.case(
            (func.count(Invoice.invoice_no) == 0, 'New'),
            (func.count(Invoice.invoice_no) <= 3, 'Regular'),
            else_='VIP'
        ).label('segment'),
        func.count(Customer.customer_id).label('customer_count'),
        func.count(Invoice.invoice_no).label('invoice_count')
    ).outerjoin(Invoice).group_by('segment').all()
    
    return render_template('dashboard1.html',
                         sales_trend=sales_trend,
                         top_products=top_products,
                         category_distribution=category_distribution,
                         customer_segments=customer_segments)

@main.route('/dashboard2')
def operational_dashboard():
    """Operational Dashboard for operations team and executives"""
    # Get recent invoices
    recent_invoices = db.session.query(
        Invoice.invoice_no,
        Invoice.invoice_date,
        Invoice.total_amount,
        Customer.name.label('customer_name')
    ).join(Customer).order_by(
        Invoice.invoice_date.desc()
    ).limit(10).all()
    
    # Get daily sales metrics
    today = datetime.now().date()
    daily_metrics = db.session.query(
        func.count(Invoice.invoice_no).label('order_count'),
        func.sum(Invoice.total_amount).label('total_sales'),
        func.avg(Invoice.total_amount).label('average_order_value')
    ).filter(
        func.date(Invoice.invoice_date) == today
    ).first()
    
    # Get invoice status distribution (all completed in this case)
    status_distribution = [{'status': 'completed', 'count': len(recent_invoices)}]
    
    return render_template('dashboard2.html',
                         recent_orders=recent_invoices,
                         daily_metrics=daily_metrics,
                         status_distribution=status_distribution)

# API endpoints for dynamic data updates
@main.route('/api/sales-trend')
def get_sales_trend():
    days = int(request.args.get('days', 30))
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    sales_trend = db.session.query(
        func.date(Invoice.invoice_date).label('date'),
        func.sum(Invoice.total_amount).label('total_sales')
    ).filter(
        Invoice.invoice_date.between(start_date, end_date)
    ).group_by(
        func.date(Invoice.invoice_date)
    ).order_by('date').all()
    
    return jsonify([{
        'date': str(record.date),
        'total_sales': float(record.total_sales)
    } for record in sales_trend])

@main.route('/api/operational-metrics')
def get_operational_metrics():
    today = datetime.now().date()
    
    # Get daily metrics
    daily_metrics = db.session.query(
        func.count(Invoice.invoice_no).label('order_count'),
        func.sum(Invoice.total_amount).label('total_sales'),
        func.avg(Invoice.total_amount).label('average_order_value')
    ).filter(
        func.date(Invoice.invoice_date) == today
    ).first()
    
    # Get invoice status distribution (all completed in this case)
    status_distribution = [{'status': 'completed', 'count': daily_metrics.order_count or 0}]
    
    return jsonify({
        'order_count': daily_metrics.order_count or 0,
        'total_sales': float(daily_metrics.total_sales or 0),
        'average_order_value': float(daily_metrics.average_order_value or 0),
        'status_distribution': status_distribution
    }) 