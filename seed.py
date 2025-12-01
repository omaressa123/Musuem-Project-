from app import app, db, Event

with app.app_context():
    db.create_all()

    if not Event.query.first(): # Only seed if no events exist
        events_data = [
            {'title': 'Ancient Wonders', 'description': 'A journey through the pyramids and ancient civilizations.', 'start_date': '2025-10-01', 'end_date': '2026-03-31'},
            {'title': 'Space Odyssey', 'description': 'Discover the mysteries of the cosmos and space travel.', 'start_date': '2025-11-15', 'end_date': '2026-05-30'},
            {'title': 'Modern Art', 'description': 'Contemporary masterpieces from the 21st century.', 'start_date': '2025-09-01', 'end_date': '2026-01-15'},
            {'title': 'Future Tech Expo', 'description': 'Explore the latest innovations in artificial intelligence and robotics.', 'start_date': '2026-02-10', 'end_date': '2026-06-30'},
            {'title': 'Wildlife Photography', 'description': 'Stunning photographs capturing the beauty of nature.', 'start_date': '2026-04-01', 'end_date': '2026-09-30'}
        ]

        for data in events_data:
            event = Event(title=data['title'], description=data['description'], start_date=data['start_date'], end_date=data['end_date'])
            db.session.add(event)
        
        db.session.commit()
        print("Database seeded with initial events!")
    else:
        print("Database already contains events, skipping seeding.")
