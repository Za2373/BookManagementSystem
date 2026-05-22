"""
=====================================================
  图书管理系统 - 第三次提交
  新增功能：借阅图书、归还图书
=====================================================
"""

import pymysql
import time
import datetime

# ====================== 数据库配置 ======================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root123456",
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

    def update_book(self, book_id):
        """修改图书信息"""
        if not self.cursor:
            print("❌ 数据库未连接")
            return

        try:
            self.cursor.execute("SELECT * FROM book WHERE book_id = %s", (book_id,))
            book = self.cursor.fetchone()

            if not book:
                print(f"❌ 未找到编号为 {book_id} 的图书！")
                return

            print(f"当前图书信息：《{book['title']}》 作者：{book['author']} 分类：{book['category']}")
            print("提示：直接回车表示不修改该项")

            new_title = input(f"请输入新书名（当前：{book['title']}）：").strip()
            new_author = input(f"请输入新作者（当前：{book['author']}）：").strip()
            new_category = input(f"请输入新分类（当前：{book['category']}）：").strip()

            update_data = {
                "title": new_title if new_title else book['title'],
                "author": new_author if new_author else book['author'],
                "category": new_category if new_category else book['category']
            }

            sql = "UPDATE book SET title=%s, author=%s, category=%s WHERE book_id=%s"
            self.cursor.execute(sql, (update_data['title'], update_data['author'], update_data['category'], book_id))
            self.conn.commit()
            print("✅ 图书信息修改成功！")
            write_log(f"修改图书：编号{book_id}", self.current_user)

        except Exception as e:
            self.conn.rollback()
            print(f"❌ 修改失败: {e}")

    def delete_book(self, book_id):
        """删除图书（含确认机制）"""
        if not self.cursor:
            print("❌ 数据库未连接")
            return

        try:
            self.cursor.execute("SELECT * FROM book WHERE book_id = %s", (book_id,))
            book = self.cursor.fetchone()

            if not book:
                print(f"❌ 未找到编号为 {book_id} 的图书！")
                return

            print(f"找到图书：《{book['title']}》 作者：{book['author']} 状态：{book['status']}")

            if confirm_action("⚠️ 确定要删除这本图书吗？"):
                sql = "DELETE FROM book WHERE book_id = %s"
                self.cursor.execute(sql, (book_id,))
                self.conn.commit()
                print("✅ 图书删除成功！")
                write_log(f"删除图书：编号{book_id} 书名《{book['title']}》", self.current_user)
            else:
                print("❌ 已取消删除操作。")

        except Exception as e:
            self.conn.rollback()
            print(f"❌ 删除失败: {e}")

    # ------------------ 新增：借阅与归还 ------------------

    def borrow_book(self, book_id, reader_id, reader_name):
        """借阅图书"""
        if not self.cursor:
            print("❌ 数据库未连接")
            return

        try:
            # 1. 检查图书是否存在且可借
            self.cursor.execute("SELECT * FROM book WHERE book_id = %s", (book_id,))
            book = self.cursor.fetchone()

            if not book:
                print(f"❌ 未找到编号为 {book_id} 的图书！")
                return

            if book['status'] == '已借出':
                print(f"❌ 该图书已被借出，无法再次借阅！")
                return

            # 2. 更新图书状态为已借出
            self.cursor.execute("UPDATE book SET status='已借出' WHERE book_id=%s", (book_id,))

            # 3. 在 borrower 表插入借阅记录
            borrow_date = datetime.date.today() # 获取当前日期
            sql = "INSERT INTO borrower(reader_id, reader_name, book_id, borrow_date, is_returned) VALUES(%s,%s,%s,%s,0)"
            self.cursor.execute(sql, (reader_id, reader_name, book_id, borrow_date))

            self.conn.commit()
            print(f"✅ 借阅成功！《{book['title']}》已借给 {reader_name}")
            write_log(f"借出图书：编号{book_id} 借阅人{reader_name}", self.current_user)

        except Exception as e:
            self.conn.rollback()
            print(f"❌ 借阅失败: {e}")

    def return_book(self, book_id):
        """归还图书"""
        if not self.cursor:
            print("❌ 数据库未连接")
            return

        try:
            # 1. 检查图书状态
            self.cursor.execute("SELECT * FROM book WHERE book_id = %s", (book_id,))
            book = self.cursor.fetchone()

            if not book:
                print(f"❌ 未找到编号为 {book_id} 的图书！")
                return

            if book['status'] == '可借阅':
                print(f"❌ 该图书未被借出，无需归还！")
                return

            # 2. 更新图书状态为可借阅
            self.cursor.execute("UPDATE book SET status='可借阅' WHERE book_id=%s", (book_id,))

            # 3. 更新借阅记录：找到该书最近一条未归还的记录
            return_date = datetime.date.today() # 获取当前日期
            sql = """UPDATE borrower 
                     SET return_date=%s, is_returned=1 
                     WHERE book_id=%s AND is_returned=0 
                     ORDER BY borrow_date DESC LIMIT 1"""
            self.cursor.execute(sql, (return_date, book_id))

            self.conn.commit()
            print(f"✅ 归还成功！《{book['title']}》已归还入库")
            write_log(f"归还图书：编号{book_id}", self.current_user)

        except Exception as e:
            self.conn.rollback()
            print(f"❌ 归还失败: {e}")

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

    login_result = login_system()
    if not login_result:
        print("👋 已退出系统，再见！")
        return

    current_user, user_role = login_result

    bm = BookManager(current_user, user_role)
    if not bm.cursor:
        return

    while True:
        role_tag = "👑超管" if user_role == 'super' else "👤管员"
        print(f"\n{'='*50}")
        print(f"    📖 图书管理系统 【{role_tag}:{current_user}】")
        print(f"{'='*50}")
        print("  1. 添加图书")
        print("  2. 查看所有图书")
        print("  3. 修改图书")
        print("  4. 删除图书")
        print("  5. 借阅图书")
        print("  6. 归还图书")
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

        elif choice == "3":
            bid = input("请输入要修改的图书编号：").strip()
            bm.update_book(bid)

        elif choice == "4":
            bid = input("请输入要删除的图书编号：").strip()
            bm.delete_book(bid)

        elif choice == "5":
            bid = input("请输入要借阅的图书编号：").strip()
            rid = input("请输入读者ID：").strip()
            rname = input("请输入读者姓名：").strip()
            if bid and rid and rname:
                bm.borrow_book(bid, rid, rname)
            else:
                print("❌ 编号、读者ID和姓名不能为空！")

        elif choice == "6":
            bid = input("请输入要归还的图书编号：").strip()
            bm.return_book(bid)

        elif choice == "0":
            bm.close()
            write_log("退出系统", current_user)
            print("👋 系统退出成功，再见！")
            break

        else:
            print("❌ 输入无效，请重新输入！")


if __name__ == "__main__":
    main()
