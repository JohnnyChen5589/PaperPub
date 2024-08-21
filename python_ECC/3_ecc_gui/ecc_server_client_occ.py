# OCC模擬
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
from packages.AppGUI import AppGUI
sys.path.append("..")
from IPManagement import IPManagement
from ConfigsManagement import ConfigsManagement

class ServerDataAndKeyManagement:
    def __init__(self):
        self.is_thread_looping: bool = True
        self.occ_priv_key = None
        self.occ_priv_key_base = PrivateKey.from_int(ConfigsManagement.OCC_PRIV_KEY)
        self.occ_cu_aes_key_dict: dict = {}
        self.occ_dev_aes_dict: dict = {}
        self.init_occ_to_dev_dict: dict = ConfigsManagement.INIT_OCC_TO_DEV_DICT
        self.occ_to_dev_dict: dict = copy.deepcopy(self.init_occ_to_dev_dict)
        self.dev_to_occ_dict: dict = {}
        self.shift_key: str = self.random_hex_str()
        self.cu_pub_key_dict: dict = {}
        self.dev_pub_key_dict: dict = {}
        self.logger = PerformanceLogger(ConfigsManagement.LOGS_PATH.get("3_occ"))
        
        self.update_private_key()

        self.occ_to_cu_client_dict: dict = self.init_udpclient()
    
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
        return AES.new(self.occ_priv_key.ecdh(bytes.fromhex(pub_key))[:16], AES.MODE_ECB)
        
    def update_dev_aes_dict(self, dev_id, pub_key):
        aes_key = self.calculate_aes_key(pub_key)
        self.occ_dev_aes_dict[dev_id] = aes_key

    def update_cu_aes_dict(self, train_id, pub_key):
        aes_key = self.calculate_aes_key(pub_key)
        self.occ_cu_aes_key_dict[train_id] = aes_key

    def update_private_key(self):
        # 私鑰更新
        # 16進制str私鑰
        hex_key = self.occ_priv_key_base.to_hex()

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
        self.occ_priv_key = PrivateKey.from_hex(result_hex)
    
    def random_hex_str(self):
        hex_chars = '0123456789abcdef'
        return ''.join(random.choice(hex_chars) for _ in range(5))
    
    def init_udpclient(self):
        udp_clients_dict: dict = {}
        for train_id, cu_ip in IPManagement.OCC_CLIENT_ADDRESS.items():
            udp_clients_dict[train_id] = OCCToCUClient(self, cu_ip)
            udp_clients_dict[train_id].send_data(train_id)
        
        return udp_clients_dict
    
    def update_all_aes_key(self):
        self.shift_key = server_and_data_key_management.random_hex_str()
        self.update_private_key()
        print(f'XXXXXXXXXXXXXXX更新公私鑰XXXXXXXXXXXXXXX: {self.occ_priv_key.public_key.format().hex()}')
        for train_id, pub_key in self.cu_pub_key_dict.items():
            self.update_cu_aes_dict(train_id, pub_key)
        for dev_id, pub_key in self.dev_pub_key_dict.items():
            self.update_dev_aes_dict(dev_id, pub_key)
        for train_id, client in self.occ_to_cu_client_dict.items():
            client.send_data(train_id)
    
class OCCToCUClient:
    def __init__(self, server_and_data_key_management, server_address):
        # 創建 UDP Socket
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 服務器地址和端口
        self.server_address = server_address
        # 保存資料管理員ref
        self.server_and_data_key_management = server_and_data_key_management
    
    # UI進入修改值
    def toggle_value_data(self, train_id, dev_id):
        cdt_ref = CheckDataType()
        dev_value = self.server_and_data_key_management.occ_to_dev_dict[train_id][dev_id]
        # 切換對應設備的值
        if cdt_ref.is_not_empty(dev_value):
            dev_value = 1 - int(dev_value)
        else:
            dev_value = 0
        
        self.server_and_data_key_management.occ_to_dev_dict[train_id][dev_id] = str(dev_value)
        self.send_encrypt_data(train_id, dev_id)
        print(f"設備 {train_id}, {dev_id} 的新值為: {self.server_and_data_key_management.occ_to_dev_dict[train_id].get(dev_id)}")

    # 發送加密消息
    def send_encrypt_data(self, train_id, dev_id):
        # 加密DEV
        cu_data_temp: dict = self.server_and_data_key_management.occ_to_dev_dict.get(train_id).copy()
        cdt_ref = CheckDataType()
        try:
            cu_aes_key = self.server_and_data_key_management.occ_cu_aes_key_dict.get(train_id)
            
            if cdt_ref.is_not_empty(cu_aes_key) and cdt_ref.is_not_empty(cu_data_temp):
                for dev_id, dev_id_data in cu_data_temp.items():
                    dev_aes_key = self.server_and_data_key_management.occ_dev_aes_dict.get(dev_id, {})
                    
                    if not (cdt_ref.is_not_empty(dev_aes_key) and cdt_ref.is_not_empty(dev_id_data)):
                        print(f'Client無法加密DEV_KEY: {dev_id}')
                        cu_data_temp[dev_id] = ""
                        continue
                    
                    if not cdt_ref.is_bytes(dev_id_data):
                        dev_id_data = dev_id_data.encode('utf-8')
                    
                    if cdt_ref.is_hex(dev_id_data):
                        dev_id_data = self.server_and_data_key_management.encrypted_data(dev_aes_key, dev_id_data)
                        
                    if cdt_ref.is_not_empty(dev_id_data):
                        cu_data_temp[dev_id] = dev_id_data
            else:
                print("Client不存在DEV加密資料 或是KEY與資料錯誤")
                cu_data_temp = self.server_and_data_key_management.init_occ_to_dev_dict.get(train_id)
            
            # 加密CU
            if cdt_ref.is_not_empty(cu_aes_key) and cdt_ref.is_json(cu_data_temp):
                cu_data_temp = json.dumps(cu_data_temp)
                cu_aes_key = self.server_and_data_key_management.occ_cu_aes_key_dict.get(train_id)
                
                if not (cdt_ref.is_not_empty(cu_aes_key)):
                    print(f'Client無法加密CU_KEY')
                    
                if not cdt_ref.is_bytes(cu_data_temp):
                    cu_data_temp = cu_data_temp.encode('utf-8')
                
                if cdt_ref.is_hex(cu_data_temp):
                    cu_data_temp = self.server_and_data_key_management.encrypted_data(cu_aes_key, cu_data_temp)
            else:
                print("Client不存在CU加密資料 或是KEY與資料錯誤")
                cu_data_temp = self.server_and_data_key_management.init_occ_to_dev_dict.get(train_id)
            
        except Exception as e:
            print(f'Client CU or DEV例外: {e}')
            cu_data_temp = self.server_and_data_key_management.init_occ_to_dev_dict.get(train_id)

        data_to_send = {
            "occ_pub_key": self.server_and_data_key_management.occ_priv_key.public_key.format().hex(),
            "data": cu_data_temp
        }

        json_data = json.dumps(data_to_send)

        # 發送數據到服務器
        print(f'OCC->CU{train_id}: {json_data}')

        if ConfigsManagement.IS_LOGS_ON:
            self.server_and_data_key_management.logger.log_performance(sys.getsizeof(json_data), "OCC_TO_CU")
        
        self.client_socket.sendto(json_data.encode('utf-8'), self.server_address)

        # 接收服務器的響應
        #response, _ = client_socket.recvfrom(4096)
        #print('從服務器收到響應:', response.decode())
    
    # 發送OCC公鑰消息
    def send_data(self, train_id):
        data_to_send = {
            "occ_pub_key": self.server_and_data_key_management.occ_priv_key.public_key.format().hex(),
            "data": self.server_and_data_key_management.init_occ_to_dev_dict.get(train_id)
        }

        json_data = json.dumps(data_to_send)

        # 發送數據到服務器
        print(f'OCC->CU更新KEY: {json_data}')

        if ConfigsManagement.IS_LOGS_ON:
            self.server_and_data_key_management.logger.log_performance(sys.getsizeof(json_data), "OCC_TO_CU_UPDATE")
        
        self.client_socket.sendto(json_data.encode('utf-8'), self.server_address)

def server_function(server_and_data_key_management: ServerDataAndKeyManagement):
    # 創建 UDP Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 綁定到特定的地址和端口
    server_address = IPManagement.OCC_SERVER_ADDRESS
    server_socket.bind(server_address)
    
    # 檢查資料是否合法
    cdt_ref = CheckDataType()

    # 跟新key的clock
    key_clock: int = 1
    while server_and_data_key_management.is_thread_looping :
        #print('等待接收數據...')
        data, address = server_socket.recvfrom(4096)
        try:
            # 週期更新OCC私鑰
            is_update_occ_priv_key_clock: bool = key_clock % ConfigsManagement.UPDATE_OCC_PRIV_KEY_CLOCK == 0
            
            # 將接收到的數據解析為 JSON
            json_data = json.loads(data.decode('utf-8'))
            print(f'DEV->OCC: {json_data}')
            if ConfigsManagement.IS_LOGS_ON:
                server_and_data_key_management.logger.log_performance(sys.getsizeof(json_data), "DEV_TO_OCC")

            cu_pub_key_dict_ref: dict = json_data.get('cu_pub_key', {})
            if not cdt_ref.is_not_empty(cu_pub_key_dict_ref):
                continue

            first_train_id: str = next(iter(cu_pub_key_dict_ref))
            
            # 取得第一筆CU公鑰
            if cdt_ref.is_not_empty(first_train_id) and not cdt_ref.is_not_empty(cu_pub_key_dict_ref.get(first_train_id)):
                #server_and_data_key_management.occ_to_cu_client_dict.get(first_train_id).send_data(first_train_id)
                continue
            
            # 更新公私鑰
            if ConfigsManagement.IS_UPDATE_OCC_PRIV_KEY and is_update_occ_priv_key_clock:
                server_and_data_key_management.update_all_aes_key()
                key_clock = 0
            
            # 更新cu_pub_key_dict
            cu_pub_key_dict = server_and_data_key_management.cu_pub_key_dict

            for train_id, pub_key in cu_pub_key_dict_ref.items():
                if train_id not in cu_pub_key_dict or cu_pub_key_dict[train_id] != pub_key:
                    server_and_data_key_management.update_cu_aes_dict(train_id, pub_key)
                    cu_pub_key_dict[train_id] = pub_key

            
            # 更新dev_pub_key_dict
            dev_pub_key_dict = server_and_data_key_management.dev_pub_key_dict

            for dev_id, pub_key in json_data.get('dev_pub_key_dict', {}).items():
                if dev_id not in dev_pub_key_dict or dev_pub_key_dict[dev_id] != pub_key:
                    server_and_data_key_management.update_dev_aes_dict(dev_id, pub_key)
                    dev_pub_key_dict[dev_id] = pub_key

            # 解密DEV資料
            dev_data = json_data['data']
            
            try:
                if cdt_ref.is_not_empty(dev_data) and cdt_ref.is_json(dev_data):
                    for dev_id, dev_id_data in dev_data.items():
                        dev_aes_key = server_and_data_key_management.occ_dev_aes_dict.get(dev_id, "")
                        
                        if not (cdt_ref.is_not_empty(dev_aes_key) and cdt_ref.is_not_empty(dev_id_data)):
                            print(f'Server無法解密DEV_KEY: {dev_id}')
                            continue

                        if not cdt_ref.is_bytes(dev_id_data):
                            dev_id_data = bytes.fromhex(dev_id_data)
                        
                        if cdt_ref.is_hex(dev_id_data):
                            dev_id_data = server_and_data_key_management.decrypted_data(dev_aes_key, dev_id_data)
                        
                        if cdt_ref.is_not_empty(dev_id_data):
                            server_and_data_key_management.dev_to_occ_dict[dev_id] = dev_id_data
                else:
                    print("Server不存在DEV解密資料 或是KEY與資料錯誤")
            except Exception as e:
                print(f'Server DEV例外: {e}')
            
            print(f'OCC監控資料: {server_and_data_key_management.dev_to_occ_dict}')
        except json.JSONDecodeError:
            print('接收到的數據不是有效的 JSON 格式')
        # 假設服務器也向客戶端發送一個簡單的響應
        #response_data = {'response': 'Data received successfully'}
        #response_json = json.dumps(response_data)
        #server_socket.sendto(response_json.encode(), address)
        
        # 迴圈運行一次
        key_clock += 1
        # 等待
        time.sleep(ConfigsManagement.OCC_SERVER_SLEEP_TIME)

def on_closing():
    server_and_data_key_management.is_thread_looping = False
    appgui.destroy()

def test_function(server_and_data_key_management: ServerDataAndKeyManagement):
    while server_and_data_key_management.is_thread_looping:
        for train_id, dev_dict in server_and_data_key_management.occ_to_dev_dict.items():
            for dev_id, var in dev_dict.items():
                server_and_data_key_management.occ_to_cu_client_dict.get(train_id).toggle_value_data(train_id, dev_id)
        time.sleep(10)

if __name__ == "__main__":
    # 創建秘鑰管理員
    server_and_data_key_management = ServerDataAndKeyManagement()

    # GUI控制
    appgui = AppGUI(server_and_data_key_management)

    # 創建服務器線程
    server_thread = threading.Thread(target=server_function, args=(server_and_data_key_management,))
    server_thread.start()

    # 創建測試線程
    test_thread = threading.Thread(target=test_function, args=(server_and_data_key_management,))

    if ConfigsManagement.TEST_MODE:
        test_thread.start()

    # 啟動UI
    appgui.protocol("WM_DELETE_WINDOW", on_closing)
    appgui.mainloop()
    
    # 等待服務器和客戶端線程結束
    if server_thread.is_alive():
        server_thread.join()
    
    if test_thread.is_alive():
        test_thread.join()
