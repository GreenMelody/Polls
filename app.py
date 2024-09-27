# app.py
from flask import Flask, request, render_template, redirect, url_for, jsonify, flash
import sqlite3
import hashlib
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Utility function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Utility function to generate unique poll ID
def generate_poll_id():
    return str(uuid.uuid4())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_poll', methods=['POST'])
def create_poll():
    title = request.form.get('title')
    options = request.form.getlist('options[]')
    password = request.form.get('password')
    end_date = request.form.get('end_date')

    # Validate input values
    if not title:
        flash('Please provide a title for the poll.', 'danger')
        return jsonify({'success': False, 'message': 'Please provide a title for the poll.'})

    if len([option for option in options if option.strip()]) < 2:
        flash('Please provide at least two options for the poll.', 'danger')
        return jsonify({'success': False, 'message': 'Please provide at least two options for the poll.'})

    try:
        end_date_dt = datetime.fromisoformat(end_date)
        if end_date_dt <= datetime.now():
            flash('End date must be in the future.', 'danger')
            return jsonify({'success': False, 'message': 'End date must be in the future.'})
    except ValueError:
        flash('Invalid date format.', 'danger')
        return jsonify({'success': False, 'message': 'Invalid date format.'})

    poll_id = generate_poll_id()
    hashed_password = hash_password(password)

    # Store poll in database
    conn = sqlite3.connect('polls.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO polls (id, title, options, password, end_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (poll_id, title, str(options), hashed_password, end_date))
    conn.commit()
    conn.close()

    # Return poll link
    poll_link = url_for('view_poll', poll_id=poll_id, _external=True)
    flash(f'Poll created! Share this link: {poll_link}', 'success')
    return jsonify({'success': True, 'message': f'{poll_link}'})

@app.route('/poll/<poll_id>', methods=['GET', 'POST'])
def view_poll(poll_id):
    conn = sqlite3.connect('polls.db')
    cursor = conn.cursor()
    cursor.execute('SELECT title, options, end_date FROM polls WHERE id = ?', (poll_id,))
    poll = cursor.fetchone()
    conn.close()

    if not poll:
        flash('Poll not found', 'danger')
        return redirect(url_for('index'))

    title, options, end_date = poll
    options = eval(options)

    if request.method == 'POST':
        user_id = request.form.get('user_id')  # Assuming fingerprintJs ID is sent
        option_index = int(request.form.get('option'))

        conn = sqlite3.connect('poll-result.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM votes WHERE user_id = ? AND poll_id = ?', (user_id, poll_id))
        vote_exists = cursor.fetchone()

        if vote_exists:
            flash('You have already voted', 'warning')
        else:
            cursor.execute('INSERT INTO votes (user_id, poll_id, option_index) VALUES (?, ?, ?)',
                           (user_id, poll_id, option_index))
            conn.commit()
            flash('Vote recorded!', 'success')

        conn.close()
        return redirect(url_for('view_poll', poll_id=poll_id))

    current_time = datetime.now()
    is_expired = current_time > datetime.fromisoformat(end_date)

    return render_template('poll.html', title=title, options=options, poll_id=poll_id, is_expired=is_expired)

@app.route('/preview/<poll_id>', methods=['GET'])
def preview_poll(poll_id):
    conn = sqlite3.connect('poll-result.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT option_index, COUNT(*) as vote_count 
        FROM votes 
        WHERE poll_id = ? 
        GROUP BY option_index
    ''', (poll_id,))
    results = cursor.fetchall()
    conn.close()

    return jsonify([{'option_index': row[0], 'vote_count': row[1]} for row in results])

if __name__ == '__main__':
    app.run(debug=True)
