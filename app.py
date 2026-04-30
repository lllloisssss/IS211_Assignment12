from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'IS211_secret_key'

DATABASE = 'hw13.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and load seed data from schema.sql."""
    conn = get_db()
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def login_required(f):
    """Decorator to redirect to login if not authenticated."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ── Login / Logout ──

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'password':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Dashboard ───

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    students = conn.execute('SELECT * FROM students ORDER BY last_name, first_name').fetchall()
    quizzes  = conn.execute('SELECT * FROM quizzes ORDER BY quiz_date DESC').fetchall()
    conn.close()
    return render_template('dashboard.html', students=students, quizzes=quizzes)


# ── Students ────

@app.route('/student/add', methods=['GET', 'POST'])
@login_required
def add_student():
    error = None
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name  = request.form.get('last_name', '').strip()
        if not first_name or not last_name:
            error = 'Both first name and last name are required.'
        else:
            conn = get_db()
            conn.execute('INSERT INTO students (first_name, last_name) VALUES (?, ?)',
                         (first_name, last_name))
            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))
    return render_template('add_student.html', error=error)


@app.route('/student/<int:student_id>')
@login_required
def student_results(student_id):
    conn = get_db()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    if not student:
        return redirect(url_for('dashboard'))
    results = conn.execute('''
        SELECT r.score, q.id AS quiz_id, q.subject, q.quiz_date
        FROM results r
        JOIN quizzes q ON r.quiz_id = q.id
        WHERE r.student_id = ?
        ORDER BY q.quiz_date
    ''', (student_id,)).fetchall()
    conn.close()
    return render_template('student_results.html', student=student, results=results)


# ── Quizzes ────

@app.route('/quiz/add', methods=['GET', 'POST'])
@login_required
def add_quiz():
    error = None
    if request.method == 'POST':
        subject       = request.form.get('subject', '').strip()
        num_questions = request.form.get('num_questions', '').strip()
        quiz_date     = request.form.get('quiz_date', '').strip()
        if not subject or not num_questions or not quiz_date:
            error = 'All fields are required.'
        else:
            try:
                num_questions = int(num_questions)
                if num_questions <= 0:
                    raise ValueError
            except ValueError:
                error = 'Number of questions must be a positive integer.'
            if not error:
                conn = get_db()
                conn.execute('INSERT INTO quizzes (subject, num_questions, quiz_date) VALUES (?, ?, ?)',
                             (subject, num_questions, quiz_date))
                conn.commit()
                conn.close()
                return redirect(url_for('dashboard'))
    return render_template('add_quiz.html', error=error)


# ── Results ───

@app.route('/results/add', methods=['GET', 'POST'])
@login_required
def add_result():
    conn = get_db()
    students = conn.execute('SELECT * FROM students ORDER BY last_name, first_name').fetchall()
    quizzes  = conn.execute('SELECT * FROM quizzes ORDER BY quiz_date DESC').fetchall()
    error = None

    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        quiz_id    = request.form.get('quiz_id', '').strip()
        score      = request.form.get('score', '').strip()
        if not student_id or not quiz_id or not score:
            error = 'All fields are required.'
        else:
            try:
                score = int(score)
                if not (0 <= score <= 100):
                    raise ValueError
            except ValueError:
                error = 'Score must be a whole number between 0 and 100.'
            if not error:
                conn.execute('INSERT INTO results (student_id, quiz_id, score) VALUES (?, ?, ?)',
                             (student_id, quiz_id, score))
                conn.commit()
                conn.close()
                return redirect(url_for('dashboard'))

    conn.close()
    return render_template('add_result.html', students=students, quizzes=quizzes, error=error)


if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
