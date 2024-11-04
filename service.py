import math
import requests
import json
from datetime import datetime, timedelta
from pytz import timezone
import typing
from bs4 import BeautifulSoup

UNIONPAY_DATA = {}
CBR_DATA = {}

def update_unionpay_data_request():
    now = datetime.now()
    current_date = now.strftime("%Y%m%d")

    # load json from url
    url = f"https://www.unionpayintl.com/upload/jfimg/{current_date}.json"
    response = requests.get(url)
    try:
        data = response.json()
    except json.JSONDecodeError:
        print("Failed to decode JSON from UnionPay")
        previous_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"https://www.unionpayintl.com/upload/jfimg/{previous_date}.json"
        response = requests.get(url)
        data = response.json()
    
    exchange_rate_dict = {f"{line['baseCur']}_{line['transCur']}": line['rateData'] for line in data['exchangeRateJson']}
    UNIONPAY_DATA['exchange_rate'] = exchange_rate_dict
    base_currencies = set()
    target_currencies = set()
    for line in data['exchangeRateJson']:
        base_currencies.add(line['baseCur'])
        target_currencies.add(line['transCur'])
    UNIONPAY_DATA['base_currencies'] = base_currencies
    UNIONPAY_DATA['target_currencies'] = target_currencies
    UNIONPAY_DATA['update_time'] = now.strftime("%Y-%m-%d %H:%M:%S")

def update_cbr_data_request():
    response = requests.get('https://www.cbr.ru/scripts/XML_daily.asp')
    data = response.text
    soup = BeautifulSoup(data, 'html.parser')
    exchange_rate_dict = {}
    nominal_dict = {}
    value_dict = {}
    base_currencies = set()
    base_currencies.add('RUB')
    target_currencies = set()
    for valute in soup.find_all('valute'):
        '''
        <Valute ID="R01035">
        <NumCode>826</NumCode>
        <CharCode>GBP</CharCode>
        <Nominal>1</Nominal>
        <Name>Фунт стерлингов Соединенного королевства</Name>
        <Value>126,0906</Value>
        <VunitRate>126,0906</VunitRate>
        </Valute>
        '''
        char_code = valute.find('charcode').text
        Nominal = int(valute.find('nominal').text)
        target_currencies.add(char_code)
        _Value = float(valute.find('value').text.replace(',', '.'))
        VunitRate = float(valute.find('vunitrate').text.replace(',', '.'))
        exchange_rate_dict[char_code] = VunitRate
        nominal_dict[char_code] = Nominal
        value_dict[char_code] = _Value
    CBR_DATA['exchange_rate'] = exchange_rate_dict
    CBR_DATA['nominal'] = nominal_dict
    CBR_DATA['value'] = value_dict
    CBR_DATA['base_currencies'] = base_currencies
    CBR_DATA['target_currencies'] = target_currencies
    CBR_DATA['update_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def update_data():
    if UNIONPAY_DATA == {}:
        update_unionpay_data_request()
    else:
        # Define timezone for Beijing
        beijing_timezone = timezone('Asia/Shanghai')
        # Get the current time in Beijing timezone
        current_time = datetime.now(beijing_timezone)
        # Convert last update time to a datetime object in Beijing timezone
        last_update_time = datetime.strptime(UNIONPAY_DATA['update_time'], "%Y-%m-%d %H:%M:%S")
        last_update_time = beijing_timezone.localize(last_update_time)

        if current_time.hour >= 16 and current_time.minute >= 30:
            # European currencies update at 16:30
            if last_update_time < current_time.replace(hour=16, minute=30, second=0, microsecond=0):
                update_unionpay_data_request()
            else:
                # European currency rates already updated today.
                pass
        elif current_time.hour >= 11:
            # Remaining currencies update at 11:00
            if last_update_time < current_time.replace(hour=11, minute=0, second=0, microsecond=0):
                update_unionpay_data_request()
            else:
                # Remaining currency rates already updated today.
                pass
        else:
            # No update required before 11:00 today.
            pass
    
    if CBR_DATA == {}:
        update_cbr_data_request()
    else:
        # Define timezone for Moscow
        moscow_timezone = timezone('Europe/Moscow')
        # Get the current time in Moscow timezone
        current_time = datetime.now(moscow_timezone)
        # Convert last update time to a datetime object in Beijing timezone
        last_update_time = datetime.strptime(UNIONPAY_DATA['update_time'], "%Y-%m-%d %H:%M:%S")
        last_update_time = moscow_timezone.localize(last_update_time)

        # update every 1 hour
        if timedelta(hours=1) < current_time - last_update_time:
            update_cbr_data_request()

def get_unionpay_exchange_rate(base_currency: str, target_currency: str) -> typing.Optional[float]:
    key = f"{base_currency}_{target_currency}"
    if base_currency in UNIONPAY_DATA['base_currencies']:
        if target_currency in UNIONPAY_DATA['target_currencies']:
            return UNIONPAY_DATA['exchange_rate'][key]
        else:
            return None
    elif base_currency in UNIONPAY_DATA['target_currencies']:
        if target_currency == 'CNY':
            return round(1/UNIONPAY_DATA['exchange_rate'][f'CNY_{base_currency}']*1.0127, 10)
        else:
            if target_currency in UNIONPAY_DATA['target_currencies']:
                if target_currency == 'EUR':
                    return round(1/UNIONPAY_DATA['exchange_rate'][f'CNY_{base_currency}']*UNIONPAY_DATA['exchange_rate'][f'CNY_{target_currency}']*1.01, 10)
                if target_currency == 'HKD':
                    return round(1/UNIONPAY_DATA['exchange_rate'][f'CNY_{base_currency}']*UNIONPAY_DATA['exchange_rate'][f'CNY_{target_currency}']*1.0115, 10)
                else:
                    return round(1/UNIONPAY_DATA['exchange_rate'][f'CNY_{base_currency}']*UNIONPAY_DATA['exchange_rate'][f'CNY_{target_currency}']*1.008, 10)
            else:
                return None
    else:
        return None

def get_target_currency_list():
    return UNIONPAY_DATA['target_currencies']

def get_exchange_rate_list(base_currency: str) -> typing.List[str]:
    exchange_rate_dict = {}
    for currency in get_target_currency_list():
        if currency != base_currency:
            _rate = get_unionpay_exchange_rate(base_currency, currency)
            # if _rate < 0.01:
                # exchange_rate_dict[f'1000 {currency}'] = _rate*1000
            # else:
            exchange_rate_dict[currency] = _rate
    # make exchange_rate_list from exchange_rate_dict
    # and sort it in the following order:
    # CNY should be the first item in the list,
    # then: USD, EUR, TRY, AED, THB, HKD, GBP, JPY, AUD, CAD, SGD
    # then other currencies in alphabetical order
    exchange_rate_list_main = []
    exchange_rate_list_main.append(('CNY', CBR_DATA['nominal'].get('CNY'), round(exchange_rate_dict.get('CNY')*CBR_DATA['nominal'].get('CNY'), 3), round(CBR_DATA['value'].get('CNY'), 3)))
    exchange_rate_list_main.append(('USD', CBR_DATA['nominal'].get('USD'), round(exchange_rate_dict.get('USD')*CBR_DATA['nominal'].get('USD'), 3), round(CBR_DATA['value'].get('USD'), 3)))
    exchange_rate_list_main.append(('EUR', CBR_DATA['nominal'].get('EUR'), round(exchange_rate_dict.get('EUR')*CBR_DATA['nominal'].get('EUR'), 3), round(CBR_DATA['value'].get('EUR'), 3)))
    exchange_rate_list_main.append(('TRY', 1, round(exchange_rate_dict.get('TRY'), 3), round(CBR_DATA['exchange_rate'].get('TRY'), 3)))
    exchange_rate_list_main.append(('AED', CBR_DATA['nominal'].get('AED'), round(exchange_rate_dict.get('AED')*CBR_DATA['nominal'].get('AED'), 3), round(CBR_DATA['value'].get('AED'), 3)))
    exchange_rate_list_main.append(('THB', 1, round(exchange_rate_dict.get('THB'), 3), round(CBR_DATA['exchange_rate'].get('THB'), 3)))
    exchange_rate_list_main.append(('VND', 1000, round(exchange_rate_dict.get('VND')*1000, 3), round(CBR_DATA['exchange_rate'].get('VND')*1000, 3)))
    exchange_rate_list_main.append(('HKD', CBR_DATA['nominal'].get('HKD'), round(exchange_rate_dict.get('HKD')*CBR_DATA['nominal'].get('HKD'), 3), round(CBR_DATA['value'].get('HKD'), 3)))
    exchange_rate_list_main.append(('JPY', CBR_DATA['nominal'].get('JPY'), round(exchange_rate_dict.get('JPY')*CBR_DATA['nominal'].get('JPY'), 3), round(CBR_DATA['value'].get('JPY'), 3)))
    exchange_rate_list = []
    for currency, rate in exchange_rate_dict.items():
        if currency not in ('CNY', 'USD', 'EUR', 'TRY', 'AED', 'THB', 'VND', 'HKD', 'JPY'):
            nominal = CBR_DATA['nominal'].get(currency) if CBR_DATA['nominal'].get(currency) else 1
            if CBR_DATA['value'].get(currency):
                _cbr_rate = round(CBR_DATA['value'].get(currency), 3)
            else:
                _cbr_rate = None
            exchange_rate_list.append((currency, nominal, round(rate*nominal, 3), _cbr_rate))
    # sort the remaining currencies in alphabetical order
    exchange_rate_list.sort(key=lambda x: x[0])
    return exchange_rate_list_main, exchange_rate_list

def get_unionpay_update_time():
    return UNIONPAY_DATA['update_time']
def get_cbr_update_time():
    return CBR_DATA['update_time']