import os
os.system("pip install tweepy")
import random
import time
from time import sleep
import tweepy as tw
from datetime import datetime, timedelta, time as timedatetime
import requests
from requests import Session
import urllib.parse
import hashlib
import hmac
import base64
import json
import math
from keep_alive import keep_alive

# Create tradeable Coin / EUR pairs dict available on Kraken

tradeable_pairs_dict = {}

resp = requests.get('https://api.kraken.com/0/public/AssetPairs').json()
commercial_ticker = {'XXDG': 'DOGE', 'XETC': 'ETC', 'XETH': 'ETH', 'XLTC': 'LTC', 'XMLN': 'MLN', 'XREP': 'REP',
                     'XXBT': 'BTC', 'XXLM': 'XLM', 'XXMR': 'XMR', 'XXRP': 'XRP', 'XZEC': 'ZEC'}

for i in resp['result'].keys():
    if resp['result'][i]['quote'] == 'ZEUR' and resp['result'][i]['base'] not in ['USDC', 'USDT', 'DAI']:
        tradeable_pairs_dict[i] = resp['result'][i]['base']

# Paris & coins
pairs = list(tradeable_pairs_dict.keys())
coins = list(tradeable_pairs_dict.values())
minimum_order = dict(zip(pairs, [
    requests.get('https://api.kraken.com/0/public/AssetPairs?pair=' + i).json()['result'][i]['ordermin'] for i in
    pairs]))
coin_pairs_dict = dict(zip(coins, pairs))
pairs_minimum_order = dict(zip(pairs, [i for i in minimum_order.values()]))
coins_minimum_order = dict(zip(coins, [i for i in minimum_order.values()]))

# General vars.
trades = [i for i in range(6)]
strategy = ['Buy', 'Sell']
quantity = [0.25, 0.5, 0.75, 1]

min_balance_zeur = 10
initial_zeur_balance = 100.42
historical_balance = [100.42]

tweets_coins_hashtags = '$BTC $ETH $DOT $ADA $LINK $KSM $SOL $MATIC #SHIB #HODL #Crypto #NTFs #Metaverse'
tweets_other_ht = '#Tarugo6monthsChallenge'


def randomizer(list_options):
    random_list = random.choice(list_options)
    return random_list


def num_format(number, decimals):
    exp = '{:,.' + str(decimals) + 'f}'
    num_format = exp.format(float(number)).replace(",", "@").replace(".", ",").replace("@", ".")
    return num_format


def num_format_american(number, decimals):
    exp = '{:,.' + str(decimals) + 'f}'
    num_format = exp.format(float(number))
    return num_format


# Twitter API config (Module Tweepy)
consumer_key = os.environ['API_TW_CONSUMER_KEY']
consumer_secret = os.environ['API_TW_CONSUMER_SECRET']
access_token = os.environ['ACCESS_TOKEN']
access_token_secret = os.environ['ACCESS_TOKEN_SECRET']


def post_tweet(tweet):
    auth = tw.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tw.API(auth)
    api.update_status(tweet)


# Coinmarketcap API Config
cmc_api_key = os.environ['CMC_PRO_API_KEY']

headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': cmc_api_key,
}


def coinmarket(url):
    session = Session()
    session.headers.update(headers)
    response = session.get(url)
    return response


def get_kraken_signature(urlpath, data, secret):
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()


# Read Kraken API key and secret stored in environment variables
api_url = "https://api.kraken.com"
api_key = os.environ['API_KEY_KRAKEN']
api_sec = os.environ['API_SEC_KRAKEN']


# Attaches auth headers and returns results of a POST request
def kraken_request(uri_path, data, api_key, api_sec):
    headers = {}
    headers['API-Key'] = api_key
    # get_kraken_signature() as defined in the 'Authentication' section
    headers['API-Sign'] = get_kraken_signature(uri_path, data, api_sec)
    req = requests.post((api_url + uri_path), headers=headers, data=data)
    return req


# Construct the request and print the result
def kraken_addorder(pair, strategy, order_type, volume):
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000 * time.time())),
        "ordertype": order_type,
        "type": strategy,
        "volume": volume,
        "pair": pair,
    }, api_key, api_sec)
    return resp.json()


def kraken_getbalance():
    resp = kraken_request('/0/private/Balance', {
        "nonce": str(int(1000 * time.time()))
    }, api_key, api_sec)
    return resp.json()['result']


def kraken_get_trade_balance(asset):
    resp = kraken_request('/0/private/TradeBalance', {
        "nonce": str(int(1000 * time.time())),
        "asset": asset
    }, api_key, api_sec)
    return resp.json()


def kraken_trades_history():
    resp = kraken_request('/0/private/TradesHistory', {
        "nonce": str(int(1000 * time.time())),
        "trades": True
    }, api_key, api_sec)
    return resp.json()


def kraken_trades(txid):
    resp = kraken_request('/0/private/QueryTrades', {
        "nonce": str(int(1000 * time.time())),
        "txid": txid,
        "trades": True
    }, api_key, api_sec)
    return resp.json()


def kraken_get_price(ticker):
    resp = requests.get('https://api.kraken.com/0/public/Ticker?pair=' + ticker)
    return resp.json()['result'][ticker]['a'][0]


def cmc_update_tweet():
    url_lastest = 'https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest'
    url_btc = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    cmc_data = json.loads(coinmarket(url_lastest).text)
    cmc_latest = json.loads(coinmarket(url_btc).text)

    btc_dominance = round(float(cmc_data['data']['btc_dominance']), 2)
    marketcap = round(float(cmc_data['data']['quote']['USD']['total_market_cap']) / 10 ** 12, 3)  # In T
    marketcap_var = round(cmc_data['data']['quote']['USD']['total_market_cap_yesterday_percentage_change'], 2)
    marketcap_var_div = marketcap_var / 100
    btc_change = round(cmc_latest['data'][0]['quote']['USD']['percent_change_24h'], 2)
    btc_price = round(cmc_latest['data'][0]['quote']['USD']['price'], 0)

    # Feeling Tarugo
    if marketcap_var_div >= 0.07:
        mood = 'Feeling Tarugo: 😎🚀'
    elif 0.04 <= marketcap_var_div < 0.07:
        mood = 'Feeling Tarugo: 😄'
    elif 0.01 < marketcap_var_div < 0.04:
        mood = 'Feeling Tarugo: 🙂'
    elif -0.01 <= marketcap_var_div <= 0.01:
        mood = 'Feeling Tarugo: 😐'
    elif -0.01 > marketcap_var_div > -0.04:
        mood = 'Feeling Tarugo: 😰'
    elif marketcap_var_div <= -0.04:
        mood = 'Feeling Tarugo: 😤'
    else:
        pass

    # Icono marketcap
    if marketcap_var >= 0:
        icon_market_cap = '▲'
    else:
        icon_market_cap = '▼'

    # Icono BTC precio
    if btc_change >= 0:
        icon_btc = '▲'
    else:
        icon_btc = '▼'
    tweet = f'¡Buenos días! Ahí va la actualización del mercado:\n- {mood}\n- Total market cap: ${num_format(marketcap, 3)} T ({icon_market_cap}{num_format(marketcap_var, 2)}% en 24h).\n- Dominancia $BTC: {num_format(btc_dominance, 2)}% \n- Precio $BTC: ${num_format(btc_price, 1)}({icon_btc}{num_format(btc_change, 2)}% en 24h).\n$BTC $ETH $SHIB #Crypto #NTFs #Metaverse'
    print('\nLog Messages: -- CMC Tweet Update')
    print(tweet)
    return post_tweet(tweet)


def trade_message(trade, total_trade):
    last_trade = list(kraken_trades_history()['result']['trades'].values())[0]
    type_operation = last_trade['type']
    price = float(last_trade['price'])
    euro_exp = num_format(last_trade['cost'], 2)

    try:
        coin = commercial_ticker[tradeable_pairs_dict[last_trade['pair']]]
    except:
        coin = tradeable_pairs_dict[last_trade['pair']]

    # Formatear números

    if len(str(math.trunc(price))) > 1:
        price = num_format(last_trade['price'], 1)
        volume = num_format(last_trade['vol'], 5)

    elif 0 < math.trunc(price) < 10:
        price = num_format(last_trade['price'], 2)
        volume = num_format(last_trade['vol'], 3)

    elif math.trunc(price) == 0:
        price = num_format(last_trade['price'], 4)
        volume = num_format(last_trade['vol'], 3)

    # Estrategia ESP

    if type_operation == 'buy':
        type_op_esp = 'comprar'
    else:
        type_op_esp = 'vender'

    # Mensaje

    message = f'Taurgo informa 🤓:\nAcabo de {type_op_esp} {volume} ${coin} ({euro_exp} EUR) a un precio de {price} EUR por moneda 🤑.\nTrade: {trade} / {total_trade}\n{tweets_coins_hashtags}\n{tweets_other_ht}'
    print('\nLog Messages: -- Buy/Sell Tweet')
    print(message)
    return post_tweet(message)


def sell_crypto():
    print(f'\nLog Messages: Selling Crypto... {datetime.now()}')
    balance = kraken_getbalance()
    coins_positive_bal = [i for i in balance.keys() if i != 'EUR.HOLD' and i != 'ZEUR']
    coin_match_minimum = []
    bad_arguments = ['EOrder:Insufficient funds', 'EGeneral:Invalid arguments:volume']

    for i in coins_positive_bal:
        if float(balance[i]) >= float(coins_minimum_order[i]):
            coin_match_minimum.append(coin_pairs_dict[i])

    if len(coin_match_minimum) == 0:
        return buy_crypto()

    else:
        random_pair_sell = randomizer(coin_match_minimum)
        iterate_max = 20
        print('\nLog Messages: -- Pair to sell', random_pair_sell)

        while True:

            percentage_to_sell = randomizer(quantity)
            crypto_to_sell = float(kraken_getbalance()[tradeable_pairs_dict[random_pair_sell]]) * percentage_to_sell
            print('\nLog Messages: -- Percentage_to_sell', percentage_to_sell)
            print('\nLog Messages: -- Volume', crypto_to_sell)

            if not any(map(lambda x: x in kraken_addorder(random_pair_sell, 'sell', 'market', crypto_to_sell)['error'],
                           bad_arguments)):
                break

            elif iterate_max == 0:
                print('\nLog Messages: -- Iteration Limit. Change to buy the minimum volumen possible')
                volume_max = float(kraken_getbalance()[tradeable_pairs_dict[random_pair_sell]])
                #volume_sell_min = float(minimum_order[random_pair_sell])

                if not any(
                        map(lambda x: x in kraken_addorder(random_pair_sell, 'sell', 'market', volume_max)[
                            'error'],
                            bad_arguments)):
                    break
                else:
                    print('change strategy')
                    print(buy_crypto())
                break
            else:
                print('iterate_max -- % sell', percentage_to_sell)
                iterate_max -= 1
                print(iterate_max)


def buy_crypto():
    print(f'\nLog Messages: buying Crypto...{datetime.now()}')
    zeur_balance = float(kraken_getbalance()['ZEUR'])
    coin_match_minimum = []
    balance = float(kraken_getbalance()['ZEUR'])
    bad_arguments = ['EOrder:Insufficient funds', 'EGeneral:Invalid arguments:volume']

    for i in pairs:
        operation = float(balance) / float(kraken_get_price(i))
        if operation >= float(minimum_order[i]):
            coin_match_minimum.append(i)

    # Check Global ZEUR Balance
    if len(coin_match_minimum) > 0:

        # Select random positive pair
        random_pair_buy = randomizer(coin_match_minimum)
        print('\nLog Messages: -- Pair to buy', random_pair_buy)
        iterate_max = 25

        # Loop until the q match with the minimum buy
        while True:
            percentage_to_buy = randomizer(quantity)
            eur_to_buy = float(zeur_balance) * percentage_to_buy
            volume = eur_to_buy / float(kraken_get_price(random_pair_buy))

            print('\nLog Messages: -- Percentage to buy', percentage_to_buy)
            print('\nLog Messages: -- Volume', random_pair_buy)

            if not any(map(lambda x: x in kraken_addorder(random_pair_buy, 'buy', 'market', volume)['error'],
                           bad_arguments)):
                break

            elif iterate_max == 0:
                print('\nLog Messages: -- Iteration Limit. Change to buy the minimum volumen possible')
                volume = float(zeur_balance) / float(kraken_get_price(random_pair_buy))
                #volumen_buy_min = float(minimum_order[random_pair_buy])

                if not any(
                        map(lambda x: x in kraken_addorder(random_pair_buy, 'buy', 'market', volume)['error'],
                            bad_arguments)):
                    break

                else:
                    print('change strategy')
                    return sell_crypto()

            else:
                print('iterate_max', percentage_to_buy)
                iterate_max -= 1
                print(iterate_max)
    else:
        print('change strategy')
        return sell_crypto()


def global_check():
    # CHECK BUY
    coin_match_minimum_buy = []
    balance = kraken_getbalance()['ZEUR']

    for i in pairs:
        operation = float(balance) / float(kraken_get_price(i))
        if operation >= float(minimum_order[i]):
            coin_match_minimum_buy.append(i)

    # CHECK SELL
    coin_match_minimum_sell = []
    balance = kraken_getbalance()
    coins_positive_bal = [i for i in balance.keys() if i != 'EUR.HOLD' and i != 'ZEUR']

    for i in coins_positive_bal:
        if float(kraken_getbalance()[i]) >= float(coins_minimum_order[i]):
            coin_match_minimum_sell.append(coin_pairs_dict[i])

    if coin_match_minimum_buy and coin_match_minimum_sell == 0:
        return 0

def sleep_delay(trades):
    trades_list = [0, 1, 2, 3, 4, 5]
    sleep_hours = [0, 0, 10, 6, 4, 3]
    seconds_dict = dict(zip(trades_list, list(i * 60 * 60 for i in sleep_hours)))

    return seconds_dict[trades]

def dt_checker(dt):
    hours = int(datetime.strftime(dt,'%H'))
    minutes = int(datetime.strftime(dt,'%M'))
    limit_hours_l = timedatetime(0, 0)
    limit_hours_r = timedatetime(8, 0)
    dt_format = '%Y-%m-%d'
    dt_time = timedatetime(hours, minutes)
    dt_now = datetime.strftime(dt, dt_format)

    if limit_hours_l <= dt_time < limit_hours_r:
        return datetime.strptime(dt_now, dt_format) + timedelta(hours=8)
    else:
        return datetime.strptime(dt_now, dt_format) + timedelta(days=1, hours=8)


def tarugo_status_check():
    status_list = ['Long_stop', 'Last_trade', 'In_process', 'First_start']

    with open('tarugo_log.txt', 'r') as tarugo:
        """
        Estructura de datos en tarugo_log.txt
        Total_Trades, Trades YTD, Timestamp del momento, Segundos sleep, base date, days_alive
        '{number_trades},{counter},{datetime.now()},{time_sleep},{base_date},{days_alive}\n'
        """
        tarugo_db = [i.replace('\n', '').split(',') for i in tarugo.readlines()]

    if len(tarugo_db) == 0:
        return status_list[3]

    elif tarugo_db[-1][0] == tarugo_db[-1][1]:
        return status_list[1]

    elif tarugo_db[-1][0] != tarugo_db[-1][1]:
        return status_list[2]

    else:
        return status_list[0]

def trading_strategy(current_trade, number_trades, days_alive, base_date):
    counter = current_trade
    print(f'\nLog Messages - Trade number {counter}')

    while counter <= number_trades:
        strategy_trade = randomizer(strategy)
        bal_to_buy = float(kraken_getbalance()['ZEUR'])

        # Incluir check point.
        
        if global_check() == 0:
            message = '@tvilafiol S.O.S. Algo va mal... '
            print(message)
            print(post_tweet(message))
            break
        
        if bal_to_buy > min_balance_zeur:
            print(f'\nLog Messages - {days_alive} {datetime.now()}\nEstrategia: BUY -- Hay suficiente balance para comprar')
            print(buy_crypto())
            
        else:
            print(f'\nLog Messages - {days_alive} {datetime.now()}\nEstrategia: SELL')
            print(sell_crypto())

        print(trade_message(counter, number_trades))
        

        # Sleep
        if sleep_delay(number_trades) != 0:
            time_sleep = sleep_delay(number_trades)

            # Write log file
            log_message = f'{number_trades},{counter},{datetime.now()},{time_sleep},{base_date},{days_alive}\n'

            with open('tarugo_log.txt', 'a+') as tarugo:
                tarugo.write(log_message)
                print('guardado en el archivo log')

            print('Delayed for', time_sleep, 'seconds')
            sleep(time_sleep)
        counter += 1


def sleep_tomorrow(now, base_date):
    seconds_sleep = (base_date - now).total_seconds()
    print(f'\nLog Messages - Sleeping for {seconds_sleep} until {base_date} ')
    sleep(seconds_sleep)


def tarugo():
    # Check del status para definir los días y el tiempo de sleep.
    current_status = tarugo_status_check()
    print(f'\nLog Messages -- Tarugo arranca / Reboot {current_status}')

    with open('tarugo_log.txt', 'r') as tarugo:
        try:
            tarugo_db = [i.replace('\n', '').split(',') for i in tarugo.readlines()]
        except:
            pass

    if current_status == 'First_start':
        print(f'\nLog Messages - First Start {datetime.now()}')
        days_alive = 1
        base_date = dt_checker(datetime.now())
        print(sleep_tomorrow(datetime.now(), base_date))

    elif current_status == 'In_process':
        print(f'\nLog Messages - En proceso {datetime.now()}')
        days_alive = int(tarugo_db[-1][-1])
        base_date = datetime.strptime(tarugo_db[-1][-2], "%Y-%m-%d %H:%M:%S")
        sleep_time = (datetime.strptime(tarugo_db[-1][2], "%Y-%m-%d %H:%M:%S.%f") + timedelta(seconds=float(tarugo_db[-1][3])) - datetime.now()).total_seconds()

        try:
            print(f'\nSleep - > {sleep_time} seconds remaining')
            sleep(sleep_time)
        except:
            print('Log Messages - Time exception')

    else:
        print(f'\nLog Messages Long / Last Trade {datetime.now()}')
        days_alive = int(tarugo_db[-1][-1]) + 1
        base_date = dt_checker(datetime.now())
        print(sleep_tomorrow(datetime.now(), base_date))

    # General Loop.
    while True:
        current_status = tarugo_status_check()
        print(f'\nLog Messages General Loop - Status: {current_status}')

        if current_status == 'In_process':
            with open('tarugo_log.txt', 'r') as tarugo:
                tarugo_db = [i.replace('\n', '').split(',') for i in tarugo.readlines()]
                number_trades = int(tarugo_db[-1][0])
                counter = int(tarugo_db[-1][1]) + 1
            print(trading_strategy(counter, number_trades, days_alive, base_date))

            # Sleep until tomorrow
            base_date += timedelta(1)
            sleep_until_tomorrow = (base_date - datetime.now()).total_seconds()
            print(f'\nLog Messages - Sleep until tomorrow {days_alive} {datetime.now()} {sleep_until_tomorrow}')
            sleep(sleep_until_tomorrow)
            days_alive += 1

        else:
            seconds_delay = 5 * 60
            print('Coinmarketcap Update Tweet')
            print(cmc_update_tweet())
            print('sleeping for', seconds_delay)
            sleep(seconds_delay)

            while True:
                counter = 1

                number_trades = randomizer(trades)
                print(f'\nLog Messages - Number of trades {number_trades}')
                zeur_bal = float(kraken_get_trade_balance('EUR')['result']['eb'])
                zeur_var = zeur_bal - initial_zeur_balance
                balance_variation = round((zeur_bal / initial_zeur_balance - 1) * 100, 2)
                with open('tarugo_balance.txt', 'r') as text:
                    file = [i.replace('\n', '').split(',') for i in text.readlines()]
                    yesterday_bal = float(file[0][-1])

                lista_hodl = ['¡Hasta mañana! #HODL 💎🙌🏻', '#HODLEAR insensatos! ¡Nos vemos mañana!', 'Hoy a descansar. ¡Hasta mañana!', 'Diamond hands. 💎🙌🏻', 'La paciencia te hará rico #HODL', '#HODL para combatir la inflación 👊🏻', '#HODL por la libertad financiera', 'JUST #HODL IT! 💫', 'Keep Calm & #HODL, ¡Hasta mañana!']

                if number_trades == 0:
                    counter = 0

                    # Twitter update message
                    message = f'Tarugo Update 🤪:\n- Días operando 🤠: {days_alive}\n- Balance en EUR: {num_format(zeur_bal, 2)} ({num_format((zeur_bal / yesterday_bal - 1) * 100, 2)}% 24h var / {num_format(balance_variation, 2)}% vs. día inicio)\n- Trades: [0] {random.choice(lista_hodl)}\n{tweets_coins_hashtags}\n{tweets_other_ht}'
                    with open('tarugo_balance.txt', 'a+') as text:
                        value = ',' + str(zeur_bal)
                        text.write(value)

                    print(f'\nLog Messages - {days_alive} {datetime.now()}\n{message}')
                    print(post_tweet(message))

                    # Sleep until tomorrow
                    base_date += timedelta(1)
                    sleep_until_tomorrow = (base_date - datetime.now()).total_seconds()
        
                    print(f'\nLog Messages - sleep for {days_alive} {datetime.now()}\n', sleep_until_tomorrow)

                    # Write log file
                    log_message = f'{number_trades},{counter},{datetime.now()},{sleep_until_tomorrow},{base_date},{days_alive}\n'

                    with open('tarugo_log.txt', 'a+') as tarugo:
                        tarugo.write(log_message)

                    sleep(sleep_until_tomorrow)

                else:
                    message = f'Tarugo Update 🤪:\n- Días operando 🤠: {days_alive}\n- Balance en EUR: {num_format(zeur_bal, 2)} ({num_format((zeur_bal / yesterday_bal - 1) * 100, 2)}% 24h var / {num_format(balance_variation, 2)}% vs. día inicio)\n- Trades: [{number_trades}] ¡Estad atentos! 🚀\n{tweets_other_ht}\n{tweets_coins_hashtags}'
                    
                    with open('tarugo_balance.txt', 'a+') as text:
                        value = ',' + str(zeur_bal)
                        text.write(value)
                    
                    print(f'\nLog Messages - {days_alive} {datetime.now()}\n', message)
                    print(post_tweet(message))
                    sleep(600)  # aquí incluir 600

                    print(trading_strategy(counter, number_trades, days_alive, base_date))

                # Sleep until tomorrow
                break
           
            # Sleep until tomorrow
            base_date += timedelta(1)
            sleep_until_tomorrow = (base_date - datetime.now()).total_seconds()
            print(f'\nLog Messages - Sleep until tomorrow {days_alive} {datetime.now()} {sleep_until_tomorrow}')
            sleep(sleep_until_tomorrow) 
            

tarugo()
