import aiohttp
import ujson

ACCESS_TOKEN = None

async def get_refresh_token(login, password, file_id):
	request = {
		'grant_type': 'password',
		'username': login,
		'password': password,
		'scope': 'FileId:%d' % int(file_id),
	}
	r = await post('authorisation/refresh', request)
	if 'refresh_token' in r:
		return r['refresh_token']
	else:
		raise Exception('Unexpected error, check credentials', r)

async def refresh_access_token(refresh_token):
	request = {
		'grant_type': 'refresh_token',
		'refresh_token': refresh_token,
	}
	r = await post('authorisation/refresh', request)
	if 'access_token' in r:
		global ACCESS_TOKEN
		ACCESS_TOKEN = r['access_token']
		return r['expires_in']
	else:
		raise Exception('Unexpected error, check credentials', r)


async def post(uri, data=None, params=None):
	headers = {
		'content-type': 'application/json',
		'X-Api-Version': '1.0',
	}
	if ACCESS_TOKEN:
		headers['Authorization'] = 'Bearer %s' % ACCESS_TOKEN
	if data is not None:
		data = ujson.dumps(data)
	async with aiohttp.ClientSession() as session:
		async with session.post('https://api.saasu.com/%s' % uri, data=data, params=params, headers=headers) as resp:
			return ujson.loads(await resp.text())


async def get(uri, params=None):
	headers = {
		'X-Api-Version': '1.0',
	}
	if ACCESS_TOKEN:
		headers['Authorization'] = 'Bearer %s' % ACCESS_TOKEN
	async with aiohttp.ClientSession() as session:
		async with session.get('https://api.saasu.com/%s' % uri, headers=headers, params=params) as resp:
			return ujson.loads(await resp.text())


async def get_paged(uri, field, params=None):
	if params is None:
		params = {}

	params['Page'] = 1
	params['PageSize'] = 25

	while True:
		r = await get(uri, params)

		if field not in r:
			raise Exception('Something wrong', r)
		for item in r[field]:
			yield item

		if len(r[field]) < params['PageSize']:
			break

		params['Page'] += 1


async def get_contacts(file_id, email=None):
	params = {'FileId': file_id}
	if email:
		params['Email'] = email
	async for contact in get_paged('Contacts', 'Contacts', params):
		yield contact


async def get_invoices(file_id, contact_id):
	params = {'FileId': file_id, 'BillingContactId': contact_id}
	async for invoice in get_paged('Invoices', 'Invoices', params):
		yield invoice


async def get_invoice(file_id, transaction_id):
	r = await get('Invoice/%s' % transaction_id, {'FileId': file_id})
	if r.get('TransactionId') != transaction_id:
		raise Exception('Something wrong', r)
	return r


async def email_invoice(file_id, transaction_id):
	r = await post('Invoice/%s/email-contact' % transaction_id, params={'FileId': file_id})
	if r.get('InvoiceId') != transaction_id:
		raise Exception('Something wrong', r)
	return r


async def get_payments(file_id, transaction_id):
	params = {'FileId': file_id, 'ForInvoiceId': transaction_id}
	async for payments in get_paged('Payments', 'PaymentTransactions', params):
		yield payments