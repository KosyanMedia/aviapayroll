import csv
from collections import defaultdict
from io import StringIO

import datetime
from multidict import MultiDictProxy


def _md_to_rowdict(input: MultiDictProxy, ignore=tuple()):
    ret = defaultdict(list)
    max_rows = 0
    for key, value in input.items():
        key = key.replace('transaction_', '')
        if key not in ignore:
            ret[key].append(value)
    for key, l in ret.items():
        max_rows = max(max_rows, len(l))
    ret = dict(filter(lambda l: len(l[1]) == max_rows, ret.items()))
    ret = [
        {
            key: ret[key][i]
            for key in ret.keys()
        }
        for i in range(len(list(ret.values())[0]))
    ]
    return ret


def to_csv(year: int, input: MultiDictProxy):
    fields = ('summary', 'date', 'amount', 'taxes', 'cb_rate', 'cb_amount', 'cb_taxes')
    output = StringIO()
    f = csv.DictWriter(output, fields, quoting=csv.QUOTE_NONNUMERIC)
    f.writeheader()
    data = _md_to_rowdict(input, ('id', ))
    f.writerows(data)
    return output.getvalue(), {'Content-type': 'text/csv', 'Content-disposition': 'attachment; filename="taxes_%d.csv"' % year}


def _date_to_dc(d: datetime.datetime):
    return (d.date() - datetime.date(1899, 12, 30)).days

def to_dc7(year: int, data: MultiDictProxy):
    data = _md_to_rowdict(data)
    ret = 'DLSG            Decl20170102FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'
    ret += '0009@DeclInfo000000000001000010'
    ret += '0005%s' % _date_to_dc(datetime.datetime.now())
    ret += '0001000015'
    ret += '00010000120001000010000100001000010000100001000010000100001000010000000010000000000001000010000100001000010'

    ret += '0011@PersonName00000000000000000000000100015@PersonDocument0001000000000' \
           '00010' \
           '00010' \
           '0000000000010' \
           '0010@Foreigner000110006РОССИЯ00000003643' \
           '0019@PhoneForeignerHome00000000' \
           '0019@PhoneForeignerWork00000000' \
           '0014@PersonAddress00010000000010000000000000000000000000000000000000' \
           '0010@HomePhone000000000010@WorkPhone00000000'

    ret += '0012@DeclForeign'
    cnt = len(data)
    ret += '%04d%d' % (len(str(cnt)), cnt)

    for i, row in enumerate(data):
        ret += '0018@CurrencyIncome%03d' % i
        ret += '000213'
        ret += '00042000'
        ret += '0097Заработная плата и другие выплаты во исполнение трудового договора (кроме договоров ГП характера)'
        ret += '0020Go Travel Un Limited'
        ret += '0003344'
        date = _date_to_dc(datetime.datetime.strptime(row['date'], '%Y-%m-%d'))
        ret += '0005%d0005%d' % (date, date)
        ret += '000110003840'
        ret += '0007%04.2f0003100' % (float(row['cb_rate']) * 100)
        ret += '0007%04.2f0003100' % (float(row['cb_rate']) * 100)
        ret += '0010Доллар сша'
        ret += '%04d%s' % (len(row['amount']), row['amount'])
        ret += '%04d%s' % (len(row['cb_amount']), row['cb_amount'])
        ret += '000100001000010000100001000010'
        ret += '0000'

    ret += '0015@StandartDeduct0001100031030003101000110001000011000100001000010000100001100010000100013@SocialDeduct000100019@ConstructionDeduct000100009@CBDeduct00010000100001000010000100001000010000100001000010000100001000010000100001000010000100001000010000100010@IISDeduct0001000010000100001000010000100001000010000100001000010000100001000010000100001000010000100001000010'
    ret += '0006@Nalog00010\0\0'
    return ret.encode('cp1251'), {'Content-type': 'text/dc7', 'Content-disposition': 'attachment; filename="taxes_%d.dc7"' % year}
