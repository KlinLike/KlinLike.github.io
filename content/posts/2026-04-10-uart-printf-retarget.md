---
title: "STM32 重定向 printf 到 UART：fputc 与 fgetc 实现"
date: 2026-04-10T20:06:36+08:00
categories: [系统与性能]
tags: [embedded, uart, c]
draft: false
---

## fputc是什么，为什么要重写

fputc是C标准库里"输出一个字符"的底层函数。printf内部就是循环调用fputc把字符一个个写出去的。
在电脑上，fputc默认输出到屏幕，但在STM32上不一定有屏幕，只有串口。所以要重写fputc，让它把字符写到UART发送寄存器。

## fputc实现

```c
int fputc(int ch, FILE *f)
{
    // 等待发送寄存器为空
    while(!(USART1->SR & USART_SR_TXE));

    // 写入发送寄存器，硬件自动发送
    USART1->DR = ch;

    return ch;
}
```

## 为什么用查询方式？

先来对比三种UART发送方式：

**查询**：CPU轮询标志位，等待就绪。优点是简单可靠，但需要CPU持续等待。适合单字符或调试打印。

**中断**：TXE为空时触发中断，然后在中断里发下一个字符。好处是CPU可以同时处理其他事情，不用傻等。但是中断很频繁，因为TDR只能存1Byte，所以一次发送只能发1Byte。**不选择中断的原因**：fputc是同步函数，中断是异步机制，两者天然冲突。

**DMA**：硬件自动搬运，CPU完全解放。但有启动开销，而且DMA通道有限。**不选择DMA的原因**：启动开销太大，发送1Byte的数据，非常不划算。

## 不够好的实现：用 `HAL_UART_Transmit`

```c
int fputc(int ch, FILE *f)
{
    uint8_t c = (uint8_t)ch;
    HAL_UART_Transmit(&huart1, &c, 1, HAL_MAX_DELAY);
    return ch;
}
```

这个实现因为用到了HAL函数，会走HAL的标准流程，内部会检查huart1的状态，等待TXE，写DR。
问题是，每个字节都会进一次HAL函数调用，有锁判断、状态检查等开销。更致命的是，如果此时DMA TX正在进行（比如UART复用，既要发送应用数据，也要输出调试信息），HAL会返回`HAL_BUSY`，这个字节就丢了。

对比着看，首选的方案优势在于：

1. printf可以在任何时候被调用，哪怕DMA TX正忙
2. 调试打印追求的是“稳定的输出”，而不是“架构优雅”

## fgetc和__backspace

### fgetc

fgetc是scanf的底层调用，每次读取一个字符，有两种实现方式：

> 这里假设接收到的数据会被放入环形队列，可以根据情况选择中断或者DMA。但是要注意裸机不能用查询方式，因为如果用阻塞方式实现fgetc，它会占着CPU，其他函数不会有执行权。

**1. 非阻塞**

```c
int fgetc(FILE *f) {
    uint8_t ch;
    if (circle_buffer_read(&uart1_rx_buffer, &ch) != 0) {
        return EOF;  // 缓冲区空，返回EOF
    }
    return ch;
}
```

**2. 阻塞**

```c
int fgetc(FILE *f) {
    uint8_t ch;
    while(circle_buffer_read(&uart1_rx_buffer, &ch) != 0);  // 死等数据
    return ch;
}
```

阻塞方式适合scanf这种"必须读到数据才能继续"的场景。

### __backspace

为什么需要__backspace？
scanf 是格式化输入，比如 `scanf("%d", &x)` 只接受数字。如果用户输入 `12abc`，scanf 会读取 `12`，遇到 `a` 时发现不符合格式，需要把 `a` "退回"给输入流。

实现很简单，就是用一个 static 变量临时保存退回的字符：

```c
static uint8_t last_char;
static int backspace_flag = 0;

int __backspace(int ch) {
    last_char = ch;        // 记住要退回的字符
    backspace_flag = 1;    // 标记有退回字符
    return 0;
}

int fgetc(FILE *f) {
    // 优先返回被退回的字符
    if (backspace_flag) {
        backspace_flag = 0;
        return last_char;
    }
    
    // 否则从环形缓冲区读
    uint8_t ch;
    while(circle_buffer_read(&uart1_rx_buffer, &ch) != 0);
    return ch;
}
```

其实有一种异常情况fgetc并没有正确处理，比如如果我一直要格式化读取数字，但是用户输入了字母，假设是`a`：
1. 读取到`a`，退回
2. 再次试图读取数字
3. fgetc不会再次检查正确性，而是会直接返回
4. 用户期望得到数字，却得到了字母`a`

但这并不是BUG，而是C的设计哲学：机制在底层，责任在上层。库不替你做决定——也许你想丢弃非法输入，也许想重试，也许想报错退出。由你决定。
换句话说就是：库没做的，都是程序员要负责的。C选择了信任程序员。

常见的处理模式：

```c
int x;
int result = scanf("%d", &x);

if (result == EOF) {
    // 输入结束（比如串口断开）
} else if (result == 0) {
    // 格式不匹配，有非法字符
    while (getchar() != '\n');  // 清空到换行
    printf("输入错误，请重新输入\n");
} else {
    // result == 1，成功读取
    printf("你输入了: %d\n", x);
}
```
