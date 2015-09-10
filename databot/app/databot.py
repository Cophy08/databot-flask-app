from flask import Flask

# Imports the hello_page blueprint from hello.py
from hello import hello_page
from bye import bye_page
from get_game_data import game_json

app = Flask(__name__)
app.register_blueprint(hello_page)
app.register_blueprint(bye_page)
app.register_blueprint(game_json)

@app.route("/databot")
def intro():
    return "I am databot!"

if __name__ == '__main__':
	app.debug = True
	app.run()