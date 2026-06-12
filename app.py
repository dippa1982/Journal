from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash
)

from flask_sqlalchemy import SQLAlchemy
from collections import Counter
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from datetime import datetime
import os


# --------------------------------------------------
# App Setup
# --------------------------------------------------

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///journal.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# --------------------------------------------------
# Models
# --------------------------------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    entries = db.relationship(
        'Entry',
        backref='author',
        lazy=True
    )

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(200),
        nullable=False
    )

    mood_score = db.Column(
        db.Integer,
        nullable=False
    )

    strongest_emotion = db.Column(
        db.String(100),
        nullable=False
    )

    emotional_event = db.Column(
        db.Text,
        nullable=False
    )

    personal_story = db.Column(
        db.Text,
        nullable=False
    )

    evidence = db.Column(
        db.Text,
        nullable=False
    )

    tomorrow_focus = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

# --------------------------------------------------
# Debug
# --------------------------------------------------

@app.route('/debug-db')
def debug_db():
    return str(db.engine.url)

# --------------------------------------------------
# Flask Login
# --------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    return redirect(url_for('login'))


# --------------------------------------------------
# Register
# --------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:
            flash('Username already exists.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        user = User(
            username=username,
            password_hash=hashed_password
        )

        db.session.add(user)
        db.session.commit()

        flash('Account created successfully.')

        return redirect(url_for('login'))

    return render_template('register.html')


# --------------------------------------------------
# Login
# --------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password_hash,
            password
        ):

            login_user(user)

            return redirect(url_for('dashboard'))

        flash('Invalid username or password.')

    return render_template('login.html')


# --------------------------------------------------
# Logout
# --------------------------------------------------

@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect(url_for('login'))


# --------------------------------------------------
# Dashboard
# --------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():

    entries = Entry.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Entry.created_at.desc()
    ).all()

    emotion_counter = Counter()

    for entry in entries:
        emotion_counter[entry.strongest_emotion] += 1

    top_emotions = emotion_counter.most_common(5)

    total_entries = len(entries)

    if total_entries > 0:
        average_mood = round(
            sum(entry.mood_score for entry in entries)
            / total_entries,
            1
        )
    else:
        average_mood = 0

    return render_template(
    'dashboard.html',
    entries=entries,
    total_entries=total_entries,
    average_mood=average_mood,
    top_emotions=top_emotions
)


# --------------------------------------------------
# New Entry
# --------------------------------------------------

@app.route('/new-entry', methods=['GET', 'POST'])
@login_required
def new_entry():

    if request.method == 'POST':

        entry = Entry(
            title=request.form['title'],
            mood_score=request.form['mood_score'],
            strongest_emotion=request.form['strongest_emotion'],
            emotional_event=request.form['emotional_event'],
            personal_story=request.form['personal_story'],
            evidence=request.form['evidence'],
            tomorrow_focus=request.form['tomorrow_focus'],
            user_id=current_user.id
        )

        db.session.add(entry)
        db.session.commit()

        flash('Journal entry saved.')

        return redirect(url_for('dashboard'))

    return render_template('new_entry.html')


# --------------------------------------------------
# Edit Entry
# --------------------------------------------------
@app.route('/edit-entry/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):

    entry = Entry.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first_or_404()

    if request.method == 'POST':

        entry.title = request.form['title']
        entry.mood_score = request.form['mood_score']
        entry.strongest_emotion = request.form['strongest_emotion']
        entry.emotional_event = request.form['emotional_event']
        entry.personal_story = request.form['personal_story']
        entry.evidence = request.form['evidence']
        entry.tomorrow_focus = request.form['tomorrow_focus']

        db.session.commit()

        flash('Entry updated successfully.')

        return redirect(
            url_for(
                'view_entry',
                entry_id=entry.id
            )
        )

    return render_template(
        'edit_entry.html',
        entry=entry
    )

# --------------------------------------------------
# View Entry
# --------------------------------------------------

@app.route('/entry/<int:entry_id>')
@login_required
def view_entry(entry_id):

    entry = Entry.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first_or_404()

    return render_template(
        'view_entry.html',
        entry=entry
    )


# --------------------------------------------------
# Delete Entry
# --------------------------------------------------

@app.route('/delete-entry/<int:entry_id>')
@login_required
def delete_entry(entry_id):

    entry = Entry.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(entry)
    db.session.commit()

    flash('Entry deleted.')

    return redirect(url_for('dashboard'))

# --------------------------------------------------
# Search Entry
# --------------------------------------------------

@app.route('/search')
@login_required
def search():

    query = request.args.get('q', '')

    entries = Entry.query.filter(
    Entry.user_id == current_user.id,
    (
        Entry.title.ilike(f"%{query}%") |
        Entry.emotional_event.ilike(f"%{query}%") |
        Entry.personal_story.ilike(f"%{query}%") |
        Entry.evidence.ilike(f"%{query}%") |
        Entry.tomorrow_focus.ilike(f"%{query}%")
    )
    ).order_by(
        Entry.created_at.desc()
    ).all()

    return render_template(
        'search_results.html',
        entries=entries,
        query=query
    )

# --------------------------------------------------
# Monthly Review
# --------------------------------------------------

@app.route('/review')
@login_required
def review():

    entries = Entry.query.filter_by(
        user_id=current_user.id
    ).all()

    total_entries = len(entries)

    if total_entries:
        average_mood = round(
            sum(e.mood_score for e in entries)
            / total_entries,
            1
        )
    else:
        average_mood = 0

    emotion_counter = Counter(
        e.strongest_emotion
        for e in entries
    )

    return render_template(
        'review.html',
        total_entries=total_entries,
        average_mood=average_mood,
        emotions=emotion_counter.most_common()
    )
# --------------------------------------------------
# Create Database
# --------------------------------------------------

with app.app_context():
    db.create_all()


# --------------------------------------------------
# Run App
# --------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)