class IPManagement:
    OCC_SERVER_ADDRESS = ('192.168.1.25', 12348)
    OCC_CLIENT_ADDRESS = {
        "1": ('192.168.1.25', 12349),
        "2": ('192.168.1.25', 13349)
    }
    CU_SERVER_ADDRESS = ('192.168.1.28', 12351)
    CU_CLIENT_ADDRESS = [
        {"ip": "192.168.1.28", "port": 21001},
        {"ip": "192.168.1.28", "port": 21002},
    ]
    DEV_SERVER_ADDRESS = ('192.168.1.31', 12345)
    DEV_CLIENT_ADDRESS = ('192.168.1.31', 12346)
    DEV_DATA_KEY = 21001
