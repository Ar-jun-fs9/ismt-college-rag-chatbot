import os
from flask import Flask, render_template, request, jsonify
from rag_backend import generate_answer

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/")
def homepage():
    """Homepage with modern ISMT College website"""
    return render_template("homepage.html")


@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.json or {}
    q = data.get("question", "").strip()
    if not q:
        return jsonify({"error": "Empty question"}), 400
    result = generate_answer(q)
    return jsonify(result)


# For local development, you can use the following line to run the Flask app so uncomment it on local mahine.
# if __name__ == "__main__":
#     app.run()

# For deployment on platforms like Render, use the following line to run the Flask app with Gunicorn and comment it if run in local machine.
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port if available
    app.run(host="0.0.0.0", port=port)
