from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from os import path
import os
from datetime import datetime, timedelta

# Initialize the database handler
db = SQLAlchemy()
migrate = Migrate()
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_user():
        return dict(user=current_user)

    return app

def create_database(app):
    if not path.exists(path.join(app.instance_path, DB_NAME)):
        with app.app_context():
            db.create_all()
            create_initial_data()
        print('Created Database!')

def create_initial_data():
    from .models import Plan, GymClass, Trainer

    # Populate Plans
    if Plan.query.count() == 0:
        plans = [
            Plan(name='Day Pass', price=5, period='day', description='Access to all gym facilities for one day with no commitment.'),
            Plan(name='Weekly Pass', price=20, period='week', description='Access to all gym facilities and group classes for one week.'),
            Plan(name='Monthly Basic', price=30, period='month', description='Unlimited access to gym facilities and group classes on a month-to-month basis.'),
            Plan(name='Monthly Premium', price=50, period='month', description='Includes everything in the Monthly Basic plan plus access to premium equipment and one personal training session per month.'),
            Plan(name='Quarterly Basic', price=80, period='3 months', description='Unlimited access to gym facilities and group classes for three months.'),
            Plan(name='Quarterly Premium', price=120, period='3 months', description='Includes everything in the Quarterly Basic plan plus access to premium equipment and three personal training sessions per quarter.'),
            Plan(name='Yearly Basic', price=300, period='year', description='Unlimited access for a year, includes special member benefits and is the best value plan.'),
            Plan(name='Yearly Premium', price=500, period='year', description='Includes everything in the Yearly Basic plan plus access to premium equipment and twelve personal training sessions per year.'),
            Plan(name='Family Plan', price=800, period='year', description='Yearly membership for up to four family members, includes access to all facilities and group classes, plus four personal training sessions per family member per year.'),
        ]
        db.session.bulk_save_objects(plans)

    # Populate Gym Classes
    if GymClass.query.count() == 0:
        classes = [
            GymClass(name='Yoga Basics', instructor='Alice Johnson', start_time=datetime.utcnow(), end_time=datetime.utcnow() + timedelta(hours=1), description='An introduction to basic yoga poses.', location='Room A', difficulty_level='Beginner', capacity=20),
            GymClass(name='Advanced Pilates', instructor='Bob Smith', start_time=datetime.utcnow() + timedelta(hours=2), end_time=datetime.utcnow() + timedelta(hours=3), description='A challenging class for experienced Pilates students.', location='Room B', difficulty_level='Advanced', capacity=15),
            GymClass(name='Strength Training', instructor='Charlie Davies', start_time=datetime.utcnow() + timedelta(hours=4), end_time=datetime.utcnow() + timedelta(hours=5), description='Focus on building muscle strength and endurance.', location='Gym Floor', difficulty_level='Intermediate', capacity=25),
            GymClass(name='HIIT Workout', instructor='Diana King', start_time=datetime.utcnow() + timedelta(hours=6), end_time=datetime.utcnow() + timedelta(hours=7), description='High-intensity interval training for maximum calorie burn.', location='Room C', difficulty_level='Advanced', capacity=20),
            GymClass(name='Zumba Dance', instructor='Eve Adams', start_time=datetime.utcnow() + timedelta(hours=8), end_time=datetime.utcnow() + timedelta(hours=9), description='A fun and energetic dance workout.', location='Room D', difficulty_level='All Levels', capacity=30),
            GymClass(name='Beginner Spin Class', instructor='Franklin Moore', start_time=datetime.utcnow() + timedelta(hours=10), end_time=datetime.utcnow() + timedelta(hours=11), description='An introduction to spin cycling.', location='Spin Studio', difficulty_level='Beginner', capacity=20)
        ]
        db.session.bulk_save_objects(classes)

    # Populate Trainers
    if Trainer.query.count() == 0:
        trainers = [
            Trainer(name='John Doe', specialty='Weightlifting', available_hours='Mon-Fri 8am-6pm'),
            Trainer(name='Jane Smith', specialty='Cardio Fitness', available_hours='Mon-Fri 7am-5pm'),
            Trainer(name='Emily White', specialty='Yoga & Wellness', available_hours='Mon-Fri 9am-4pm'),
            Trainer(name='Chris Green', specialty='HIIT', available_hours='Mon-Fri 10am-6pm'),
            Trainer(name='Paul Black', specialty='Strength Training', available_hours='Mon-Fri 6am-2pm'),
            Trainer(name='Sarah Brown', specialty='Endurance Training', available_hours='Mon-Fri 8am-6pm')
        ]
        db.session.bulk_save_objects(trainers)

    db.session.commit()




