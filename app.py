from flask import Flask, render_template, request, jsonify
import json
import re
import string
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

    # Try each scorer and keep the best match
    for scorer in scorers:
        match, score, _ = process.extractOne(
            processed_input,
            original_questions,
            scorer=scorer
        )
        if score > best_score:
            best_score = score
            best_match = match

    print(f"Best match: '{best_match}' with score: {best_score}")

    # Only return answer if score is above threshold (60)
    if best_score >= 60:
        return knowledge[best_match]

    return "Sorry 😅 I couldn't understand that well. Try asking something related to football rules, tickets, or fan engagement!"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    reply = get_response(user_message)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(debug=True)