---
layout: post
title:  "🌱Linux实现TCP百万并发需要进行的系统设置"
date:   2025-04-05 23:28:56 +0800
tags: [linux, networking, tcp, concurrency, performance]
---

# 1. 设置文件描述符限制

## 1.1 配置用户级别限制

在 `/etc/security/limits.conf` 里添加或修改以下行：

```bash
* soft nofile 1048576
* hard nofile 1048576
root soft nofile 1048576
root hard nofile 1048576
```

编辑文件：
```bash
sudo vim /etc/security/limits.conf
```

**⚠️ 注意**：配置项之间的分隔符必须是 **Tab** 而不是空格。

### 配置说明

- **soft 限制**：普通用户可以自行调整的上限，但不能超过 hard 限制
- **hard 限制**：系统设定的绝对上限，只能由 root 用户设置
- **用户名（第一项）**：`*` 表示所有普通用户，但不包括 root，所以 root 需要单独设置
- **临时生效方式**：如果只需在当前会话临时生效（避免重新登录），可以使用：
  ```bash
  ulimit -n 1048576
  ```

---

## 1.2 配置系统级别限制

在 `/etc/sysctl.conf` 里添加或修改：

```bash
fs.file-max = 2097152
```

编辑文件：
```bash
sudo vim /etc/sysctl.conf
```

---

## 1.3 深入理解文件描述符限制

### 为什么要在两个文件中进行设置？

因为这两个配置文件控制不同层级的限制：

- **`sysctl.conf`**：控制内核参数，影响整个系统
- **`limits.conf`**：控制用户和进程级别的限制，在用户登录时应用（**这也是为什么修改后需要重新登录才会生效**）

可以理解为：`sysctl.conf` 控制了整个系统的上限，`limits.conf` 控制了单个用户和进程的上限。

**层级关系**：  
系统全局限制（`fs.file-max`） → 用户限制（`limits.conf`）

类似多重筛子，最后能通过的沙子大小，取决于最细的一层。

### 为什么要设置文件描述符限制？

在 Linux 系统中，每个进程能打开的文件描述符数量有限（**默认限制是 1024**）。

如果要实现 **100W 的并发连接**，因为**每个 socket 都会占用一个文件描述符**，所以必须调整这个限制。

### 为什么是这些数值？

- **`nofile = 1048576`**（1024 × 1024）  
  略大于 100W，为 100W 连接提供足够的文件描述符

- **`file-max = 2097152`**（2 × 1024 × 1024）  
  实际使用时，需要的文件描述符数可能大于连接数（还有日志文件、配置文件等），设置更大的值是为了让 `file-max` 不会成为瓶颈

---

# 2. 设置 TCP 协议栈

## 2.1 配置内核参数

在 `/etc/sysctl.conf` 里添加或修改以下行：

```bash
# TCP 内存配置
net.ipv4.tcp_mem = 786432 1048576 1572864
net.ipv4.tcp_rmem = 4096 4096 16777216
net.ipv4.tcp_wmem = 4096 4096 16777216

# 端口范围
net.ipv4.ip_local_port_range = 1024 65535

# 连接队列
net.ipv4.tcp_max_syn_backlog = 65536
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65536

# 连接回收
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_tw_reuse = 1
```

---

## 2.2 参数详解

### TCP 内存管理

**`net.ipv4.tcp_mem`** - TCP 总内存限制

三个数值分别表示：**最小阈值**、**压力阈值**、**最大阈值**

- 当 TCP 的内存使用达到**压力阈值**时，系统会尝试减少内存的使用
- 当达到**最大阈值**时，会拒绝新的连接

**`net.ipv4.tcp_rmem` / `net.ipv4.tcp_wmem`** - TCP 接收/发送缓冲区

三个数值分别表示：**最小值**、**默认值**、**最大值**

- **最小值**：保证每个 TCP 连接至少拥有的缓冲区大小
- **默认值**：每个连接默认拥有的缓冲区大小，如果内存紧张可以设置得小一些
- **最大值**：连接可用的最大缓冲区大小，允许某些功能使用更多的缓冲区

### 端口范围

**`net.ipv4.ip_local_port_range`** - 本地可用的端口范围

设置为 `1024 65535` 表示可用范围是 **1024~65535**

- **最小值 1024**：因为 0~1023 是特权端口（Well-known Ports），需要 root 权限才能绑定
- **最大值 65535**：TCP 协议中端口号字段是 16 bit，能表示的最大数值是 65535，这是协议层面的限制

### 连接队列

**`net.ipv4.tcp_max_syn_backlog`** - 半连接队列长度

表示能同时处理的半连接数量（处于 TCP 三次握手第一阶段的连接），防止高并发场景下的半连接队列溢出。

**`net.core.somaxconn`** - 全连接队列长度

设置全连接队列的最大长度。

**连接队列说明**：
- **半连接队列**：请求连接但还没有完成三次握手的连接
- **全连接队列**：完成三次握手但还未被 `accept()` 的连接

**`net.core.netdev_max_backlog`** - 网卡接收队列长度

设置网络设备驱动程序接收队列长度，表示内核处理数据包之前能缓存的数据包数量。设置得大一点，可以降低高流量场景下因数据包未及时处理导致的丢包。

### 连接回收优化

**`net.ipv4.tcp_fin_timeout`** - FIN_WAIT_2 状态超时时间

设置 TCP 连接在 FIN_WAIT_2 状态的停留时间。

**`net.ipv4.tcp_tw_reuse`** - TIME_WAIT 复用

允许处于 TIME_WAIT 状态的 socket 可用于新的 TCP 连接。

#### 理解 TCP 连接状态

**FIN_WAIT_2 状态**：
- TCP 连接中的一方表示"我不再发送数据"后进入的状态（主动关闭方发送 FIN 并收到对方的 ACK 后进入）
- 此时还能继续接收数据，完成最后的数据传送
- `tcp_fin_timeout` 设置的就是停留在这个状态的时间（默认 60s）
- 在高并发情况下，60s 可能导致更高的资源占用，**设为 10s** 可以满足大多数应用场景

**TIME_WAIT 状态**：
- TCP 连接中的双方都表示"不再发送数据"后进入的状态
- 是连接完全关闭前的等待状态，确保最后的数据包能够到达
- 让当前连接的数据包在网络中自然消失，避免"连接混淆"
- 在这个状态下的文件描述符无法被重用（也占用资源，包括端口号）
- 在高并发场景，文件描述符可能被迅速耗尽，**需要允许重用**才能满足性能需求

**⚠️ 重要提示**：在高并发场景中，这两个状态是需要特别关注的。

![设置完成后的sysctl.conf]({{ site.baseurl }}/assets/images/2025-03-11-simple-implementation-of-posix-thread-pool.png)

---

# 3. 配置 PAM

确保 `/etc/pam.d/common-session` 中包含以下配置：

```bash
session required pam_limits.so
```

**作用**：通过 pam_limits 模块强制应用 `/etc/security/limits.conf` 中定义的限制，对所有 PAM 认证的应用程序生效。

---

# 4. 重新登录

**⚠️ 重要**：修改 `limits.conf` 后需要重新登录才能生效，仅重启终端是不够的。

重新登录：
```bash
sudo su - <你的用户名>
```

验证配置：
```bash
ulimit -n  # 确认当前的文件描述符限制
```

---

# 5. 增加交换空间（可选）

设置 8GB 的交换文件，可以作为安全网（虽然使用物理内存是更好的选择）。

在终端执行：
```bash
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**命令说明**：
- `fallocate`：分配 8GB 空间
- `chmod 600`：设置适当的权限
- `mkswap`：格式化为交换空间
- `swapon`：启用交换文件