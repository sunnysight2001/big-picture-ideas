from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import json
import os
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
 
app = Flask(__name__)
<<<<<<< HEAD
app.secret_key = 'your-secret-key-change-this-in-production'

# Database setup
DATABASE = 'stats.db'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database with stats table"""
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS idea_stats (
                id TEXT PRIMARY KEY,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

=======
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this!
 
>>>>>>> d7ce6b0bcc1b8aba7ddee40cd02e1b068091a531
# Load ideas from JSON
def load_ideas():
    json_path = os.path.join('data', 'ideas.json')
    with open(json_path, 'r', encoding='utf-8') as f:
<<<<<<< HEAD
        ideas = json.load(f)
    
    # Merge with database stats
    db = get_db()
    for idea in ideas:
        cursor = db.execute('SELECT views, likes, shares FROM idea_stats WHERE id = ?', (idea['id'],))
        stats = cursor.fetchone()
        
        if stats:
            idea['views'] = stats['views']
            idea['likes'] = stats['likes']
            idea['shares'] = stats['shares'] if stats['shares'] else 0
        else:
            # Initialize stats in database
            db.execute(
                'INSERT OR IGNORE INTO idea_stats (id, views, likes, shares) VALUES (?, 0, 0, 0)',
                (idea['id'],)
            )
            db.commit()
            idea['views'] = 0
            idea['likes'] = 0
            idea['shares'] = 0
    
    return ideas

=======
        return json.load(f)
 
# Save ideas to JSON
def save_ideas(ideas):
    json_path = os.path.join('data', 'ideas.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(ideas, f, indent=2, ensure_ascii=False)
 
>>>>>>> d7ce6b0bcc1b8aba7ddee40cd02e1b068091a531
# Get a single idea by ID
def get_idea_by_id(idea_id):
    ideas = load_ideas()
    for idea in ideas:
        if idea['id'] == idea_id:
            return idea
    return None
 
# HOME PAGE
@app.route('/')
def index():
    ideas = load_ideas()
    
    # Get unique themes/categories
    themes = set()
    for idea in ideas:
        if 'category' in idea:
            themes.update(idea['category'])
    
    # Get today's idea - rotates daily
    import datetime
    today = datetime.date.today()
<<<<<<< HEAD
    day_of_year = today.timetuple().tm_yday
    todays_idea_index = day_of_year % len(ideas)
=======
    day_of_year = today.timetuple().tm_yday  # Day number (1-365)
    todays_idea_index = day_of_year % len(ideas)  # Cycles through all ideas
>>>>>>> d7ce6b0bcc1b8aba7ddee40cd02e1b068091a531
    todays_idea = ideas[todays_idea_index] if ideas else None
    
    # Limit to 4 themes and 4 ideas for homepage
    limited_themes = sorted(themes)[:4]
    limited_ideas = ideas[:4]
    
    return render_template(
        'index.html',
        ideas=limited_ideas,
        themes=limited_themes,
        todays_idea=todays_idea
    )
 
# INDIVIDUAL IDEA PAGE (with view tracking)
@app.route('/idea/<idea_id>')
def idea_detail(idea_id):
    ideas = load_ideas()
    idea = get_idea_by_id(idea_id)
    
    if not idea:
        return "Idea not found", 404
    
    # Increment view count in database
    db = get_db()
    db.execute('UPDATE idea_stats SET views = views + 1, updated_at = ? WHERE id = ?',
               (datetime.now(), idea_id))
    db.commit()
    
    # Get updated stats
    cursor = db.execute('SELECT views FROM idea_stats WHERE id = ?', (idea_id,))
    stats = cursor.fetchone()
    if stats:
        idea['views'] = stats['views']
    
    # Find next idea (circular navigation)
    current_index = next((i for i, x in enumerate(ideas) if x['id'] == idea_id), None)
    next_idea = ideas[(current_index + 1) % len(ideas)] if current_index is not None else None
    
    return render_template('idea.html', idea=idea, next_idea=next_idea)
<<<<<<< HEAD

# THEME PAGE
=======
 
# THEME PAGE (optional)
>>>>>>> d7ce6b0bcc1b8aba7ddee40cd02e1b068091a531
@app.route('/theme/<theme_name>')
def theme_page(theme_name):
    ideas = load_ideas()
    filtered_ideas = [
        idea for idea in ideas
        if 'category' in idea and theme_name in idea['category']
    ]
    
    return render_template(
        'theme.html',
        theme=theme_name,
        ideas=filtered_ideas
    )
 
# ALL IDEAS PAGE
@app.route('/ideas')
def all_ideas():
    ideas = load_ideas()
    return render_template('all_ideas.html', ideas=ideas)
 
# ALL THEMES PAGE
@app.route('/themes')
def all_themes():
    ideas = load_ideas()
    
    themes = set()
    for idea in ideas:
        if 'category' in idea:
            themes.update(idea['category'])
    
    return render_template('all_themes.html', themes=sorted(themes))
<<<<<<< HEAD

# PROBLEM MATCHER (show results page)
=======
 
# PROBLEM MATCHER (show results page instead of direct redirect)
>>>>>>> d7ce6b0bcc1b8aba7ddee40cd02e1b068091a531
@app.route('/match', methods=['POST'])
def match_problem():
    problem = request.form.get('problem', '').lower()
    ideas = load_ideas()
    
    if not problem or not ideas:
        return redirect(url_for('index'))
    
    problem_words = set(problem.split())
    scored_ideas = []
    
    for idea in ideas:
        score = 0
        
        if 'tags' in idea:
            for tag in idea['tags']:
                if any(word in tag.lower() for word in problem_words):
                    score += 3
        
        if 'category' in idea:
            for cat in idea['category']:
                if any(word in cat.lower() for word in problem_words):
                    score += 2
        
        title_words = idea.get('title', '').lower()
        subtitle_words = idea.get('subtitle', '').lower()
        
        for word in problem_words:
            if word in title_words:
                score += 2
            if word in subtitle_words:
                score += 1
        
        essence_words = idea.get('essence', '').lower()
        for word in problem_words:
            if word in essence_words:
                score += 1
        
        if score > 0:
            scored_ideas.append((score, idea))
    
    if scored_ideas:
        scored_ideas.sort(reverse=True, key=lambda x: x[0])
        matched_ideas = [idea for score, idea in scored_ideas]
<<<<<<< HEAD
        return render_template('search_results.html', 
                             query=problem, 
                             ideas=matched_ideas)
    
    return render_template('search_results.html', 
                         query=problem, 
=======
        
        # Show results page with all matches
        return render_template('search_results.html',
                             query=problem,
                             ideas=matched_ideas)
    
    # If no matches, show message
    return render_template('search_results.html',
                         query=problem,
>>>>>>> d7ce6b0bcc1b8aba7ddee40cd02e1b068091a531
                         ideas=[])
 
# NEWSLETTER SUBSCRIBE
@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email', '')
    
    if not email:
        flash('Please enter a valid email address', 'error')
        return redirect(url_for('index'))
    
    csv_path = os.path.join('data', 'subscribers.csv')
    os.makedirs('data', exist_ok=True)
    
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write('email,subscribed_at\n')
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        existing_emails = [line.split(',')[0] for line in f.readlines()[1:]]
        if email in existing_emails:
            flash('You are already subscribed!', 'info')
            return redirect(url_for('index'))
    
    timestamp = datetime.now().isoformat()
    
    with open(csv_path, 'a', encoding='utf-8') as f:
        f.write(f'{email},{timestamp}\n')
    
    send_welcome_email(email)
    
    flash('Thank you for subscribing! Check your email for confirmation.', 'success')
    return redirect(url_for('index'))
<<<<<<< HEAD

=======
 
# Optional: Send welcome email
>>>>>>> d7ce6b0bcc1b8aba7ddee40cd02e1b068091a531
def send_welcome_email(to_email):
    """Send welcome email - configure environment variables"""
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL', 'your-email@gmail.com')
        sender_password = os.getenv('SENDER_PASSWORD', 'your-app-password')
        
        if sender_email == 'your-email@gmail.com':
            print(f"Email not configured. Would send welcome email to: {to_email}")
            return
        
        message = MIMEMultipart('alternative')
        message['Subject'] = 'Welcome to Big Picture Ideas!'
        message['From'] = sender_email
        message['To'] = to_email
        
        text = "Welcome! You'll receive one powerful idea every week."
        html = "<html><body><h2>Welcome to Big Picture Ideas!</h2><p>Thank you for subscribing.</p></body></html>"
        
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        message.attach(part1)
        message.attach(part2)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())
        
        print(f"Welcome email sent to: {to_email}")
    except Exception as e:
        print(f"Error sending email: {e}")
<<<<<<< HEAD

# LIKE AN IDEA
@app.route('/api/like/<idea_id>', methods=['POST'])
def like_idea(idea_id):
    try:
        db = get_db()
        db.execute('UPDATE idea_stats SET likes = likes + 1, updated_at = ? WHERE id = ?',
                   (datetime.now(), idea_id))
        db.commit()
        
        cursor = db.execute('SELECT likes FROM idea_stats WHERE id = ?', (idea_id,))
        stats = cursor.fetchone()
        likes = stats['likes'] if stats else 0
        
        return jsonify({'success': True, 'likes': likes})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# SHARE AN IDEA
@app.route('/api/share/<idea_id>', methods=['POST'])
def share_idea(idea_id):
    try:
        db = get_db()
        db.execute('UPDATE idea_stats SET shares = shares + 1, updated_at = ? WHERE id = ?',
                   (datetime.now(), idea_id))
        db.commit()
        
        cursor = db.execute('SELECT shares FROM idea_stats WHERE id = ?', (idea_id,))
        stats = cursor.fetchone()
        shares = stats['shares'] if stats else 0
        
        return jsonify({'success': True, 'shares': shares})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Initialize database on startup
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
=======
        # Don't crash if email fails
 
# LIKE AN IDEA (API endpoint)
@app.route('/api/like/<idea_id>', methods=['POST'])
def like_idea(idea_id):
    ideas = load_ideas()
    
    for i, idea in enumerate(ideas):
        if idea['id'] == idea_id:
            ideas[i]['likes'] = ideas[i].get('likes', 0) + 1
            save_ideas(ideas)
            return jsonify({'success': True, 'likes': ideas[i]['likes']})
    
    return jsonify({'success': False, 'error': 'Idea not found'}), 404
 
# SHARE AN IDEA (track share count)
@app.route('/api/share/<idea_id>', methods=['POST'])
def share_idea(idea_id):
    ideas = load_ideas()
    
    for i, idea in enumerate(ideas):
        if idea['id'] == idea_id:
            # Add shares field if it doesn't exist
            if 'shares' not in ideas[i]:
                ideas[i]['shares'] = 0
            ideas[i]['shares'] += 1
            save_ideas(ideas)
            return jsonify({'success': True, 'shares': ideas[i]['shares']})
    
    return jsonify({'success': False, 'error': 'Idea not found'}), 404
 
if __name__ == '__main__':
    app.run(debug=True)
>>>>>>> d7ce6b0bcc1b8aba7ddee40cd02e1b068091a531
