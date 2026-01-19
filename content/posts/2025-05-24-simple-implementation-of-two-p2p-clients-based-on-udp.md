---
title: "两个P2P通信客户端的简单实现（基于UDP）"
date: 2025-05-24T20:00:05+08:00
categories: [网络]
tags: [p2p, udp, socket, networking, cpp]
---

目标：实现一个尽可能简单的、基于UDP的P2P通信程序。

重要概念：P2P通信是在知道对方IP+Port的前提下进行直接的通信。

# 版本1
我们先来实现一个最简单的版本，只有单线程，交替处理数据收发，通过指定对方的IP+Port来通信。
```
#include <iostream>
#include <string>
#include <cstring>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
// --- 配置 (重要：请根据你的虚拟机环境修改这些值) ---
// 这是 P2P 的核心之一：每个节点需要知道对方的地址才能直接通信。
//
// 当你在 VM1 上运行时:
//   MY_IP_ADDRESS_STR 应该是 VM1 的 IP 地址 (字符串格式)
//   MY_PORT 应该是 VM1 准备监听传入消息的 UDP 端口号
//   PEER_IP_ADDRESS_STR 应该是 VM2 的 IP 地址 (字符串格式)
//   PEER_PORT 应该是 VM2 监听其消息的 UDP 端口号
//
// 当你在 VM2 上运行时，这些配置应该相应地设置，使得 MY_* 指向 VM2，PEER_* 指向 VM1
#define MY_IP_ADDRESS_STR "192.168.126.129" // 本机VM的IP地址 (例如 VM1 的 IP)
#define MY_PORT 55566                     // 本机VM监听的UDP端口
#define PEER_IP_ADDRESS_STR "192.168.126.128" // 对方VM的IP地址 (例如 VM2 的 IP)
#define PEER_PORT 55577                     // 对方VM监听的UDP端口 (VM2 需用此端口bind)
#define BUFFER_SIZE 1024
// 用于处理致命错误并退出程序
void die_with_error(const char *errorMessage){
    perror(errorMessage);   // perror 会打印 errorMessage 和 errno 对应的系统错误信息
    exit(EXIT_FAILURE);
}
int main(){
    int sockfd;
    struct sockaddr_in my_addr;
    struct sockaddr_in peer_addr;
    char buffer[BUFFER_SIZE];
    
    // 1. 创建UDP Socket
    // AF_INET：指定地址族为IPv4，P2P通信也是发生在IP网络上的
    // SOCK_DGRAM：指定Socket类型为Datagram，对应UDP协议
    // 对于AF_INET+SOCK_DGRAM，协议设置为0，系统会自动选择UDP
    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if(sockfd < 0){
        die_with_error("socket() 创建失败");
    }
    std::cout << "[INFO] UDP Socket 创建成功 (fd: " << sockfd << ")." << std::endl;
    // 2. 配置本地信息
    // 为了能够接收到来自其他节点的消息，本节点需要将socket绑定到一个具体的IP+Port
    memset(&my_addr, 0, sizeof(my_addr));
    my_addr.sin_family = AF_INET;
    my_addr.sin_port = htons(MY_PORT);
    // 将点分十进制的IP地址字符串转换为网络字节序的32bit整数
    if(inet_pton(AF_INET, MY_IP_ADDRESS_STR, &my_addr.sin_addr) < 0){
        close(sockfd); // 创建了，就要记得关闭
        die_with_error("inet_pton() 装换地址失败");
    }
    // Q: 为什么已经在创建sock的时候指定了地址族，在地址中还要指定？
    // A: 创建socket指定AF_INET是告诉操作系统要创建一个用于IPv4网络的通信端点
    // 在sockaddr_in中再次指定sin_family是因为需要这个结构体来告诉bind\sendto等函数需要使用的地址结构
    // 简而言之，就是一个地址族标志是告诉系统的，一个是告诉sock api的。
    // 3. 将Socket绑定到本机地址和端口
    if(bind(sockfd, (struct sockaddr*)&my_addr, sizeof(my_addr)) < 0){
        close(sockfd);
        die_with_error("bind() 失败. 端口可能已被占用或IP地址无效。");
    }
    std::cout << "[INFO] Socket 成功绑定到 " << MY_IP_ADDRESS_STR << ":" << MY_PORT << "." << std::endl;
    // 4. 配置对方节点
    memset(&peer_addr, 0, sizeof(peer_addr));
    peer_addr.sin_family = AF_INET;
    peer_addr.sin_port = htons(PEER_PORT);
    if(inet_pton(AF_INET, PEER_IP_ADDRESS_STR, &peer_addr.sin_addr) < 0){
        close(sockfd);
        die_with_error("inet_pton() 转换对方IP失败. 请检查 PEER_IP_ADDRESS_STR 定义。");
    }
    // 为了使得单线程的模型也能交替收发，给recvfrom设置一个超时
    struct timeval tv;
    tv.tv_sec = 1;
    tv.tv_usec = 0;
    if(setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof(tv)) < 0){
        std::cerr << "[WARNING] setsockopt SO_RCVTIMEO 失败. recvfrom 可能会永久阻塞." << std::endl;
    }
    std::cout << "\nP2P UDP 节点已准备就绪。你可以输入消息并按 Enter 发送。" << std::endl;
    std::cout << "输入 'quit' 退出程序。" << std::endl;
    // 5. 主要的通信循环
    std::string input_line;
    while (true)
    {
        // a. 试图接收信息
        struct sockaddr_in temp_sender_addr;
        socklen_t temp_sender_addr_len = sizeof(temp_sender_addr);
        
        memset(buffer, 0, BUFFER_SIZE);
        ssize_t bytes_received = recvfrom(
            sockfd, 
            buffer, 
            BUFFER_SIZE - 1, 
            0,
            (struct sockaddr *)&temp_sender_addr, 
            &temp_sender_addr_len);
        // 这是POSIX socket API中用于从一个socket接收数据的标准函数，特别适用于UDP协议。
        // 返回值：
        // 返回值大于0，代表接收到了数据；
        // 返回值等于0，对UDP而言代表没有有效数据被接收到（因为UDP无连接，不能代表连接关闭）；
        // 返回值小于0，代表发生了错误。
        // ssize_t可以表示大小或错误指示符，因为他是有符号的，可以存储负数的错误码。
        // 参数：
        // flag = 0 表示执行标准的接收操作。
        // 如果参数addr不是NULL（在这里不是），当recvfrom接收到数据包，会将这个数据包的源节点地址信息保存到这个结构体中。
        // 如果填充了addr，addr_len也会被改成填充数据的byte长度。
        
        if(bytes_received > 0){ // 接收到数据
            buffer[bytes_received] = '\0';
            char sender_ip_str[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &temp_sender_addr.sin_addr, sender_ip_str, INET_ADDRSTRLEN);
            std::cout << "\n[收到来自 " << sender_ip_str << ":" << ntohs(temp_sender_addr.sin_port) << "] "
                      << buffer << std::endl;
        } else if(bytes_received < 0){ // 报错
            // 如果错误是 EAGAIN 或 EWOULDBLOCK，表示是超时，这是正常的
            if(errno != EAGAIN && errno != EWOULDBLOCK){
                std::cerr << "[ERROR] recvfrom() 失败: " << strerror(errno) << std::endl;
                // die_with_error("recvfrom() 接收数据失败");
            }
            // 超时则不打印错误，继续执行
        }
        // bytes_received == 0 对于 UDP 而言，通常不表示连接关闭，但可以忽略
        // b. 提示用户输入并发送信息
        std::cout << "Enter message ('quit' to exit): ";
        std::getline(std::cin, input_line);
        if (std::cin.eof() || input_line == "quit")
        {
            std::cout << "正在退出..." << std::endl;
            break; // 跳出主循环
        }
        
        if(input_line.empty()){
            continue; // 如果用户只按了 Enter，则继续下一次循环（尝试接收）
        }
        // sendto
        // 参数1：socket fd
        // 参数2：指向要发送数据的缓冲区的指针
        // 参数3：要发送的数据长度 Byte
        // 参数4：标志位，通常为0
        // 参数5： 指向目标地址结构(struct sockaddr *)的指针
        // 参数6：目标地址结构的长度
        // 这个函数调用，是P2P直接发送的核心，因为明确指定了接收方的地址
        ssize_t bytes_sent = sendto(sockfd, input_line.c_str(), input_line.length(), 0,
                                (struct sockaddr *)&peer_addr, sizeof(peer_addr));
        if (bytes_sent < 0) {
            std::cerr << "[ERROR] sendto() 失败: " << strerror(errno) << std::endl;
            // 即使发送失败，我们通常也会继续循环，允许用户重试或接收消息
        } else {
            std::cout << "[SENT] 消息已发送 (" << bytes_sent << " bytes)." << std::endl; // 可选的发送确认
        }
    
    }
    // 6. 关闭socket
    close(sockfd);
    std::cout << "[INFO] Socket 已关闭。程序结束。" << std::endl;
    return 0;
}
```

这个实现虽然能实现通信，但有个很影响使用体验的缺点：只能一收一发，对方发来的消息没法及时收到。下面我们会实现一个 主线程进行数据发送，子线程进行数据接收 的版本来解决这个问题。

# 版本2

```
#include <iostream>
#include <string>
#include <cstring>
#include <sys/types.h>
#include <thread>
#include <atomic>
#include <csignal>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
// --- 配置 (重要：请根据你的虚拟机环境修改这些值) ---
// 这是 P2P 的核心之一：每个节点需要知道对方的地址才能直接通信。
//
// 当你在 VM1 上运行时:
//   MY_IP_ADDRESS_STR 应该是 VM1 的 IP 地址 (字符串格式)
//   MY_PORT 应该是 VM1 准备监听传入消息的 UDP 端口号
//   PEER_IP_ADDRESS_STR 应该是 VM2 的 IP 地址 (字符串格式)
//   PEER_PORT 应该是 VM2 监听其消息的 UDP 端口号
//
// 当你在 VM2 上运行时，这些配置应该相应地设置，使得 MY_* 指向 VM2，PEER_* 指向 VM1
#define MY_IP_ADDRESS_STR "192.168.126.129" // 本机VM的IP地址 (例如 VM1 的 IP)
#define MY_PORT 55566                     // 本机VM监听的UDP端口
#define PEER_IP_ADDRESS_STR "192.168.126.128" // 对方VM的IP地址 (例如 VM2 的 IP)
#define PEER_PORT 55577                     // 对方VM监听的UDP端口 (VM2 需用此端口bind)
#define BUFFER_SIZE 1024
// 全局原子变量， 用于控制所有线程的运行状态
std::atomic<bool> running(true);
// 用于处理致命错误并退出程序
void die_with_error(const char *errorMessage){
    perror(errorMessage);   // perror 会打印 errorMessage 和 errno 对应的系统错误信息
    exit(EXIT_FAILURE);
}
// 信号处理函数，用于捕获终止信号
void signal_handler(int signum){
    // Ctrl+C (SIGINT) , 终止信号 (SIGTERM)
    if(signum == SIGINT || signum == SIGTERM){
        std::cout << "\n[SYSTEM] 捕获到中断/终止信号，正在准备退出..." << std::endl;
        running = false;
    }
}
// 用于接收消息的线程函数
void receive_message(int sockfd){
    char buffer[BUFFER_SIZE];
    struct sockaddr_in sender_addr; // 发送方的地址信息
    socklen_t sender_addr_len = sizeof(sender_addr);
    std::cout << "[RECEIVER] 消息接收线程已启动 (sockfd: " << sockfd << ")，正在监听端口 " << MY_PORT << "..." << std::endl;
    // 同样为recvfrom设置一个短的超时，这样即使没有消息进来，
    // 循环也能周期性地检查running标志，以便能及时退出线程。
    struct timeval tv;
    tv.tv_sec = 1;
    tv.tv_usec = 0;
    if(setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof(tv)) < 0){
        perror("[RECEIVER WARNING] setsockopt SO_RCVTIMEO failed");
        std::cerr << "[RECEIVER WARNING] setsockopt SO_RCVTIMEO 失败. 线程可能无法及时响应退出信号." << std::endl;
        // 即使设置超时失败，线程仍然可以工作，但退出可能会有延迟
    }
    while(running){
        memset(buffer, 0, BUFFER_SIZE);
        memset(&sender_addr, 0, sender_addr_len); 
        ssize_t bytes_received = recvfrom(sockfd, buffer, BUFFER_SIZE - 1, 0,
        (struct sockaddr*)&sender_addr, &sender_addr_len);
        // TODO 可以在应用层实现只接受VM2发来的消息,recvfrom并不能实现这样的效果
        if(bytes_received > 0){
            buffer[bytes_received] = '\0';
            char sender_ip_str[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &sender_addr.sin_addr, sender_ip_str, INET_ADDRSTRLEN);
            // 注意：这里的输出有可能会与用户输出的内容交错，这是一个常见的并发控制台输出问题
            std::cout << "\n[收到来自 " << sender_ip_str << ":" << ntohs(sender_addr.sin_port) << "] "
                      << buffer << std::endl;
            if (running) { // 避免在准备退出时还打印提示
                 std::cout << "Enter message ('quit' to exit): " << std::flush;
            }
        } else if(bytes_received < 0){
            if(errno != EAGAIN && errno != EWOULDBLOCK){
                if (running) { // 只有在程序还在运行时才报告错误
                    std::cerr << "[RECEIVER ERROR] recvfrom() 失败: " << strerror(errno) << std::endl;
                }
                running = false;
                break;
            }
        }
        // bytes_received = 0 忽略
    }
    std::cout << "[RECEIVER] 消息接收线程正在停止..." << std::endl;
}
int main(){
    // 注册信号处理函数
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    int sockfd;
    struct sockaddr_in my_addr;
    struct sockaddr_in peer_addr;
    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if(sockfd < 0){
        die_with_error("socket() 创建失败");
    }
    std::cout << "[INFO] UDP Socket 创建成功 (fd: " << sockfd << ")." << std::endl;
    memset(&my_addr, 0, sizeof(my_addr));
    my_addr.sin_family = AF_INET;
    my_addr.sin_port = htons(MY_PORT);
    if(inet_pton(AF_INET, MY_IP_ADDRESS_STR, &my_addr.sin_addr) <= 0){
        close(sockfd);
        die_with_error("inet_pton() 转换本机IP失败");
    }
    if(bind(sockfd, (struct sockaddr*)&my_addr, sizeof(my_addr)) < 0){
        close(sockfd);
        die_with_error("bind() 失败. 端口可能已被占用或IP地址无效。");
    }
    std::cout << "[INFO] Socket 成功绑定到 " << MY_IP_ADDRESS_STR << ":" << MY_PORT << "." << std::endl;
    memset(&peer_addr, 0, sizeof(peer_addr));
    peer_addr.sin_family = AF_INET;
    peer_addr.sin_port = htons(PEER_PORT);
    if(inet_pton(AF_INET, PEER_IP_ADDRESS_STR, &peer_addr.sin_addr) <= 0){ // 注意这里检查返回值 <=0 更标准
        close(sockfd);
        die_with_error("inet_pton() 转换对方IP失败. 请检查 PEER_IP_ADDRESS_STR 定义。");
    }
    std::cout << "\nP2P UDP 节点已准备就绪。你可以输入消息并按 Enter 发送。" << std::endl;
    std::cout << "输入 'quit' 退出程序。" << std::endl;
    // 创建+启动接收线程
    std::thread receiver_thread(receive_message, sockfd);
    // 主线程开始处理用户输入+发送消息
    std::string input_line;
    while (running)
    {
        // NOTICE
        // 按下Ctrl+C后，主线程可能会阻塞在这里，也就是getline
        // 所以需要提供任意输入，才能退出阻塞并结束任务
        // 因为涉及到了非阻塞输入，与主题P2P无关，这里不探讨
        if(!std::getline(std::cin, input_line)){
            if(std::cin.eof()){
                std::cout << "\n[MAIN] 检测到输入结束 (EOF)，准备退出..." << std::endl;
            } else{
                std::cout << "\n[MAIN] 读取输入时发生错误，准备退出..." << std::endl;
            }
            running = false;
            break;
        }
        if (!running) { // 在读取输入后，再次检查 running 状态，可能在输入过程中被信号改变
            break;
        }
        if (input_line == "quit") {
            std::cout << "[MAIN] 用户请求退出..." << std::endl;
            running = false; // 通知接收线程退出
            break; 
        }
        if(input_line.empty()){
            std::cout << "Enter message ('quit' to exit): " << std::flush; // 如果输入为空，重新打印提示
            continue;
        }
        ssize_t bytes_sent = sendto(sockfd, input_line.c_str(), input_line.length(), 0,
                                (struct sockaddr *)&peer_addr, sizeof(peer_addr));
        if (bytes_sent < 0) {
            if (running) { // 只有在程序还在运行时才报告错误
                std::cerr << "[MAIN ERROR] sendto() 失败: " << strerror(errno) << std::endl;
            }
        } else {
            // std::cout << "[SENT] 消息已发送 (" << bytes_sent << " bytes)." << std::endl; // 可选的发送确认
        }
        if (running) { // 避免在准备退出时还打印提示
            std::cout << "Enter message ('quit' to exit): " << std::flush;
        }
    }

    // 等待接收线程结束
    if(receiver_thread.joinable()){
        receiver_thread.join();
    }
    std::cout << "[MAIN] 接收线程已成功汇合。" << std::endl;
    close(sockfd);
    std::cout << "[INFO] Socket 已关闭。程序结束。" << std::endl;
    return 0;
}
```

这个实现也很简单，注释较为完备，这里就不多解释了。

# 一些补充
### sockfd的线程安全
在多个线程上对同一个sockfd进行操作（就像上面的一个线程调用recvfrom,一个线程调用sendto），在POSIX兼容的系统上通常是安全的，并不需要针对sockfd增加额外的互斥锁。这是因为内核能够处理来自多个线程或进程对同一个sockfd的并发请求。

### 为什么要使用joinable
一个线程对象要满足以下条件，才是joinable的：
1. 对象代表着一个正在执行或已经执行完毕的线程
2. 之前没有对它调用过join
3. 之前没有对它调用过detach

那为什么要判断joinable呢？因为如果对一个不可join的对象调用join，会导致系统抛出异常，进行检查可以提升代码的健壮性。
