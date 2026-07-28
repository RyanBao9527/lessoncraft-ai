# CODE-01 · 最小可运行版本：重复猜到正确
answer = 7
guess = 0

while guess != answer:
    guess = int(input("请输入 1～10 的数字："))

print("猜对了！")

# CODE-02 · 完整版本：加入大小提示
answer = 7
guess = 0

while guess != answer:
    guess = int(input("请输入 1～10 的数字："))
    if guess < answer:
        print("太小了")
    elif guess > answer:
        print("太大了")

print("猜对了！")
