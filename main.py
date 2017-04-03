# -*- coding: utf-8 -*-
from bot.bot import CampusBot
from flask import Flask, request
from bot.request_handler import RequestHandler
 
app = Flask(__name__)
bot = CampusBot()
request_handler = RequestHandler(bot)

@app.route('/', methods=['GET'])
def get_webhook():
	"""Handles verification of Facebook messenger bot
	"""
	return request.args.get('hub.challenge', '')

@app.route('/', methods=['POST'])
def post_webhook():
	request_handler.handle(request)
	return "ok", 200

@app.errorhandler(404)
def page_not_found(e):
	return 'Sorry, Nothing at this URL.', 404

@app.errorhandler(500)
def application_error(e):
	return 'Sorry, unexpected error: {}'.format(e), 500
 
if __name__ == '__main__':
	app.run(debug=True)
