from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>🔥 Bench Sales AI Running Live</h1>
    <p>Your app is deployed successfully!</p>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
