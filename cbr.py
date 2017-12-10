import datetime
import aiohttp
import re
import logging

r = re.compile(r'<Valute ID="R01235">\s*<NumCode>840</NumCode>\s*<CharCode>USD</CharCode>\s*<Nominal>(\d+)</Nominal>\s*<Name>[^<]+</Name>\s*<Value>([^<]+)')

async def get_currency_rate(date: datetime.date, currency: str) -> float:
    async with aiohttp.ClientSession() as session:
        async with session.get('https://cbr.ru/scripts/XML_daily.asp?date_req=%s' % date.strftime('%d/%m/%Y')) as resp:
            cbr_info = await resp.text()
            m = r.search(cbr_info)
            if m:
                return float(m.group(2).replace(',', '.'))
            else:
                raise ValueError('Currency rate not found')
