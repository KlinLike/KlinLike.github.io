---
title: "学习协程小记 (ucontext)"
date: 2025-06-07T20:53:14+08:00
categories: [并发]
tags: [coroutine, concurrency, cpp]
---

# ucontext的主要类型、函数及其用法
## 1. 定义上下变量 -> ucontext_t 类型
```
ucontext_t main_ctx;  // 为主流程定义
ucontext_t ctx[3];        // 为协程定义
```

## 2. 分配栈空间
每个协程都需要有自己的独立栈空间，通常使用字符数组
```
chat stack[1024];
```

## 3. 使用 getcontext 获取当前上下文模板
```
getcontext(ctx[0]);
```

getcontext操作的意义是为了获取一个 合法的、完整的上下文模板 ，以便再次基础上进行修改，从而创建一个新的、可执行的协程。
为什么需要模板呢？因为从0创建一个正确的上下文及其复杂，需要处理包括 CPU寄存器当前值、信号掩码和其他平台相关状态。而 getcontext 解决了这个问题，函数会把 当前正在运行的、合法的 上下文信息完整地复制一份。

## 4. 设置新的上下文信息
这一步需要对上下文结构体进行修改，为其指定独立的栈空间和大小，同时设置uc_link，它指向当这个新的上下文函数结束后，程序应该恢复到的上下文（也是 ucontext_t）
```
// 指定栈
ctx[0].uc_stack.ss_sp = stack1;
ctx[0].uc_stack.ss_size = sizeof(stack1);
// 指定后继上下文
ctx[0].uc_link = &main_ctx;
```
## 5. 创建上下文
使用 makecontext 将一个函数 func1 与刚刚设置好的上下文关联起来，这样当这个上下文被激活的时候，func1 就会被执行
```
makecontext(&ctx[0], func1, 0);
```

*void makecontext(ucontext_t *ucp, void (*func)(), int argc, ...);，函数的第三个参数是参数2传入的函数的参数个数*

## 6. 切换上下文
使用 swapcontext 函数来切换，函数会保存当前上下文，并激活一个新的上下文，从而使得程序跳转到新的上下文所关联的函数中执行。

```
// 从 main_ctx 切换到 ctx[count%3]
swapcontext(&main_ctx, &ctx[count%3]);
```
**getcontext和swapcontext都保存了上下文，但他们保存的目的和时机完全不同。**
getcontext保存的是“模板”，swapcontext保存的是当前正在运行的上下文状态，也就是“快照”或“断点”。

# ucontext如何解决提升执行效率
首先要明白的是，协程的调度是发生在用户态的，它非常 **轻量和快速**。但是像read \ write这种IO操作是系统调用，会陷入内核态。也就是说，如果内核发现数据未就绪，就会挂起整个OS线程，而不是仅仅挂起用户态的那个协程。
一旦线程被挂起，不管线程中还有多少个IO是就绪的，都无法继续执行！

而通过 函数钩子+ucontext ，可以解决这个问题。在进行真正的 read \ write 调用前，我们可以检查IO的就绪状态，如果未就绪，就让出执行权，这是通过 swapcontext 实现的。

### 下面来说明更多的实现细节
1. 首次尝试
在首次调用 read 前，先将文件描述符设置为非阻塞，然后调用。
如果成功读到数据，那这次调用和普通的函数调用无区别；
如果读取到EOF，也是正常情况，和普通调用无区别；
如果返回 EAGAIN 或 EWOULDBLOCK ，这时候就有区别了。
2. 切换
如果返回 EAGAIN 或 EWOULDBLOCK，这时候我们不会继续调用read，而是将这个fd注册到调度器管理的epoll实例中。
同时，我们会记录映射关系(fd -> ucontext_t)，告诉调度器，如果这个fd就绪了，我们应该唤醒那个协程。
最后，调用 swapcontext 将执行权交还调度器。
3. 恢复
此时，调度器的主循环会阻塞在 epoll_wait 上，它会持续等待 IO事件。
当有fd就绪后，调度器会根据映射关系找到并恢复对应的协程。
对应的协程被恢复后，会再次调用 read 函数，这是一次必然成功的读取。

**通过这个实现细节的例子，我们已经可以一窥协程的威力：配合 函数钩子及epoll 使用，能够创建一个非阻塞的、异步的执行模型。这使得开发者可以用直观的方式写出具备极致性能的代码。**

# 示例
最后贴出我学习使用的示例代码
```
#define _GNU_SOURCE
#include <stdio.h>
#include <ucontext.h>
#include <string.h>

// 全局变量
ucontext_t ctx[3];      // 用于存储三个协程的上下文
ucontext_t main_ctx;    // 用于存储主流程（调度器）的上下文
int count = 0;          // 协程共享的计数器，用于控制调度

/**
 * @brief 协程1的执行体
 */
void func1(void) {
	while (count++ < 30) {
		printf("--> Coroutine 1: 开始执行。全局 count = %d\n", count);
		printf("    Coroutine 1: 即将让出CPU...\n");

		// 核心操作：保存当前协程状态，并切换回主调度器
		swapcontext(&ctx[0], &main_ctx);

		// 协程被恢复后，将从这里继续执行
		printf("<-- Coroutine 1: 已被恢复，继续执行。\n\n");
	}
}

/**
 * @brief 协程2的执行体
 */
void func2(void) {
	while (count++ < 30) {
		printf("--> Coroutine 2: 开始执行。全局 count = %d\n", count);
		printf("    Coroutine 2: 即将让出CPU...\n");
		swapcontext(&ctx[1], &main_ctx);
		printf("<-- Coroutine 2: 已被恢复，继续执行。\n\n");
	}
}

/**
 * @brief 协程3的执行体
 */
void func3(void) {
	while (count++ < 30) {
		printf("--> Coroutine 3: 开始执行。全局 count = %d\n", count);
		printf("    Coroutine 3: 即将让出CPU...\n");
		swapcontext(&ctx[2], &main_ctx);
		printf("<-- Coroutine 3: 已被恢复，继续执行。\n\n");
	}
}

/**
 * @brief 主函数：初始化协程并充当调度器
 */
int main() {
	// 为每个协程分配独立的栈空间
	char stack1[2048] = {0};
	char stack2[2048] = {0};
	char stack3[2048] = {0};

	/*
	 * 初始化协程1 (ctx[0])
	 * 流程: 获取上下文模板 -> 设置独立栈 -> 关联后继上下文 -> 绑定执行函数
	 */
	getcontext(&ctx[0]);
	ctx[0].uc_stack.ss_sp = stack1;
	ctx[0].uc_stack.ss_size = sizeof(stack1);
	ctx[0].uc_link = &main_ctx;
	makecontext(&ctx[0], func1, 0);

	// 初始化协程2 (ctx[1])
	getcontext(&ctx[1]);
	ctx[1].uc_stack.ss_sp = stack2;
	ctx[1].uc_stack.ss_size = sizeof(stack2);
	ctx[1].uc_link = &main_ctx;
	makecontext(&ctx[1], func2, 0);

	// 初始化协程3 (ctx[2])
	getcontext(&ctx[2]);
	ctx[2].uc_stack.ss_sp = stack3;
	ctx[2].uc_stack.ss_size = sizeof(stack3);
	ctx[2].uc_link = &main_ctx;
	makecontext(&ctx[2], func3, 0);

	printf("--- 协程调度开始 ---\n");
	
	// 主循环充当调度器 (Scheduler)，轮流执行三个协程
	while (count <= 30) {
		swapcontext(&main_ctx, &ctx[count%3]);
	}

	printf("\n--- 协程调度结束 ---\n");
	
	return 0;
}
```

