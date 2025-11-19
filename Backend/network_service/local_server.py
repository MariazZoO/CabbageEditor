import socket
import threading
import json
import os

class Server:
    def __init__(self, tcp_port=8888, search_port=10000):
        self.tcp_port = tcp_port  # TCP通信端口
        self.search_port = search_port  # 用于接收搜索请求的UDP端口
        self.server_ip = self.get_local_ip()  # 自动获取局域网IP

    def get_local_ip(self):
        """获取服务器的局域网IP（排除回环地址）"""
        try:
            # 通过连接外部地址（不实际连接）获取本地出口IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            # 遍历所有网络接口（备选方案）
            for interface in socket.if_nameindex():
                iface = interface[1]
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.bind((iface, 0))
                    ip = s.getsockname()[0]
                    s.close()
                    if not ip.startswith("127."):
                        return ip
                except:
                    continue
            return "127.0.0.1"

    def handle_tcp_client(self, client_socket, client_addr):
        """处理单个TCP客户端连接"""
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if data:
                print(f"TCP收到 {client_addr} 的消息：{data}")
                response = f"服务器已收到：{data}"
                client_socket.send(response.encode('utf-8'))
        finally:
            client_socket.close()
            print(f"TCP客户端 {client_addr} 断开")

    def tcp_server(self):
        """启动TCP服务器"""
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_sock.bind(('0.0.0.0', self.tcp_port))
        tcp_sock.listen(5)
        print(f"TCP服务启动：{self.server_ip}:{self.tcp_port}")
        while True:
            client_sock, addr = tcp_sock.accept()
            threading.Thread(target=self.handle_tcp_client, args=(client_sock, addr)).start()

    def udp_search_handler(self):
        """UDP监听线程：响应客户端的搜索请求"""
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 允许广播，并绑定搜索端口
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.bind(('0.0.0.0', self.search_port))
        print(f"UDP搜索监听启动：{self.search_port} 端口（等待客户端搜索）")

        while True:
            # 接收客户端的搜索请求
            data, client_addr = udp_sock.recvfrom(1024)
            message = data.decode('utf-8')
            if message == "SEARCH_SERVER":
                # 回复服务器信息（IP+TCP端口，用JSON格式方便解析）
                response = json.dumps({
                    "ip": self.server_ip,
                    "tcp_port": self.tcp_port,
                    "name": "局域网服务器"
                })
                udp_sock.sendto(response.encode('utf-8'), client_addr)
                print(f"已响应搜索请求：{client_addr}")

    def start(self):
        """启动服务器（TCP+UDP搜索）"""
        # 启动UDP搜索响应线程
        threading.Thread(target=self.udp_search_handler, daemon=True).start()
        # 启动TCP服务（主线程）
        self.tcp_server()

if __name__ == "__main__":
    server = Server()
    server.start()