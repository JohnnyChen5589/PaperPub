import time
import csv
import psutil
import os

class PerformanceLogger:
    def __init__(self, filename: str="performance_data.csv"):
        self.filename = os.path.join(os.getcwd(), "csv_data", filename)
        self.fields = ["Timestamp", "Data Size (bytes)", "CPU Usage (%)", "Memory Usage (%)", "Steps"]
        self.csvfile = open(self.filename, "a", newline="")
        self.writer = csv.DictWriter(self.csvfile, fieldnames=self.fields)
        self.create_csv_file()

    def create_csv_file(self):
        file_size = os.path.getsize(self.filename) if os.path.exists(self.filename) else 0

        if file_size == 0:
            self.writer.writeheader()

    def log_performance(self, data_size: int=0, steps: str=""):
        timestamp = time.time()
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent

        data = {
            "Timestamp": timestamp,
            "Data Size (bytes)": data_size,
            "CPU Usage (%)": cpu_usage,
            "Memory Usage (%)": memory_usage,
            "Steps": steps,
        }

        self.writer.writerow(data)
        self.csvfile.flush()

    def close(self):
        self.csvfile.close()
