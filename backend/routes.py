from flask import request, jsonify, send_from_directory
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from config import app, db
import os
from models import User, SubscriptionPlan, UserSubscription, Attendance, HealthProfile, WorkoutClass, ClassRSVP
from datetime import datetime, timedelta
import logging

@app.route('/api/')
def api_home():
    return jsonify({"message": "Gym Management System Backend - API is running"}), 200

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        if User.query.filter_by(username=data['username']).first() or User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'User exists'}), 400
        user = User(username=data['username'], email=data['email'], role=data.get('role', 'user'))
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        access_token = create_access_token(identity=user.id)
        logging.info(f"User {data['username']} registered with role {user.role}")
        return jsonify({'access_token': access_token, 'role': user.role}), 201
    except Exception as e:
        logging.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data or 'username' not in data or 'password' not in data:
            logging.info(f"Login failed: Missing username or password in payload {data}")
            return jsonify({'error': 'Missing username or password'}), 400
        user = User.query.filter_by(username=data['username']).first()
        if not user:
            logging.info(f"Login failed: User {data['username']} not found")
            return jsonify({'error': 'Invalid credentials'}), 401
        if not user.check_password(data['password']):
            logging.info(f"Login failed: Invalid password for user {data['username']}")
            return jsonify({'error': 'Invalid credentials'}), 401
        access_token = create_access_token(identity=user.id)
        logging.info(f"User {data['username']} logged in successfully")
        return jsonify({'access_token': access_token, 'role': user.role}), 200
    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/dashboard', methods=['GET'])
@jwt_required()
def user_dashboard():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'user':
            logging.info(f"Unauthorized dashboard access by user_id {user_id} with role {user.role if user else 'None'}")
            return jsonify({'error': 'Access denied'}), 403
        subscriptions = SubscriptionPlan.query.all()
        user_subscriptions = UserSubscription.query.filter_by(user_id=user_id).all()
        attendance = Attendance.query.filter_by(user_id=user_id).all()
        trainer = user.trainers.first()
        trainer_details = trainer.to_dict() if trainer else None
        classes = WorkoutClass.query.all()
        rsvps = ClassRSVP.query.filter_by(user_id=user_id).all()
        return jsonify({
            'user': user.to_dict(),
            'subscriptions': [s.to_dict() for s in subscriptions],
            'user_subscriptions': [us.to_dict() for us in user_subscriptions],
            'attendance': [a.to_dict() for a in attendance],
            'trainer_details': trainer_details,
            'classes': [c.to_dict() for c in classes],
            'rsvps': [r.to_dict() for r in rsvps]
        }), 200
    except Exception as e:
        logging.error(f"Dashboard error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/admin-dashboard', methods=['GET'])
@jwt_required()
def admin_dashboard():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            logging.info(f"Unauthorized admin dashboard access by user_id {user_id} with role {user.role if user else 'None'}")
            return jsonify({'error': 'Access denied'}), 403
        users = User.query.all()
        trainers = User.query.filter_by(role='trainer').all()
        subscriptions = SubscriptionPlan.query.all()
        user_count = len(users)
        trainer_count = len(trainers)
        subscription_count = len(subscriptions)
        return jsonify({
            'user': user.to_dict(),
            'users': [u.to_dict() for u in users],
            'trainers': [t.to_dict() for t in trainers],
            'subscriptions': [s.to_dict() for s in subscriptions],
            'stats': {'user_count': user_count, 'trainer_count': trainer_count, 'subscription_count': subscription_count}
        }), 200
    except Exception as e:
        logging.error(f"Admin dashboard error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/trainer-dashboard', methods=['GET'])
@jwt_required()
def trainer_dashboard():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'trainer':
            logging.info(f"Unauthorized trainer dashboard access by user_id {user_id} with role {user.role if user else 'None'}")
            return jsonify({'error': 'Access denied'}), 403
        classes = WorkoutClass.query.filter_by(trainer_id=user_id).all()
        trained_users = user.trainees.all()
        class_stats = [{'name': c.name, 'attendance_count': c.current_capacity} for c in classes]
        return jsonify({
            'user': user.to_dict(),
            'classes': [c.to_dict() for c in classes],
            'trained_users': [u.to_dict() for u in trained_users],
            'class_stats': class_stats
        }), 200
    except Exception as e:
        logging.error(f"Trainer dashboard error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/attendance', methods=['GET', 'POST'])
@jwt_required()
def attendance():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user.role != 'user':
            return jsonify({'error': 'Access denied'}), 403
        if request.method == 'GET':
            attendances = Attendance.query.filter_by(user_id=user_id).all()
            return jsonify([a.to_dict() for a in attendances]), 200
        elif request.method == 'POST':
            attendance = Attendance(user_id=user_id, date=datetime.utcnow().date(), attended=True)
            db.session.add(attendance)
            db.session.commit()
            logging.info(f"Attendance marked for user_id {user_id}")
            return jsonify({'message': 'Attendance marked'}), 200
    except Exception as e:
        logging.error(f"Attendance error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/rsvp', methods=['POST'])
@jwt_required()
def rsvp_class():
    try:
        data = request.json
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user.role != 'user':
            return jsonify({'error': 'Access denied'}), 403
        class_instance = WorkoutClass.query.get(data['class_id'])
        if not class_instance or class_instance.current_capacity >= class_instance.max_capacity:
            return jsonify({'error': 'Class full or not found'}), 400
        rsvp = ClassRSVP(user_id=user_id, class_id=data['class_id'], attending=True)
        class_instance.current_capacity += 1
        db.session.add(rsvp)
        db.session.commit()
        logging.info(f"User {user_id} RSVP'd for class {data['class_id']}")
        return jsonify({'message': 'RSVP successful'}), 200
    except Exception as e:
        logging.error(f"RSVP error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/classes', methods=['GET', 'POST'])
@jwt_required()
def classes():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if request.method == 'GET':
            classes = WorkoutClass.query.all()
            return jsonify([c.to_dict() for c in classes]), 200
        elif request.method == 'POST':
            if user.role != 'trainer':
                return jsonify({'error': 'Access denied'}), 403
            data = request.json
            class_instance = WorkoutClass(
                trainer_id=user_id,
                name=data['name'],
                date_time=data['date_time'],
                max_capacity=data.get('max_capacity', 10)
            )
            db.session.add(class_instance)
            db.session.commit()
            logging.info(f"Class {data['name']} created by trainer {user.username}")
            return jsonify(class_instance.to_dict()), 201
    except Exception as e:
        logging.error(f"Class error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/subscriptions', methods=['POST'])
@jwt_required()
def create_subscription():
    try:
        data = request.json
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user.role != 'admin':
            logging.info(f"Unauthorized subscription creation attempt by user_id {user_id}")
            return jsonify({'error': 'Access denied'}), 403
        
        duration_months = int(data.get('duration_months', 0))
        if duration_months < 1 or duration_months > 60:
            logging.info(f"Invalid duration_months: {duration_months} by user_id {user_id}")
            return jsonify({'error': 'Duration must be between 1 and 60 months'}), 400
        
        duration_days = duration_months * 30
        if duration_days > 2147483647:
            logging.info(f"Duration days {duration_days} exceeds INTEGER limit by user_id {user_id}")
            return jsonify({'error': 'Duration too large'}), 400
        
        price = float(data.get('price', 0))
        if price <= 0:
            logging.info(f"Invalid price: {price} by user_id {user_id}")
            return jsonify({'error': 'Price must be positive'}), 400
        
        subscription = SubscriptionPlan(
            name=data['plan_name'],
            price=price,
            duration_days=duration_days,
            description=data.get('description', '')
        )
        db.session.add(subscription)
        db.session.commit()
        logging.info(f"Subscription {data['plan_name']} created by admin {user.username}")
        return jsonify(subscription.to_dict()), 201
    except ValueError as ve:
        logging.error(f"Subscription creation error: Invalid input {str(ve)}")
        return jsonify({'error': 'Invalid input format'}), 400
    except Exception as e:
        logging.error(f"Subscription creation error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users', methods=['GET', 'POST', 'PUT', 'DELETE'])
@jwt_required()
def manage_users():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user.role != 'admin':
            logging.info(f"Unauthorized user management attempt by user_id {user_id} with role {user.role}")
            return jsonify({'error': 'Access denied'}), 403
        if request.method == 'GET':
            users = User.query.all()
            return jsonify([u.to_dict() for u in users]), 200
        elif request.method == 'POST':
            data = request.json
            new_user = User(username=data['username'], email=data['email'], role=data.get('role', 'user'))
            new_user.set_password(data['password'])
            db.session.add(new_user)
            db.session.commit()
            logging.info(f"Admin {user.username} created user {data['username']}")
            return jsonify(new_user.to_dict()), 201
        elif request.method == 'PUT':
            data = request.json
            user_to_update = User.query.get(data['id'])
            if not user_to_update:
                logging.info(f"User {data['id']} not found for update by admin {user.username}")
                return jsonify({'error': 'User not found'}), 404
            user_to_update.username = data.get('username', user_to_update.username)
            user_to_update.email = data.get('email', user_to_update.email)
            user_to_update.role = data.get('role', user_to_update.role)
            if data.get('password'):
                user_to_update.set_password(data['password'])
            db.session.commit()
            logging.info(f"Admin {user.username} updated user {user_to_update.username}")
            return jsonify(user_to_update.to_dict()), 200
        elif request.method == 'DELETE':
            data = request.json
            user_to_delete = User.query.get(data['id'])
            if user_to_delete:
                db.session.delete(user_to_delete)
                db.session.commit()
                logging.info(f"Admin {user.username} deleted user {data['id']}")
                return jsonify({'message': 'User deleted'}), 200
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        logging.error(f"User management error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/trainers', methods=['GET', 'POST', 'PUT', 'DELETE'])
@jwt_required()
def manage_trainers():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user.role != 'admin':
            logging.info(f"Unauthorized trainer management attempt by user_id {user_id} with role {user.role}")
            return jsonify({'error': 'Access denied'}), 403
        if request.method == 'GET':
            trainers = User.query.filter_by(role='trainer').all()
            return jsonify([t.to_dict() for t in trainers]), 200
        elif request.method == 'POST':
            data = request.json
            new_trainer = User(username=data['username'], email=data['email'], role='trainer')
            new_trainer.set_password(data['password'])
            db.session.add(new_trainer)
            db.session.commit()
            logging.info(f"Admin {user.username} created trainer {data['username']}")
            return jsonify(new_trainer.to_dict()), 201
        elif request.method == 'PUT':
            data = request.json
            trainer_to_update = User.query.get(data['id'])
            if not trainer_to_update:
                logging.info(f"Trainer {data['id']} not found for update by admin {user.username}")
                return jsonify({'error': 'Trainer not found'}), 404
            trainer_to_update.username = data.get('username', trainer_to_update.username)
            trainer_to_update.email = data.get('email', trainer_to_update.email)
            if data.get('password'):
                trainer_to_update.set_password(data['password'])
            db.session.commit()
            logging.info(f"Admin {user.username} updated trainer {trainer_to_update.username}")
            return jsonify(trainer_to_update.to_dict()), 200
        elif request.method == 'DELETE':
            data = request.json
            trainer_to_delete = User.query.get(data['id'])
            if trainer_to_delete:
                db.session.delete(trainer_to_delete)
                db.session.commit()
                logging.info(f"Admin {user.username} deleted trainer {data['id']}")
                return jsonify({'message': 'Trainer deleted'}), 200
            return jsonify({'error': 'Trainer not found'}), 404
    except Exception as e:
        logging.error(f"Trainer management error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health-profile', methods=['GET', 'PATCH'])
@jwt_required()
def health_profile():
    try:
        user_id = get_jwt_identity()
        profile = HealthProfile.query.filter_by(user_id=user_id).first()
        if request.method == 'GET':
            if not profile:
                return jsonify({'error': 'Profile not found'}), 404
            return jsonify(profile.to_dict()), 200
        elif request.method == 'PATCH':
            data = request.json
            if not profile:
                profile = HealthProfile(user_id=user_id)
                db.session.add(profile)
            profile.height_cm = data.get('height_cm', profile.height_cm)
            profile.weight_kg = data.get('weight_kg', profile.weight_kg)
            profile.goal = data.get('goal', profile.goal)
            if profile.height_cm and profile.weight_kg:
                profile.bmi = profile.weight_kg / ((profile.height_cm / 100) ** 2)
            db.session.commit()
            logging.info(f"Health profile updated for user_id {user_id}")
            return jsonify(profile.to_dict()), 200
    except Exception as e:
        logging.error(f"Health profile error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/assign-trainer', methods=['POST'])
@jwt_required()
def assign_trainer():
    try:
        user_id = get_jwt_identity()
        admin = User.query.get(user_id)
        if admin.role != 'admin':
            logging.info(f"Unauthorized trainer assignment attempt by user_id {user_id}")
            return jsonify({'error': 'Access denied'}), 403
        data = request.json
        user = User.query.get(data['user_id'])
        trainer = User.query.get(data['trainer_id'])
        if not user or not trainer:
            logging.info(f"User {data['user_id']} or trainer {data['trainer_id']} not found")
            return jsonify({'error': 'User or trainer not found'}), 404
        if trainer.role != 'trainer':
            logging.info(f"Invalid trainer role for trainer_id {data['trainer_id']}")
            return jsonify({'error': 'Selected user is not a trainer'}), 400
        if trainer in user.trainers:
            logging.info(f"Trainer {trainer.username} already assigned to user {user.username}")
            return jsonify({'error': 'Trainer already assigned to this user'}), 400
        user.trainers.append(trainer)
        db.session.commit()
        logging.info(f"Admin {admin.username} assigned trainer {trainer.username} to user {user.username}")
        return jsonify({'message': 'Trainer assigned successfully'}), 200
    except Exception as e:
        logging.error(f"Trainer assignment error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/user-subscriptions', methods=['POST'])
@jwt_required()
def register_subscription():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user.role != 'user':
            logging.info(f"Unauthorized subscription registration attempt by user_id {user_id}")
            return jsonify({'error': 'Access denied'}), 403
        data = request.json
        plan = SubscriptionPlan.query.get(data['plan_id'])
        if not plan:
            logging.info(f"Subscription plan {data['plan_id']} not found")
            return jsonify({'error': 'Subscription plan not found'}), 404
        # Check for active subscription
        active_sub = UserSubscription.query.filter_by(user_id=user_id).filter(UserSubscription.end_date > datetime.utcnow()).first()
        if active_sub:
            logging.info(f"User {user_id} has an active subscription")
            return jsonify({'error': 'You have an active subscription. Cannot register for a new one until the current one expires'}), 400
        # Check if already subscribed to this plan
        existing_subscription = UserSubscription.query.filter_by(user_id=user_id, plan_id=data['plan_id']).first()
        if existing_subscription:
            logging.info(f"User {user_id} already subscribed to plan {data['plan_id']}")
            return jsonify({'error': 'Already subscribed to this plan'}), 400
        # Calculate end_date
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=plan.duration_days)
        subscription = UserSubscription(
            user_id=user_id,
            plan_id=plan.id,
            start_date=start_date,
            end_date=end_date
        )
        db.session.add(subscription)
        db.session.commit()
        logging.info(f"User {user.username} subscribed to plan {plan.name}")
        return jsonify(subscription.to_dict()), 201
    except Exception as e:
        logging.error(f"Subscription registration error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# Serve frontend build for all non-API routes so the app is reachable
# via a single base URL (e.g. http://localhost:10000)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    # Do not intercept API requests
    if path.startswith('api'):
        return jsonify({'error': 'Not Found'}), 404

    build_dir = app.template_folder
    # If requested file exists in the build folder, serve it directly
    requested_path = os.path.join(build_dir, path)
    if path != '' and os.path.exists(requested_path):
        return send_from_directory(build_dir, path)

    # Fallback to index.html for client-side routing
    return send_from_directory(build_dir, 'index.html')