from flask import Flask, render_template, request, jsonify
import json
import re
import string
import threading
import requests
import time
from rapidfuzz import process, fuzz

app = Flask(__name__)

# Load Knowledge Base
with open("knowledge.json", "r", encoding="utf-8") as file:
    knowledge = json.load(file)

# Original questions (keys)
original_questions = list(knowledge.keys())

# Preprocessing function: lowercases, removes punctuation, and removes common stop words
STOP_WORDS = set([
    "who", "what", "when", "where", "why", "how", "is", "are", "was", "were",
    "do", "does", "did", "the", "a", "an", "to", "for", "with", "about", "in",
    "on", "at", "by", "of", "and", "or", "but", "if", "then", "else", "when",
    "up", "so", "than", "too", "very", "can", "will", "just", "don", "t",
    "now", "get", "me", "my", "your", "tell", "know", "like", "please", "help"
])

def preprocess(text):
    length = len(text.split())
    if length < 3:
        return text.lower()  # For very short inputs, just lowercase without removing stop words
    text = text.lower()
    # Remove punctuation
    text = re.sub(f"[{re.escape(string.punctuation)}]", "", text)
    # Split into words and remove stop words
    words = text.split()
    words = [w for w in words if w not in STOP_WORDS]
    return " ".join(words)

# Preprocess all questions once for faster matching
# We keep the original questions as the reference for scoring,
# but we will preprocess the user input before passing it to the scorers.
# The scorers will compare the preprocessed input against the original questions.
# This way we don't lose the context of the original questions.

processed_knowledge = {}
preprocessed_questions = []
for q in original_questions:
    processed_q = preprocess(q)
    processed_knowledge[processed_q] = knowledge[q]
    preprocessed_questions.append(processed_q)
 
def get_response(user_input):
    # Preprocess user input
    processed_input = preprocess(user_input)

    # Define scorers to try
    scorers = [
        fuzz.token_sort_ratio,
        fuzz.token_set_ratio,
        fuzz.partial_ratio
    ]

    best_score = 0
    best_match = None

    question_length = len(processed_input.split())

    if processed_knowledge.get(processed_input):
        return processed_knowledge[processed_input]
    
    # Try each scorer and keep the best match
    for scorer in scorers:
        match, score, _ = process.extractOne(
            processed_input,
            preprocessed_questions,#original_questions,
            scorer=scorer
        )
        if score > best_score:
            best_score = score
            best_match = match

    print(f"Best match: '{best_match}' with score: {best_score}")

    # Only return answer if score is above threshold (60)
    if best_score >= 60:
        return processed_knowledge[best_match]

    return "Sorry 😅 I couldn't understand that well. Try asking something related to football rules, tickets, or fan engagement!"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    reply = get_response(user_message)
    return jsonify({"reply": reply})
@app.route("/ping", methods=["GET"])
def ping():
    """Simple endpoint to keep the service alive"""
    return "pong", 200

def self_ping():
    """Background thread that pings the service every 10 minutes"""
    # Get the Render URL from environment variable or use localhost for testing
    render_url = "https://sports-knowledge-chatbot.onrender.com/"  # REPLACE WITH YOUR ACTUAL RENDER URL
    
    # For local testing, uncomment this line and comment the one above
    #render_url = "http://localhost:5000"
    
    while True:
        try:
            # Wait 10 minutes between pings
            time.sleep(2)  # 600 seconds = 10 minutes
            
            # Ping the /ping endpoint
            response = requests.get(f"{render_url}/ping", timeout=10)
            print(f"Self-ping sent. Status code: {response.status_code}")
        except Exception as e:
            print(f"Self-ping failed: {e}")

# Start the self-pinging thread when running on Render (not in debug mode)
if __name__ == "__main__":
    # Only start the pinger if we're running on Render (not in debug mode)
    # Check if we're in production (no debug) or if a specific env var is set
    import os
    if not app.debug or os.environ.get("RENDER") == "true":
        pinger_thread = threading.Thread(target=self_ping, daemon=True)
        pinger_thread.start()
        print("Self-ping thread started. Will ping every 10 minutes.")
    
    app.run(debug=True)
