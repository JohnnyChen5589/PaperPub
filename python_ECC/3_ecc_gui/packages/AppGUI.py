import tkinter as tk
from tkinter import ttk
import sys
sys.path.append("..")

class AppGUI(tk.Tk):
    def __init__(self, server_and_data_key_management):
        super().__init__()
        self.title("OCC模擬器")
        self.geometry("1000x300")
        # 發送與接收資料
        self.server_and_data_key_management = server_and_data_key_management
        
        # 創建一個框架容器來放置按鈕
        b_frame = ttk.Frame(self)
        b_frame.pack(pady=20)

        # 創建按鈕並綁定事件處理函數
        for train_id, dev_dict in self.server_and_data_key_management.occ_to_dev_dict.items():
            for dev_id, var in dev_dict.items():
                button = ttk.Button(b_frame, text=f"設備 {train_id} {dev_id}", command=lambda dev_id=dev_id, train_id=train_id: self.toggle_value(train_id, dev_id))
                button.pack(side=tk.LEFT, padx=10)
        
        l_frame = ttk.Frame(self)
        l_frame.pack()
        l_frame.place(relx=0.0, rely=0.5, anchor=tk.W)
        self.label = ttk.Label(l_frame, text="WAIT")
        self.label.pack()
        self.update_label()
    
    # 按按鈕後UI輸出修改值
    def toggle_value(self, train_id, dev_id):
        # 切換對應設備的值並送出
        self.server_and_data_key_management.occ_to_cu_client_dict.get(train_id).toggle_value_data(train_id, dev_id)
    
    # 顯示當前狀態
    def update_label(self):
        dev_pub_key = '\n'.join([f"{key}: {value}" for key, value in self.server_and_data_key_management.dev_pub_key_dict.items()])
        data = str(f'\
                       OCC->DEV: {self.server_and_data_key_management.occ_to_dev_dict}\n\
                       DEV->OCC: {self.server_and_data_key_management.dev_to_occ_dict}\n\
                       OCC public key: {self.server_and_data_key_management.occ_priv_key.public_key.format().hex()}\n\
                       CU public key: {self.server_and_data_key_management.cu_pub_key_dict}\n\
                       DEV public key: \n{dev_pub_key}\n\
                       ')
        self.label.config(text=data)
        self.label.after(100, self.update_label)
