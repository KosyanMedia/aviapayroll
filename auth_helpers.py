import os
from aiohttp_session import get_session
import aiohttp
from aiohttp import web
from urllib.parse import urlencode
import saasu


def login_required(fn):
	"""auth decorator
	call function(request, user: <aioauth_client User object>)
	"""

	async def wrapped(request, **kwargs):
		session = await get_session(request)

		if 'user' not in session:
			session['desired_location'] = request.path_qs
			return web.HTTPFound('/auth/login')
		elif not session['user'].get('email') or session['user']['hd'] not in os.environ['DOMAIN'].split(','):
			raise web.HTTPForbidden(body='Unexpected email')

		if 'saasu_user' not in session or session['saasu_user']['EmailAddress'] != session['user']['email']:
			async for user in saasu.get_contacts(session['user']['email']):
				session['saasu_user'] = user

		if 'saasu_user' not in session:
			raise web.HTTPForbidden(body='Unexpected billing user')

		return await fn(request, user=session['user'], saasu_user=session['saasu_user'], **kwargs)

	return wrapped


async def google_oauthcallback(request):
	if request.GET.get('error', None):
		raise web.HTTPUnauthorized(body='Unauthorized, denied Google Authentication')
	opts = {
		'code': request.GET.get('code'),
		'client_id': os.environ['GOOGLE_ID'],
		'client_secret': os.environ['GOOGLE_SECRET'],
		'redirect_uri': os.environ['GOOGLE_REDIRECT_URI'],
		'grant_type': 'authorization_code',
	}

	async with aiohttp.ClientSession() as session:
		async with session.post('https://www.googleapis.com/oauth2/v4/token', data=opts) as resp:
			token_info = await resp.json()
		async with session.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={'Authorization': 'Bearer ' + token_info['access_token']}) as resp:
			guser = await resp.json()

	session = await get_session(request)
	location = session.pop('desired_location')
	session['user'] = guser
	session['token'] = token_info['access_token']
	return web.HTTPFound(location)


async def google_loginreq(request):
	opts = {
		'scope': 'email profile',
		'state': 'security_token',
		'redirect_uri': os.environ['GOOGLE_REDIRECT_URI'],
		'response_type': 'code',
		'client_id': os.environ['GOOGLE_ID'],
		'access_type': 'online',
	}
	return web.HTTPFound('https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(opts))


def register(app):
	app.router.add_route('GET', '/auth/login', google_loginreq)
	app.router.add_route('GET', '/auth/oauth_callback', google_oauthcallback)

