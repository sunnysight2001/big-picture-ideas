from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import json
import os
import sqlite3
import hashlib
from datetime import date, datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ======================================================
# APP SETUP
# ======================================================

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# ======================================================
# CONTENT (IDEAS JSON)
# ======================================================

def load_ideas():
    json_path = os.path.join('data', 'ideas.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_idea_by_id(idea_id):
    for idea in load_ideas():
        if idea['id'] == idea_id:
            return idea
    return None

# ======================================================
# ANALYTICS (SQLITE – PERSISTENT)
# ======================================================

STATS_DB = "stats.db"

def init_stats_db():
    conn = sqlite3.connect(STATS_DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS page_views (
            page TEXT,
            visitor TEXT,
            visit_date TEXT,
            PRIMARY KEY (page, visitor, visit_date)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS idea_likes (
            idea_id TEXT PRIMARY KEY,
            likes INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

init_stats_db()

def visitor_id():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "")
    raw = f"{ip}-{ua}"
    return hashlib.sha256(raw.encode()).hexdigest()

def track_view(page: str):
    conn = sqlite3.connect(STATS_DB)
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO page_views VALUES (?, ?, ?)",
            (page, visitor_id(), date.today().isoformat())
        )
    except sqlite3.IntegrityError:
        pass  # already counted today

    conn.commit()
    conn.close()

def get_view_count(page: str) -> int:
    """Get total view count for a page"""
    conn = sqlite3.connect(STATS_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM page_views WHERE page = ?", (page,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_like_count(idea_id: str) -> int:
    """Get like count for an idea"""
    conn = sqlite3.connect(STATS_DB)
    cur = conn.cursor()
    cur.execute("SELECT likes FROM idea_likes WHERE idea_id = ?", (idea_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else 0

# ======================================================
# EMAIL (WELCOME MAIL)
# ======================================================

def send_welcome_email(to_email: str) -> None:
    try:
        api_key = os.getenv("SENDGRID_API_KEY")
        sender_email = os.getenv("SENDER_EMAIL")

        if not api_key or not sender_email:
            print("SendGrid not configured. Skipping email.")
            return

        message = Mail(
            from_email=sender_email,
            to_emails=to_email,
            subject="Welcome to Big Picture Ideas",
            plain_text_content=(
                "Welcome to Big Picture Ideas!\n\n"
                "You'll receive one powerful idea to improve clarity and thinking.\n\n"
                "No spam. No noise. Just perspective.\n\n"
                "– Big Picture Ideas"
            ),
            html_content="""
            <html>
              <body style="font-family: Arial, sans-serif; color:#333;">
                <h2>Welcome to Big Picture Ideas 👋</h2>
                <p>You'll receive <b>one powerful idea</b> to improve clarity and thinking.</p>
                <p>No spam. No noise. Just perspective.</p>
                <p>– <b>Big Picture Ideas</b></p>
              </body>
            </html>
            """
        )

        sg = SendGridAPIClient(api_key)
        sg.send(message)

        print(f"Welcome email sent via SendGrid to {to_email}")

    except Exception as e:
        # Never crash user flow
        print(f"SendGrid email failed but user subscribed: {e}")


# ======================================================
# ROUTES
# ======================================================

@app.route('/')
def index():
    track_view("home")

    ideas = load_ideas()

    # Enrich ideas with stats from database
    for idea in ideas:
        idea['views'] = get_view_count(f"idea:{idea['id']}")
        idea['likes'] = get_like_count(idea['id'])

    themes = set()
    for idea in ideas:
        themes.update(idea.get('category', []))

    # Today's idea - rotates daily
    today = date.today()
    todays_idea = ideas[today.timetuple().tm_yday % len(ideas)] if ideas else None

    # Latest ideas - last 4 added to JSON, shown newest first
    latest_ideas = ideas[-4:] if len(ideas) >= 4 else ideas
    latest_ideas.reverse()  # Show newest first

    return render_template(
        'index.html',
        ideas=latest_ideas,
        themes=sorted(themes)[:4],
        todays_idea=todays_idea
    )

@app.route('/idea/<idea_id>')
def idea_detail(idea_id):
    track_view(f"idea:{idea_id}")

    idea = get_idea_by_id(idea_id)
    if not idea:
        return "Idea not found", 404

    # Add stats from database
    idea['views'] = get_view_count(f"idea:{idea_id}")
    idea['likes'] = get_like_count(idea_id)

    ideas = load_ideas()
    idx = next((i for i, x in enumerate(ideas) if x['id'] == idea_id), None)
    next_idea = ideas[(idx + 1) % len(ideas)] if idx is not None else None

    return render_template('idea.html', idea=idea, next_idea=next_idea)

@app.route('/theme/<theme_name>')
def theme_page(theme_name):
    track_view(f"theme:{theme_name}")
    ideas = load_ideas()
    
    # Enrich with stats
    for idea in ideas:
        idea['views'] = get_view_count(f"idea:{idea['id']}")
        idea['likes'] = get_like_count(idea['id'])
    
    filtered = [i for i in ideas if theme_name in i.get('category', [])]
    return render_template('theme.html', theme=theme_name, ideas=filtered)

@app.route('/ideas')
def all_ideas():
    track_view("all-ideas")
    ideas = load_ideas()
    
    # Enrich with stats
    for idea in ideas:
        idea['views'] = get_view_count(f"idea:{idea['id']}")
        idea['likes'] = get_like_count(idea['id'])
    
    return render_template('all_ideas.html', ideas=ideas)

@app.route('/themes')
def all_themes():
    track_view("all-themes")
    themes = set()
    for idea in load_ideas():
        themes.update(idea.get('category', []))
    return render_template('all_themes.html', themes=sorted(themes))

# ======================================================
# SEARCH
# ======================================================

@app.route('/match', methods=['POST'])
def match_problem():
    problem = request.form.get('problem', '').lower()
    if not problem:
        return redirect(url_for('index'))

    ideas = load_ideas()
    
    # Enrich with stats
    for idea in ideas:
        idea['views'] = get_view_count(f"idea:{idea['id']}")
        idea['likes'] = get_like_count(idea['id'])
    
    words = set(problem.split())
    scored = []

    for idea in ideas:
        score = 0
        for tag in idea.get('tags', []):
            if any(w in tag.lower() for w in words):
                score += 3
        for cat in idea.get('category', []):
            if any(w in cat.lower() for w in words):
                score += 2
        for w in words:
            if w in idea.get('title', '').lower():
                score += 2
            if w in idea.get('subtitle', '').lower():
                score += 1
            if w in idea.get('essence', '').lower():
                score += 1
        if score > 0:
            scored.append((score, idea))

    scored.sort(reverse=True, key=lambda x: x[0])
    return render_template('search_results.html', query=problem, ideas=[i for _, i in scored])

# ======================================================
# SUBSCRIBE
# ======================================================

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email', '').strip().lower()

    # 1. Basic validation
    if not email or '@' not in email:
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('index'))

    os.makedirs('data', exist_ok=True)
    csv_path = os.path.join('data', 'subscribers.csv')

    # 2. Create file if it does not exist
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write('email,subscribed_at\n')

    # 3. Check if already subscribed
    with open(csv_path, 'r', encoding='utf-8') as f:
        existing_emails = {line.split(',')[0] for line in f.readlines()[1:]}

    if email in existing_emails:
        flash(
            "You're already subscribed 😊 "
            "If you don't see our emails, please check your Spam or Promotions folder "
            "and mark them as 'Not Spam'.",
            'info'
        )
        return redirect(url_for('index'))

    # 4. Save subscriber
    with open(csv_path, 'a', encoding='utf-8') as f:
        f.write(f"{email},{datetime.now().isoformat()}\n")

    # 5. Send welcome email (best-effort)
    send_welcome_email(email)

    # 6. Clear, confidence-building success message
    flash(
        "Thanks for subscribing! 🎉 "
        "We've sent you a welcome email. "
        "If you don't see it within a minute, please check your Spam or Promotions folder "
        "and mark it as 'Not Spam' so you don't miss future ideas.",
        'success'
    )

    return redirect(url_for('index'))


# ======================================================
# API: LIKE & SHARE
# ======================================================

@app.route('/api/like/<idea_id>', methods=['POST'])
def like_idea(idea_id):
    conn = sqlite3.connect(STATS_DB)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO idea_likes (idea_id, likes)
        VALUES (?, 1)
        ON CONFLICT(idea_id) DO UPDATE SET likes = likes + 1
    """, (idea_id,))

    conn.commit()
    cur.execute("SELECT likes FROM idea_likes WHERE idea_id=?", (idea_id,))
    likes = cur.fetchone()[0]

    conn.close()
    return jsonify({'success': True, 'likes': likes})

@app.route('/api/share/<idea_id>', methods=['POST'])
def share_idea(idea_id):
    track_view(f"share:{idea_id}")
    return jsonify({'success': True})

# ======================================================
# LOCAL RUN
# ======================================================

if __name__ == '__main__':
    app.run(debug=True)