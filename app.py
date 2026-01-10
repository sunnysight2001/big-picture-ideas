from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
from datetime import date, datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()
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

def load_ai_hacks():
    json_path = os.path.join('data', 'ai_hacks.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def get_ai_hack_by_slug(slug):
    json_path = os.path.join('data', 'ai_hacks', f'{slug}.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def get_next_ai_hack(slug):
    hacks = load_ai_hacks()  # listing file
    idx = next((i for i, x in enumerate(hacks) if x.get('slug') == slug), None)
    if idx is not None and len(hacks) > 1:
        return hacks[(idx + 1) % len(hacks)]
    return None

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
        print(f"SendGrid email failed but user subscribed: {e}")


# ======================================================
# ROUTES
# ======================================================
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/all_ideas')
def all_ideas():
    ideas = load_ideas()
    return render_template('all_ideas.html', ideas=ideas)
    

@app.route('/ideas')
def ideas_redirect():
    ideas = load_ideas()
    return render_template('all_ideas.html', ideas=ideas)

@app.route('/workshop')
def workshop():
    razorpay_key = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_default')
    print("=" * 50)
    print(f"Razorpay Key from env: {razorpay_key}")
    print(f"Key length: {len(razorpay_key)}")
    print(f"Starts with rzp_: {razorpay_key.startswith('rzp_')}")
    print("=" * 50)
    return render_template('workshop.html', razorpay_key=razorpay_key)

@app.route('/learn_ai')
def learn_ai():
    ai_items = load_ai_hacks()
    return render_template('learn_ai.html', ai_items=ai_items)

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/learn_ai/<slug>')
def learn_ai_detail(slug):
    hack = get_ai_hack_by_slug(slug)
    next_hack = get_next_ai_hack(slug)
    return render_template(
        'ai_hack.html',
        hack=hack,
        next_hack=next_hack
    )

@app.route('/')
def index():
    ideas = load_ideas()

    themes = set()
    for idea in ideas:
        themes.update(idea.get('category', []))

    # Today's idea - rotates daily
    today = date.today()
    todays_idea = ideas[today.timetuple().tm_yday % len(ideas)] if ideas else None

    # Latest ideas - last 3 added to JSON, shown newest first
    latest_ideas = ideas[-3:] if len(ideas) >= 3 else ideas
    latest_ideas.reverse()

    return render_template(
        'index.html',
        ideas=latest_ideas,
        themes=sorted(themes)[:3],
        todays_idea=todays_idea
    )

@app.route('/idea/<idea_id>')
def idea_detail(idea_id):
    idea = get_idea_by_id(idea_id)
    if not idea:
        return "Idea not found", 404

    # Get next idea
    ideas = load_ideas()
    idx = next((i for i, x in enumerate(ideas) if x['id'] == idea_id), None)
    next_idea = ideas[(idx + 1) % len(ideas)] if idx is not None else None

    return render_template('idea.html', idea=idea, next_idea=next_idea)

@app.route('/theme/<theme_name>')
def theme_page(theme_name):
    ideas = load_ideas()
    filtered = [i for i in ideas if theme_name in i.get('category', [])]
    return render_template('theme.html', theme=theme_name, ideas=filtered)

@app.route('/themes')
def all_themes():
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

    if not email or '@' not in email:
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('index'))

    os.makedirs('data', exist_ok=True)
    csv_path = os.path.join('data', 'subscribers.csv')

    if not os.path.exists(csv_path):
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write('email,subscribed_at\n')

    with open(csv_path, 'r', encoding='utf-8') as f:
        existing_emails = {line.split(',')[0] for line in f.readlines()[1:]}

    if email in existing_emails:
        flash(
            "You're already subscribed 😊 "
            "If you don't see our emails, check your Spam folder.",
            'info'
        )
        return redirect(url_for('index'))

    with open(csv_path, 'a', encoding='utf-8') as f:
        f.write(f"{email},{datetime.now().isoformat()}\n")

    # ✅ THESE MUST BE INSIDE THE FUNCTION
    send_welcome_email(email)

    flash(
        "Thanks for subscribing! 🎉 "
        "We've sent you a welcome email. "
        "Check your Spam folder if you don't see it.",
        'success'
    )

    next_page = request.form.get('next')
    return redirect(next_page or url_for('index'))

# ======================================================
# SHARE API (optional - just for tracking if you want analytics later)
# ======================================================

@app.route('/api/share/<idea_id>', methods=['POST'])
def share_idea(idea_id):
    # Just acknowledge the share
    from flask import jsonify
    return jsonify({'success': True})

# ======================================================
# doawnload route
# ======================================================

@app.route('/download')
def download():
    return render_template('download.html')

# ======================================================
# LOCAL RUN
# ======================================================

if __name__ == '__main__':
    app.run(debug=True)