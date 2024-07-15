import tkinter as tk
from tkinter import scrolledtext, simpledialog, filedialog, ttk
from tkinter import font as tkfont
import threading
import socket
import os
from PIL import Image, ImageTk
import cv2
import numpy as np

class ChatClient:
    def __init__(self, host='127.0.0.1', port=55555):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.settimeout(1)

        self.root = tk.Tk()
        self.root.withdraw()

        self.default_font = tkfont.nametofont("TkDefaultFont")
        self.default_font.configure(family="Helvetica", size=10)
        self.root.option_add("*Font", self.default_font)

        self.nickname = simpledialog.askstring("Nickname", "Please choose a nickname", parent=self.root)

        self.gui_done = False
        self.running = True

        self.win = tk.Toplevel()
        self.win.protocol("WM_DELETE_WINDOW", self.stop)
        self.win.title("Chat Application")
        self.win.configure(bg="#E6F3FF")  # Alice Blue


        self.users = []  # 초기 사용자 목록
        self.create_gui()
        self.update_user_list()

        self.gui_done = True

        receive_thread = threading.Thread(target=self.receive)
        receive_thread.start()

        self.win.after(100, self.request_user_list)

        self.win.mainloop()
    
    def request_user_list(self):
        self.sock.send("REQUEST_USERS".encode('utf-8'))

    def create_gui(self):
        bg_color = "#F0F4F8"  # 연한 청회색 배경
        primary_color = "#1E88E5"  # 파란색 주 색상
        secondary_color = "#FFC107"  # 노란색 보조 색상
        text_color = "#333333"  # 어두운 회색 텍스트

        self.win.configure(bg=bg_color)
        self.win.grid_columnconfigure(0, weight=1)
        self.win.grid_rowconfigure(0, weight=1)

        main_frame = tk.Frame(self.win, bg=bg_color)
        main_frame.grid(sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=3)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

    # 채팅 영역
        chat_frame = tk.Frame(main_frame, bg=bg_color)
        chat_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        chat_frame.grid_rowconfigure(1, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_label = tk.Label(chat_frame, text="Chat Room", bg=bg_color, fg=primary_color, font=("Helvetica", 18, "bold"))
        self.chat_label.grid(row=0, column=0, pady=(0, 10), sticky="w")

        self.text_area = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, bg="white", fg=text_color, font=("Helvetica", 11))
        self.text_area.grid(row=1, column=0, sticky="nsew")
        self.text_area.config(state='disabled')

    # 입력 영역
        input_frame = tk.Frame(chat_frame, bg=bg_color)
        input_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_area = tk.Text(input_frame, height=3, bg="white", fg=text_color, font=("Helvetica", 11))
        self.input_area.grid(row=0, column=0, sticky="nsew")
        self.input_area.insert("1.0", "Type your message here...")
        self.input_area.bind("<FocusIn>", lambda e: self.input_area.delete("1.0", tk.END) if self.input_area.get("1.0", tk.END).strip() == "Type your message here..." else None)

        button_frame = tk.Frame(input_frame, bg=bg_color)
        button_frame.grid(row=0, column=1, padx=(10, 0))

        button_style = {"bg": primary_color, "fg": "white", "font": ("Helvetica", 11, "bold"), "relief": tk.FLAT, "borderwidth": 0}
    
        self.send_button = tk.Button(button_frame, text="Send", command=self.write, **button_style)
        self.send_button.pack(side=tk.TOP, pady=(0, 5), fill=tk.X)
        self.send_button.bind("<Enter>", lambda e: e.widget.config(bg="#1976D2"))
        self.send_button.bind("<Leave>", lambda e: e.widget.config(bg=primary_color))

        self.file_button = tk.Button(button_frame, text="Send File", command=self.send_file, **button_style)
        self.file_button.pack(side=tk.TOP, fill=tk.X)
        self.file_button.bind("<Enter>", lambda e: e.widget.config(bg="#1976D2"))
        self.file_button.bind("<Leave>", lambda e: e.widget.config(bg=primary_color))

    # 사용자 목록 영역
        users_frame = tk.Frame(main_frame, bg="white", relief=tk.RIDGE, borderwidth=1)
        users_frame.grid(row=0, column=1, sticky="nsew")
        users_frame.grid_rowconfigure(1, weight=1)
        users_frame.grid_columnconfigure(0, weight=1)

        self.users_label = tk.Label(users_frame, text="Recipients", bg=primary_color, fg="white", font=("Helvetica", 14, "bold"))
        self.users_label.grid(row=0, column=0, pady=(0, 10), sticky="ew")

        self.users_canvas = tk.Canvas(users_frame, bg="white", highlightthickness=0)
        self.users_canvas.grid(row=1, column=0, sticky="nsew")

        self.users_scrollbar = ttk.Scrollbar(users_frame, orient=tk.VERTICAL, command=self.users_canvas.yview)
        self.users_scrollbar.grid(row=1, column=1, sticky="ns")

        self.users_canvas.configure(yscrollcommand=self.users_scrollbar.set)
        self.users_canvas.bind('<Configure>', lambda e: self.users_canvas.configure(scrollregion=self.users_canvas.bbox("all")))

        self.users_inner_frame = tk.Frame(self.users_canvas, bg="white")
        self.users_canvas.create_window((0, 0), window=self.users_inner_frame, anchor="nw")

        self.user_vars = {}
        self.all_var = tk.BooleanVar()
        tk.Checkbutton(self.users_inner_frame, text="All", variable=self.all_var, bg="white", command=self.toggle_all).pack(anchor="w", padx=5, pady=2)

    # 스타일 설정
        self.text_area.tag_configure('left', justify='left')
        self.text_area.tag_configure('right', justify='right')

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Vertical.TScrollbar", gripcount=0, background=primary_color, darkcolor="#1976D2", lightcolor="#1976D2", troughcolor=bg_color, bordercolor=bg_color, arrowcolor="white")
    
    
    def update_user_list(self):
        for widget in self.users_inner_frame.winfo_children():
            if widget.cget("text") != "All":
                widget.destroy()
        
        self.user_vars = {}
        for user in self.users:
            if user != self.nickname:  # 자신의 닉네임은 제외
                var = tk.BooleanVar()
                self.user_vars[user] = var
                tk.Checkbutton(self.users_inner_frame, text=user, variable=var, bg="#FFFFFF").pack(anchor="w")
        
        # 캔버스 크기 업데이트
        self.users_inner_frame.update_idletasks()
        self.users_canvas.configure(scrollregion=self.users_canvas.bbox("all"))

    def write(self):
        message = self.input_area.get('1.0', 'end').strip()
        if message:
            recipients = [user for user, var in self.user_vars.items() if var.get()]
        
            if self.all_var.get() or not recipients:
            # 전체 메시지
                full_message = f"MSG:{self.nickname}:{message}"
                self.sock.send(full_message.encode('utf-8'))
                self.display_message(self.nickname, message)
            else:
            # 개인 메시지
                recipients_str = ','.join(recipients)
                full_message = f"PM:{recipients_str}:{self.nickname}:{message}"
                self.sock.send(full_message.encode('utf-8'))
                self.display_message(self.nickname, f"[To {recipients_str}] {message}", is_private=True)
        
            self.input_area.delete('1.0', 'end')

    def stop(self):
        self.running = False
        self.root.quit()
        self.win.destroy()
        self.sock.close()
        exit(0)

    def receive(self):
        while self.running:
            try:
                message = self.sock.recv(1024).decode('utf-8')
                if not message:
                    print("Connection closed by the server")
                    break
                
                if message == 'NICK':
                    self.sock.send(self.nickname.encode('utf-8'))
                elif message.startswith("USERS:"):
                    _, users_str = message.split(":", 1)
                    self.users = users_str.split(",")
                    self.win.after(0, self.update_user_list)
                elif message.startswith("MSG:"):
                    _, sender, content = message.split(":", 2)
                    self.display_message(sender, content)
                elif message.startswith("PM:"):
                    _, sender, content = message.split(":", 2)
                    self.display_message(sender, content, is_private=True)
                elif message.startswith(("FILE:", "IMAGE:")):
                    file_type, filename, filesize = message.split(":", 2)
                    self.receive_file(filename, int(filesize), file_type)
                else:
                    if self.gui_done:
                        self.text_area.config(state='normal')
                        self.text_area.insert('end', message + '\n', 'left')
                        self.text_area.yview('end')
                        self.text_area.config(state='disabled')
            except socket.timeout:
                continue
            except ConnectionResetError:
                print("Connection reset by the server")
                break
            except ConnectionAbortedError:
                print("Connection aborted")
                break
            except Exception as e:
                print(f"Error in receive: {e}")
                break
        
        print("Receive loop ended")
        self.stop()

    

    def send_file(self, file_path=None, file_type="FILE"):
        if not file_path:
            file_path = filedialog.askopenfilename(parent=self.win)
        if file_path:
            try:
                filename = os.path.basename(file_path)
                filesize = os.path.getsize(file_path)
                self.sock.send(f"{file_type}:{filename}:{filesize}".encode('utf-8'))
                
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        self.sock.sendall(chunk)
                
                # 전송 완료 메시지 전송
                self.sock.send("FILE_TRANSFER_COMPLETE".encode('utf-8'))
                
                self.text_area.config(state='normal')
                self.text_area.insert('end', f"{file_type} {filename} sent\n")
                self.text_area.yview('end')
                self.text_area.config(state='disabled')
            except Exception as e:
                print(f"Error sending file: {e}")
                self.text_area.config(state='normal')
                self.text_area.insert('end', f"Error sending {file_type} {filename}: {e}\n")
                self.text_area.yview('end')
                self.text_area.config(state='disabled')

    def receive_file(self, filename, filesize, file_type):
        try:
            save_path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".*", initialfile=filename)
            if save_path:
                received_size = 0
                with open(save_path, 'wb') as f:
                    while received_size < filesize:
                        chunk = self.sock.recv(min(4096, filesize - received_size))
                        if not chunk:
                            break
                        f.write(chunk)
                        received_size += len(chunk)
                
                # 수신 완료 메시지 전송
                self.sock.send("FILE_RECEIVE_COMPLETE".encode('utf-8'))
                
                self.text_area.config(state='normal')
                self.text_area.insert('end', f"{file_type} {filename} received and saved\n")
                self.text_area.yview('end')
                self.text_area.config(state='disabled')
            else:
                # 파일 저장을 취소한 경우
                self.text_area.config(state='normal')
                self.text_area.insert('end', f"{file_type} {filename} receive cancelled\n")
                self.text_area.yview('end')
                self.text_area.config(state='disabled')
                
                # 받은 데이터를 버립니다
                remaining = filesize
                while remaining > 0:
                    chunk_size = 4096 if remaining > 4096 else remaining
                    chunk = self.sock.recv(chunk_size)
                    remaining -= len(chunk)
                    if not chunk:
                        break
        except Exception as e:
            print(f"Error receiving file: {e}")
            self.text_area.config(state='normal')
            self.text_area.insert('end', f"Error receiving {file_type} {filename}: {e}\n")
            self.text_area.yview('end')
            self.text_area.config(state='disabled')

    def display_message(self, sender, content, is_private=False):
        if self.gui_done:
            self.text_area.config(state='normal')

        if sender == self.nickname:
            tag = 'right'
            prefix = f"{sender} (You)"
            box_color = "#E6F3FF"  # 연한 하늘색 (보낸 메시지)
        else:
            tag = 'left'
            prefix = sender
            box_color = "#B0E0E6"  # 파우더 블루 (받은 메시지)

        if is_private:
            prefix = f"[Private] {prefix}"

        message_tag = f"message_{self.text_area.index('end-1c')}"

        self.text_area.insert('end', '\n')
        self.text_area.insert('end', f" {prefix} \n", (tag, f"{message_tag}_prefix"))
        self.text_area.insert('end', f" {content}\n", (tag, f"{message_tag}_content"))
        self.text_area.insert('end', '\n')

        last_line_start = self.text_area.index('end-4l')
        last_line_end = self.text_area.index('end-1c')

        self.text_area.tag_add(f"{message_tag}_background", last_line_start, last_line_end)
        self.text_area.tag_configure(f"{message_tag}_background", background=box_color)

        self.text_area.tag_configure(f"{message_tag}_prefix", font=("Helvetica", 9, "bold"), foreground="#000000")  # 검은색
        if is_private:
            self.text_area.tag_configure(f"{message_tag}_prefix", foreground="#006400")  # 진한 초록색
        self.text_area.tag_configure(f"{message_tag}_content", font=("Helvetica", 10), foreground="#000000")  # 검은색

        self.text_area.yview('end')
        self.text_area.config(state='disabled')

    def toggle_all(self):
        all_state = self.all_var.get()
        for var in self.user_vars.values():
            var.set(all_state)

if __name__ == "__main__":
    client = ChatClient()