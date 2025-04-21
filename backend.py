import json
import time
import random
import string
import hashlib
from pathlib import Path

import openai
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
client = openai.OpenAI()
data_dir = Path("/Users/yuxuanlu/code/simulated_web_agent/data")

# Global configurations
MAX_REQUESTS = 5
DIFFICULTY = 4  # Number of leading zeros required in the hash

# Connect to MongoDB
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["chat_sessions"]
sessions_collection = db["sessions"]


def generate_random_string(length=10):
    """Generate a random string of fixed length"""
    letters = string.ascii_letters + string.digits
    return "".join(random.choice(letters) for _ in range(length))


def verify_challenge(challenge, solution):
    """Verify if the solution meets the difficulty requirement"""
    if not solution.startswith(challenge):
        return False

    # Calculate SHA256 hash
    hash_bytes = hashlib.sha256(solution.encode()).digest()

    # Check for leading zeros in binary representation
    # Each byte needs to be 0 for a full 8 zeros in binary
    full_bytes_to_check = DIFFICULTY // 8
    remaining_bits = DIFFICULTY % 8

    # Check full bytes first
    for i in range(full_bytes_to_check):
        if hash_bytes[i] != 0:
            return False

    # Check remaining bits if any
    if remaining_bits > 0 and full_bytes_to_check < len(hash_bytes):
        # Check if the most significant 'remaining_bits' bits are zeros
        # For example, if remaining_bits=3, then the byte should be < 32 (00100000 in binary)
        return hash_bytes[full_bytes_to_check] < (1 << (8 - remaining_bits))

    return True


def chat(messages, model="gpt-4o", **kwargs):
    print(messages)
    for message in messages:
        del message["id"]
        new_contents = []
        for content in message["content"]:
            if content["type"] == "image":
                new_content = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{content['source']['media_type']};base64,"
                        + content["source"]["data"]
                    },
                }
                new_contents.append(new_content)
            else:
                new_contents.append(content)
        message["content"] = new_contents
    print(messages)
    try:
        return (
            client.chat.completions.create(model=model, messages=messages, **kwargs)
            .choices[0]
            .message.content
        )
    except Exception as e:
        print(messages)
        print(e)
        raise e


@app.route("/api/create_session", methods=["POST"])
def create_session():
    """Create a new session with a session ID and challenge"""
    session_id = generate_random_string(16)
    challenge = generate_random_string(24)

    # Save to MongoDB
    session_data = {
        "session_id": session_id,
        "challenge": challenge,
        "requests_count": 0,
        "max_requests": MAX_REQUESTS,
        "created_at": time.time(),
        "difficulty": DIFFICULTY,
    }
    sessions_collection.insert_one(session_data)

    return jsonify(
        {"session_id": session_id, "challenge": challenge, "difficulty": DIFFICULTY}
    ), 200


@app.route("/api/openai", methods=["POST"])
def proxy():
    session_id = request.json.get("session_id")
    solution = request.json.get("solution")

    # Check if session exists
    session = sessions_collection.find_one({"session_id": session_id})
    if not session:
        return jsonify({"error": "Invalid session ID"}), 401

    # Verify the challenge solution
    if not verify_challenge(session["challenge"], solution):
        return jsonify({"error": "Invalid solution to challenge"}), 403

    # Check if maximum requests reached
    if session["requests_count"] >= MAX_REQUESTS:
        return jsonify({"error": "Maximum request limit reached"}), 429

    # Increment request count
    sessions_collection.update_one(
        {"session_id": session_id}, {"$inc": {"requests_count": 1}}
    )

    messages = request.json.get("messages")
    response = chat(messages)
    return jsonify({"message": response}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5001)
