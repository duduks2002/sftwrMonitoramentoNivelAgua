import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import serial
import csv
import threading
import time

class LeitorArduirno:
    def __init__(self, port):
        self.serial_port = port
        self.serial_connection = None
        self.is_reading = False
        self.data = []
        self.root = None
        self.connected = False
        self.read_thread = None
        self.lock = threading.Lock()  # Semaphore para proteger o acesso a recursos compartilhados

    def connect(self):
        try:
            self.serial_connection = serial.Serial(self.serial_port, baudrate=9600, timeout=2)
            self.connected = True
            return True
        except serial.SerialException as e:
            messagebox.showerror("Erro", f"Erro na conexão com Arduino: {e}")
            return False

    def disconnect(self):
        if self.serial_connection:
            self.serial_connection.close()
            self.connected = False

    def read_data(self):
        while self.is_reading:
            try:
                line = self.serial_connection.readline().decode("utf-8").strip()
                if line:
                    with self.lock:
                        self.data.append(line)
                    if line == "LIMITE ALCANÇADO !!":
                        self.show_alert()
            except serial.SerialException as e:
                messagebox.showerror("Erro", f"Erro na leitura do Arduino: {e}")
                self.disconnect()
                self.is_reading = False
                break
            except Exception as e:
                messagebox.showerror("Erro", f"Erro inesperado: {e}")
                self.disconnect()
                self.is_reading = False
                break
            time.sleep(0.1)  # Aguarda um pouco antes de ler novamente

    def start_reading(self):
        if not self.is_reading and self.connected:
            self.is_reading = True
            self.read_thread = threading.Thread(target=self.read_data)
            self.read_thread.start()

    def stop_reading(self):
        self.is_reading = False
        if self.read_thread:
            self.read_thread.join()  # Espera a thread de leitura terminar

    def show_alert(self):
        resposta = messagebox.askyesno("Alerta", "LIMITE ALCANÇADO!\nDeseja acender o LED?")
        if resposta:
            self.acender_led()

    def acender_led(self):
        c = 0
        try:
            self.serial_connection.write(b'5')  # Envia o comando para o Arduino
            while c<6:
                self.serial_connection.write(b'5')
                c +=1
                self.serial_connection.flush()
            time.sleep(2) #aguarda para tentar pegar de primeira a mensagem de conclusao do LED    
            response = self.serial_connection.readline().decode("utf-8").strip()  # Aguarda a resposta
            time.sleep(5) #aguarda a leitura da linha anterior, pois estava passando direto mesmo quando o led acendia
            if response == "LED ACESO":
                messagebox.showinfo("Sucesso", "LED acendido com sucesso!")
            else:
                messagebox.showerror("Erro", f"Falha ao acender o LED: {response}")
        except serial.SerialException as e:
            messagebox.showerror("Erro", f"Erro na comunicação serial: {e}")

    def save_to_csv(self, filename):
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Leitura"])
            with self.lock:
                for item in self.data:
                    writer.writerow([item])

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitoramento Nivel de Água")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        self.arduino = LeitorArduirno(port="COM3")
        self.arduino.root = self.root
        self.init_ui()

    def init_ui(self):
        self.root.configure(bg="#1e1e1e")

        # Botões
        self.connect_button = tk.Button(self.root, text="Conectar Arduino", command=self.connect_arduino, bg="#3498db", fg="white", height=2, width=15, bd=0, borderwidth=5, relief=tk.RIDGE)
        self.connect_button.place(y=20, x=135)

        self.start_button = tk.Button(self.root, text="Iniciar Leitura", command=self.start_reading, bg="#3498db", fg="white", height=2, width=15, bd=0, borderwidth=5, relief=tk.RIDGE)
        self.start_button.place(y=85, x=135)

        self.stop_button = tk.Button(self.root, text="Parar Leitura", command=self.stop_reading, bg="#3498db", fg="white", height=2, width=15, bd=0, borderwidth=5, relief=tk.RIDGE)
        self.stop_button.place(y=85, x=270)

        self.save_button = tk.Button(self.root, text="Salvar CSV", command=self.save_to_csv, bg="#3498db", fg="white", height=2, width=15, bd=0, borderwidth=5, relief=tk.RIDGE)
        self.save_button.place(y=20, x= 270)

        # Labels
        self.status_label = tk.Label(self.root, text="Status: Não Conectado", bg="#5C5C5C", fg="white", height=2, width=20)
        self.status_label.place(y=250, x=50)

        self.output_label = tk.Label(self.root, text="Saída do Arduino: ", bg="#5C5C5C", fg="white", height=2, width=15)
        self.output_label.place(y=250, x=220)

        self.reading_label = tk.Label(self.root, text="", bg="#5C5C5C", fg="white", height=2, width=20)
        self.reading_label.place(y=250, x=325)

    def connect_arduino(self):
        if self.arduino.connect():
            self.status_label.config(text="Status: Conectado")
            self.start_button.config(state=tk.NORMAL)  # Habilita o botão Iniciar Leitura

    def start_reading(self):
        self.arduino.start_reading()
        self.root.after(2000, self.update_reading_label)

    def update_reading_label(self):
        if self.arduino.is_reading:
            if self.arduino.data:
                self.reading_label.config(text=f"{self.arduino.data[-1]}")
                if self.arduino.data[-1] == "LIMITE ALCANÇADO !!":
                    self.reading_label.config(bg="#ffa500")
                else:
                    self.reading_label.config(bg="#5C5C5C")
            else:
                self.reading_label.config(text="Sem leituras ainda")
            self.root.after(2000, self.update_reading_label)

    def stop_reading(self):
        self.arduino.stop_reading()
        self.status_label.config(text="Status: Desconectado")
        self.start_button.config(state=tk.DISABLED)  # Desabilita o botão Iniciar Leitura

    def save_to_csv(self):
        filename = tk.filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filename:
            self.arduino.save_to_csv(filename)
            messagebox.showinfo("Sucesso", f"Leituras salvas em {filename}")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()