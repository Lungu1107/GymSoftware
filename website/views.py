from flask import Blueprint, flash, redirect, url_for, request, render_template
from flask_login import login_required, current_user
from .models import WorkoutLog, Trainer, TrainerAssignment, Plan, Transaction, Invoice, GymClass, ClassBooking, BillingInfo, User
from . import db
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import re

views = Blueprint('views', __name__)

@views.route('/')
@login_required
def home():
    return render_template("home.html", user=current_user)

@views.route('/profile')
@login_required
def profile():
    plans = Plan.query.all()
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.payment_date.desc()).all()
    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.due_date.desc()).all()
    classes = GymClass.query.order_by(GymClass.start_time).all()
    trainers = Trainer.query.all()
    trainer_assignments = TrainerAssignment.query.filter_by(user_id=current_user.id).all()
    workout_logs = WorkoutLog.query.filter_by(user_id=current_user.id).order_by(WorkoutLog.date.desc()).all()

    return render_template("profile.html", user=current_user, plans=plans, transactions=transactions, invoices=invoices,
                           classes=classes, trainers=trainers, trainer_assignments=trainer_assignments, workout_logs=workout_logs)


@views.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

        user = User.query.filter_by(email=email).first()
        if user and user.id != current_user.id:
            flash('Email already exists.', category='error')
        elif not re.match(email_pattern, email):
            flash('Invalid email address.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        else:
            current_user.email = email
            current_user.phone = phone
            current_user.address = address

            if password1:
                if password1 != password2:
                    flash('Passwords do not match.', category='error')
                elif len(password1) < 7:
                    flash('Password must be at least 7 characters.', category='error')
                else:
                    current_user.password = generate_password_hash(password1, method='pbkdf2:sha256')

            db.session.commit()
            flash('Profile updated successfully!', category='success')
            return redirect(url_for('views.profile'))

    return render_template("edit_profile.html", user=current_user)

@views.route('/billing', methods=['GET', 'POST'])
@login_required
def billing():
    if request.method == 'POST':
        card_last_four = request.form.get('cardLastFour')
        cardholder_name = request.form.get('cardholderName')
        expiration_date = request.form.get('expiryDate')
        billing_address = request.form.get('billingAddress')

        if not current_user.billing_info:
            new_billing_info = BillingInfo(card_last_four=card_last_four, cardholder_name=cardholder_name,
                                           expiration_date=expiration_date, billing_address=billing_address, user_id=current_user.id)
            db.session.add(new_billing_info)
            flash('Billing information added!', category='success')
        else:
            current_user.billing_info.card_last_four = card_last_four
            current_user.billing_info.cardholder_name = cardholder_name
            current_user.billing_info.expiration_date = expiration_date
            current_user.billing_info.billing_address = billing_address
            flash('Billing information updated!', category='success')
        db.session.commit()
    return redirect(url_for('views.profile') + '#billing')

@views.route('/delete-card', methods=['POST'])
@login_required
def delete_card():
    billing_info = current_user.billing_info
    if billing_info:
        try:
            db.session.delete(billing_info)
            db.session.commit()
            flash('Card deleted successfully.', category='success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to delete card due to an error: {str(e)}', category='error')
    else:
        flash('No card information to delete.', category='error')
    return redirect(url_for('views.profile') + '#billing')

@views.route('/transactions', methods=['GET'])
@login_required
def transactions():
    user_transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    return render_template('transactions.html', transactions=user_transactions)

@views.route('/membership-plans')
@login_required
def membership_plans():
    plans = Plan.query.all()
    if not plans:
        flash('No membership plans available.', category='info')
    return render_template('membership_plans.html', plans=plans)

@views.route('/purchase-plan', methods=['POST'])
@login_required
def purchase_plan():
    plan_id = request.form.get('plan_id')
    desired_plan = Plan.query.get(plan_id)

    if not desired_plan:
        flash('Plan not found.', category='error')
        return redirect(url_for('views.profile') + '#membership')

    if not current_user.billing_info:
        flash('Please add a credit card before purchasing a membership.', category='error')
        return redirect(url_for('views.profile') + '#billing')

    # Updated plan hierarchy
    plan_hierarchy = {
        'Day Pass': 1,
        'Weekly Pass': 2,
        'Monthly Basic': 3,
        'Monthly Premium': 4,
        'Quarterly Basic': 5,
        'Quarterly Premium': 6,
        'Yearly Basic': 7,
        'Yearly Premium': 8,
        'Family Plan': 9
    }

    if current_user.membership_plan_id:
        current_plan = Plan.query.get(current_user.membership_plan_id)
        current_plan_level = plan_hierarchy.get(current_plan.name, 0)
        desired_plan_level = plan_hierarchy.get(desired_plan.name, 0)
        if desired_plan_level <= current_plan_level:
            flash('You can only upgrade to a higher tier plan.', category='error')
            return redirect(url_for('views.profile') + '#membership')

    try:
        invoice = Invoice(
            user_id=current_user.id,
            plan_id=desired_plan.id,
            amount_due=desired_plan.price,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=365 if desired_plan.period == 'year' else 30),
            due_date=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(invoice)

        transaction = Transaction(
            user_id=current_user.id,
            invoice_id=invoice.id,
            paid_amount=desired_plan.price,
            payment_method="Stored Credit Card",
            payment_date=datetime.utcnow()
        )
        db.session.add(transaction)

        current_user.membership_plan_id = desired_plan.id
        current_user.membership_start_date = datetime.utcnow()
        current_user.membership_end_date = datetime.utcnow() + timedelta(days=365 if desired_plan.period == 'year' else 30)

        db.session.commit()
        flash('Membership plan upgraded successfully!', category='success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while processing your purchase: {e}', category='error')

    return redirect(url_for('views.profile'))


@views.route('/class-scheduling')
@login_required
def class_scheduling():
    classes = GymClass.query.order_by(GymClass.start_time).all()
    return render_template('class_scheduling.html', classes=classes)

@views.route('/book_class', methods=['POST'])
@login_required
def book_class():
    class_id = request.form.get('class_id')
    gym_class = GymClass.query.get(class_id)
    if not gym_class:
        flash('Class not found.', category='error')
        return redirect(url_for('views.profile') + '#scheduling')

    if not current_user.membership_plan_id:
        flash('You need an active membership to book a class.', category='error')
        return redirect(url_for('views.profile') + '#membership')

    existing_booking = ClassBooking.query.filter_by(user_id=current_user.id, class_id=class_id).first()
    if existing_booking:
        flash('You have already booked this class.', category='info')
        return redirect(url_for('views.profile') + '#scheduling')

    new_booking = ClassBooking(user_id=current_user.id, class_id=class_id)
    db.session.add(new_booking)
    db.session.commit()
    flash('Class booked successfully!', category='success')
    return redirect(url_for('views.profile'))

@views.route('/cancel-class/<int:class_booking_id>', methods=['POST'])
@login_required
def cancel_class(class_booking_id):
    class_booking = ClassBooking.query.get(class_booking_id)
    if class_booking and class_booking.user_id == current_user.id:
        try:
            db.session.delete(class_booking)
            db.session.commit()
            flash('Class booking canceled successfully!', category='success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to cancel class booking due to an error: {str(e)}', category='error')
    else:
        flash('Class booking not found or you do not have permission to cancel it.', category='error')
    return redirect(url_for('views.profile'))

def validate_schedule(schedule):
    total_hours = 0
    days = schedule.split(',')
    for day in days:
        hours = re.findall(r'(\d+)-(\d+)', day)
        for start, end in hours:
            total_hours += int(end) - int(start)
            if int(end) - int(start) > 1:
                raise ValueError('Cannot assign more than one hour per day.')
    if total_hours > 7:
        raise ValueError('Cannot assign more than 7 hours per week.')
    return True

@views.route('/assign-trainer', methods=['GET', 'POST'])
@login_required
def assign_trainer():
    trainers = Trainer.query.limit(6).all()

    if request.method == 'POST':
        if not current_user.membership_plan_id or current_user.membership_end_date < datetime.utcnow():
            flash('You need an active membership plan to assign a trainer.', category='error')
            return redirect(url_for('views.profile') + '#membership')

        trainer_id = request.form.get('trainer_id')
        schedule = request.form.get('schedule')
        desired_plan = Plan.query.get(current_user.membership_plan_id)

        # Check if the plan includes personal training sessions
        if 'Premium' in desired_plan.name:
            included_sessions = True
        else:
            included_sessions = False
            extra_fee = 50  # Example extra fee for personal training sessions

        # Validate the schedule
        if trainer_id:
            existing_assignment = TrainerAssignment.query.filter_by(user_id=current_user.id, trainer_id=trainer_id).first()
            if existing_assignment:
                flash('You have already assigned this trainer.', category='info')
            else:
                try:
                    validate_schedule(schedule)
                except ValueError as e:
                    flash(str(e), category='error')
                    return redirect(url_for('views.profile') + '#trainers')

                new_assignment = TrainerAssignment(user_id=current_user.id, trainer_id=trainer_id, schedule=schedule)
                db.session.add(new_assignment)

                if not included_sessions:
                    try:
                        invoice = Invoice(
                            user_id=current_user.id,
                            plan_id=desired_plan.id,
                            amount_due=extra_fee,
                            start_date=datetime.utcnow(),
                            end_date=datetime.utcnow() + timedelta(days=30),
                            due_date=datetime.utcnow() + timedelta(days=30)
                        )
                        db.session.add(invoice)

                        transaction = Transaction(
                            user_id=current_user.id,
                            invoice_id=invoice.id,
                            paid_amount=extra_fee,
                            payment_method="Stored Credit Card",
                            payment_date=datetime.utcnow()
                        )
                        db.session.add(transaction)

                        db.session.commit()
                        flash('Trainer assigned successfully! Extra fee applied.', category='success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f'An error occurred while processing your assignment: {e}', category='error')
                        return redirect(url_for('views.profile') + '#trainers')
                else:
                    db.session.commit()
                    flash('Trainer assigned successfully!', category='success')
            return redirect(url_for('views.profile'))

    return render_template('assign_trainer.html', trainers=trainers)


@views.route('/cancel-trainer/<int:trainer_assignment_id>', methods=['POST'])
@login_required
def cancel_trainer(trainer_assignment_id):
    trainer_assignment = TrainerAssignment.query.get(trainer_assignment_id)
    if trainer_assignment and trainer_assignment.user_id == current_user.id:
        try:
            db.session.delete(trainer_assignment)
            db.session.commit()
            flash('Trainer assignment canceled successfully!', category='success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to cancel trainer assignment due to an error: {str(e)}', category='error')
    else:
        flash('Trainer assignment not found or you do not have permission to cancel it.', category='error')
    return redirect(url_for('views.profile'))


@views.route('/track-hours', methods=['GET', 'POST'])
@login_required
def track_hours():
    if request.method == 'POST':
        date_str = request.form.get('date')
        hours = request.form.get('hours')

        if not current_user.membership_plan_id:
            flash('You need an active membership plan to log workout hours.', category='error')
            return redirect(url_for('views.profile') + '#track-hours')

        today = datetime.utcnow().date()

        try:
            log_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', category='error')
            return redirect(url_for('views.profile') + '#track-hours')

        if log_date < current_user.membership_start_date.date() or log_date > current_user.membership_end_date.date():
            flash('You can only log hours for days you have an active membership.', category='error')
            return redirect(url_for('views.profile') + '#track-hours')

        if not date_str or not hours:
            flash('Please provide both date and hours.', category='error')
        else:
            try:
                hours = float(hours)
                new_log = WorkoutLog(user_id=current_user.id, date=log_date, hours=hours)
                db.session.add(new_log)
                db.session.commit()
                flash('Workout hours logged successfully!', category='success')
            except ValueError:
                flash('Invalid input for hours.', category='error')

        return redirect(url_for('views.profile') + '#track-hours')

    workout_logs = WorkoutLog.query.filter_by(user_id=current_user.id).order_by(WorkoutLog.date.desc()).all()
    return render_template("track_hours.html", user=current_user, workout_logs=workout_logs)

@views.route('/locations')
def locations():
    return render_template("locations.html")

@views.route('/equipment')
def equipment():
    return render_template("equipment.html")
