# databot-flask-app
Retrieve data from MySQL database, process it, and produce json

## To install on my A Small Orange host

Based on the instructions here: https://kb.asmallorange.com/customer/en/portal/articles/1619184-create-a-python-hello-world-app-with-flask

1. Copy files to host. Keep the file structure, where the root directory for this repository is my home directory (the Flask application lives outside public_html).
2. The public_html/databot folder (containing the .htaccess file) will be the URL used to access the application (e.g., put the .htaccess file in public_html/abc if I want the application to be accessed at datarink.com/abc). This change also needs to be reflected in the routing lines (e.g., .route('/databot/hello')) in the application files: databot.py, hello.py, bye.py, get_game_data.py
3. Test if the application is working by accessing datarink.com/databot or datarink.com/databot/hello or datarink.com/databot/bye
4. Turn off debug mode in databot.py - otherwise, others can execute code
5. Remove cross-origin decorator from get_game_data.py - this is only needed when I host and access the application locally
