#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 15 14:30:38 2019
@author: kojy
"""
import json

from base_handler import BaseHandler
from utils import decimal_default,str_to_decimal,get_linenumber
from .proxy import EthereumProxy
from constants import ETH_IP_ADDR,ETH_RPC_PORT,ETH_DEFAULT_GAS_PRICE

ip_addr, port = ETH_IP_ADDR,ETH_RPC_PORT
default_gas = 21000
default_gasprice = ETH_DEFAULT_GAS_PRICE

####################################################################################################################
# General ##########################################################################################################
####################################################################################################################

class ETH_ListAccounts(BaseHandler):
    def get(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            data = rpc_connection.eth_accounts()
            self.write(json.dumps(BaseHandler.success_ret_with_data(data), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_Accounts error:{0} in {1}".format(e,get_linenumber()))
              
class ETH_GetBalance(BaseHandler):
    @staticmethod
    def get_balance(rpc_connection,addr):
        balance = rpc_connection.eth_getBalance(addr)
        return balance/float(10**18)

    def get(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            address = self.get_argument("address")
            if len(address) != 42:
                self.write(json.dumps(BaseHandler.error_ret_with_data("arguments error")))
                return
            balance = ETH_GetBalance.get_balance(rpc_connection,address)
            self.write(json.dumps(BaseHandler.success_ret_with_data([balance]), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_GetBalance error:{0} in {1}".format(e,get_linenumber()))
           
class ETH_NewAccount(BaseHandler):
    def post(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            passphrase = self.get_argument("passphrase")
            data = rpc_connection.personal_newAccount(passphrase)
            self.write(json.dumps(BaseHandler.success_ret_with_data(data), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_NewAccount error:{0} in {1}".format(e,get_linenumber()))

####################################################################################################################
# Hot Wallet #######################################################################################################
####################################################################################################################

class ETH_GasPrice(BaseHandler):
    def get(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            data = rpc_connection.eth_gasPrice()
            self.write(json.dumps(BaseHandler.success_ret_with_data(data), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_GasPrice error:{0} in {1}".format(e,get_linenumber()))
            
class ETH_PendingTransactions(BaseHandler):
    def get(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            data = rpc_connection.eth_pendingTransactions()
            self.write(json.dumps(BaseHandler.success_ret_with_data(data), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_PendingTransactions error:{0} in {1}".format(e,get_linenumber()))

class ETH_SendTransaction(BaseHandler):
    @staticmethod
    def checkBalance(rpc_connection,addr,value,gas,gas_price):
        balance = ETH_GetBalance.get_balance(rpc_connection,addr) * 10 ** 18
        if balance < value + gas*gas_price:
            err_msg = "balance(%d) is below value(%d) + gas(%d) * gasprice(%d)"%(balance,value,gas,gas_price)
            return False,err_msg
        return True,balance

    @staticmethod
    def unlockAccount(rpc_connection,address,passphrase):
        rsp = rpc_connection.personal_unlockAccount(address,passphrase)
        if not rsp:
            err_msg = "unlock failed"
            return False,err_msg
        return True, rsp

    def post(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            from_addr = self.get_argument("from")
            passphrase = self.get_argument("passphrase").encode("utf-8")
            to_addr = self.get_argument("to")
            gas = self.get_argument("gas")
            gas_price = self.get_argument("gasPrice")
            value = self.get_argument("value")
            # check arguments
            _gas = int(gas) if not gas == '' else default_gas
            _gas_price = str_to_decimal(gas_price) if not gas_price == '' else default_gasprice    # 10Gwei
            _value = str_to_decimal(value) * 10 ** 18
            # checking balance
            ret, err_msg = ETH_SendTransaction.checkBalance(rpc_connection,from_addr,_value,_gas,_gas_price)
            if not ret:
                self.write(json.dumps(BaseHandler.error_ret_with_data(err_msg)))
                return
            # unlocking account
            ret, err_msg = ETH_SendTransaction.unlockAccount(rpc_connection,from_addr,passphrase)
            if not ret:
                self.write(json.dumps(BaseHandler.error_ret_with_data(err_msg)))
                return
            # sending money
            rsp = rpc_connection.eth_sendTransaction(to_addr,from_addr,_gas,_gas_price,_value)
            if not rsp:
                self.write(json.dumps(BaseHandler.error_ret_with_data('transaction failed')))
                return 
            self.write(json.dumps(BaseHandler.success_ret_with_data(rsp), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_SendTransaction error:{0} in {1}".format(e,get_linenumber()))

####################################################################################################################
# Cold Wallet ######################################################################################################
####################################################################################################################
from .transcationex import TransactionEx, UnsignedTransactionEx

def createRawTransaction(nonce, gasprice, startgas, to, value, data):
    nonce_ = int(nonce,16) if isinstance(nonce,str) and '0x' in nonce else int(nonce)
    gasprice_ = int(gasprice,16) if isinstance(gasprice,str) and '0x' in gasprice else int(gasprice)
    startgas_ = int(startgas,16) if isinstance(startgas,str) and '0x' in startgas else int(startgas)
    value_ = int(value,16) if isinstance(value,str) and '0x' in value else int(value)
    from rlp.utils import encode_hex,decode_hex
    to_ = decode_hex(to[2:]) if isinstance(to,str) and '0x' in to else decode_hex(to)
    data_ = decode_hex(data)
    rawTransaction = TransactionEx(nonce_, gasprice_, startgas_, to_, value_, data_)
    rlp_data = rawTransaction.unsigned
    return encode_hex(rlp_data)

def signRawTransaction(key,data):
    from rlp.utils import encode_hex,decode_hex
    rlpdata = decode_hex(data[2:]) if isinstance(data,str) and '0x' in data else decode_hex(data)
    key = decode_hex(key[2:]) if isinstance(key,str) and '0x' in key else decode_hex(key)
    import rlp
    tx = rlp.decode(rlpdata, UnsignedTransactionEx)
    assert tx.startgas >= tx.intrinsic_gas_used
    signed_rlp=rlp.encode(tx.sign(key),TransactionEx)
    return encode_hex(signed_rlp)

class ETH_CreateRawTransaction(BaseHandler):
    def post(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            to_addr = str(self.get_argument("to")) if self.get_argument("to") else '0xba1099cc91acdf45771d0a0c6e3b80e8e880c684'
            startgas = str(self.get_argument("startgas")) if self.get_argument("startgas") else default_gas
            gas_price = str(self.get_argument("gasPrice")) if self.get_argument("gasPrice") else default_gasprice
            value = float(self.get_argument("value"))  if self.get_argument("value") else 0.1
            nonce = str(self.get_argument("nonce")) if self.get_argument("nonce") else 0
            data = str(self.get_argument("data"))
            value_ = int(value * 10 ** 18)
            # create raw transaction
            encoded = createRawTransaction(nonce, gas_price, startgas, to_addr, value_, data)
            # sending raw transaction 
            self.write(json.dumps(BaseHandler.success_ret_with_data(encoded), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_CreateRawTransaction error:{0} in {1}".format(e,get_linenumber()))

class ETH_SignRawTransaction(BaseHandler):
    def post(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            key = str(self.get_argument('key')) if self.get_argument('key') else '1be48a93cb149ea2cbc3e85db6056c83a37a1d7aafcee079c266dd05af2e7c31'
            data = str(self.get_argument("data")) if self.get_argument("data") else 'e980850ba43b740082520894ba1099cc91acdf45771d0a0c6e3b80e8e880c68488016345785d8a000080'
            # sending raw transaction
            encoded = signRawTransaction(key,data)
            self.write(json.dumps(BaseHandler.success_ret_with_data(encoded), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_SignRawTransaction error:{0} in {1}".format(e,get_linenumber()))

class ETH_SendRawTransaction(BaseHandler):
    def post(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            data = str(self.get_argument("data")) if self.get_argument("data") else '0xf86c80850ba43b740082520894ba1099cc91acdf45771d0a0c6e3b80e8e880c68488016345785d8a0000801ba0217def430ee63758f3142b20d7632f1b8d13864e83c50e4118a7caabe94dc353a06c5c12df29768a0fd54903fa76b01b27f1b1038e6ce2a3c5a3c8b07989f5974f'
            # 0x checking
            rlpdata = "0x" + data if "0x" not in data else data
            # sending raw transaction
            rsp = rpc_connection.eth_sendRawTransaction(rlpdata)
            self.write(json.dumps(BaseHandler.success_ret_with_data(rsp), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_SendRawTransaction error:{0} in {1}".format(e,get_linenumber()))

####################################################################################################################
# Timer ############################################################################################################
####################################################################################################################

class ETH_BlockNumber(BaseHandler):
    @staticmethod
    def latest(rpc_connection):
        return rpc_connection.eth_blockNumber()

    def get(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            data = ETH_BlockNumber.latest(rpc_connection)
            self.write(json.dumps(BaseHandler.success_ret_with_data(data), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_BlockNumber error:{0} in {1}".format(e,get_linenumber()))

class ETH_GetTransactionFromBlock(BaseHandler):
    @staticmethod
    def process(rpc_connection,blknumber,txindex):
        txdata =  rpc_connection.eth_getTransactionByBlockNumberAndIndex(blknumber,txindex)
        from utils import filtered,alterkeyname
        return filtered(alterkeyname(txdata,'hash','txid'),["nonce","hash","from","to","value","gas","gasPrice"])
    def get(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            blknumber = int(self.get_argument("blknumber")) if self.get_argument("blknumber") else int(ETH_BlockNumber.latest(rpc_connection))
            txindex = int(self.get_argument("txindex")) if self.get_argument("txindex") else 0
            data = ETH_GetTransactionFromBlock.process(rpc_connection,blknumber,txindex)
            self.write(json.dumps(BaseHandler.success_ret_with_data(data), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_GetTransactionFromBlock error:{0} in {1}".format(e,get_linenumber()))

class ETH_GetBlockTransactionCount(BaseHandler):
    @staticmethod
    def process(rpc_connection,blknumber):
        return rpc_connection.eth_getBlockTransactionCountByNumber(blknumber)

    def get(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            blknumber = int(self.get_argument("blknumber")) if self.get_argument("blknumber") else int(ETH_BlockNumber.latest(rpc_connection))
            data =  ETH_GetBlockTransactionCount.process(rpc_connection,blknumber)
            self.write(json.dumps(BaseHandler.success_ret_with_data(data), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_GetBlockTransactionCount error:{0} in {1}".format(e,get_linenumber()))


class ETH_GetBlockTransactions(BaseHandler):
    @staticmethod
    def process(rpc_connection,blknumber,txcount):
        txlist = []
        for index in range(txcount):
            txdata = ETH_GetTransactionFromBlock.process(rpc_connection,blknumber,index)
            txlist.append(txdata)
        return txlist

    def post(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            blknumber = int(self.get_argument("blknumber")) if self.get_argument("blknumber") else int(ETH_BlockNumber.latest(rpc_connection))
            txcount = int(ETH_GetBlockTransactionCount.process(rpc_connection,blknumber))
            data = ETH_GetBlockTransactions.process(rpc_connection,blknumber,txcount)
            self.write(json.dumps(BaseHandler.success_ret_with_data(data), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_GetBlockTransactions error:{0} in {1}".format(e,get_linenumber()))

####################################################################################################################
# Last Block Monitoring ############################################################################################
####################################################################################################################

class ETH_GetTransactionCount(BaseHandler):
    def post(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            address = self.get_argument("address")
            rsp = rpc_connection.eth_getTransactionCount(address)
            self.write(json.dumps(BaseHandler.success_ret_with_data(rsp), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_GetTransactionCount error:{0} in {1}".format(e,get_linenumber()))

class ETH_GetBlockByNumber(BaseHandler):
    def get(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            block_number = self.get_argument("number")
            block_number = int(block_number,16) if '0x' in block_number else int(block_number)
            tx_infos = rpc_connection.eth_getBlockByNumber(block_number)
            self.write(json.dumps(BaseHandler.success_ret_with_data(tx_infos), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_GetBlockByNumber Error:{0} in {1}".format(e,get_linenumber()))

class ETH_GetTransactionByHash(BaseHandler):
    def post(self):
        rpc_connection = EthereumProxy(ip_addr, port)
        try:
            tx_hash = self.get_argument("tx_hash")#?????not ready
            tx_info = rpc_connection.eth_getTransactionByHash(tx_hash)
            self.write(json.dumps(BaseHandler.success_ret_with_data(tx_info), default=decimal_default))
        except Exception as e:
            self.write(json.dumps(BaseHandler.error_ret_with_data("error: %s"%e)))
            print("ETH_GetTransactionByHash error:{0} in {1}".format(e,get_linenumber()))