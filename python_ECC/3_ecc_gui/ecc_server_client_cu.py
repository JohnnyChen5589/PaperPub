# CU模擬
import socket
import json
import threading
import time
import sys
import random
import copy
from coincurve import PrivateKey
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from packages.CheckDataType import CheckDataType
from packages.PerformanceLogger import PerformanceLogger
sys.path.append("..")
from IPManagement import IPManagement
from ConfigsManagement import ConfigsManagement

class ServerDataAndKeyManagement:
    def __init__(self):
        self.cu_priv_key = None
        self.cu_priv_key_base = PrivateKey.from_int(ConfigsManagement.CU_PRIV_KEY)
        self.occ_cu_aes_key = None
        self.shift_key: str = self.random_hex_str()
        self.server_json_data: dict = {}
        self.occ_pub_key = ''
        self.init_cu_to_dev_dict: dict = copy.deepcopy(ConfigsManagement.INIT_CU_TO_DEV_DICT)
        self.logger = PerformanceLogger(ConfigsManagement.LOGS_PATH.get("3_cu"))
        self.is_client_needs_update_key: bool = False

        self.update_private_key()

    def encrypted_data(self, aes_key, decrypted_data: bytes):
        str_data: str = None
        try:
            str_data = aes_key.encrypt(pad(decrypted_data, AES.block_size)).hex()
        except Exception as e:
            pass
        return str_data

    def decrypted_data(self, aes_key, encrypted_data: bytes):
        str_data: str= None
        try:
            str_data = unpad(aes_key.decrypt(bytes.fromhex(encrypted_data.hex())), AES.block_size).decode('utf-8')
        except Exception as e:
            pass
        return str_data

    def calculate_aes_key(self, pub_key):
        return AES.new(self.cu_priv_key.ecdh(bytes.fromhex(pub_key))[:16], AES.MODE_ECB)
    
    def update_private_key(self):
        # 私鑰更新
        # 16進制str私鑰
        hex_key = self.cu_priv_key_base.to_hex()

        # 較短的XOR鍵
        short_xor_key = self.shift_key

        # 將短XOR鍵擴展到與私鑰相同的長度
        extended_xor_key = (short_xor_key * (len(hex_key) // len(short_xor_key) + 1))[:len(hex_key)]

        # 將16進制數轉換為整數進行XOR運算
        int_key = int(hex_key, 16)
        int_xor_key = int(extended_xor_key, 16)
        xor_result = int_key ^ int_xor_key

        # 將XOR運算結果轉換回16進制格式
        result_hex = hex(xor_result)[2:].zfill(len(hex_key))
        self.cu_priv_key = PrivateKey.from_hex(result_hex)
    
    def random_hex_str(self):
        hex_chars = '0123456789abcdef'
        return ''.join(random.choice(hex_chars) for _ in range(5))
    
class UDPClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.data = None

    def send_data(self, data):
        self.sock.sendto(data.encode(), (self.ip, self.port))
        if ConfigsManagement.IS_LOGS_ON:
            server_and_data_key_management.logger.log_performance(sys.getsizeof(data), "CU_TO_DEV")
        print(f'CU->DEV: {data}')

def server_function(server_and_data_key_management: ServerDataAndKeyManagement):
    # 創建 UDP Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 綁定到特定的地址和端口
    server_address = IPManagement.CU_SERVER_ADDRESS
    server_socket.bind(server_address)

    cdt_ref = CheckDataType()
    while True:
        #print('等待接收數據...')
        data, address = server_socket.recvfrom(4096)
        
        # 將接收到的數據解析為 JSON
        try:
            json_data = json.loads(data.decode('utf-8'))
            if ConfigsManagement.IS_LOGS_ON:
                server_and_data_key_management.logger.log_performance(sys.getsizeof(data), "OCC_TO_CU")
            print(f'OCC->CU: {data}')
            server_and_data_key_management.server_json_data = json_data
            
            if not cdt_ref.is_not_empty(json_data.get('occ_pub_key', '')):
                continue
    
            # 更新公私鑰
            if server_and_data_key_management.occ_pub_key != json_data.get('occ_pub_key', ''):
                server_and_data_key_management.occ_pub_key = json_data.get('occ_pub_key', '')
                server_and_data_key_management.occ_cu_aes_key = server_and_data_key_management.calculate_aes_key(server_and_data_key_management.occ_pub_key)
                print(f'XXXXXXXXXXXXXXX計算公私鑰XXXXXXXXXXXXXXX: {server_and_data_key_management.cu_priv_key.public_key.format().hex()}')
                server_and_data_key_management.is_client_needs_update_key = True
            """elif counter % 19 == 0:
                server_and_data_key_management.shift_key = server_and_data_key_management.random_hex_str()
                server_and_data_key_management.update_private_key()
                server_and_data_key_management.occ_cu_aes_key = server_and_data_key_management.calculate_aes_key(server_and_data_key_management.occ_pub_key)
                print(f'XXXXXXXXXXXXXXX更新公私鑰XXXXXXXXXXXXXXX: {server_and_data_key_management.cu_priv_key.public_key.format().hex()}')"""
            
            cu_encrypted_data = server_and_data_key_management.server_json_data.get('data', {})
            
            # 解密CU
            if cdt_ref.is_not_empty(cu_encrypted_data):
                cu_aes_key = server_and_data_key_management.occ_cu_aes_key

                if not (cdt_ref.is_not_empty(cu_aes_key)):
                    print(f'Server無法解密CU_KEY')
                    continue
                
                if cdt_ref.is_json(cu_encrypted_data):
                    continue

                if not cdt_ref.is_bytes(cu_encrypted_data):
                    cu_encrypted_data = bytes.fromhex(cu_encrypted_data)
                
                if cdt_ref.is_hex(cu_encrypted_data):
                    cu_encrypted_data = server_and_data_key_management.decrypted_data(cu_aes_key, cu_encrypted_data)
                
            else:
                print("Server不存在CU解密資料 或是KEY與資料錯誤")
            
            if not cdt_ref.is_not_empty(cu_encrypted_data):
                print(f'無法正常解密 CU公鑰: {server_and_data_key_management.cu_priv_key.public_key.format().hex()}')
                server_and_data_key_management.server_json_data['data'] = server_and_data_key_management.init_cu_to_dev_dict
                server_and_data_key_management.is_client_needs_update_key = True
                continue
            
            cu_decrypted_data = json.loads(cu_encrypted_data)
            
            server_and_data_key_management.server_json_data['data'] = cu_decrypted_data
            
        except json.JSONDecodeError:
            print('接收到的數據不是有效的 JSON 格式')
        
        # 假設服務器也向客戶端發送一個簡單的響應
        #response_data = {'response': 'Data received successfully'}
        #response_json = json.dumps(response_data)
        #server_socket.sendto(response_json.encode(), address)
        
        # 等待
        time.sleep(ConfigsManagement.CU_SERVER_SLEEP_TIME)

def client_function(client, server_and_data_key_management: ServerDataAndKeyManagement):
    while True:
        cdt_ref = CheckDataType()
        try:
            # 從隊列中獲取數據
            if not cdt_ref.is_not_empty(server_and_data_key_management.server_json_data):
                print("Client沒有資料請等待")
                continue
            
            server_data = server_and_data_key_management.server_json_data.get('data', {})

            # 用port判斷送出資訊
            if str(client.port) in server_data:
                if client.data is not server_data[str(client.port)] or server_and_data_key_management.is_client_needs_update_key:
                    json_data = json.dumps({
                        "occ_pub_key": server_and_data_key_management.occ_pub_key,
                        "cu_pub_key": server_and_data_key_management.cu_priv_key.public_key.format().hex(),
                        "data": {
                            str(client.port): server_data[str(client.port)]
                            }
                        })
                    # 發送數據到服務器
                    client.send_data(json_data)
                    client.data = server_data[str(client.port)]
            
            server_and_data_key_management.is_client_needs_update_key = False
            
        except Exception as e:
            print(f'Client CU例外: {e}')
        
        # 接收服務器的響應
        #response, _ = client_socket.recvfrom(4096)
        #print('從服務器收到響應:', response.decode())

        # 等待
        time.sleep(ConfigsManagement.CU_CLIENT_SLEEP_TIME)


if __name__ == "__main__":
    # 創建秘鑰管理員
    server_and_data_key_management = ServerDataAndKeyManagement()

    # 設定客戶端 ip 與 port
    client_info = IPManagement.CU_CLIENT_ADDRESS

    # 創建多個客戶端
    clients = [UDPClient(info["ip"], info["port"]) for info in client_info]

    # 創建服務器線程
    server_thread = threading.Thread(target=server_function, args=(server_and_data_key_management,))
    server_thread.start()
    
    client_threads = []

    # 創建客戶端線程
    for client in clients:
        t = threading.Thread(target=client_function, args=(client, server_and_data_key_management,))
        client_threads.append(t)
        t.start()
    
    # 等待服務器和客戶端線程結束
    server_thread.join()
    for client_thread in client_threads:
        client_thread.join()
