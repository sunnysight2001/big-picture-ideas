from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this!

# Load ideas from JSON
def load_ideas():
    json_path = os.path.join('data', 'ideas.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Save ideas to JSON
def save_ideas(ideas):
    json_path = os.path.join('data', 'ideas.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(ideas, f, indent=2, ensure_ascii=False)

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
    
    # Get today's idea (first one for now, you can randomize)
    todays_idea = ideas[0] if ideas else None
    
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
    
    # Increment view count
    for i, current_idea in enumerate(ideas):
        if current_idea['id'] == idea_id:
            ideas[i]['views'] = ideas[i].get('views', 0) + 1
            save_ideas(ideas)
            idea = ideas[i]
            break
    
    # Find next idea (circular navigation)
    current_index = next((i for i, x in enumerate(ideas) if x['id'] == idea_id), None)
    next_idea = ideas[(current_index + 1) % len(ideas)] if current_index is not None else None
    
    return render_template('idea.html', idea=idea, next_idea=next_idea)

# THEME PAGE (optional)
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
    
    # Get all unique themes/categories
    themes = set()
    for idea in ideas:
        if 'category' in idea:
            themes.update(idea['category'])
    
    return render_template('all_themes.html', themes=sorted(themes))

# PROBLEM MATCHER (show results page instead of direct redirect)
@app.route('/match', methods=['POST'])
def match_problem():
    problem = request.form.get('problem', '').lower()
    ideas = load_ideas()
    
    if not problem or not ideas:
        return redirect(url_for('index'))
    
    # Score each idea based on keyword matches
    problem_words = set(problem.split())
    scored_ideas = []
    
    for idea in ideas:
        score = 0
        
        # Check tags (highest priority)
        if 'tags' in idea:
            for tag in idea['tags']:
                if any(word in tag.lower() for word in problem_words):
                    score += 3
        
        # Check category
        if 'category' in idea:
            for cat in idea['category']:
                if any(word in cat.lower() for word in problem_words):
                    score += 2
        
        # Check title and subtitle
        title_words = idea.get('title', '').lower()
        subtitle_words = idea.get('subtitle', '').lower()
        
        for word in problem_words:
            if word in title_words:
                score += 2
            if word in subtitle_words:
                score += 1
        
        # Check essence
        essence_words = idea.get('essence', '').lower()
        for word in problem_words:
            if word in essence_words:
                score += 1
        
        if score > 0:
            scored_ideas.append((score, idea))
    
    # Sort by score (highest first)
    if scored_ideas:
        scored_ideas.sort(reverse=True, key=lambda x: x[0])
        matched_ideas = [idea for score, idea in scored_ideas]
        
        # Show results page with all matches
        return render_template('search_results.html', 
                             query=problem, 
                             ideas=matched_ideas)
    
    # If no matches, show message
    return render_template('search_results.html', 
                         query=problem, 
                         ideas=[])

# NEWSLETTER SUBSCRIBE
@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email', '')
    
    if not email:
        flash('Please enter a valid email address', 'error')
        return redirect(url_for('index'))
    
    # Save to CSV file
    csv_path = os.path.join('data', 'subscribers.csv')
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Create file with headers if it doesn't exist
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write('email,subscribed_at\n')
    
    # Check if already subscribed
    with open(csv_path, 'r', encoding='utf-8') as f:
        existing_emails = [line.split(',')[0] for line in f.readlines()[1:]]
        if email in existing_emails:
            flash('You are already subscribed!', 'info')
            return redirect(url_for('index'))
    
    # Append new subscriber
    import datetime
    timestamp = datetime.datetime.now().isoformat()
    
    with open(csv_path, 'a', encoding='utf-8') as f:
        f.write(f'{email},{timestamp}\n')
    
    # Optional: Send confirmation email
    send_welcome_email(email)
    
    flash('Thank you for subscribing! Check your email for confirmation.', 'success')
    return redirect(url_for('index'))

# Optional: Send welcome email
def send_welcome_email(to_email):
    """
    Send a welcome email to new subscriber.
    Configure your email settings in environment variables.
    """
    try:
        # Email configuration (use environment variables in production)
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL', 'your-email@gmail.com')
        sender_password = os.getenv('SENDER_PASSWORD', 'your-app-password')
        
        # Skip if not configured
        if sender_email == 'your-email@gmail.com':
            print(f"Email not configured. Would send welcome email to: {to_email}")
            return
        
        # Create message
        message = MIMEMultipart('alternative')
        message['Subject'] = 'Welcome to Big Picture Ideas!'
        message['From'] = sender_email
        message['To'] = to_email
        
        # Email body
        text = """
        Welcome to Big Picture Ideas!
        
        Thank you for subscribing. You'll receive one powerful idea every week.
        No noise. No spam. Just clarity.
        
        Best regards,
        The Big Picture Ideas Team
        """
        
        html = """
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #0984e3;">Welcome to Big Picture Ideas!</h2>
            <p>Thank you for subscribing. You'll receive <strong>one powerful idea every week</strong>.</p>
            <p style="color: #636e72;">No noise. No spam. Just clarity.</p>
            <p>Best regards,<br>The Big Picture Ideas Team</p>
          </body>
        </html>
        """
        
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        message.attach(part1)
        message.attach(part2)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())
        
        print(f"Welcome email sent to: {to_email}")
        
    except Exception as e:
        print(f"Error sending email: {e}")
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