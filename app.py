import os
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, request, render_template, url_for, jsonify, escape
import sqlite3
import hashlib
import uuid
from datetime import datetime, date, timedelta
from pytz import timezone
import json
import re
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import atexit
import subprocess

app = Flask(__name__)

dotenv_path = os.path.abspath(os.path.join('sharedworkspace/','.env'))
load_dotenv(dotenv_path)

app.secret_key = os.getenv('SECRET_KEY')

app_db_path = os.getenv('DB_PATH')
app_db_file = os.getenv('DB_FILE')

app_db_file_path = os.path.join(app_db_path, app_db_file)

# Utility function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Utility function to generate unique poll ID
def generate_poll_id():
    return str(uuid.uuid4())

def update_visitor_count():
    conn = sqlite3.connect(app_db_file_path)
    cursor = conn.cursor()
    today = date.today().isoformat()

    cursor.execute('INSERT OR IGNORE INTO visits (date, count) VALUES (?, 0)', (today,))
    cursor.execute('UPDATE visits SET count = count + 1 WHERE date = ?', (today,))

    cursor.execute('UPDATE total_visits SET total_count = total_count + 1')
    cursor.execute('SELECT count FROM visits WHERE date = ?', (today,))
    today_count = cursor.fetchone()[0]
    cursor.execute('SELECT total_count FROM total_visits')
    total_count = cursor.fetchone()[0]
    cursor.execute('SELECT total_polls FROM polls_count')
    total_polls = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    app.logger.debug(f"Visitor counts updated: Today: {today_count}, Total: {total_count}, Total Polls: {total_polls}")
    
    return today_count, total_count, total_polls

# 유효성 검사 함수
def is_valid_text(input_text):
    control_char_regex = r'[\x00-\x1F\x7F\u200B-\u200D\uFEFF\u180E\u3164]'
    if len(input_text.strip()) > 300:
        app.logger.warning(f"Invalid input length: {len(input_text.strip())}")
        return False
    return not bool(re.search(control_char_regex, input_text.strip())) and bool(input_text.strip())

@app.route('/')
def index():
    today_count, total_count, total_polls = update_visitor_count()
    return render_template('index.html', today_count=today_count, total_count=total_count, total_polls=total_polls)

@app.route('/create_poll', methods=['POST'])
def create_poll():
    title = escape(request.form.get('title'))
    options = [escape(option) for option in request.form.getlist('options[]')]
    password = request.form.get('password')
    end_date = request.form.get('end_date')

    if not title or not is_valid_text(title):
        app.logger.error("Invalid poll title or options.")
        return jsonify({'success': False, 'message': 'Please provide a valid title for the poll (maximum 300 characters).'})

    valid_options = [option for option in options if is_valid_text(option.strip())]
    if len(valid_options) < 2:
        app.logger.error("Insufficient valid options provided.")
        return jsonify({'success': False, 'message': 'Please provide at least two valid options (maximum 300 characters).'})

    try:
        end_date_dt = datetime.fromisoformat(end_date)
        if end_date_dt <= datetime.now():
            app.logger.error("Invalid end date provided.")
            return jsonify({'success': False, 'message': 'End date must be in the future.'})
    except ValueError:
        app.logger.error("Invalid date format.")
        return jsonify({'success': False, 'message': 'Invalid date format.'})

    poll_id = generate_poll_id()
    hashed_password = hash_password(password)

    kst = timezone('Asia/Seoul')
    created_at_kst = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')

    options_json = json.dumps(valid_options)

    conn = sqlite3.connect(app_db_file_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO polls (id, title, options, password, end_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (poll_id, title, options_json, hashed_password, end_date, created_at_kst))

    cursor.execute('UPDATE polls_count SET total_polls = total_polls + 1')

    conn.commit()
    conn.close()

    app.logger.info(f"Poll created: ID={poll_id}, Title={title}")
    
    poll_link = url_for('view_poll', poll_id=poll_id, _external=True)
    return jsonify({'success': True, 'message': poll_link})

@app.route('/poll/<poll_id>', methods=['GET', 'POST'])
def view_poll(poll_id):
    conn = sqlite3.connect(app_db_file_path)
    cursor = conn.cursor()

    if request.method == 'GET':
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
        current_time = datetime.now()
        is_expired = current_time > datetime.fromisoformat(end_date)

        return render_template(
            'poll.html',
            title=escape(title),
            options=[escape(option) for option in options],
            poll_id=escape(poll_id),
            is_expired=is_expired,
            start_time=formatted_start_time,
            end_time=formatted_end_time,
            poll_visit_count=poll_visit_count
        )

    elif request.method == 'POST':
        user_id = request.form.get('user_id')
        option_index = int(request.form.get('option'))
        
        # 만료된 투표에 대한 처리
        cursor.execute('SELECT end_date FROM polls WHERE id = ?', (poll_id,))
        end_date = cursor.fetchone()[0]
        is_expired = datetime.now() > datetime.fromisoformat(end_date)
        
        if is_expired:
            return jsonify({'success': False, 'reason': 'expired', 'message': 'This poll has already expired.'})

        # 투표를 갱신하도록 수정
        cursor.execute('SELECT * FROM votes WHERE user_id = ? AND poll_id = ?', (user_id, poll_id))
        vote_exists = cursor.fetchone()
        
        if vote_exists:
            # 이미 투표한 경우, 기존 투표를 업데이트
            cursor.execute('UPDATE votes SET option_index = ? WHERE user_id = ? AND poll_id = ?', (option_index, user_id, poll_id))
        else:
            # 투표가 없으면 새로 추가
            cursor.execute('INSERT INTO votes (user_id, poll_id, option_index) VALUES (?, ?, ?)', (user_id, poll_id, option_index))
        
        conn.commit()
        conn.close()

        app.logger.info(f"Vote recorded successfully. Poll ID: {poll_id}, User ID: {user_id}, Option: {option_index}")
        return jsonify({'success': True, 'message': 'Vote recorded successfully!'})

@app.route('/poll/<poll_id>/user_vote', methods=['GET'])
def get_user_vote(poll_id):
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID not provided'}), 400

    conn = sqlite3.connect(app_db_file_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT option_index FROM votes WHERE user_id = ? AND poll_id = ?', (user_id, poll_id))
    user_vote = cursor.fetchone()
    conn.close()
    
    user_vote = user_vote[0] if user_vote else None

    return jsonify({'user_vote': user_vote})

@app.route('/preview/<poll_id>', methods=['GET'])
def preview_poll(poll_id):
    conn = sqlite3.connect(app_db_file_path)
    cursor = conn.cursor()
    cursor.execute('SELECT options FROM polls WHERE id = ?', (poll_id,))
    poll = cursor.fetchone()
    conn.close()

    if not poll:
        return jsonify({'success': False, 'message': 'Poll not found.'})

    options = json.loads(poll[0])

    conn = sqlite3.connect(app_db_file_path)
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

    conn = sqlite3.connect(app_db_file_path)
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

    conn = sqlite3.connect(app_db_file_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM votes WHERE poll_id = ?', (poll_id,))
    conn.commit()
    conn.close()

    app.logger.info(f"Poll deleted: ID={poll_id}")
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

    conn = sqlite3.connect(app_db_file_path)
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
            'title': escape(title),
            'created_date': created_at,
            'end_date': datetime.fromisoformat(end_date).strftime('%Y-%m-%d'),
            'is_expired': 'Yes' if is_expired else 'No',
            'hits': visit_count,
            'link': url_for('view_poll', poll_id=poll_id, _external=True)
        })

    return jsonify(formatted_polls)

# 매일 새벽 3시에 만료된 투표와 관련된 데이터 삭제
def delete_expired_polls():
    conn = sqlite3.connect(app_db_file_path)
    cursor = conn.cursor()

    threshold_date = (datetime.now() - timedelta(days=15)).isoformat()

    cursor.execute('SELECT id FROM polls WHERE end_date < ?', (threshold_date,))
    expired_polls = cursor.fetchall()

    for poll_id in expired_polls:
        poll_id = poll_id[0]
        cursor.execute('DELETE FROM polls WHERE id = ?', (poll_id,))
        cursor.execute('DELETE FROM votes WHERE poll_id = ?', (poll_id,))
    
    conn.commit()
    conn.close()

    app.logger.info(f"Deleted expired polls older than {threshold_date}")

# 스케줄러 설정
scheduler = BackgroundScheduler(timezone="Asia/Seoul")
# scheduler.add_job(func=delete_expired_polls, trigger='cron', hour=3, minute=0)
# scheduler.start()

@app.route('/scheduler/jobs', methods=['GET'])
def get_scheduled_jobs():
    jobs_info = []
    try:
        jobs = scheduler.get_jobs()
        for job in jobs:
            jobs_info.append({
                'id': job.id,
                'next_run_time': str(job.next_run_time),
                'trigger': str(job.trigger)
            })
        app.logger.info("Fetched scheduler jobs.")
    except Exception as e:
        jobs_info.append({
                'Exception Error': str(e)
            })
    return jsonify(jobs_info)

@app.before_first_request
def initialize_scheduler():
    if not scheduler.running:
        scheduler.start()
    atexit.register(lambda: scheduler.shutdown() if scheduler.running else None)

if __name__ == '__main__':
    app.run(debug=True)
