---
title: "STM32 UART 通信方式（二）：DMA 与 IDLE 空闲中断"
date: 2026-04-04T11:38:35+08:00
categories: [系统与性能]
tags: [embedded, uart, interrupt]
draft: false
---

上一篇文章我们讨论了UART通信三种方式中的查询和中断两种方式，这里讨论第三种：DMA。

## DMA 是什么？

Direct Memory Access（直接内存访问）—— 让硬件自动搬运数据，解放 CPU。

```
传统方式：CPU 搬运数据（循环1000次）
DMA方式：  配置一次 → DMA自动搬运 → 完成后通知CPU
```

## 好用的发送

```c
// 发送1000字节，立即返回
HAL_UART_Transmit_DMA(&huart1, tx_buffer, 1000);

// 回调通知完成
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart == &huart1) {
        tx_complete = 1;  // 发送完成
    }
}
```

## 不实用的接收

DMA接收非常不实用，因为需要预先配置好需要接收的字节数：

```
你配置接收1000字节...
对方只发了100字节就停了...
DMA还在傻等剩下的900字节 → 永远不知道数据已完整
```

这就导致了，DMA发送非常好用，但是DMA接收单独使用实用性很差，但如果配合IDLE空闲中断，就可以改善这个问题。

## DMA + IDLE

IDLE中断是UART硬件自带的检测机制：

```
RX引脚 -> 接收逻辑 -> IDLE检测 -> 检测到空闲 -> 置位SR[IDLE]标志 -> IDLE=1触发中断
```

IDLE触发的条件（硬件自动判断）：
1. 之前有收到至少一个字节
2. RX线路持续高电平超过一个字符时间（大约10bit时间）

两个条件同时满足。

### CubeMX 配置

需要配置两个 DMA 通道：
- `USART1_TX`：发送用
- `USART1_RX`：接收用

还要打开全局中断让IDLE可以触发：
- USART1 → NVIC Settings → USART1 global interrupt → Enable

最后打开DMA中断，不然DMA完成传输的中断不会触发：
- DMA → NVIC 里也要开启对应的 DMA 中断

### 工作原理

它们是这样配合工作的：
- DMA负责：自动搬运数据到buffer（不消耗CPU）
- IDLE负责：告诉程序"数据传完了，来处理"

接收数据退出的条件有两个：
1. 收到了指定的最大数量数据，DMA完成退出
2. 没有收到最大数量数据，但是发完了，IDLE中断触发退出

### 使用方式

```c
// 启动接收
HAL_UARTEx_ReceiveToIdle_DMA(&huart1, rx_buffer, 100);
```

函数内部打开了IDLE中断，然后启动DMA接收。因为IDLE+DMA接收太常见了，HAL厂家提前进行了封装，我们只要调用这一个函数即可。

```c
// 实现回调函数
// HAL库会在DMA接收到足够的数据或者IDLE触发的时候调用这个回调
// 而且传入的Pos参数就是正确的实际收到的字节数
// 底层是通过DMA的CNDTR寄存器实现的，这个寄存器会保存剩余传输字节数
// 类似这样：HAL_UARTEx_RxEventCallback(huart, 缓冲区长度 - DMA->CNDTR);
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Pos)
{
    if (huart == &huart1) {
        process_data(rx_buffer, Pos);
        
        // 重新启动
        HAL_UARTEx_ReceiveToIdle_DMA(&huart1, rx_buffer, 100);
    }
}
```

如果`process_data`处理的速度太慢，可能会导致新数据来了覆盖缓冲区或者没来得及启动接收丢失数据，这时候我们可以考虑使用双缓冲区或者交给后台任务处理。

### 双缓冲区实现

```c
uint8_t buffer_a[100];
uint8_t buffer_b[100];
uint8_t *active_buffer = buffer_a;   // DMA 当前写入的
uint8_t *process_buffer;             // 待处理的

void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Pos)
{
    process_buffer = active_buffer;  // 保存当前缓冲区指针
    
    // 切换到另一个缓冲区
    active_buffer = (active_buffer == buffer_a) ? buffer_b : buffer_a;
    
    // 立即重启，用新缓冲区接收
    HAL_UARTEx_ReceiveToIdle_DMA(&huart1, active_buffer, 100);
    
    // 处理刚才收完的那个缓冲区
    process_data(process_buffer, Pos);
}
```

思考这样一个场景：

```
缓冲区 100 字节
收到 80 字节 → IDLE 触发 → 回调开始执行
            → 回调执行中...
            → 新数据来了！发来 50 字节
            → DMA 还没重启，数据丢了！
```

如果配合使用双缓冲区+在回调一开始就重启DMA接收，就能解决。

> **注**：一般来说，DMA和IDLE的中断优先级不会是问题，因为DMA TC中断触发的时候，会关闭DMA接收，禁用IDLE中断，然后调用回调。