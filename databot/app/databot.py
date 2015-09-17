from flask import Flask

# Imports the hello_page blueprint from hello.py
from hello import hello_page
from get_game_data import game_json
from get_game_list import game_list_json

app = Flask(__name__)
app.register_blueprint(hello_page)
app.register_blueprint(game_json)
app.register_blueprint(game_list_json)

@app.route("/databot/")
def intro():
    return "Hello, I'm databot!"

if __name__ == '__main__':
	app.debug = True
	app.run()