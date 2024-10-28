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
    base_currencies = set()
    base_currencies.add('RUB')
    target_currencies = set()
    for valute in soup.find_all('valute'):
        char_code = valute.find('charcode').text
        target_currencies.add(char_code)
        VunitRate = float(valute.find('vunitrate').text.replace(',', '.'))
        exchange_rate_dict[char_code] = VunitRate
    CBR_DATA['exchange_rate'] = exchange_rate_dict
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
            return round(1/UNIONPAY_DATA['exchange_rate'][f'CNY_{base_currency}']*1.0125, 6)
        else:
            if target_currency in UNIONPAY_DATA['target_currencies']:
                if target_currency == 'EUR':
                    return round(1/UNIONPAY_DATA['exchange_rate'][f'CNY_{base_currency}']*UNIONPAY_DATA['exchange_rate'][f'CNY_{target_currency}']*1.01, 6)
                else:
                    return round(1/UNIONPAY_DATA['exchange_rate'][f'CNY_{base_currency}']*UNIONPAY_DATA['exchange_rate'][f'CNY_{target_currency}']*1.008, 6)
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
    exchange_rate_list_main.append(('CNY', exchange_rate_dict.get('CNY'), CBR_DATA['exchange_rate'].get('CNY')))
    exchange_rate_list_main.append(('USD', exchange_rate_dict.get('USD'), CBR_DATA['exchange_rate'].get('USD')))
    exchange_rate_list_main.append(('EUR', exchange_rate_dict.get('EUR'), CBR_DATA['exchange_rate'].get('EUR')))
    exchange_rate_list_main.append(('TRY', exchange_rate_dict.get('TRY'), CBR_DATA['exchange_rate'].get('TRY')))
    exchange_rate_list_main.append(('AED', exchange_rate_dict.get('AED'), CBR_DATA['exchange_rate'].get('AED')))
    exchange_rate_list_main.append(('THB', exchange_rate_dict.get('THB'), CBR_DATA['exchange_rate'].get('THB')))
    exchange_rate_list_main.append(('VND', exchange_rate_dict.get('VND'), CBR_DATA['exchange_rate'].get('VND')))
    exchange_rate_list_main.append(('HKD', exchange_rate_dict.get('HKD'), CBR_DATA['exchange_rate'].get('HKD')))
    exchange_rate_list_main.append(('JPY', exchange_rate_dict.get('JPY'), CBR_DATA['exchange_rate'].get('JPY')))
    exchange_rate_list = []
    for currency, rate in exchange_rate_dict.items():
        if currency not in ('CNY', 'USD', 'EUR', 'TRY', 'AED', 'THB', 'VND', 'HKD', 'JPY'):
            exchange_rate_list.append((currency, rate, CBR_DATA['exchange_rate'].get(currency)))
    # sort the remaining currencies in alphabetical order
    exchange_rate_list.sort(key=lambda x: x[0])
    return exchange_rate_list_main, exchange_rate_list

def get_unionpay_update_time():
    return UNIONPAY_DATA['update_time']
def get_cbr_update_time():
    return CBR_DATA['update_time']