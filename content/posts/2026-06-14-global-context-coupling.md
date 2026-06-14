---
title: "全局隐式上下文引出的设计反思"
date: 2026-06-14T17:40:39+08:00
categories: [软件工程]
tags: [software-engineering, architecture, api-design]
draft: false
---

## 真实的 BUG

这篇文章的思考来源于一个真实的 bug：

在嵌入式 UI 框架里，用户快速在两个界面之间来回切换，会出现偶发的卡死。排查到最后，根因一句话就能点明：**资源归属和执行上下文被耦合在同一个全局变量里**。

框架用一个全局变量 `currentWindow` 表示当前正在活动的窗口，所有需要知道当前活动窗口的操作 —— 创建定时器、触发刷新、新建子页面 —— 都在隐式读取它。

同时，事件派发的时候，框架会临时切换 `currentWindow` 到目标窗口，派发完成再恢复。看起来很合理 —— 保存、修改、恢复，标准的上下文管理。

但问题出在事件处理回调可以触发窗口切换：

```c
bool onEvent(EventType event){
	if(event == OnPress){
		createNewWindowAndSwitch();
		return true;
	}
	return false;
}
```

`currentWindow` 被修改了，但派发程序不知道这件事，它只会机械地恢复 `currentWindow`，然后导致其被指向一个已经进入了销毁流程的窗口。随后如果有通过 `currentWindow` 进行的内存访问，就有可能出现访问已释放内存造成的闪退！

## 本质问题

表面上看是忘了处理回调的副作用，但更深层的问题是：**资源归属和执行上下文被耦合在同一个全局变量里**。

`currentWindow` 同时承担了两个职责：

1. **执行上下文**：当前在哪个窗口里运行？
2. **归属标记**：新创建的资源属于谁？

任何使用全局隐式上下文的系统，只要回调中能产生改变上下文的副作用，都会面临同类问题。

## 解决方案

### 显式参数传递

最直接的做法 —— 把归属信息从全局变量变成函数参数。

```c
Page* addPage(Win* owner, PageConfig config);
Timer* addTimer(Win* owner, TimerConfig config);
```

调用者必须明确这个资源属于谁，不依赖于隐式的 `currentWindow`。但缺点是代码可能会变得很啰嗦，特别是 `currentWindow` 需要层层透传。

### 上下文对象随事件传递

把 `currentWindow` 这类上下文封装成结构体，作为事件的一部分传递给回调。

```c
typedef struct {
	int currentWindowID;
} Context;

bool onEvent(Context* ctx, EventType event){
	// do something
}
```

每个回调拿到的都是自己的上下文副本，不是共享的全局变量。本质上是显式参数传递的结构体优化版，方便拓展。缺点是额外还需要管理上下文结构体的生命周期。

### 命令队列

`onEvent` 回调内部不直接执行窗口切换，而是投递请求到队列中，等事件派发完成后，框架统一处理这些请求。

缺点是回调中不能立即看到操作的结果、需要引入队列、如果命令之间有依赖关系，处理逻辑会变复杂。

## 总结

全局隐式上下文的危险不在于它是全局的，而在于它把“谁在执行”和“资源属于谁”混为一谈。一旦回调能产生改变上下文的副作用，这两个本该独立的概念就会撕裂，制造出极难定位的 bug。
