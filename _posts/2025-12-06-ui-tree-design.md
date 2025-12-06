---
layout: post
title:  "🌱浅谈UI树的结构设计"
date:   2025-12-06 14:51:29 +0800
tags: [framework, gui, data-structure]
---

UI树是很多UI框架中使用的底层数据结构，这种结构容易理解，维护起来也比较方便。下面我会简单说明一下UI树的设计和我的理解。

![UI树指针结构图]({{ site.baseurl }}/assets/images/2025-12-06-UI-Tree.png)

这是一个Page内包含有 `Btn`、`Img`、`Text` 的情况：
- Page通过双向链表存储子控件
- 因为Page也继承自UI，所以Page也有 `parent`、`prev`、`next`，因此Page也可以嵌套。

可见，UI树和其他树状数据结构（如DOM树）并没有本质的区别：
- 每个节点都有 `parent` 指针指向父节点
- Page节点有 `head`/`tail` 指针管理子节点链表
- 兄弟节点通过 `next`/`prev` 形成双向链表

只看图片可能没有办法体会UI树设计的优势，下面我们来展开说明。

## 渲染自动化

```cpp
// 伪代码
void renderLoop() {
    while(true) {
        // 遍历所有窗口
        for(Win* win = winList; win; win = win->next) {
            if(win->isShow) {
                // 递归渲染窗口的UI树
                renderPage(win->mainPage);
            }
        }
        
        // 刷新屏幕
        GPU_flush();
    }
}
void renderPage(Page* page) {
    if(!page || !page->isShow) return;
    
    // 遍历Page的所有子控件
    for(UIBase* ui = page->head; ui; ui = ui->next) {
        if(ui->isShow) {
            // 根据类型渲染
            switch(ui->UIType) {
                case BtnType:   renderBtn((Btn*)ui); break;
                case ImgType:   renderImg((Img*)ui); break;
                case TextType:  renderText((Text*)ui); break;
                case PageType:  renderPage((Page*)ui); break;  // 递归
                // ...
            }
        }
    }
}
```

如上，只需要在框架中实现一个主渲染循环（通常用定时器或者主循环处理），就可以把渲染的过程自动化。开发者只需要关注控件是如何被组织到UI树中的即可，不用每写一个控件，都去关心它是如何被渲染的。
一个更大的优势是，如果你打算实现一些基于现有的 GPU图元组成的新控件，你只需要在框架层进行组合，UI树+渲染循环会帮你自动处理好这个组合空间的渲染，让你可以专注于其他控件逻辑的实现。

## 层次化

内存管理简单，符合逻辑直觉：比如删除某个Page的时候，只要把其作为根节点的树递归释放即可。
这个释放算法和常用的树删除节点算法非常类似，大多数程序员都能轻松读懂。

## 批量操作方便，子节点会继承效果

子控件使用相对坐标，这样当移动父节点的时候，子节点也会自动跟随。
同样的，给父节点设置效果，如透明度，子节点也能方便地跟随。
显示/隐藏也同样如此，只需要在渲染循环中跳过设置为`hide`的节点及其子节点，就可以做到隐藏根节点，其子节点全部自动隐藏。
这个优势会在实现动画效果的时候也被发挥出来，只要对某个节点施加动画，其子节点都可以被递归地施加同样的动画。

