"""
=====================================================
  图书管理系统 - 基础骨架版
  功能：管理员登录、添加图书、查看图书
=====================================================
"""

import pymysql
import time

# ====================== 数据库配置 ======================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root123456",  # 请修改为你的MySQL密码
    "database": "book_db",
    "charset": "utf8mb4"
}

# ====================== 工具函数模块 ======================

def get_db_conn():
    """获取数据库连接"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None

def write_log(msg, operator="系统"):
    """日志记录工具"""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{now}] [操作员:{operator}] {msg}\n")

def input_number(prompt, allow_zero=False):
    """数字输入校验工具"""
    while True:
        val = input(prompt).strip()
        try:
            num = int(val)
            if not allow_zero and num == 0:
                print("❌ 输入不能为0，请重新输入！")
                continue
            return num
        except ValueError:
            print("❌ 请输入有效的数字！")

def confirm_action(prompt="是否确认操作？"):
    """操作确认机制"""
    while True:
        choice = input(prompt).strip().lower()
        if choice in ('y', 'yes'):
            return True
        elif choice in ('n', 'no'):
            return False
        else:
            print("❌ 请输入 y 或 n")

# ====================== 登录验证模块 ======================

def login_system():
    """管理员登录功能"""
    print("\n" + "=" * 40)
    print("      欢迎使用图书管理系统")
    print("=" * 40)

    while True:
        username = input("请输入管理员账号（输入0退出）：").strip()
        if username == '0':
            return None

        password = input("请输入密码：").strip()

        try:
            conn = get_db_conn()
            if not conn:
                return None

            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                sql = "SELECT * FROM admin WHERE username = %s AND password = %s"
                cursor.execute(sql, (username, password))
                admin = cursor.fetchone()

                if admin:
                    role_name = "超级管理员" if admin['role'] == 'super' else "普通管理员"
                    print(f"\n✅ 登录成功！欢迎，{username}（{role_name}）！")
                    write_log(f"管理员登录：{username}（{role_name}）", username)
                    conn.close()
                    return (username, admin['role'])
                else:
                    print("❌ 账号或密码错误，请重新输入！\n")
            conn.close()
        except Exception as e:
            print(f"❌ 登录验证异常: {e}")
            write_log(f"登录异常: {e}")
            return None

# ====================== 图书管理核心类 ======================

class BookManager:
    """图书管理系统核心业务类"""

    def __init__(self, current_user, user_role):
        """初始化"""
        self.current_user = current_user
        self.user_role = user_role
        self.conn = get_db_conn()
        if self.conn:
            self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)
            print("✅ 数据库连接成功")
        else:
            self.cursor = None
            print("❌ 数据库连接失败，请检查配置")

    def add_book(self, book_id, title, author, category):
        """添加图书"""
        if not self.cursor:
            print("❌ 数据库未连接")
            return

        try:
            sql = "INSERT INTO book(book_id, title, author, category, status) VALUES(%s,%s,%s,%s,'可借阅')"
            self.cursor.execute(sql, (book_id, title, author, category))
            self.conn.commit()
            print("✅ 图书添加成功！")
            write_log(f"添加图书：编号{book_id} 书名《{title}》", self.current_user)
        except Exception as e:
            self.conn.rollback()
            print(f"❌ 添加失败: {e}")

    def show_all_books(self):
        """查询所有图书"""
        if not self.cursor:
            print("❌ 数据库未连接")
            return

        try:
            sql = "SELECT * FROM book"
            self.cursor.execute(sql)
            books = self.cursor.fetchall()

            if not books:
                print("📭 暂无图书数据！")
                return

            print(f"\n{'='*70}")
            print(f"{'编号':<10}{'书名':<20}{'作者':<15}{'分类':<12}{'状态':<10}")
            print(f"{'-'*70}")
            for b in books:
                print(f"{b['book_id']:<10}{b['title']:<20}{b['author']:<15}{b['category']:<12}{b['status']:<10}")
            print(f"{'='*70}")
        except Exception as e:
            print(f"❌ 查询失败: {e}")

    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ 数据库连接已关闭")


# ====================== 主菜单流程 ======================

def main():
    """主程序入口"""

    # 第一步：管理员登录
    login_result = login_system()
    if not login_result:
        print("👋 已退出系统，再见！")
        return

    current_user, user_role = login_result

    # 第二步：初始化图书管理对象
    bm = BookManager(current_user, user_role)
    if not bm.cursor:
        return

    # 第三步：主菜单循环
    while True:
        role_tag = "👑超管" if user_role == 'super' else "👤管员"
        print(f"\n{'='*50}")
        print(f"    📖 图书管理系统 【{role_tag}:{current_user}】")
        print(f"{'='*50}")
        print("  1. 添加图书")
        print("  2. 查看所有图书")
        print("  0. 退出系统")
        print(f"{'='*50}")

        choice = input("请输入功能编号：").strip()

        if choice == "1":
            bid = input("请输入图书编号：").strip()
            title = input("请输入书名：").strip()
            author = input("请输入作者：").strip()
            category = input("请输入分类：").strip()
            if bid and title and author and category:
                bm.add_book(bid, title, author, category)
            else:
                print("❌ 所有字段不能为空！")

        elif choice == "2":
            bm.show_all_books()

        elif choice == "0":
            bm.close()
            write_log("退出系统", current_user)
            print("👋 系统退出成功，再见！")
            break

        else:
            print("❌ 输入无效，请重新输入！")


if __name__ == "__main__":
    main()
