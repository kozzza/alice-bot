from flask import Flask

from os import environ

app = Flask(__name__)

@app.route('/')
def home():
    return None

if __name__ == '__main__':
    app.run(port=environ.get("PORT", 8000))