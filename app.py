from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash
)

from flask_sqlalchemy import SQLAlchemy
from flask import Response
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
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY',
    'local-development-key'
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

    mood_score = db.Column(
        db.Integer,
        nullable=False
    )

    content = db.Column(
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

    total_entries = len(entries)

    if total_entries:
        average_mood = round(
            sum(
                e.mood_score
                for e in entries
            ) / total_entries,
            1
        )
    else:
        average_mood = 0

    return render_template(
        'dashboard.html',
        entries=entries,
        total_entries=total_entries,
        average_mood=average_mood
    )

# --------------------------------------------------
# New Entry
# --------------------------------------------------

@app.route('/new-entry', methods=['GET', 'POST'])
@login_required
def new_entry():

    if request.method == 'POST':

        entry = Entry(
            mood_score=int(request.form['mood_score']),
            content=request.form['content'],
            user_id=current_user.id
        )

        db.session.add(entry)
        db.session.commit()

        flash('Journal entry saved.')

        return redirect(url_for('dashboard'))

    return render_template(
        'new_entry.html',
        now=datetime.now()
    )


# --------------------------------------------------
# Edit Entry
# --------------------------------------------------

@app.route('/edit-entry/<int:entry_id>',
           methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):

    entry = Entry.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first_or_404()

    if request.method == 'POST':

        entry.mood_score = int(
            request.form['mood_score']
        )

        entry.content = request.form['content']

        db.session.commit()

        flash('Entry updated.')

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
        Entry.content.ilike(
            f"%{query}%"
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
# Export to AI
# --------------------------------------------------

@app.route('/export-markdown')
@login_required
def export_markdown():

    entries = Entry.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Entry.created_at.asc()
    ).all()

    markdown = "# My Journal\n\n"

    for entry in entries:

        mood_text = {
            5: "😁 Great",
            4: "🙂 Good",
            3: "😐 Okay",
            2: "😔 Low",
            1: "😞 Struggling"
        }.get(entry.mood_score, "Unknown")

        markdown += f"""## {entry.created_at.strftime('%d %B %Y %H:%M')}

Mood: {mood_text}

{entry.content}

---

"""

    return Response(
        markdown,
        mimetype="text/markdown",
        headers={
            "Content-Disposition":
            "attachment; filename=journal.md"
        }
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