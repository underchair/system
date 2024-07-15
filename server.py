import socket
import threading

class ChatServer:
    def __init__(self, host='127.0.0.1', port=55555):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen()
        self.clients = {}
        self.nicknames = {}

    def broadcast(self, message, sender=None):
        for client in self.clients:
            if client != sender:
                client.send(message)

    def send_private_message(self, sender, recipient, message):
        if recipient in self.nicknames:
            recipient_socket = self.nicknames[recipient]
            recipient_socket.send(f"PM:{self.clients[sender]}:{message}".encode('utf-8'))
        else:
            sender.send(f"User {recipient} not found.".encode('utf-8'))

    def handle_file_transfer(self, sender, file_type, filename, filesize):
        try:
            for client in self.clients:
                if client != sender:
                    client.send(f"{file_type}:{filename}:{filesize}".encode('utf-8'))
        
            remaining = filesize
            while remaining > 0:
                chunk = sender.recv(min(4096, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                for client in self.clients:
                    if client != sender:
                        try:
                            client.send(chunk)
                        except:
                            print(f"Failed to send chunk to {self.clients[client]}")
        
        # 파일 전송 완료 대기
            completion_message = sender.recv(1024).decode('utf-8')
            if completion_message == "FILE_TRANSFER_COMPLETE":
                print(f"File transfer completed: {filename}")
            else:
                print(f"Unexpected message after file transfer: {completion_message}")
        except Exception as e:
            print(f"Error during file transfer: {e}")
                
            file_data = sender.recv(filesize)
            for client in self.clients:
                if client != sender:
                    client.send(file_data)

    def update_user_list(self):
        user_list = ",".join(self.nicknames.keys())
        user_list_message = f"USERS:{user_list}".encode('utf-8')
        for client in self.clients:
            client.send(user_list_message)

    def handle_client(self, client):
        while True:
            try:
                message = client.recv(1024).decode('utf-8')
                if not message:
                    raise ConnectionResetError("Client disconnected")
            
                if message == "REQUEST_USERS":
                    self.send_user_list(client)
                elif message.startswith("MSG:"):
                    _, sender, content = message.split(":", 2)
                    self.broadcast(f"MSG:{sender}:{content}".encode('utf-8'), client)
                elif message.startswith("PM:"):
                    _, recipients, sender, content = message.split(":", 3)
                    recipients_list = recipients.split(',')
                    for recipient in recipients_list:
                        self.send_private_message(client, recipient, content)
                elif message.startswith(("FILE:", "IMAGE:")):
                    file_type, filename, filesize = message.split(":", 2)
                    self.handle_file_transfer(client, file_type, filename, int(filesize))
                elif message == "FILE_RECEIVE_COMPLETE":
                    print(f"File received by {self.clients[client]}")
                else:
                    self.broadcast(message.encode('utf-8'), client)
            except ConnectionResetError as e:
                print(f"Client {self.clients[client]} disconnected: {e}")
                break
            except Exception as e:
                print(f"Error handling client {self.clients[client]}: {e}")
                break

        nickname = self.clients[client]
        del self.clients[client]
        del self.nicknames[nickname]
        client.close()
        self.broadcast(f'{nickname} left the chat!'.encode('utf-8'))
        self.update_user_list()
            
    def send_user_list(self, client):
        user_list = ",".join(self.nicknames.keys())
        user_list_message = f"USERS:{user_list}".encode('utf-8')
        client.send(user_list_message)

    def receive(self):
        while True:
            client, address = self.server.accept()
            print(f"Connected with {str(address)}")

            client.send('NICK'.encode('utf-8'))
            nickname = client.recv(1024).decode('utf-8')
            self.nicknames[nickname] = client
            self.clients[client] = nickname

            print(f"Nickname of the client is {nickname}!")
            self.broadcast(f"{nickname} joined the chat!".encode('utf-8'))
            client.send('Connected to the server!\n'.encode('utf-8'))

            # 새로 연결된 클라이언트에게 현재 사용자 목록 전송
            self.update_user_list()

            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.start()

    def start(self):
        print("Server is listening...")
        self.receive()

if __name__ == "__main__":
    server = ChatServer()
    server.start()