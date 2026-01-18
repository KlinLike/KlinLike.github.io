---
title:  "无锁队列如何使用CAS入队"
date: 2025-08-08T23:04:12+08:00
tags: [lock-free, queue, cas, concurrency, data-structure, cpp]
---

# 思想

CAS是乐观锁，也就是线程会乐观地假设自己可以成功在队列中插入数据。因此，线程会做好一切准备，最后停过一次CAS操作来提交。如果不幸失败了，就再来一次。
乐观假设这个前提是很重要的，假设我们在一个竞争非常激烈的环境使用无锁队列，就有可能出现某个线程因为一直满足不了CAS而等待很久的情况。

# 伪代码
```
void enqueue(Node* newNode) {
	while(true){
		// 读取旧状态
		Node* last = tail;
		Node* next = last->next;

		// 检查在两次读取期间，tail有没有被更改
		if(last != tail){
			continue; // 被改了，再来一次
		}

		if(next == nullptr){
			// 好的情况：tail就是队尾结点，是期望的“开心路径”

			if(last->next.compare_exchange_weak(nullptr, newNode)){
				// 操作成功
				// 然后更新队尾指针，但这个不成功也没关系，因为别的线程会帮我们完成 -> “伤心路径”
				tail.compare_exchange_weak(last, newNode);
				return;
			}

		} else {
			// 不那么好的情况：tail不是队尾结点，它落后了，这是“伤心路径”
			// 这说明别的线程入队了新节点，却还没来得及更新队尾指针

			// 帮助其他线程更新队尾
			tail.compare_exchange_weak(last, next);

			continue; // 不反悔，直接开始下一轮循环，重新尝试
		}
	}
}
```
*-> 注意: 这个实现没有避免ABA问题*


### 关键一步：
整个入队操作的成功与否，都取决于插入节点的CAS：
last->next.compare_exchange_weak(nullptr, newNode)
只要这个操作成功，入队就算完成了。就算尾指针没有正确指向队尾也无所谓，因为队尾指针存在的目的是可以更快地找到队尾，就算更新稍微慢点也能接受。

我觉得这里解决“两个变量需要更新，但CAS只能处理一个变量”的方式还是挺巧妙的，他不是粗暴地创建一个结构体，而是选择了一个决定性的原子变量用于CAS。
就算队尾指针更新失败也没关系，只要入队操作能顺利执行，就算成功了。

# 为什么是compare_exchange_weak

compare_exchange_weak 和 compare_exchange_strong 都是CAS的实现，区别在于weak函数执行性能更高，但是会有“伪失败”的问题。
伪失败指的是：即使CAS的条件是满足的，操作却还是失败了，并且返回了false。
如果我们的代码不需要更具CAS的成功与否执行不同的分支，那weak函数的伪失败我们是可以接受的，比如入队函数出现伪失败的结果是再来一次。
容忍伪失败可以让我们得到更加极致的性能发挥。