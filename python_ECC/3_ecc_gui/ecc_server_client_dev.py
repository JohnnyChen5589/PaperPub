# DEV模擬
import socket
import json
import threading
import time
import sys
from coincurve import PrivateKey
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from packages.CheckDataType import CheckDataType
from packages.PerformanceLogger import PerformanceLogger
sys.path.append("..")
from IPManagement import IPManagement
from ConfigsManagement import ConfigsManagement

try:
    from packages.LedGPIO import LedGPIO
    gpiod_available = True
except ImportError:
    gpiod_available = False

class ServerDataAndKeyManagement:
    def __init__(self):
        self.dev_priv_key = PrivateKey.from_int(ConfigsManagement.DEV_PRIV_KEY)
        self.occ_dev_aes = None
        self.occ_pub_key = ''
        self.cu_pub_key = ''
        self.dev_decrypted_data = ''
        self.data_key = IPManagement.DEV_DATA_KEY

        self.logger = PerformanceLogger(ConfigsManagement.LOGS_PATH.get("3_dev"))

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
        return AES.new(self.dev_priv_key.ecdh(bytes.fromhex(pub_key))[:16], AES.MODE_ECB)
    
def server_function(server_and_data_key_management):
    # 創建 UDP Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 綁定到特定的地址和端口
    server_address = IPManagement.DEV_SERVER_ADDRESS
    server_socket.bind(server_address)

    print('UDP 服務器啟動...')
    led = None
    if gpiod_available:
        led = LedGPIO()
    
    while True:
        #print('等待接收數據...')
        data, address = server_socket.recvfrom(4096)
        # 將接收到的數據解析為 JSON
        try:
            json_data = json.loads(data.decode('utf-8'))
            if ConfigsManagement.IS_LOGS_ON:
                server_and_data_key_management.logger.log_performance(sys.getsizeof(data), "CU_TO_DEV")
            print(f'CU->DEV: {json_data}')
            try:
                if json_data.get('occ_pub_key', '') != server_and_data_key_management.occ_pub_key:
                    server_and_data_key_management.occ_pub_key = json_data.get('occ_pub_key', '')
                    server_and_data_key_management.occ_dev_aes = server_and_data_key_management.calculate_aes_key(server_and_data_key_management.occ_pub_key)
                
                if json_data.get('cu_pub_key', '') != server_and_data_key_management.cu_pub_key:
                    server_and_data_key_management.cu_pub_key = json_data.get('cu_pub_key', '')
                
                # 解秘DEV資料
                dev_data = json_data['data']
                cdt_ref = CheckDataType()
                
                if cdt_ref.is_not_empty(dev_data) and cdt_ref.is_json(dev_data):                    
                    for dev_id, dev_id_data in dev_data.items():
                        dev_aes_key = server_and_data_key_management.occ_dev_aes
                        
                        if not (cdt_ref.is_not_empty(dev_aes_key) and cdt_ref.is_not_empty(dev_id_data)):
                            print(f'Server無法解密DEV_KEY: {dev_id}')
                            continue
                        
                        if not cdt_ref.is_bytes(dev_id_data):
                            dev_id_data = bytes.fromhex(dev_id_data)
                        
                        if cdt_ref.is_hex(dev_id_data):
                            dev_id_data = server_and_data_key_management.decrypted_data(dev_aes_key, dev_id_data)
                        
                        if cdt_ref.is_not_empty(dev_id_data):
                            print(f'成功解密: {dev_id}, {dev_id_data}')
                            server_and_data_key_management.dev_decrypted_data = dev_id_data
                        else:
                            print(f'解密失敗: {dev_id}')
                            continue
                        
                        if not gpiod_available:
                            continue

                        if int(dev_id_data) == 0:
                            led.turn_off()
                        elif int(dev_id_data) == 1:
                            led.turn_on()
                        else:
                            pass
                else:
                    print("Server不存在DEV解密資料 或是KEY與資料錯誤")
            
            except Exception as e:
                print(f'Server DEV例外: {e}')
            
        except json.JSONDecodeError:
            print('接收到的數據不是有效的 JSON 格式')

        # 假設服務器也向客戶端發送一個簡單的響應
        #response_data = {'response': 'Data received successfully'}
        #response_json = json.dumps(response_data)
        #server_socket.sendto(response_json.encode(), address)

        # 等待
        time.sleep(ConfigsManagement.DEV_SERVER_SLEEP_TIME)

def client_function(server_and_data_key_management):
    # 創建 UDP Socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 服務器地址和端口
    server_address = IPManagement.DEV_CLIENT_ADDRESS

    while True:
        
        try:
            dev_data_temp = str(f'{server_and_data_key_management.dev_decrypted_data},{int(time.time())}')
            # 加密DEV
            cdt_ref = CheckDataType()
            dev_aes_key = server_and_data_key_management.occ_dev_aes
            if cdt_ref.is_not_empty(dev_data_temp) and cdt_ref.is_not_empty(dev_aes_key):
                
                if not cdt_ref.is_bytes(dev_data_temp):
                    dev_data_temp = dev_data_temp.encode('utf-8')
                
                if cdt_ref.is_hex(dev_data_temp):
                    dev_data_temp = server_and_data_key_management.encrypted_data(dev_aes_key, dev_data_temp)
            else:
                print("Client不存在DEV加密資料 或是KEY與資料錯誤")
                dev_data_temp = ""
        except Exception as e:
            print(f'Client DEV例外: {e}')
        
        data_to_send = {
            # 每個CU只能有一個DEV轉傳cu_pub_key
            "cu_pub_key": {ConfigsManagement.CU_DEV_TRAIN_ID:server_and_data_key_management.cu_pub_key,},
            "dev_pub_key_dict": {
                str(server_and_data_key_management.data_key): server_and_data_key_management.dev_priv_key.public_key.format().hex(),
            },
            "data": {
                str(server_and_data_key_management.data_key): dev_data_temp
            }
        }
        json_data = json.dumps(data_to_send)

        # 發送數據到服務器
        if ConfigsManagement.IS_LOGS_ON:
            server_and_data_key_management.logger.log_performance(sys.getsizeof(json_data), "DEV_TO_OCC")
        print(f'DEV->OCC: {json_data}')
        client_socket.sendto(json_data.encode(), server_address)
        #print('已發送數據到服務器:', json_data)

        # 接收服務器的響應
        #response, _ = client_socket.recvfrom(4096)
        #print('從服務器收到響應:', response.decode())

        # 等待
        time.sleep(ConfigsManagement.DEV_CLIENT_SLEEP_TIME)


    # 關閉客戶端 Socket
    client_socket.close()

if __name__ == "__main__":
    # 創建秘鑰管理員
    server_and_data_key_management = ServerDataAndKeyManagement()
    # 創建服務器線程
    server_thread = threading.Thread(target=server_function, args=(server_and_data_key_management,))
    server_thread.start()

    # 創建客戶端線程
    client_thread = threading.Thread(target=client_function, args=(server_and_data_key_management,))
    client_thread.start()

    # 等待服務器和客戶端線程結束
    server_thread.join()
    client_thread.join()
