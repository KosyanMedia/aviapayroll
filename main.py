import asyncio
import logging
import os
import aiohttp
import ujson
import saasu
from aiohttp import web
from aiohttp_session import session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import os
import auth_helpers
import aiohttp_jinja2
import jinja2
import routes
import hashlib


async def refresh_access_token():
	exp = await saasu.refresh_access_token(os.environ.get('SAASU_REFRESH_TOKEN'), os.environ.get('SAASU_FILE_ID'))
	logging.info('Access token updated, expire in %s', exp)
	loop.call_later(int(exp*0.9), refresh_access_token)


async def main():
	if not (os.environ.get('SAASU_FILE_ID') and (os.environ.get('SAASU_REFRESH_TOKEN') or (os.environ.get('SAASU_PASSWORD') and os.environ.get('SAASU_LOGIN')))):
		logging.error('You should specify SAASU File Id in variable SAASU_FILE_ID')
		logging.error('You should specify oAuth 2 refresh token in variable SAASU_REFRESH_TOKEN')
		logging.error('or your login & password in variables SAASU_LOGIN and SAASU_PASSWORD')
		logging.error('If you feel incomfortable with sending your login & password here, just execute the following command, and don`t forget to replace <USER> and <PASSWORD> to correct values')
		logging.error('curl -XPOST -H "Content-Type: application/json" -d \'{"username": "<USER>", "password": "<PASSWORD>", "grant_type": "password", "scope": "full"}\' https://api.saasu.com/authorisation/token')
		logging.error('and set SAASU_REFRESH_TOKEN to correct value from the response')
		exit(1)
	elif os.environ.get('SAASU_REFRESH_TOKEN') and os.environ.get('SAASU_PASSWORD') and os.environ.get('SAASU_LOGIN'):
		logging.error('Please remove your login & password from config variables, we already have some token')
		exit(1)
	elif os.environ.get('SAASU_PASSWORD') and os.environ.get('SAASU_LOGIN'):
		r = await saasu.get_refresh_token(os.environ.get('SAASU_LOGIN'), os.environ.get('SAASU_PASSWORD'), file_id)
		logging.error('Please remove your login & password from config variables')
		logging.error('And set SAASU_REFRESH_TOKEN to following value:')
		logging.error(r)
		exit(0)
	else:
		await refresh_access_token()
	logging.info('working')

	if os.environ.get('COOKIE_KEY'):
		cookie_key = hashlib.md5(os.environ.get('COOKIE_KEY').encode('utf-8')).hexdigest()
	else:
		cookie_key = os.urandom(16).hex()

	app = web.Application(loop=loop,
		middlewares=(
	    	session_middleware(
	           EncryptedCookieStorage(cookie_key.encode(),
	                                  cookie_name='oauth',
	                                  max_age=1800)
			),
		)
	)

	aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
	app['static_root_url'] = '/static'
	auth_helpers.register(app)
	routes.register(app)

	return app

loop = asyncio.get_event_loop()
app = loop.run_until_complete(main())