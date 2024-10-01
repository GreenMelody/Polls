from flask import Flask, request, render_template, url_for, jsonify, escape
import sqlite3
import hashlib
import uuid
from datetime import datetime, date
from pytz import timezone
import json
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Utility function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Utility function to generate unique poll ID
def generate_poll_id():
    return str(uuid.uuid4())

def update_visitor_count():
    conn = sqlite3.connect('app_data.db')
    cursor = conn.cursor()
    today = date.today().isoformat()

    # Update today's count
    cursor.execute('INSERT OR IGNORE INTO visits (date, count) VALUES (?, 0)', (today,))
    cursor.execute('UPDATE visits SET count = count + 1 WHERE date = ?', (today,))

    # Update total count
    cursor.execute('UPDATE total_visits SET total_count = total_count + 1')

    # Get today's and total counts
    cursor.execute('SELECT count FROM visits WHERE date = ?', (today,))
    today_count = cursor.fetchone()[0]
    cursor.execute('SELECT total_count FROM total_visits')
    total_count = cursor.fetchone()[0]

    conn.commit()
    conn.close()
    
    return today_count, total_count

# 유효성 검사 함수 (제어 문자, 특수 공백, 이모지 등을 필터링)
def is_valid_text(input_text):
    # 제어 문자, 특수 공백, 이모지 등을 필터링하는 정규 표현식
    control_char_regex = r'[\x00-\x1F\x7F\u200B-\u200D\uFEFF\u180E]'
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # 이모지 범위
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F700-\U0001F77F"
        "]+", flags=re.UNICODE)
    
    # 공백으로만 구성된 텍스트 또는 필터링해야 할 문자가 없는지 확인
    return not bool(re.search(control_char_regex, input_text.strip())) and not bool(emoji_pattern.search(input_text)) and bool(input_text.strip())

@app.route('/')
def index():
    today_count, total_count = update_visitor_count()
    return render_template('index.html', today_count=today_count, total_count=total_count)

@app.route('/create_poll', methods=['POST'])
def create_poll():
    title = escape(request.form.get('title'))  # XSS 방지를 위한 HTML 이스케이프 처리
    options = [escape(option) for option in request.form.getlist('options[]')]  # 옵션에 대해 이스케이프 처리
    password = request.form.get('password')
    end_date = request.form.get('end_date')

    # 제목 유효성 확인
    if not title or not is_valid_text(title):
        return jsonify({'success': False, 'message': 'Please provide a valid title for the poll.'})

    # 옵션 유효성 확인
    valid_options = [option for option in options if is_valid_text(option.strip())]
    if len(valid_options) < 2:
        return jsonify({'success': False, 'message': 'Please provide at least two valid options for the poll.'})

    try:
        end_date_dt = datetime.fromisoformat(end_date)
        if end_date_dt <= datetime.now():
            return jsonify({'success': False, 'message': 'End date must be in the future.'})
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format.'})

    poll_id = generate_poll_id()
    hashed_password = hash_password(password)

    # 한국 시간(KST)으로 생성 시각 설정
    kst = timezone('Asia/Seoul')
    created_at_kst = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')

    options_json = json.dumps(valid_options)

    conn = sqlite3.connect('app_data.db')  # 변경된 DB 경로
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO polls (id, title, options, password, end_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (poll_id, title, options_json, hashed_password, end_date, created_at_kst))
    conn.commit()
    conn.close()

    poll_link = url_for('view_poll', poll_id=poll_id, _external=True)
    return jsonify({'success': True, 'message': poll_link})

@app.route('/poll/<poll_id>', methods=['GET', 'POST'])
def view_poll(poll_id):
    conn = sqlite3.connect('app_data.db')
    cursor = conn.cursor()
    
    if request.method == 'GET':
        # Update poll visit count only on GET request
        cursor.execute('UPDATE polls SET visit_count = visit_count + 1 WHERE id = ?', (poll_id,))
    
    cursor.execute('SELECT title, options, end_date, created_at, visit_count FROM polls WHERE id = ?', (poll_id,))
    poll = cursor.fetchone()
    conn.commit()
    conn.close()

    if not poll:
        return render_template('error.html')

    title, options_str, end_date, created_at, poll_visit_count = poll
    options = json.loads(options_str)

    formatted_start_time = datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S')
    formatted_end_time = datetime.fromisoformat(end_date).strftime('%Y-%m-%d %H:%M:%S')

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        option_index = int(request.form.get('option'))
        conn = sqlite3.connect('app_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM votes WHERE user_id = ? AND poll_id = ?', (user_id, poll_id))
        vote_exists = cursor.fetchone()
        if vote_exists:
            conn.close()
            return jsonify({'success': False, 'message': 'You have already voted.'})
        else:
            cursor.execute('INSERT INTO votes (user_id, poll_id, option_index) VALUES (?, ?, ?)', (user_id, poll_id, option_index))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Vote recorded successfully!'})

    current_time = datetime.now()
    is_expired = current_time > datetime.fromisoformat(end_date)

    return render_template(
        'poll.html',
        title=escape(title),  # 제목 이스케이프 처리
        options=[escape(option) for option in options],  # 옵션에 대해 이스케이프 처리
        poll_id=escape(poll_id),  # poll_id 이스케이프 처리
        is_expired=is_expired,
        start_time=formatted_start_time,
        end_time=formatted_end_time,
        poll_visit_count=poll_visit_count
    )

@app.route('/preview/<poll_id>', methods=['GET'])
def preview_poll(poll_id):
    conn = sqlite3.connect('app_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT options FROM polls WHERE id = ?', (poll_id,))
    poll = cursor.fetchone()
    conn.close()

    if not poll:
        return jsonify({'success': False, 'message': 'Poll not found.'})

    options = json.loads(poll[0])

    conn = sqlite3.connect('app_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT option_index, COUNT(*) as vote_count
        FROM votes
        WHERE poll_id = ?
        GROUP BY option_index
    ''', (poll_id,))
    vote_results = cursor.fetchall()
    conn.close()

    results = [{'option_index': i, 'option_text': escape(options[i]), 'vote_count': vote[1]} for i, vote in enumerate(vote_results)]

    return jsonify(results)

@app.route('/delete_poll/<poll_id>', methods=['POST'])
def delete_poll(poll_id):
    data = request.json
    password = data.get('password')

    if not password or len(password) != 6 or not password.isdigit():
        return jsonify({'success': False, 'message': 'Invalid password format.'})

    conn = sqlite3.connect('app_data.db')
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

    conn = sqlite3.connect('app_data.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM votes WHERE poll_id = ?', (poll_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Poll deleted successfully.'})

@app.route('/polls')
def polls_list():
    return render_template('polls_list.html')

@app.route('/polls/filter', methods=['POST'])
def filter_polls():
    data = request.json
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    start_date_with_time = f"{start_date} 00:00:00"
    end_date_with_time = f"{end_date} 23:59:59"

    conn = sqlite3.connect('app_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, created_at, end_date, visit_count 
        FROM polls 
        WHERE created_at BETWEEN ? AND ?
        ORDER BY created_at DESC
    ''', (start_date_with_time, end_date_with_time))
    polls = cursor.fetchall()
    conn.close()

    formatted_polls = []
    for index, (poll_id, title, created_at, end_date, visit_count) in enumerate(polls, start=1):
        is_expired = datetime.now() > datetime.fromisoformat(end_date)
        formatted_polls.append({
            'index': index,
            'title': escape(title),  # 제목 이스케이프 처리
            'created_date': created_at,
            'end_date': datetime.fromisoformat(end_date).strftime('%Y-%m-%d'),
            'is_expired': 'Yes' if is_expired else 'No',
            'hits': visit_count,
            'link': url_for('view_poll', poll_id=poll_id, _external=True)
        })

    return jsonify(formatted_polls)

if __name__ == '__main__':
    app.run(debug=True)
