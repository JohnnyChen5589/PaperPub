class IPManagement:
    OCC_SERVER_ADDRESS = ('192.168.1.25', 12348)
    OCC_CLIENT_ADDRESS = {
        "1": ('192.168.1.25', 12349),
        "2": ('192.168.1.25', 13349)
    }
    CU_SERVER_ADDRESS = ('192.168.1.27', 12351)
    CU_CLIENT_ADDRESS = [
        {"ip": "192.168.1.27", "port": 11001},
        {"ip": "192.168.1.27", "port": 11002},
    ]
    DEV_SERVER_ADDRESS = ('192.168.1.30', 12345)
    DEV_CLIENT_ADDRESS = ('192.168.1.30', 12346)
    DEV_DATA_KEY = 11002
