import os
from datetime import timedelta

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:5h5hjfkC@localhost:3306/online_retail_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # Debug settings
    DEBUG = True 