from app.parsers import parse_kbank, parse_krungsri

KRUNGSRI = '''Dear SIRAVICH JITPREMVANICH,
Please be notified of your bill payment transaction via krungsri app as follows:
Transaction Result: Success
Type of Transaction: Bill Payment
From Account: SIRAVICH JITP
To Biller: JENKONGKLAI PUBLIC COMPANY LIMITED
Amount (THB): 40.00
Fee (THB): 0.00
ORDER ID: AP35051791542888
MOBILE NO.: AP35051791542888126
Reference No.: KSA00000000980548504
Date/Time: 09/10/2026 19:16:07
'''

KBANK = '''Dear Customer of mobile number 09-XXXX-5498
Subject: Result of PromptPay Funds Transfer (Success)
With reference to your request for funds transfer via K PLUS Service as follows:
Transaction Date: 09/10/2026  13:01:35
Transaction Number: 016282130135BPP02725
From Account: xxx-x-x2262-x
To PromptPay ID: xxx-xxx-7975
Received Name: MS. Tanyaton Oranrigsupak
Amount (THB): 498.00
Fee (THB): 0.00
Available Balance (THB): 42,662.56
'''


def test_krungsri():
    tx = parse_krungsri(KRUNGSRI)
    assert tx is not None
    assert str(tx['amount']) == '40.00'
    assert tx['counterparty'] == 'JENKONGKLAI PUBLIC COMPANY LIMITED'
    assert tx['category'] == 'Bills & Utilities'
    assert tx['occurred_at'].isoformat() == '2026-10-09T19:16:07+07:00'


def test_kbank():
    tx = parse_kbank(KBANK)
    assert tx is not None
    assert str(tx['amount']) == '498.00'
    assert tx['counterparty'] == 'MS. Tanyaton Oranrigsupak'
    assert tx['category'] == 'Transfer / Review'
    assert tx['occurred_at'].isoformat() == '2026-10-09T13:01:35+07:00'
