from flask import Flask
from flask_ngrok import run_with_ngrok

app = Flask(__name__)
app.secret_key = 'cairocoders-ednalan'


run_with_ngrok(app)
# app.config.from_object('config')
from app import routes

