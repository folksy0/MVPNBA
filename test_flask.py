from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "NBA MVP System is working!"

if __name__ == '__main__':
    print("Starting Flask test server...")
    app.run(debug=True, host='127.0.0.1', port=5000)
