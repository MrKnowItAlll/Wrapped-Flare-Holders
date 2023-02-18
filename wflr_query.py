import json
import requests
from web3 import Web3

#rpcurl = "https://rpc.viri.uk/http"
#web3 = Web3(Web3.HTTPProvider(rpcurl))


# json helper funcs
def read_json(path):
    with open(path) as json_file:
        return json.load(json_file)


def write_json(data, path):
    with open(path, 'w') as json_file:
        json.dump(data, json_file, indent=2)


# Check if account had FLR amount on Genesis Block
def block_0_account(account):
    try:
        req = requests.get(
            "https://flare-explorer.flare.network/api?module=account&action=eth_get_balance&address=" + account +
            "&block=0")
        account_balance_0 = req.json()

        if account_balance_0['result'] != "0":
            return True
        else:
            return False
    except:
        return False


# Check if account got FLR from an internal transaction and the amount was above 3M
def from_internal_transaction(account):
    try:
        req = requests.get(
            "https://flare-explorer.flare.network/api?module=account&action=txlistinternal&address=" + account)
        internal_trans = req.json()

        for tx in internal_trans['result']:
            if tx['to'] == account and Web3.fromWei(int(tx['value']), 'ether') > 3000000:
                return True
        return False
    except:
        return False


# check where did the account FLR originated from
# CHECK FOR:
#          1.Did the FLR originated at Genesis
#          2.Did the FLR originated from an Internal transaction and amount above 3M
#          3.Did the account received more than 1k FLR before TDE
#          4.Did the FLR(over 100k) received from an account that existed at Genesis
#          5.Did the FLR(over 100k) received from other account from the above
def check_account_flr_tokens(account):
    if block_0_account(account):
        return "Block #0 account"
    if from_internal_transaction(account):
        return "Internal Transaction FLR received from Contract"
    for i in range(1, 100):
        req = requests.get("https://flare-explorer.flare.network/api?module=account&action=txlist&address=" + account +
                           "&page=" + "{}".format(i))
        account_transactions = req.json()
        if len(account_transactions['result']) == 0:
            return "eligible"
        for tx in account_transactions['result']:
            if int(tx['timeStamp']) < 1673274938 and Web3.fromWei(int(tx['value']), 'ether') > 1000:
                return "Recieved Flare before TDE"
            if Web3.fromWei(int(tx['value']), 'ether') > 1000000 and block_0_account(tx['from']):
                return "Recieved Flare from Block #0 account"
            if Web3.fromWei(int(tx['value']), 'ether') > 1000000 and account_searched(tx['from']):
                return "Recieved Flare from Other team account: {}".format(tx['from'])
    return "eligible"

# Get a list of WFLR holder above 1M WFLR
def get_wflr_holders():
    holders_list = []
    # search in 20 pages should be enough
    for i in range(1, 20):
        req = requests.get(
            "https://flare-explorer.flare.network/api?module=token&action=getTokenHolders&contractaddress=" +
            "0x1d80c49bbbcd1c0911346656b529df9e5c2f783d" + "&page=" + "{}".format(i))
        holders = req.json()
        for holder in holders['result']:
            if Web3.fromWei(int(holder['value']), 'ether') > 1000000:
                holders_list.append({
                    'address': holder['address'],
                    'amount': "{}".format(Web3.fromWei(int(holder['value']), 'ether'))
                })
    return holders_list

# Add a suspected Team/VC/backers account to the list
def add_verified(account, amount, reason):
    verified = read_json('verified_flr_accounts.json')
    verified.append({
        "account": account,
        "amount": amount,
        "reason": reason,
    })
    write_json(verified, 'verified_flr_accounts.json')


# Check if this account already got marked as team wallet
def account_searched(account):
    verified = read_json('verified_flr_accounts.json')
    for ver in verified:
        if ver['account'] == account:
            return True
    return False


# Get verified wallet holding amount from json
def get_verified_account_amount(account):
    verified = read_json('verified_flr_accounts.json')
    for ver in verified:
        if ver['account'] == account:
            return ver['amount']
    return 0


# Get WFLR holders
holders = get_wflr_holders()
write_json(holders, "wflr_holders.json")

# Parse through the list and search for potential candidates
total_flr_not_eligble = 0
for holder in holders:
    if not account_searched(holder['address']):
        print("Checking for account: {}".format(holder['address']))
        reason = check_account_flr_tokens(holder['address'])
        if reason != "eligible":
            holder_amount = float(holder['amount'])
            total_flr_not_eligble += holder_amount
            add_verified(holder['address'], holder_amount, reason)
            print("Not eligibale amount found : {} current sum: {}".format(holder_amount, total_flr_not_eligble))
    else:
        total_flr_not_eligble += get_verified_account_amount(holder['address'])
        print("current sum: {}".format(total_flr_not_eligble))

print("Total uneligble WFLR: {}".format(total_flr_not_eligble))