import os
import datetime
import aiohttp_jinja2
import auth_helpers
from dateutil.relativedelta import relativedelta
import saasu
from aiohttp import web
import ujson
import cbr
import taxes as t


@aiohttp_jinja2.template('index.html')
@auth_helpers.login_required
async def index(request, user, saasu_user):
    payroll_from = request.GET.get('from')
    if not payroll_from:
        payroll_from = datetime.date.today()
        payroll_from -= relativedelta(months=int(os.environ.get(
            'DEFAULT_INVOICES_DEPTH', '6')), days=payroll_from.day - 1)
        payroll_from = payroll_from.strftime('%Y-%m-%d')

    invoices = []
    async for invoice in saasu.get_invoices(saasu_user['Id'], date_from=payroll_from):
        invoices.append(invoice)

    return {
        'user': user,
        'saasu_user': saasu_user,
        'payroll_from': payroll_from,
        'invoices': invoices,
        'current_year': int(datetime.datetime.today().strftime('%Y')),
        'current_month': int(datetime.datetime.today().strftime('%-m')),
    }


@aiohttp_jinja2.template('view.html')
@auth_helpers.login_required
async def view_invoice(request, user, saasu_user):
    try:
        invoice = await saasu.get_invoice(request.match_info['invoice_id'])
    except:
        raise web.HTTPNotFound(body='Requested invoice not found')

    if invoice['BillingContactId'] != saasu_user['Id']:
        raise web.HTTPNotFound(body='Requested invoice not found')

    payments = []
    async for payment in saasu.get_payments(invoice['TransactionId']):
        payments.append(payment)

    return {
        'invoice': invoice,
        'payments': payments,
        'sorted_lines': sorted(invoice['LineItems'], key=lambda x: x['TotalAmount'], reverse=True),
    }


@aiohttp_jinja2.template('email.html')
@auth_helpers.login_required
async def email_invoice(request, user, saasu_user):
    try:
        invoice = await saasu.get_invoice(request.match_info['invoice_id'])
    except:
        raise web.HTTPNotFound(body='Requested invoice not found')

    if invoice['BillingContactId'] != saasu_user['Id']:
        raise web.HTTPNotFound(body='Requested invoice not found')

    r = await saasu.email_invoice(invoice['TransactionId'])
    return {
        'invoice': invoice,
        'email_result': r,
        'saasu_user': saasu_user,
    }

@aiohttp_jinja2.template('taxes.html')
@auth_helpers.login_required
async def taxes(request, user, saasu_user):
    year = int(request.match_info['year'])

    invoices = []
    date_from = '%s-12-01' % (year - 1)
    date_to = '%s-12-31' % year
    async for invoice in saasu.get_invoices(saasu_user['Id'], date_from=date_from, date_to=date_to):
        invoices.append(invoice)

    return {
        'year': year,
        'invoices': invoices,
    }


@auth_helpers.login_required
async def invoice_details(request, user, saasu_user):
    def last_day_of_month(date):
        if date.month == 12:
            return date.replace(day=31)
        return date.replace(month=date.month+1, day=1) - datetime.timedelta(days=1)

    try:
        invoice = await saasu.get_invoice(request.match_info['invoice_id'])
    except:
        raise web.HTTPNotFound(body='Requested invoice not found')

    if invoice['BillingContactId'] != saasu_user['Id']:
        raise web.HTTPNotFound(body='Requested invoice not found')

    transaction_date = datetime.datetime.strptime(invoice['CreatedDateUtc'][0:10], '%Y-%m-%d')
    transaction_date = last_day_of_month(transaction_date)

    payments = []
    async for payment in saasu.get_payments(invoice['TransactionId']):
        if request.query.get('target') == 'taxes' and transaction_date.date() < datetime.date.today():
            payment['TransactionDate'] = transaction_date.strftime('%Y-%m-%d')
        date = datetime.datetime.strptime(payment['TransactionDate'][0:10], '%Y-%m-%d')
        try:
            payment['cbRate'] = await cbr.get_currency_rate(date, 'USD')
        except:
            payment['cbRate'] = None
        payments.append(payment)

    invoice['payments'] = payments

    return web.json_response(invoice, dumps=ujson.dumps)


@aiohttp_jinja2.template('payment.html')
@auth_helpers.login_required
async def view_payment(request, user, saasu_user):
    try:
        payment = await saasu.get_payment(request.match_info['transaction_id'])
    except:
        raise web.HTTPNotFound(body='Requested payment not found')

    invoice_ids = []
    invoices = {}
    items = []
    if len(payment.get('PaymentItems', [])) > 10:
        raise web.HTTPTooManyRequests(body='Too many invoices in this payment, sorry')
    for item in payment.get('PaymentItems', []):
        if item['InvoiceTransactionId'] not in invoice_ids:
            try:
                invoice = await saasu.get_invoice(item['InvoiceTransactionId'])
            except:
                raise web.HTTPNotFound(body='Requested payment not found')
            if invoice['BillingContactId'] == saasu_user['Id']:
                invoice_ids.append(item['InvoiceTransactionId'])
                invoices[item['InvoiceTransactionId']] = invoice
                items.append(item)
            else:
                payment['TotalAmount'] -= item['AmountPaid']

    payment['PaymentItems'] = items

    return {
        'invoices': invoices,
        'payment': payment,
    }

@auth_helpers.login_required
async def taxes_export(request, user, saasu_user):
    year = int(request.match_info['year'])
    body = await request.post()
    fmt = body.get('format')
    if fmt == 'DC7':
        ret = t.to_dc7(year, body)
        return web.Response(body=ret[0], headers=ret[1])
    elif fmt == 'CSV':
        ret = t.to_csv(year, body)
        return web.Response(body=ret[0], headers=ret[1])
    else:
        raise web.HTTPBadRequest(body='Unknown export format')

@auth_helpers.login_required
async def pdf_invoice(request, user, saasu_user):
    try:
        invoice = await saasu.get_invoice(request.match_info['invoice_id'])
    except:
        raise web.HTTPNotFound(body='Requested invoice not found')

    if invoice['BillingContactId'] != saasu_user['Id']:
        raise web.HTTPNotFound(body='Requested invoice not found')

    resp = web.StreamResponse(headers={'Content-type': 'application/pdf', 'Content-disposition': 'attachment; filename="%s.pdf"' % invoice['Summary']})
    await resp.prepare(request)
    async for data in saasu.pdf_invoice(invoice['TransactionId']):
        resp.write(data)
        await resp.drain()
    resp.write_eof()
    return resp

def register(app):
    app.router.add_get('/', index)
    app.router.add_get(r'/invoice/{invoice_id:\d+}/email', email_invoice)
    app.router.add_get(r'/invoice/{invoice_id:\d+}/pdf', pdf_invoice)
    app.router.add_get(r'/invoice/{invoice_id:\d+}/view', view_invoice)
    app.router.add_get(r'/invoice/{invoice_id:\d+}/json', invoice_details)
    app.router.add_get(r'/taxes/{year:\d{4}}', taxes)
    app.router.add_post(r'/taxes/{year:\d{4}}/export', taxes_export)
    app.router.add_get(r'/payment/{transaction_id:\d+}/view', view_payment)
    app.router.add_static('/', './')
