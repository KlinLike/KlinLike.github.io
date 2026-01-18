---
title:  "对Socket基本用法的复习和理解 - Part 4"
date: 2025-01-20T22:48:03+08:00
tags: [socket, networking, programming, cpp]
---

# 前言
&nbsp;&nbsp;前面三篇文章已经对一些SOCKET编程的常用函数进行了讲解，本节会在这些函数的基础上实现一个简单的客户端和服务器并让他们之间进行通信。

# 关于回环地址
&nbsp;&nbsp;在IPv4中，回环地址的典型值是 127.0.0.1，当IP地址被设为回环地址时，发送的数据会在本机内部循环处理，不会往外发送。
&nbsp;&nbsp;实际上，在IPv4中，127.0.0.0 - 127.255.255.255 都是回环地址。在IPv6中，::1是回环地址（也可以写成0:0:0:0:0:0:0:1）。

# 示例代码
&nbsp;&nbsp;本节的实现代码较简单，就不多做解释了，直接贴代码。

### 服务器端
```
// server.cpp : 此文件包含 "main" 函数。程序执行将在此处开始并结束。
//

#include <iostream>
#include <string>
#include <WinSock2.h>
#include <WS2tcpip.h>
#pragma comment(lib, "ws2_32.lib")

inline int clean() {
    std::cerr << "[Server] Scoket Error:" << WSAGetLastError() << std::endl;
    WSACleanup();
    return 1;
}

int main(){
    // 初始化winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        std::cerr << "[Server] WSAStartup failed.\n";
        return 1;
    }

    // 创建Socket
    SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == INVALID_SOCKET) {
        std::cerr << "[Server] Create socket failed.\n";
        return clean();
    }

    // 绑定监听地址
    sockaddr_in addr;
    addr.sin_family = AF_INET;
    inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);
    addr.sin_port = htons(8888);
    if (bind(sock, (sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
        std::cerr << "[Server] Bind failed.\n";
        closesocket(sock);
        return clean();
    }

    // 开始监听
    if (listen(sock, 5) == SOCKET_ERROR) {
        std::cerr << "[Server] Listen failed.\n";
        closesocket(sock);
        return clean();
    }
    std::cout << "[Server] Listening ..." << std::endl;

    // 接受连接
    sockaddr_in clientAddr;
    int clientAddrLen = sizeof(clientAddr);
    SOCKET clientSock = accept(sock, (sockaddr*)&clientAddr, &clientAddrLen);
    if (clientSock == INVALID_SOCKET) {
        std::cerr << "[Server] Accept failed.\n";
        closesocket(sock);
        return clean();
    }
    std::cout << "[Server] client connected." << std::endl;

    // 通信循环
    char buffer[1024];
    memset(buffer, 0, sizeof(buffer));
    int idx = 0; // 消息序号
    while (true) {
        // 接收
        int bytesReceived = recv(clientSock, buffer, sizeof(buffer) - 1, 0);
        if (bytesReceived == 0) {
            std::cout << "[Server] client closed connect.\n";
            break;
        } else if (bytesReceived < 0) {
            std::cerr << "[Server] Recv failed." << WSAGetLastError() << std::endl;
            break;
        }
        buffer[bytesReceived] = '\0'; // 也可以在client端多发送一个\0，即发送长度+1，在这里就不用设置了
        std::cout << "[Server] Received:" << buffer << std::endl;

        // 发送
        std::string msg = "Server says hello " + std::to_string(++idx);
        if (send(clientSock, msg.c_str(), msg.length(), 0) == SOCKET_ERROR) {
            std::cerr << "[Server] Send failed.\n" << WSAGetLastError() << std::endl;
            break;
        }
    }

    // 关闭并释放资源
    std::cout << "[Server] connection closed.\n";
    closesocket(sock);
    closesocket(clientSock);
    WSACleanup();
    return 0;
}
```
### 客户端
```
// client.cpp : 此文件包含 "main" 函数。程序执行将在此处开始并结束。
//

#include <iostream>
#include <string>
#include <winsock2.h>
#include <WS2tcpip.h>

#pragma comment(lib, "ws2_32.lib")

inline int clean() {
    std::cerr << "[Client] Scoket Error:" << WSAGetLastError() << std::endl;
    WSACleanup();
    return 1;
}

int main(){
    // 初始化Winsock
    // 初始化winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        std::cerr << "[Client] WSAStartup failed.\n";
        return 1;
    }

    // 创建Socket
    SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == INVALID_SOCKET) {
        std::cerr << "[Client] Create socket failed.\n";
        return clean();
    }

    // 设置服务器地址
    sockaddr_in addr;
    addr.sin_family = AF_INET;
    inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);
    addr.sin_port = htons(8888);

    // 连接到服务器
    if (connect(sock, (sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
        std::cerr << "[Client] Connect failed.\n";
        closesocket(sock);
        return clean();
    }
    std::cout << "[Client] Connected to server.\n";

    // 通信循环
    char buffer[1024];
    int idx = 0; // 消息序号
    while (true) {
        if (++idx > 100){
            break; // 发送100条消息后由客户端先终止通信
        }
        memset(buffer, 0, sizeof(buffer));
        // 发送 -> 客户端先发
        std::string msg = "Client says hello " + std::to_string(idx);
        if (send(sock, msg.c_str(), msg.length(), 0) == SOCKET_ERROR) {
            std::cerr << "[Client] Send failed.\n" << WSAGetLastError() << std::endl;
            break;
        }

        // 接收
        int bytesReceived = recv(sock, buffer, sizeof(buffer) - 1, 0);
        if (bytesReceived == 0) {
            std::cout << "[Client] client closed connect.\n";
            break;
        }
        else if (bytesReceived < 0) {
            std::cerr << "[Client] Recv failed." << WSAGetLastError() << std::endl;
            break;
        }
        buffer[bytesReceived] = '\0';
        std::cout << "[Client] Received:" << buffer << std::endl;
    }

    // 关闭并释放资源
    std::cout << "[Client] connection closed.\n";
    closesocket(sock);
    WSACleanup();
    return 0;
}
```

&nbsp;&nbsp;分别复制代码到两个项目并运行（先运行server），就可以看到运行结果：
![运行结果图]({{ site.baseurl }}/assets/images/2025-01-20-socket-programming-basics-4.png)

&nbsp;&nbsp;*还有一些细节问题可以注意，比如可以把c_str()返回的结尾空字符一并发送，或者是要把buffer size减一，以免没有位置写入\0，但这些都是无伤大雅的小问题。*