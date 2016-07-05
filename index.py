from flask import Flask

app = Flask(__name__)


@app.route('/')
def cs_flash_cards():
    return 'Hello World, you ready to learn?'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)