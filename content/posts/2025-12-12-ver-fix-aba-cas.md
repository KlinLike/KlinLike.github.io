---
title:  "CAS的版本号如何解决ABA问题"
date: 2025-12-12T11:34:55+08:00
tags: [cas, atomic, lock-free]
---

假设没有版本号，两个线程同时操作一个链表可能会发生什么？

没有版本号的 C++ 实现：

```cpp
// 链表节点定义
typedef struct Node{
	struct Node* next;
	int val;
} Node;

class LinkList {
	std::atomic<Node*> head;

	Node* pop(){
		Node* oldHead = head.load();
		Node* newHead = nullptr;

		do{
			if(oldHead == nullptr) return nullptr;
			newHead = oldHead->next; // 有崩溃风险，考虑如何用 shared_ptr 来解决
		} while(head.compare_exchange_weak(oldHead, newHead) == false);

		return oldHead;
	}
	
	void push(int val){
		Node* newNode = new Node{nullptr, val};

		Node* oldHead = head.load();
		Node* newHead = newNode;

		do{
			newNode->next = oldHead;
		}while(head.compare_exchange_weak(oldHead, newHead) == false);
	}
};
```

1. 链表的初始状态： `head -> A -> B`
2. 线程 1 执行，准备把 **节点 A** POP，让 `head` 指向 **节点 B**
3. 线程 1 保存 `head` 状态，然后准备执行 CAS (`Node* oldHead = head.load()`)
4. 此时线程 2 取得控制权，它执行了 `POP -> POP -> PUSH A`，链表最终状态： `head -> A`
5. 线程 1 执行，对比通过（因为 `head` 指向 A），执行了 POP，但预期的链表状态 `head -> B` 变成了 `head ->` **已经被释放的 Node B 的地址**

那版本号是如何解决这个问题的呢？先来看代码：

```cpp
// 有版本号的 C++ 实现

typedef struct Head{
	Node* nodes;
	uint64_t ver; // 使用 uint64_t 保证内存对齐
} Head;

class LinkList {
	std::atomic<Head> head;

	Node* pop(){
		Head oldHead = head.load();
		Head newHead;

		do{
			if(oldHead.nodes == nullptr) return nullptr;
			newHead.nodes = oldHead.nodes->next;
			newHead.ver = oldHead.ver + 1;
		} while(head.compare_exchange_weak(oldHead, newHead) == false);

		return oldHead.nodes;
	}
	
	void push(int val){
		Node* newNode = new Node{nullptr, val};

		Head oldHead = head.load();
		Head newHead;

		do{
			newHead.nodes = newNode;
			newHead.ver = oldHead.ver + 1;
			newNode->next = oldHead.nodes;
		}while(head.compare_exchange_weak(oldHead, newHead) == false);
	}
};
```

现在看再次按照上次的流程执行会发生什么：

1. 链表的初始状态： `head -> A -> B`
2. 线程 1 执行，准备把 **节点 A** POP，让 `head` 指向 **节点 B**
3. 线程 1 保存 `head` 状态，然后准备执行 CAS (`Node* oldHead = head.load()`)
4. 此时线程 2 取得控制权，它执行了 `POP -> POP -> PUSH A`，链表最终状态： `head -> A`
5. 线程 1 执行，对比没有通过，因为 `head` 的版本号不一样了，此时会更新数据并进行下一次 CAS 尝试，避免了野指针！
