---
layout: post
title:  "Linux实现TCP百万并发需要进行的系统设置"
date:   2025-04-05 23:28:56 +0800
tags: [linux, networking, tcp, concurrency, performance]
---

# 1. 设置文件描述符限制

在 /etc/security/limits.conf 里添加或修改以下行：
```
* soft nofile 1048576
* hard nofile 1048576
root soft nofile 1048576
root hard nofile 1048576
```

通过指令：sudo vim /etc/security/limits.conf
注意：分隔符是Tab

##说明：
1. soft限制是普通用户可以自行调整的上限，但不能超过hard限制
2. hard限制是系统设定的绝对上限，只能由root用户设置
3. 第一项是用户名，如果是针对所有普通用户的，可以设为 *。
4. *并不会对root用户生效，所以root用户需要单独设置。
5. 如果只需要在当前窗口临时生效（这样可以避免重新登录），可以通过指令 ulimit -n 1048576 设置，而不用修改limits.conf


在 /etc/sysctl.conf 里添加或修改一行：
```
fs.file-max = 2097152
```

通过指令：sudo vim /etc/sysctl.conf

##为什么要在两个文件中进行设置呢？

是因为sysctl.conf控制的是内核参数，会影响整个系统。而limits.conf控制的是用户和进程级别的限制，会在用户登录的时候应用（**这也是为什么修改后需要重新登录才会生效**）。
总结来说，就是sysctl.conf控制了整个系统的上限，limits.conf控制了单个用户和进程的上限。
需要理解的是，这些限制之间是有层级关系的：
系统全局限制(fs.file-max) ---> 用户限制(limit.conf)，类似多重筛子，最后能通过的沙子大小，取决于最细的一层。


##为什么要设置文件描述符限制呢？
是因为在Linux系统中每个进程能打开的文件描述符有限（默认限制是1024）。
如果要实现100w的连接，因为每个SOCKET都会占用一个文件描述符，所以必须修改这个限制。

##为什么是 1048576?
 因为这个值略大于100w，且等于 1024 * 1024。
那为什么file-max要设为2097152?是因为实际使用的时候，需要的文件描述符数可能大于连接数，设置更大的值是为了让file-max不会成为瓶颈。


#2. 设置TCP协议栈

在 /etc/sysctl.conf 里添加或修改以下行：
```
net.ipv4.tcp_mem = 786432 1048576 1572864
net.ipv4.tcp_rmem = 4096 4096 16777216
net.ipv4.tcp_wmem = 4096 4096 16777216
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_max_syn_backlog = 65536
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65536
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_tw_reuse = 1
```

##说明：
net.ipv4.tcp_mem 的三个数值分别表示：最小阈值、压力阈值、最大阈值。
当TCP的内存使用达到压力阈值时，系统会尝试减少内存的使用。
当达到最大阈值时，会拒绝新的连接

net.ipv4.tcp_rmem、net.ipv4.tcp_wmem 分别设置TCP的接收/发送缓冲区大小。
三个数值分别表示：最小值、默认值、最大值。
和net.ipv4.tcp_mem不同，三个数值的含义是：
最小值：保证每个TCP连接至少拥有的缓冲区大小
默认值：每个连接默认拥有的缓冲区大小，如果内存紧张可以设置得小一些
最大值：连接可用的最大的缓冲区大小，允许某些功能使用更多的缓冲区

net.ipv4.ip_local_port_range 表示本地可用的端口范围，
net.ipv4.ip_local_port_range = 1024 65535则表示可用的范围是 1025~65535。
为什么最小值是1024呢？因为0~1023已经被系统保留了。
为什么最大值是65535呢？这是因为TCP协议中，端口号的字段是16bit，而16bit能表示的最大数值是65535，也就是说这是个协议上的限制。

net.ipv4.tcp_max_syn_backlog 表示能同时处理的半连接数量（也就是处于TCP握手的第一阶段的连接），
设置这个值是因为防止高并发场景下的半连接队列溢出。
net.core.somaxconn 设置的则是全连接队列的最大长度。
只要是请求连接但还没有完成三次握手的，都在半连接队列里；而完成三次握手但还未被accept的，都在全连接队列里。这两组参数设置的就是这两个连接队列的最大长度。

net.core.netdev_max_backlog 设置网路设备驱动程序接收队列长度，表示内核处理数据包之前能缓存的数据包数量。
设置得大一点，可以降低高流量场景下因为没有及时处理数据包导致的数据包丢失。

net.ipv4.tcp_fin_timeout 设置TCP连接在FIN_WAIT_2状态的停留时间；
net.ipv4.tcp_tw_reuse = 1 允许处于TIME_WAIT状态的socket可用于新的TCP连接。
###可以通过这两个状态的区别来理解这两个设置：
FIN_WAIT_2状态是TCP连接中的一方表示“我不再发送数据”后进入的状态(主动关闭方发送FIN并收到对方的ACK后进入的状态)，但此时还能继续接收数据，完成最后的数据传送。
net.ipv4.tcp_fin_timeout设置的就是停留在这个状态的时间，默认是60s，但在高并发情况下这可能会导致更高的资源占用，设为10s可以满足大多数应用场景。
TIME_WAIT则是TCP连接中的双方都表示“不再发送数据”后进入的状态，是连接完全关闭前的等待状态，是为了确保最后的数据包能够到达，让当前连接的数据包在网络中自然消失，避免“连接混淆”。在这个状态下的文件描述符无法被重用(也占用资源，包括端口号)，但如果是高并发场景，文件描述符可能会被迅速耗尽，需要允许重用才能满足性能需求。
在高并发场景中，这两个状态是需要特别关注的。

![设置完成后的sysctl.conf]({{ site.baseurl }}/assets/images/2025-03-11-simple-implementation-of-posix-thread-pool.png)

#3. 配置PAM
确保 /etc/pam.d/common-session 中包含 session required pam_limits.so，
这是为了通过pam_limits模块强制应用/etc/security/limits.conf中定义的限制，对所有PAM认证的应用程序生效。

#4. 重新登录
重新登录才能让limits.conf生效，重启终端是不够的：
sudo su - <你的用户名>

可以通过ulimits -n确认当前的file-max限制。

#5. 增加交换空间
在 终端 执行指令：
```
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

指令说明：设置8GB的交换文件，可以作为安全网(虽然使用物理内存是更好的选择)。

