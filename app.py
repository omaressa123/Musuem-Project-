from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'museum.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(20))
    password_hash = db.Column(db.String(200), nullable=False) # Increased length for hashed passwords

    def __repr__(self):
        return f'<Visitor {self.email}>'

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.String(100), nullable=False) # Storing as string for simplicity
    end_date = db.Column(db.String(100), nullable=False)   # Storing as string for simplicity

    def __repr__(self):
        return f'<Event {self.title}>'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey('visitor.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.String(100), nullable=False)
    order_status = db.Column(db.String(50), default='Pending') # e.g., Pending, Confirmed, Cancelled

    visitor = db.relationship('Visitor', backref=db.backref('orders', lazy=True))

    def __repr__(self):
        return f'<Order {self.id}>'

class ETicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code = db.Column(db.String(200), unique=True, nullable=False)
    visit_date = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='Valid') # e.g., Valid, Used
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)

    event = db.relationship('Event', backref=db.backref('e_tickets', lazy=True))
    order = db.relationship('Order', backref=db.backref('e_tickets', lazy=True))

    def __repr__(self):
        return f'<ETicket {self.id}>'

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(50), default='Pending') # e.g., Pending, Completed, Failed
    bank = db.Column(db.String(100))
    card_number = db.Column(db.String(100)) # In a real app, this would be tokenized/last 4 digits

    order = db.relationship('Order', backref=db.backref('payment', uselist=False))

    def __repr__(self):
        return f'<Payment {self.id}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey('visitor.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id')) # Optional: notification might not be event-specific
    message = db.Column(db.Text, nullable=False)
    create_date = db.Column(db.String(100), nullable=False)

    visitor = db.relationship('Visitor', backref=db.backref('notifications', lazy=True))
    event = db.relationship('Event', backref=db.backref('notifications', lazy=True))

    def __repr__(self):
        return f'<Notification {self.id}>'

@app.route('/')
def index():
    return render_template('musuemwebsite.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    phone_number = data.get('phone_number')
    password = data.get('password')

    if not all([first_name, last_name, email, password]):
        return jsonify({'error': 'Please fill in all required fields (First Name, Last Name, Email, Password)'}), 400

    if Visitor.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    hashed_password = generate_password_hash(password, method='sha256')

    new_visitor = Visitor(first_name=first_name, last_name=last_name, email=email, phone_number=phone_number, password_hash=hashed_password)
    db.session.add(new_visitor)
    db.session.commit()

    return jsonify({'message': 'Visitor registered successfully!'}), 201

@app.route('/events', methods=['GET'])
def get_events():
    events = Event.query.all()
    events_list = []
    for event in events:
        events_list.append({
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'start_date': event.start_date,
            'end_date': event.end_date
        })
    return jsonify(events_list), 200

@app.route('/order', methods=['POST'])
def create_order():
    data = request.get_json()
    visitor_id = data.get('visitor_id')
    event_id = data.get('event_id')
    visit_date = data.get('visit_date')
    adult_tickets = data.get('adult_tickets', 0)
    child_tickets = data.get('child_tickets', 0)
    senior_tickets = data.get('senior_tickets', 0)
    total_price = data.get('total_price')

    if not all([visitor_id, event_id, visit_date, total_price is not None]):
        return jsonify({'error': 'Missing required order data'}), 400
    
    visitor = Visitor.query.get(visitor_id)
    event = Event.query.get(event_id)
    if not visitor or not event:
        return jsonify({'error': 'Visitor or Event not found'}), 404

    new_order = Order(
        visitor_id=visitor_id,
        total_amount=total_price,
        order_date=visit_date, # Using visit_date as order_date for simplicity
        order_status='Pending'
    )
    db.session.add(new_order)
    db.session.commit()

    # Generate E-Tickets for each ticket type
    tickets_to_generate = []
    for _ in range(adult_tickets):
        tickets_to_generate.append({'type': 'adult'})
    for _ in range(child_tickets):
        tickets_to_generate.append({'type': 'child'})
    for _ in range(senior_tickets):
        tickets_to_generate.append({'type': 'senior'})

    for ticket_info in tickets_to_generate:
        # In a real application, a unique QR code would be generated
        qr_code = f"QR_{new_order.id}_{event.id}_{ticket_info['type']}_{db.session.query(ETicket).count() + 1}"
        new_eticket = ETicket(
            qr_code=qr_code,
            visit_date=visit_date,
            status='Valid',
            event_id=event_id,
            order_id=new_order.id
        )
        db.session.add(new_eticket)
    db.session.commit()

    # Placeholder for Payment creation (assuming payment is handled externally or confirmed later)
    # new_payment = Payment(order_id=new_order.id, amount=total_price, payment_status='Pending')
    # db.session.add(new_payment)
    # db.session.commit()

    return jsonify({'message': 'Order created successfully!', 'order_id': new_order.id}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Please enter both email and password'}), 400

    visitor = Visitor.query.filter_by(email=email).first()

    if visitor and check_password_hash(visitor.password_hash, password):
        return jsonify({'message': 'Login successful!', 'visitor_id': visitor.id, 'first_name': visitor.first_name, 'last_name': visitor.last_name, 'email': visitor.email}), 200
    else:
        return jsonify({'error': 'Invalid email or password'}), 401

@app.route('/visitor/<int:visitor_id>/orders', methods=['GET'])
def get_visitor_orders(visitor_id):
    visitor = Visitor.query.get(visitor_id)
    if not visitor:
        return jsonify({'error': 'Visitor not found'}), 404

    orders = Order.query.filter_by(visitor_id=visitor_id).all()
    orders_list = []
    for order in orders:
        e_tickets = ETicket.query.filter_by(order_id=order.id).all()
        e_tickets_list = []
        for ticket in e_tickets:
            event = Event.query.get(ticket.event_id)
            e_tickets_list.append({
                'ticket_id': ticket.id,
                'qr_code': ticket.qr_code,
                'visit_date': ticket.visit_date,
                'status': ticket.status,
                'event_title': event.title if event else 'Unknown Event'
            })
        orders_list.append({
            'order_id': order.id,
            'total_amount': order.total_amount,
            'order_date': order.order_date,
            'order_status': order.order_status,
            'e_tickets': e_tickets_list
        })
    return jsonify(orders_list), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create database tables
    app.run(debug=True)
