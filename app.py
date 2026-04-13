import os
from flask import Flask, render_template, request, jsonify
from rag_backend import generate_answer

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/")
def homepage():
    return render_template("homepage.html")


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.json or {}
    q = data.get("question", "").strip()
    if not q:
        return jsonify({"error": "Empty question"}), 400
    result = generate_answer(q)
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
