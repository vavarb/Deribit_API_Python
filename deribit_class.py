
from connection import *
from websocket import create_connection
from datetime import datetime
from PyQt5 import QtWidgets
import json
import hmac
import hashlib
import time

global list_monitor_log
global counter_send_order
global sender_rate_dict
global delay_delay


class Deribit:
    def __init__(self, client_id=None, client_secret=None, wss_url=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.wss_url = wss_url

        self._auth(client_id=client_id, wss_url=wss_url, client_secret=client_secret)

    # noinspection PyMethodMayBeStatic
    def logwriter(self, msg):
        from lists import list_monitor_log

        filename = 'log_spread.log'

        try:
            out = datetime.now().strftime("\n[%Y/%m/%d, %H:%M:%S] ") + str(msg)
            list_monitor_log.append(str(msg))
            with open(filename, 'a') as logwriter_file:
                logwriter_file.write(str(out))

        except Exception as er:
            from connection import connect
            from lists import list_monitor_log
            with open(filename, 'a') as logwriter_file:
                logwriter_file.write(str(datetime.now().strftime("\n[%Y/%m/%d, %H:%M:%S] ")) +
                                     '***** ERROR except in logwriter: ' +
                                     str(er) + str(msg) +
                                     '_' + str(counter_send_order) + ' *****')
            list_monitor_log.append('***** ERROR except in logwriter: ' + str(er) + ' *****')
        finally:
            pass

    def _auth(self, client_id=None, wss_url=None, client_secret=None):
        self.client_id = client_id
        self.wss_url = wss_url
        self.client_secret = client_secret

        from lists import list_monitor_log
        global counter_send_order
        global sender_rate_dict
        global delay_delay

        counter_send_order = 0
        delay_delay = 0

        sender_rate_dict = dict()
        sender_rate_dict['time_1'] = time.time()
        sender_rate_dict['counter_send_order_for_sender_rate'] = 0

        timestamp = round(datetime.now().timestamp() * 1000)
        nonce = "abcd"
        data = ""
        signature = hmac.new(
            bytes(client_secret, "latin-1"),
            msg=bytes('{}\n{}\n{}'.format(timestamp, nonce, data), "latin-1"),
            digestmod=hashlib.sha256
        ).hexdigest().lower()

        try:
            self._WSS = create_connection(wss_url)
            msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "public/auth",
                "params": {
                    "grant_type": "client_signature",
                    "client_id": client_id,
                    "timestamp": timestamp,
                    "signature": signature,
                    "nonce": nonce,
                    "data": data
                }
            }
            self.logwriter('Auth OK\n############')
            list_monitor_log.append('Auth OK\n############')
            list_monitor_log.append('identified')
            return self._sender(msg)

        except Exception as er:
            from lists import list_monitor_log
            list_monitor_log.append('***** auth ERROR:' + ' error: ' + str(er) + ' *****')
            self.logwriter('***** auth ERROR:' + ' error: ' + str(er) + ' *****')

    # noinspection PyMethodMayBeStatic
    def sender_rate(self, counter_send_order_for_sender_rate, time_now):
        global sender_rate_dict

        if float(time_now - sender_rate_dict['time_1']) >= 10:
            delta_counter_send_order = float(
                counter_send_order_for_sender_rate) - float(sender_rate_dict['counter_send_order_for_sender_rate'])
            delta_time_for_sender_rate = float(time_now - sender_rate_dict['time_1'])
            rate_sender_orders = float(delta_counter_send_order) / float(delta_time_for_sender_rate)

            sender_rate_dict['time_1'] = time_now
            sender_rate_dict['counter_send_order_for_sender_rate'] = float(counter_send_order_for_sender_rate)

            return round(rate_sender_orders, 2)
        else:
            return False

    def _delay(self, sender_rate_rate):
        global delay_delay
        from lists import list_monitor_log

        if sender_rate_rate is False:
            return delay_delay

        else:
            list_monitor_log.append('*** Check Sent Orders Rate ***')
            self.logwriter(
                '*** Sent Orders Rate: ' + str(sender_rate_rate) + ' Orders/Second ***')
            if sender_rate_rate >= 5:
                delay_delay = round(delay_delay + 0.01, 2)
                list_monitor_log.append('*** Sent Orders Rate Checked: >= 5 Orders/second ***')
                self.logwriter('*** Setup New Delay for send order: ' + str(delay_delay) + ' seconds ***')
            else:
                list_monitor_log.append('*** Sent Orders Rate Checked: < 5 Orders/second ***')
                if delay_delay >= 0.01:
                    delay_delay = round(delay_delay - 0.01, 2)
                    self.logwriter('*** Setup Delay for send order: ' + str(delay_delay) + ' seconds ***')
                else:
                    self.logwriter('*** Setup Delay for send order Unmodified ***')
            return delay_delay

    def _sender(self, msg):
        global counter_send_order

        counter_send_order = counter_send_order + 1

        try:
            if str(msg['id']) == '4':
                self.logwriter(
                    str(msg['method']) + '(* Connection Test *)' + ' ID: ' + str(msg['id']) + '_' + str(
                        counter_send_order))
            elif str(msg['method']) == 'private/buy' or str(msg['method']) == 'private/sell':
                if str(msg['id']) == "8" or str(msg['id']) == "9":
                    instrument_name = str(msg['params']['instrument_name'])
                    instrument_direction = str(msg['method']) + ' ' + str(msg['params']['type'])
                    order_amount_instrument = str(msg['params']['amount'])
                    instrument_price = str(msg['params']['price'])
                    self.logwriter(str(instrument_name) +
                                   ': ' + str(instrument_direction) +
                                   ' ' + str(order_amount_instrument) +
                                   ' at ' + str(instrument_price) +
                                   ' ID: ' + str(msg['id']) +
                                   '_' + str(counter_send_order))
                elif str(msg['id']) == "10" or str(msg['id']) == "11":
                    instrument_name = str(msg['params']['instrument_name'])
                    instrument_direction = str(msg['method']) + ' - Pos-Only: ' + str(msg['params']['post_only'])
                    order_amount_instrument = str(msg['params']['amount'])
                    instrument_price = str(msg['params']['price'])
                    self.logwriter(str(instrument_name) +
                                   ': ' + str(instrument_direction) +
                                   ' ' + str(order_amount_instrument) +
                                   ' at ' + str(instrument_price) +
                                   ' ID: ' + str(msg['id']) +
                                   '_' + str(counter_send_order))
                elif str(msg['id']) == "12" or str(msg['id']) == "13":
                    instrument_name = str(msg['params']['instrument_name'])
                    instrument_direction = str(msg['method']) + ' ' + str(msg['params']['type'])
                    order_amount_instrument = str(msg['params']['amount'])
                    self.logwriter(str(instrument_name) +
                                   ': ' + str(instrument_direction) +
                                   ' ' + str(order_amount_instrument) +
                                   ' ID: ' + str(msg['id']) +
                                   '_' + str(counter_send_order))

            else:
                self.logwriter(str(msg['method']) + ' ID: ' + str(msg['id']) + '_' + str(counter_send_order))

            self._WSS.send(json.dumps(msg))
            out = json.loads(self._WSS.recv())

            sender_rate_rate = self.sender_rate(
                counter_send_order_for_sender_rate=counter_send_order, time_now=time.time())
            delay = self._delay(sender_rate_rate=sender_rate_rate)

            if delay > 0:
                time.sleep(delay)
            else:
                pass

            if 'error' in str(out):
                self.logwriter(' ***** ERROR: ' + str(out) + ' ID: ' + str(msg['id']) + '_' + str(
                    counter_send_order) + ' *****')

                if str(out['error']['code']) == '13009' or str(out['error']['code']) == '13004':
                    self.logwriter('***** VERIFY CREDENTIALS - Type your Deribit API and Secret Keys *****')
                    if str(msg['id']) == '19':
                        return float(0)
                    elif str(msg['id']) == '25':
                        return 0
                    else:
                        return out['error']

                elif str(msg['id']) == '19':
                    return float(0)

                elif str(msg['id']) == '25':
                    return 0

                else:
                    return out['error']

            elif str(msg['id']) == '4':
                if 'too_many_requests' in str(out) or '10028' in str(out['error']) or 'too_many_requests' in str(
                        out['result']) or '10028' in str(out['error']):
                    self.logwriter(str('**************** ERROR too_many_requests *****************' + str(
                        out) + str(msg['id']) + '_' + str(
                        counter_send_order)))
                    time.sleep(10)
                    return 'too_many_requests'

                else:
                    return out['result']

            elif str(msg['id']) == '18':
                return out['result']['trades'][0]['price']

            elif str(msg['id']) == '19':
                if str(out['result']['size']) == 'None' or str(out['result']['size']) == 'none':
                    return float(0)
                else:
                    return out['result']['size']

            elif str(msg['id']) == '20':
                if str(out['result']['best_ask_price']) == 'null' or str(out['result']['best_ask_price']) == 'None':
                    return 0
                else:
                    return out['result']['best_ask_price']

            elif str(msg['id']) == '21':
                if str(out['result']['best_bid_price']) == 'null' or str(out['result']['best_bid_price']) == 'None':
                    return 0
                else:
                    return out['result']['best_bid_price']

            elif str(msg['id']) == '22':
                return out['result'][0]['mark_price']

            elif str(msg['id']) == '23':
                if str(out['result']['best_bid_amount']) == 'null' or str(out['result']['best_bid_amount']) == 'None':
                    return 0
                else:
                    return out['result']['best_bid_amount']

            elif str(msg['id']) == '24':
                if str(out['result']['best_ask_amount']) == 'null' or str(out['result']['best_ask_amount']) == 'None':
                    return 0
                else:
                    return out['result']['best_ask_amount']

            elif str(msg['id']) == '25':
                if len(out['result']['data']) == 0 or out['result']['data'] == 'ok' or out[
                    'result']['data'] == 'OK' or out['result']['data'] == 'Ok' or out[
                        'result'] == 'ok' or out['result'] == 'Ok' or out['result'] == 'OK':
                    return 0
                elif 'error' in str(out):
                    return 0
                elif len(out['result']['data']) != 0:
                    return out['result']['data'][-1][-1]
                else:
                    return 0

            else:
                return out['result']

        except Exception as er:
            self.logwriter('_sender error: ' + str(er) + ' ID: ' + str(msg['id']) + '_' + str(counter_send_order))
        finally:
            pass

    def get_instruments(self, currency):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "public/get_instruments",
                "params": {
                    "currency": currency,
                    "expired": False
                }
            }
        return self._sender(msg)

    def index_price(self, currency):
        msg = \
            {
                "jsonrpc": "2.0",
                "method": "public/get_index_price",
                "id": 3,
                "params": {
                    "index_name": currency
                }
            }
        return self._sender(msg)

    def set_heartbeat(self):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "public/set_heartbeat",
                "params": {
                    "interval": 60
                }
            }
        return self._sender(msg)

    def disable_heartbeat(self):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "public/disable_heartbeat",
                "params": {

                }
            }
        return self._sender(msg)

    def get_position(self, instrument_name=None):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "private/get_position",
                "params": {
                    "instrument_name": instrument_name
                }
            }
        return self._sender(msg)

    def get_order_book(self, instrument_name=None):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "public/get_order_book",
                "params": {
                    "instrument_name": instrument_name
                }
            }
        return self._sender(msg)

    def buy_limit(self, currency, amount, price):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "private/buy",
                "params": {
                    "instrument_name": currency,
                    "amount": amount,
                    "type": "limit",
                    "price": price
                }
            }
        return self._sender(msg)

    def sell_limit(self, currency, amount, price):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "private/sell",
                "params": {
                    "instrument_name": currency,
                    "amount": amount,
                    "type": "limit",
                    "price": price
                }
            }
        return self._sender(msg)

    def buy_pos_only(self, currency, amount, price):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "private/buy",
                "params": {
                    "instrument_name": currency,
                    "amount": amount,
                    "price": price,
                    "post_only": True
                }
            }
        return self._sender(msg)

    def sell_pos_only(self, currency, amount, price):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "private/sell",
                "params": {
                    "instrument_name": currency,
                    "amount": amount,
                    "price": price,
                    "post_only": True
                }
            }
        return self._sender(msg)

    def buy_market(self, currency, amount):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 12,
                "method": "private/buy",
                "params": {
                    "instrument_name": currency,
                    "amount": amount,
                    "type": "market"
                }
            }
        return self._sender(msg)

    def sell_market(self, currency, amount):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 13,
                "method": "private/sell",
                "params": {
                    "instrument_name": currency,
                    "amount": amount,
                    "type": "market"
                }
            }
        return self._sender(msg)

    def cancel_all(self):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 14,
                "method": "private/cancel_all",
                "params": {

                }
            }
        return self._sender(msg)

    def get_instruments_future(self, currency):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 15,
                "method": "public/get_instruments",
                "params": {
                    "currency": currency,
                    "kind": "future",
                    "expired": False
                }
            }
        return self._sender(msg)

    def get_book_summary_by_instrument(self, instrument_name):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 16,
                "method": "public/get_book_summary_by_instrument",
                "params": {
                    "instrument_name": instrument_name
                }
            }
        return self._sender(msg)

    def close_position(self, instrument_name):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 17,
                "method": "private/close_position",
                "params": {
                    "instrument_name": instrument_name,
                    "type": "market"
                }
            }
        return self._sender(msg)

    def get_last_trades_by_instrument_price(self, instrument_name):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 18,
                "method": "public/get_last_trades_by_instrument",
                "params": {
                    "instrument_name": instrument_name
                }
            }
        return self._sender(msg)

    def get_position_size(self, instrument_name):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 19,
                "method": "private/get_position",
                "params": {
                    "instrument_name": instrument_name
                }
            }
        return self._sender(msg)

    def ask_price(self, instrument_name=None):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 20,
                "method": "public/get_order_book",
                "params": {
                    "instrument_name": instrument_name
                }
            }
        return self._sender(msg)

    def bid_price(self, instrument_name=None):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 21,
                "method": "public/get_order_book",
                "params": {
                    "instrument_name": instrument_name
                }
            }
        return self._sender(msg)

    def mark_price(self, instrument_name=None):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 22,
                "method": "public/get_book_summary_by_instrument",
                "params": {
                    "instrument_name": instrument_name
                }
            }
        return self._sender(msg)

    def best_bid_amount(self, instrument_name=None):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 23,
                "method": "public/get_order_book",
                "params": {
                    "instrument_name": instrument_name
                }
            }
        return self._sender(msg)

    def best_ask_amount(self, instrument_name=None):
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 24,
                "method": "public/get_order_book",
                "params": {
                    "instrument_name": instrument_name
                }
            }
        return self._sender(msg)

    def volatility_index_data(self, currency):
        timestamp_end = float(round(datetime.now().timestamp()) * 1000)
        timestamp_start = timestamp_end - 10000
        msg = \
            {
                "jsonrpc": "2.0",
                "id": 25,
                "method": "public/get_volatility_index_data",
                "params": {
                    "currency": currency,
                    "start_timestamp": timestamp_start,
                    "end_timestamp": timestamp_end,
                    "resolution": "1"
                }
            }
        return self._sender(msg)


class CredentialsSaved:
    def __init__(self):
        self.self = self

    @staticmethod
    def api_secret_saved():
        from lists import list_monitor_log
        import os

        if os.path.isfile('api-key_spread.txt') is False:
            with open('api-key_spread.txt', 'a') as api_key_save_file:
                api_key_save_file.write(str('<Type your Deribit Key>'))
        else:
            pass

        with open('api-key_spread.txt', 'r') as api_secret_saved_file:
            api_secret_saved_file_read = str(api_secret_saved_file.read())
        list_monitor_log.append('*** API key: ' + str(api_secret_saved_file_read) + ' ***')
        return api_secret_saved_file_read

    @staticmethod
    def secret_key_saved():
        from lists import list_monitor_log
        import os

        if os.path.isfile('secret-key_spread.txt') is False:
            with open('secret-key_spread.txt', 'a') as api_key_save_file:
                api_key_save_file.write(str('<Type your Deribit Secret Key>'))
        else:
            pass

        with open('secret-key_spread.txt', 'r') as secret_key_saved_file:
            secret_key_saved_file_read = str(secret_key_saved_file.read())
        list_monitor_log.append('*** SECRET key: ' + str(secret_key_saved_file_read) + ' ***')
        return secret_key_saved_file_read

    @staticmethod
    def testnet_saved_tru_or_false():
        from lists import list_monitor_log
        with open('testnet_true_or_false_spread.txt', 'r') as testnet_saved_tru_or_false_file:
            testnet_saved_tru_or_false_file_read = str(testnet_saved_tru_or_false_file.read())
        if testnet_saved_tru_or_false_file_read == 'True':
            list_monitor_log.append('*** TEST Account Selected ***')
            return True
        elif testnet_saved_tru_or_false_file_read == 'False':
            list_monitor_log.append('*** REAL Account Selected ***')
            return False
        else:
            list_monitor_log.append('***** ERROR in testnet_saved_tru_or_false - Error Code: 633 *****')
            connect.logwriter('***** ERROR in testnet_saved_tru_or_false - Error Code: 634 *****')

    @staticmethod
    def url():
        from lists import list_monitor_log
        if CredentialsSaved.testnet_saved_tru_or_false() is True:
            list_monitor_log.append('*** URL: ' + 'wss://test.deribit.com/ws/api/v2' + ' Selected ***')
            return 'wss://test.deribit.com/ws/api/v2'
        elif CredentialsSaved.testnet_saved_tru_or_false() is False:
            list_monitor_log.append('*** URL: ' + 'wss://deribit.com/ws/api/v2' + ' Selected ***')
            return 'wss://deribit.com/ws/api/v2'
        else:
            list_monitor_log.append('***** URL ERROR in testnet True or False - Error Code: 630 *****')


class InstrumentsSaved:
    def __init__(self):
        self.self = self
        self.instrument_number = None

    @staticmethod
    def instruments_check():
        with open('instruments_spread.txt', 'r') as instruments_check_file:
            return str(instruments_check_file.read())

    def instrument_name_construction_from_file(self, instrument_number=None):
        self.instrument_number = instrument_number
        file_open = 'instruments_spread.txt'

        instrument_number_adjusted_to_list = (int(instrument_number) - 1)

        # open file instruments
        with open(file_open, 'r') as file_instruments:
            lines_file_instruments = file_instruments.readlines()  # file instruments_spread.txt ==> lines
            # Instrument
            list_line_instrument = lines_file_instruments[instrument_number_adjusted_to_list].split()  # line ==> list
            if 'Unassigned' in list_line_instrument:
                return 'Unassigned'
            else:
                instrument_name = str(list_line_instrument[5])
                return str(instrument_name)

    def instrument_available(self, instrument_number=None):
        from lists import list_monitor_log
        from connection import connect

        self.instrument_number = instrument_number

        instrument_name = InstrumentsSaved().instrument_name_construction_from_file(
            instrument_number=instrument_number)

        if instrument_name == 'Unassigned':
            return 'Unassigned'
        else:
            currency = str
            if 'BTC' in instrument_name:
                currency = 'BTC'
            elif 'ETH' in instrument_name:
                currency = 'ETH'
            else:
                connect.logwriter(str('********** Instrument currency ERROR Error Code:: 678 *********'))
                list_monitor_log.append('********** Instrument currency ERROR Error Code:: 679 *********')
            a10 = connect.get_instruments(currency=currency)
            list_instrument_name = []
            for i in a10:
                list_instrument_name.append(i['instrument_name'])
            if instrument_name in list_instrument_name:
                list_instrument_name.clear()
                # time.sleep(0.3)
                return 'instrument available'
            else:
                list_instrument_name.clear()
                # time.sleep(0.3)
                return 'instrument NO available'

    def instrument_buy_or_sell(self, instrument_number=None):
        file_open = 'instruments_spread.txt'
        self.instrument_number = instrument_number
        instrument_number_adjusted_to_list = (int(instrument_number) - 1)
        if InstrumentsSaved().instrument_name_construction_from_file(
                instrument_number=instrument_number) == 'Unassigned':
            return 'Unassigned'
        else:
            with open(file_open, 'r') as file_instruments:
                lines_file_instruments = file_instruments.readlines()  # file instruments.txt ==> lines
                # Instrument
                list_line_instrument = \
                    lines_file_instruments[instrument_number_adjusted_to_list].split()  # line ==> list
                instrument_buy_or_sell = str(list_line_instrument[3])
                return str(instrument_buy_or_sell)

    def instrument_amount_saved(self, instrument_number=None):
        file_open = 'instruments_spread.txt'
        self.instrument_number = instrument_number

        instrument_number_adjusted_to_list = (int(instrument_number) - 1)

        if InstrumentsSaved().instrument_name_construction_from_file(
                instrument_number=instrument_number) == 'Unassigned':
            return 'Unassigned'
        else:
            with open(file_open, 'r') as file_instruments:
                lines_file_instruments = file_instruments.readlines()  # file instruments.txt ==> lines
                # Instrument
                list_line_instrument = lines_file_instruments[
                    instrument_number_adjusted_to_list].split()  # line ==> list
                instrument_amount_saved = str(list_line_instrument[4])
                return str(instrument_amount_saved)

    def instrument_kind_saved(self, instrument_number=None):
        self.instrument_number = instrument_number
        from connection import connect

        file_open = 'instruments_spread.txt'
        instrument_number_adjusted_to_list = (int(instrument_number) - 1)

        with open(file_open, 'r') as file_instruments:
            lines_file_instruments = file_instruments.readlines()  # file instruments_spread.txt ==> lines
            # Instrument
            # open file instruments
            list_line_instrument = lines_file_instruments[instrument_number_adjusted_to_list].split()  # line ==> list
            if 'Unassigned' in list_line_instrument:
                return 'Unassigned'
            elif 'future' in list_line_instrument:
                return 'future'
            elif 'option' in list_line_instrument:
                return 'option'
            else:
                connect.logwriter('*** Instrument ' + str(instrument_number) + ' kind ERROR Error Code:: 746 ***')
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Information)
                msg.setText('Instrument ' + str(instrument_number) + ' kind ERROR Error Code:: 749')
                msg.setWindowTitle('***** ERROR *****')
                msg.exec_()
                pass

    def instrument_direction_construction_from_instrument_file(self, instrument_number=None):
        self.instrument_number = instrument_number
        from connection import connect

        file_open = 'instruments_spread.txt'
        instrument_number_adjusted_to_list = (int(instrument_number) - 1)

        # open file instruments

        with open(file_open, 'r') as file_instruments:
            lines_file_instruments = file_instruments.readlines()  # file instruments_spread.txt ==> lines
            # Instrument
            list_line_instrument = lines_file_instruments[instrument_number_adjusted_to_list].split()  # line ==> list
            if 'Unassigned' in list_line_instrument:
                return 'Unassigned'
            elif 'buy' in list_line_instrument:
                return 'buy'
            elif 'sell' in list_line_instrument:
                return 'sell'
            else:
                connect.logwriter(str(
                    '*** Instrument ' + str(instrument_number) + ' direction ERROR Error Code:: 775 ***'))
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Information)
                msg.setText('Instrument ' + str(instrument_number) + ' direction ERROR Error Code:: 778')
                msg.setWindowTitle('***** ERROR *****')
                msg.exec_()
                pass
