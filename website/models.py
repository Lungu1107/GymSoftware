from flask_login import UserMixin
from . import db
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
import re
from datetime import datetime, timedelta, date

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    phone = db.Column(db.String(15))
    dob = db.Column(db.Date)
    address = db.Column(db.String(255))
    billing_info = db.relationship('BillingInfo', backref='user', uselist=False)
    transactions = db.relationship('Transaction', back_populates='user', lazy='dynamic')
    membership_plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'))
    membership_start_date = db.Column(db.DateTime, nullable=True)
    membership_end_date = db.Column(db.DateTime, nullable=True)
    plan = db.relationship('Plan', back_populates='users')
    workout_logs = db.relationship('WorkoutLog', backref='user_workout_logs', lazy='dynamic')

class BillingInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    card_last_four = db.Column(db.String(4))
    cardholder_name = db.Column(db.String(100))
    billing_address = db.Column(db.String(255))
    expiration_date = db.Column(db.String(5))

    @validates('card_last_four')
    def validate_card_last_four(self, key, card_last_four):
        assert len(card_last_four) == 4 and card_last_four.isdigit(), "Card last four digits must be numeric and exactly 4 digits long."
        return card_last_four

    @validates('expiration_date')
    def validate_expiration_date(self, key, expiration_date):
        if not re.match(r"^(0[1-9]|1[0-2])\/\d{2}$", expiration_date):
            raise AssertionError("Expiration date must be in MM/YY format.")
        return expiration_date

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)
    paid_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)

    user = db.relationship('User', back_populates='transactions')
    invoice = db.relationship('Invoice', back_populates='transactions')

class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    period = db.Column(db.String(50))
    description = db.Column(db.String(255))
    users = db.relationship('User', back_populates='plan')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'))
    amount_due = db.Column(db.Float)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime, nullable=True)
    due_date = db.Column(db.DateTime, default=func.now() + timedelta(days=30))

    user = db.relationship('User', backref='invoices')
    plan = db.relationship('Plan', backref='invoices')
    transactions = db.relationship('Transaction', back_populates='invoice')

class GymClass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    instructor = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(255))
    location = db.Column(db.String(100))
    difficulty_level = db.Column(db.String(50))
    capacity = db.Column(db.Integer)

    def __repr__(self):
        return f'<GymClass {self.name}>'


class ClassBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    class_id = db.Column(db.Integer, db.ForeignKey('gym_class.id'))
    booking_time = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='class_bookings')
    gym_class = db.relationship('GymClass', backref='bookings')

class Trainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100))
    available_hours = db.Column(db.String(255), nullable=False)  # Store available hours as a JSON string

class TrainerAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainer.id'))
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    schedule = db.Column(db.String(255))  # Store the selected schedule as a JSON string

    user = db.relationship('User', backref='assigned_trainers')
    trainer = db.relationship('Trainer', backref='assignments')


class WorkoutLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    hours = db.Column(db.Float, nullable=False)

    user = db.relationship('User', backref='user_workout_logs')
