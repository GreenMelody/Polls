from flask import Flask, request, render_template, url_for, jsonify
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
        return jsonify({'success': False, 'message': 'Please provide a title for the poll.'})

    if len([option for option in options if option.strip()]) < 2:
        return jsonify({'success': False, 'message': 'Please provide at least two options for the poll.'})

    try:
        end_date_dt = datetime.fromisoformat(end_date)
        if end_date_dt <= datetime.now():
            return jsonify({'success': False, 'message': 'End date must be in the future.'})
    except ValueError:
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
    return jsonify({'success': True, 'message': poll_link})

@app.route('/poll/<poll_id>', methods=['GET', 'POST'])
def view_poll(poll_id):
    conn = sqlite3.connect('polls.db')
    cursor = conn.cursor()
    cursor.execute('SELECT title, options, end_date, created_at FROM polls WHERE id = ?', (poll_id,))
    poll = cursor.fetchone()
    conn.close()

    if not poll:
        return render_template('error.html')  # Render error page instead of JSON response

    title, options, end_date, created_at = poll
    options = eval(options)

    # Format dates for display
    formatted_start_time = datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S')
    formatted_end_time = datetime.fromisoformat(end_date).strftime('%Y-%m-%d %H:%M:00')

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        option_index = int(request.form.get('option'))

        conn = sqlite3.connect('poll-result.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM votes WHERE user_id = ? AND poll_id = ?', (user_id, poll_id))
        vote_exists = cursor.fetchone()

        if vote_exists:
            conn.close()
            return jsonify({'success': False, 'message': 'You have already voted.'})
        else:
            cursor.execute('INSERT INTO votes (user_id, poll_id, option_index) VALUES (?, ?, ?)',
                           (user_id, poll_id, option_index))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Vote recorded successfully!'})

    current_time = datetime.now()
    is_expired = current_time > datetime.fromisoformat(end_date)

    return render_template(
        'poll.html',
        title=title,
        options=options,
        poll_id=poll_id,
        is_expired=is_expired,
        start_time=formatted_start_time,
        end_time=formatted_end_time
    )

@app.route('/preview/<poll_id>', methods=['GET'])
def preview_poll(poll_id):
    conn = sqlite3.connect('polls.db')
    cursor = conn.cursor()
    cursor.execute('SELECT options FROM polls WHERE id = ?', (poll_id,))
    poll = cursor.fetchone()
    conn.close()

    if not poll:
        return jsonify({'success': False, 'message': 'Poll not found.'})

    options = eval(poll[0])

    conn = sqlite3.connect('poll-result.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT option_index, COUNT(*) as vote_count
        FROM votes
        WHERE poll_id = ?
        GROUP BY option_index
    ''', (poll_id,))
    vote_results = cursor.fetchall()
    conn.close()

    results = [{'option_index': i, 'option_text': options[i], 'vote_count': 0} for i in range(len(options))]
    for vote in vote_results:
        results[vote[0]]['vote_count'] = vote[1]

    return jsonify(results)

@app.route('/delete_poll/<poll_id>', methods=['POST'])
def delete_poll(poll_id):
    data = request.json
    password = data.get('password')

    if not password or len(password) != 6 or not password.isdigit():
        return jsonify({'success': False, 'message': 'Invalid password format.'})

    conn = sqlite3.connect('polls.db')
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM polls WHERE id = ?', (poll_id,))
    poll = cursor.fetchone()

    if not poll:
        conn.close()
        return jsonify({'success': False, 'message': 'Poll not found.'})

    hashed_password = poll[0]

    if hash_password(password) != hashed_password:
        conn.close()
        return jsonify({'success': False, 'message': 'Incorrect password.'})

    cursor.execute('DELETE FROM polls WHERE id = ?', (poll_id,))
    conn.commit()
    conn.close()

    conn = sqlite3.connect('poll-result.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM votes WHERE poll_id = ?', (poll_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Poll deleted successfully.'})

if __name__ == '__main__':
    app.run(debug=True)
