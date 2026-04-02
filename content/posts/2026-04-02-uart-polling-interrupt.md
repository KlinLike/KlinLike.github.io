---
title: "从查询到中断：STM32 UART 三种通信方式（一）"
date: 2026-04-02T19:40:24+08:00
categories: [系统与性能]
tags: [embedded, uart, interrupt]
draft: false
---

三种UART方式：查询、中断、DMA，这里先讨论前两种。

## 查询

HAL库提供了发送函数`HAL_UART_Transmit`和接收函数`HAL_UART_Receive`。

CubeMX 配置：
1. 打开 USART1 → Mode 选择 Asynchronous
2. 引脚默认 PA9(TX) / PA10(RX)
3. 波特率 115200，8数据位，无校验，1停止位
4. 生成代码

CubeMX 会帮你：
- 新增 usart.c 文件（初始化代码）
- 在 main.c 中调用 `MX_USART1_UART_Init()`

**`HAL_UART_Transmit` 内部逻辑：**

```
循环每个字节：
    等待 TXE
    写入 TDR
等待 TC 标志
```

TXE=1 表示 TDR 空，可以写下一个；
TC=1 表示 TSR 空，也就是全部发完。
如果 TSR 空了，而且 TDR 也没数据了，就会触发 TC。

**`HAL_UART_Receive` 内部逻辑：**

```
循环每个字节：
    等待 RXNE（RDR 有数据）
    读取 RDR  // 读取后，硬件会将 RXNE 清零
```

读取就只有一个标志位了，因为我们不知道什么时候是发完，还会有丢失的风险。

## 中断

### 官方的中断函数

CubeMX 配置（在查询方式基础上）：
- USART1 → NVIC Settings → 使能 USART1 全局中断

这会生成：
- `stm32f1xx_it.c` 中增加 `USART1_IRQHandler` 中断处理函数
- 初始化时设置中断优先级

官方提供了两个中断函数：
- `HAL_UART_Transmit_IT`：使能 TXE 中断
- `HAL_UART_Receive_IT`：使能 RXNE 中断

### 发送

`HAL_UART_Transmit_IT` 调用一次会持续触发中断，直到发送完毕。
怎么理解发送完毕呢？就是 TC 触发了：

```
TC 标志出现  ← TSR 也空了，最后一个字节真正发出去了
    ↓
TC 中断触发
    ↓
关闭 TC 中断
调用 HAL_UART_TxCpltCallback
    ↓
整个发送流程结束，所有中断都关闭了
```

| 时机 | TXE 中断 | TC 中断 |
|---|---|---|
| 调用 `Transmit_IT` 后 | 使能 | 禁止 |
| 字节写完（TxXferCount=0）后 | 禁止 | 使能 |
| TC 中断触发后 | 禁止 | 禁止 |

假设要发送100个字节要怎么做呢？

首先要实现一个自己的发送完成回调（HAL库里的定义是 `__weak`，可以被覆盖）：

```c
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart == &huart1) {
        tx_complete = 1;  // 设置标记
    }
}
```

然后调用 `HAL_UART_Transmit_IT`，HAL库会自动利用中断发送数据，并在发送完成后调用一次回调函数：

```
┌─────────────────────────────────────────┐
│ TXE 中断触发（TDR 空）                    │
│                                         │
│ HAL_UART_IRQHandler 内部：               │
│   if (TXE 中断使能 && TXE 标志) {        │
│       取 txbuff[i] 写入 TDR              │
│       TxXferCount--                      │
│       pTxBuffPtr++                      │
│                                         │
│       if (TxXferCount == 0) {           │
│           // 最后一个字节已写入           │
│           关闭 TXE 中断                  │
│           使能 TC 中断                   │
│       }                                 │
│   }                                     │
└─────────────────────────────────────────┘
         ↓ 重复 99 次
         ↓
┌─────────────────────────────────────────┐
│ 第 100 次 TXE 中断                       │
│                                         │
│   写入最后一个字节                        │
│   TxXferCount = 0                        │
│   关闭 TXE 中断                          │
│   使能 TC 中断                           │
└─────────────────────────────────────────┘
         ↓ 等 TSR 发完最后一个字节
         ↓
┌─────────────────────────────────────────┐
│ TC 中断触发（TSR 空，彻底发完）           │
│                                         │
│ HAL_UART_IRQHandler 内部：               │
│   if (TC 中断使能 && TC 标志) {          │
│       关闭 TC 中断                       │
│       调用 HAL_UART_TxCpltCallback()     │
│   }                                     │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ 回调函数（你实现的）                      │
│                                         │
│ void HAL_UART_TxCpltCallback(...) {     │
│     tx_complete = 1;  // 通知主程序      │
│ }                                       │
└─────────────────────────────────────────┘
```

### 接收

接收也是类似的流程，首先是实现自己的中断函数 `HAL_UART_RxCpltCallback`，然后是主程序调用：

```c
uint8_t rxbuff[1];
HAL_UART_Receive_IT(&huart1, rxbuff, 1);
```

`HAL_UART_Receive_IT` 内部：

```
1. 记录参数到 handle
   huart->pRxBuffPtr = rxbuff      // 存放地址
   huart->RxXferCount = 1          // 预期接收字节数

2. 使能 RXNE 中断
   __HAL_UART_ENABLE_IT(huart, UART_IT_RXNE)

3. 立刻返回（不等待）
```

整个数据接收流程：

```
┌─────────────────────────────────────────┐
│ 数据从外部进入 RDR                        │
│ RXNE 标志出现                             │
│                                         │
│ RXNE 中断触发                            │
│                                         │
│ HAL_UART_IRQHandler 内部：               │
│   if (RXNE 中断使能 && RXNE 标志) {      │
│       从 RDR 读出数据                     │
│       存入 pRxBuffPtr                    │
│       RxXferCount--                      │
│       pRxBuffPtr++                      │
│                                         │
│       if (RxXferCount == 0) {           │
│           // 收够了                      │
│           关闭 RXNE 中断                  │
│           调用 HAL_UART_RxCpltCallback() │
│       }                                 │
│   }                                     │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ 回调函数（你实现的）                      │
│                                         │
│ void HAL_UART_RxCpltCallback(...) {     │
│     rx_complete = 1;  // 通知主程序      │
│ }                                       │
└─────────────────────────────────────────┘
```

看完接收的工作流程，你应该就能理解为什么HAL提供的中断函数不实用：
如果接收完了一批数据，需要再次调用 `HAL_UART_Receive_IT` 才能继续接收，不然期间的数据都会丢失。
而且，不知道能接收多少字节，只能指定固定大小的缓冲区。

简而言之，就是调用一次只能接收一次，收完就关中断，想要持续接收还得反复调用。

### 改造官方中断

上一节提到了官方提供的中断方式中有一个致命缺陷，就是无法保证不会丢失接收数据。通过简单的改造，我们就能避免这个问题。

改造思路：
1. **一开始就使能中断**，启动的时候就调用一次，不要等到主程序调用。官方的方式是，主程序决定什么时候调用 `Receive_IT`，调用之后才能开始接收。但问题是，如果主程序在忙别的事情没调用，就会导致数据丢失。改造之后，初始化就调用，并且中断会一直打开，任何时候数据来了都会触发中断，不会丢失。

2. **数据存入环形队列**，在回调里存，不限定固定长度。官方中断假设你知道会收到多少字节，但实际上你往往不知道，这就会导致丢失。改造之后，每接收一个字节，马上就存入环形队列，只要队列不满，都不会丢失数据。

3. **接收完成后，在回调里重新使能中断**，实现持续接收。这一个改造非常关键，中断刚关闭马上就会被打开，能保证始终可以被触发。

改造的关键代码：

```c
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == &huart1) {
        // 存入环形缓冲区
        circle_buffer_write(&uart1_rx_buffer, rx_byte);
        
        // 重新使能中断（关键：持续接收）
        HAL_UART_Receive_IT(&huart1, &rx_byte, 1);
    }
}

// 主程序读取接口
int UART1_Read(uint8_t *data)
{
    // 从环形缓冲区读
    return circle_buffer_read(&uart1_rx_buffer, data);
}

// 主循环
int main(void)
{
    // ...
    Start_UART1_Receive();  // 启动接收
    
    while (1) {
        uint8_t c;
        if (UART1_Read(&c) == 0) {
            // 收到数据，处理它
            HAL_UART_Transmit(&huart1, &c, 1, 100);  // 回显
        }
    }

    // ...
}
```
