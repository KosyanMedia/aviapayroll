import aiohttp
import ujson
import datetime

ACCESS_TOKEN = None
FILE_ID = None


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


async def refresh_access_token(refresh_token, file_id):
    request = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'scope': 'FileId:%d' % int(file_id),
    }
    r = await post('authorisation/refresh', request)
    if 'access_token' in r:
        global ACCESS_TOKEN, FILE_ID
        ACCESS_TOKEN = r['access_token']
        FILE_ID = file_id
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


async def get_contacts(email=None):
    params = {'FileId': FILE_ID}
    if email:
        params['Email'] = email
    async for contact in get_paged('Contacts', 'Contacts', params):
        yield contact


async def get_invoices(contact_id, date_from=None, date_to=None):
    params = {'FileId': FILE_ID, 'BillingContactId': contact_id}
    if date_from is not None:
        params['InvoiceFromDate'] = date_from
        if date_to is None:
            date_to = datetime.datetime.today().strftime('%Y-%m-%d')
    if date_to is not None:
        params['InvoiceToDate'] = date_to
    async for invoice in get_paged('Invoices', 'Invoices', params):
        yield invoice


async def get_invoice(transaction_id):
    r = await get('Invoice/%s' % transaction_id, {'FileId': FILE_ID})
    if r.get('TransactionId') != int(transaction_id):
        raise Exception('Something wrong', r)
    return r


async def email_invoice(transaction_id):
    r = await post('Invoice/%s/email-contact' % transaction_id, params={'FileId': FILE_ID})
    if r.get('InvoiceId') != transaction_id:
        raise Exception('Something wrong', r)
    return r


async def get_payments(transaction_id=None, date_from='2005-01-01', date_to=datetime.datetime.today().strftime('%Y-%m-%d'), transaction_type=None):
    params = {'FileId': FILE_ID}
    if transaction_id:
        params['ForInvoiceId'] = transaction_id
    if transaction_type:
        params['TransactionType'] = transaction_type
    params['PaymentFromDate'] = date_from
    params['PaymentToDate'] = date_to
    async for payments in get_paged('Payments', 'PaymentTransactions', params):
        yield payments

async def get_payment(transaction_id):
    r = await get('Payment/%s' % transaction_id, {'FileId': FILE_ID})
    if r.get('TransactionId') != int(transaction_id):
        raise Exception('Something wrong', r)
    return r