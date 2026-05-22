"""
=====================================================
  图书管理系统 - 第五次提交 (最终版)
  进阶功能：借阅限额、逾期提醒、数据统计、批量导入、连接池
=====================================================
"""

import pymysql
from dbutils.pooled_db import PooledDB
import time
import datetime
import math
import os

# ====================== 数据库配置与连接池 ======================

# 使用连接池优化数据库连接效率
DB_POOL = PooledDB(
    creator=pymysql,
    maxconnections=6,
    mincached=2,
    host="localhost",
    user="root",
    password="root123456",  # 请修改为你的MySQL密码
    database="book_db",
    charset="utf8mb4"
)

def get_db_conn():
    """从连接池获取数据库连接"""
    try:
        conn = DB_POOL.connection()
        return conn
    except Exception as e:
        print(f"❌ 数据库连接池获取失败: {e}")
        return None

# ====================== 工具函数模块 ======================

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

def confirm_action(prompt="是否确认操作？(y/n): "):
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
    print("\n" + "=" * 50)
    print("||               欢迎使用 图书管理系统              ||")
    print("=" * 50)

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
            print("✅ 数据库连接成功(连接池)")
        else:
            self.cursor = None
            print("❌ 数据库连接失败")

    # ------------------ 管理员管理模块 ------------------

    def change_password(self):
        """修改当前管理员密码"""
        old_pwd = input("请输入旧密码：").strip()
        new_pwd = input("请输入新密码：").strip()
        confirm_pwd = input("请再次输入新密码：").strip()

        if new_pwd != confirm_pwd:
            print("❌ 两次输入的新密码不一致！")
            return

        try:
            self.cursor.execute("SELECT * FROM admin WHERE username=%s AND password=%s", (self.current_user, old_pwd))
            if not self.cursor.fetchone():
                print("❌ 旧密码错误！")
                return

            self.cursor.execute("UPDATE admin SET password=%s WHERE username=%s", (new_pwd, self.current_user))
            self.conn.commit()
            print("✅ 密码修改成功！")
            write_log("修改密码", self.current_user)
        except Exception as e:
            self.conn.rollback()
            print(f"❌ 修改密码失败: {e}")

    def manage_admins(self):
        """管理员账号管理（仅超管）"""
        if self.user_role != 'super':
            print("❌ 权限不足，仅超级管理员可操作！")
            return

        while True:
            print(f"\n{'='*30}\n  👑 管理员账号管理\n{'='*30}")
            print("  1. 查看所有管理员\n  2. 新增管理员\n  3. 删除管理员\n  0. 返回")
            choice = input("请输入编号：").strip()

            if choice == "1":
                self.cursor.execute("SELECT username, role FROM admin")
                admins = self.cursor.fetchall()
                print(f"\n{'账号':<20}{'角色':<15}\n" + "-"*35)
                for a in admins:
                    print(f"{a['username']:<20}{'超管' if a['role']=='super' else '普通':<15}")
            elif choice == "2":
                new_user = input("新账号名：").strip()
                new_pwd = input("初始密码：").strip()
                role = input("角色(super/normal)：").strip().lower()
                if role not in ['super', 'normal']: print("❌ 角色错误！"); continue
                try:
                    self.cursor.execute("INSERT INTO admin(username, password, role) VALUES(%s,%s,%s)", (new_user, new_pwd, role))
                    self.conn.commit()
                    print("✅ 新增成功！")
                    write_log(f"新增管理员：{new_user}", self.current_user)
                except Exception as e:
                    self.conn.rollback()
                    print(f"❌ 新增失败: {e}")
            elif choice == "3":
                del_user = input("删除账号：").strip()
                if del_user == self.current_user: print("❌ 不能删除自己！"); continue
                if confirm_action(f"⚠️ 确定删除 {del_user} 吗？"):
                    try:
                        self.cursor.execute("DELETE FROM admin WHERE username=%s", (del_user,))
                        if self.cursor.rowcount == 0: print("❌ 账号不存在！")
                        else: self.conn.commit(); print("✅ 删除成功！"); write_log(f"删除管理员：{del_user}", self.current_user)
                    except Exception as e: self.conn.rollback(); print(f"❌ 删除失败: {e}")
            elif choice == "0": break

    # ------------------ 图书管理模块 ------------------

    def add_book(self, book_id, title, author, category):
        """添加图书：含编号唯一校验"""
        try:
            self.cursor.execute("SELECT book_id FROM book WHERE book_id = %s", (book_id,))
            if self.cursor.fetchone():
                print(f"❌ 编号 {book_id} 已存在，禁止重复添加！")
                return

            sql = "INSERT INTO book(book_id, title, author, category, status) VALUES(%s,%s,%s,%s,'可借阅')"
            self.cursor.execute(sql, (book_id, title, author, category))
            self.conn.commit()
            print("✅ 图书添加成功！")
            write_log(f"添加图书：编号{book_id}", self.current_user)
        except Exception as e:
            self.conn.rollback()
            print(f"❌ 添加失败: {e}")

    def batch_import_books(self):
        """批量导入图书：从TXT文件读取(格式：编号,书名,作者,分类 每行一本)"""
        filepath = input("请输入导入文件路径(如 books.txt)：").strip()
        if not os.path.exists(filepath):
            print("❌ 文件不存在！")
            return

        success_count = 0
        fail_count = 0

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if confirm_action(f"⚠️ 读取到 {len(lines)} 条数据，确认导入吗？"):
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    parts = line.split(",")
                    if len(parts) == 4:
                        bid, title, author, cat = [p.strip() for p in parts]
                        try:
                            # 使用事务处理批量操作，确保数据一致性
                            self.cursor.execute("SELECT book_id FROM book WHERE book_id = %s", (bid,))
                            if self.cursor.fetchone():
                                print(f"  - 跳过：编号 {bid} 已存在")
                                fail_count += 1
                                continue

                            self.cursor.execute("INSERT INTO book VALUES(%s,%s,%s,%s,'可借阅')", (bid, title, author, cat))
                            success_count += 1
                        except Exception as e:
                            print(f"  - 错误：{line} 导入失败({e})")
                            fail_count += 1
                    else:
                        print(f"  - 格式错误：{line}")
                        fail_count += 1

                self.conn.commit() # 统一提交事务
                print(f"\n✅ 批量导入完成！成功：{success_count} 本，失败/跳过：{fail_count} 本")
                write_log(f"批量导入图书：成功{success_count}本", self.current_user)
        except Exception as e:
            self.conn.rollback()
            print(f"❌ 导入异常: {e}")

    def show_all_books(self):
        """查询所有图书（分页显示，每页5条）"""
        try:
            self.cursor.execute("SELECT COUNT(*) as total FROM book")
            total = self.cursor.fetchone()['total']
            if total == 0: print("📭 暂无图书数据！"); return

            page_size = 5
            total_pages = math.ceil(total / page_size)
            current_page = 1

            while True:
                offset = (current_page - 1) * page_size
                self.cursor.execute("SELECT * FROM book LIMIT %s OFFSET %s", (page_size, offset))
                books = self.cursor.fetchall()

                print(f"\n{'='*70}\n 图书列表 (第 {current_page}/{total_pages} 页) 共 {total} 条\n{'='*70}")
                print(f"{'编号':<10}{'书名':<20}{'作者':<15}{'分类':<12}{'状态':<10}\n" + "-"*70)
                for b in books:
                    print(f"{b['book_id']:<10}{b['title']:<20}{b['author']:<15}{b['category']:<12}{b['status']:<10}")
                print("="*70)

                op = input("操作：[N]下一页 [P]上一页 [Q]退出：").strip().lower()
                if op == 'n' and current_page < total_pages: current_page += 1
                elif op == 'p' and current_page > 1: current_page -= 1
                elif op == 'q': break
                else: print("❌ 无效操作")
        except Exception as e:
            print(f"❌ 查询失败: {e}")

    def search_books(self):
        """图书查询优化"""
        print("\n1.按书名模糊 2.按分类 3.按作者")
        choice = input("选择查询方式：").strip()
        try:
            if choice == "1":
                kw = input("书名关键字：").strip()
                self.cursor.execute("SELECT * FROM book WHERE title LIKE %s", (f"%{kw}%",))
            elif choice == "2":
                cat = input("分类：").strip()
                self.cursor.execute("SELECT * FROM book WHERE category = %s", (cat,))
            elif choice == "3":
                aut = input("作者：").strip()
                self.cursor.execute("SELECT * FROM book WHERE author LIKE %s", (f"%{aut}%",))
            else: print("❌ 无效选择"); return

            books = self.cursor.fetchall()
            if not books: print("📭 未找到相关图书！")
            else:
                print(f"\n找到 {len(books)} 本：")
                print(f"{'编号':<10}{'书名':<20}{'作者':<15}{'分类':<12}{'状态':<10}\n" + "-"*70)
                for b in books: print(f"{b['book_id']:<10}{b['title']:<20}{b['author']:<15}{b['category']:<12}{b['status']:<10}")
        except Exception as e: print(f"❌ 查询失败: {e}")

    def update_book(self, book_id):
        """修改图书"""
        try:
            self.cursor.execute("SELECT * FROM book WHERE book_id = %s", (book_id,))
            book = self.cursor.fetchone()
            if not book: print("❌ 未找到该图书！"); return

            print(f"当前：《{book['title']}》 作者：{book['author']} 分类：{book['category']} (回车不修改)")
            new_title = input("新书名：").strip()
            new_author = input("新作者：").strip()
            new_cat = input("新分类：").strip()

            data = {
                "title": new_title if new_title else book['title'],
                "author": new_author if new_author else book['author'],
                "category": new_cat if new_cat else book['category']
            }

            if confirm_action("⚠️ 确认修改吗？"):
                self.cursor.execute("UPDATE book SET title=%s, author=%s, category=%s WHERE book_id=%s", (data['title'], data['author'], data['category'], book_id))
                self.conn.commit()
                print("✅ 修改成功！")
                write_log(f"修改图书：编号{book_id}", self.current_user)
            else: print("❌ 已取消")
        except Exception as e: self.conn.rollback(); print(f"❌ 修改失败: {e}")

    def delete_book(self, book_id):
        """删除图书"""
        try:
            self.cursor.execute("SELECT * FROM book WHERE book_id = %s", (book_id,))
            book = self.cursor.fetchone()
            if not book: print("❌ 未找到该图书！"); return

            if confirm_action(f"⚠️ 确定删除《{book['title']}》吗？"):
                self.cursor.execute("DELETE FROM book WHERE book_id = %s", (book_id,))
                self.conn.commit()
                print("✅ 删除成功！")
                write_log(f"删除图书：编号{book_id}", self.current_user)
            else: print("❌ 已取消")
        except Exception as e: self.conn.rollback(); print(f"❌ 删除失败: {e}")

    # ------------------ 借阅管理增强模块 ------------------

    def borrow_book(self, book_id, reader_id, reader_name):
        """借阅图书：含限额(3本)与状态校验"""
        try:
            # 1. 检查图书状态
            self.cursor.execute("SELECT * FROM book WHERE book_id = %s", (book_id,))
            book = self.cursor.fetchone()
            if not book: print("❌ 未找到该图书！"); return
            if book['status'] == '已借出': print("❌ 该图书已被借出！"); return

            # 2. 限额校验：检查该读者当前借阅中(is_returned=0)的数量
            self.cursor.execute("SELECT COUNT(*) as cnt FROM borrower WHERE reader_id = %s AND is_returned = 0", (reader_id,))
            borrow_count = self.cursor.fetchone()['cnt']
            if borrow_count >= 3:
                print(f"❌ 借阅失败！读者 {reader_name} 已借阅 {borrow_count} 本，达到上限(3本)！")
                return

            # 3. 执行借阅
            self.cursor.execute("UPDATE book SET status='已借出' WHERE book_id=%s", (book_id,))
            borrow_date = datetime.date.today()
            self.cursor.execute("INSERT INTO borrower(reader_id, reader_name, book_id, borrow_date, is_returned) VALUES(%s,%s,%s,%s,0)",
                                (reader_id, reader_name, book_id, borrow_date))

            self.conn.commit()
            print(f"✅ 借阅成功！《{book['title']}》已借给 {reader_name}(当前借阅{borrow_count+1}本)")
            write_log(f"借出图书：编号{book_id} 借阅人{reader_name}", self.current_user)
        except Exception as e:
            self.conn.rollback()
            print(f"❌ 借阅失败: {e}")

    def return_book(self, book_id):
        """归还图书"""
        try:
            self.cursor.execute("SELECT * FROM book WHERE book_id = %s", (book_id,))
            book = self.cursor.fetchone()
            if not book: print("❌ 未找到该图书！"); return
            if book['status'] == '可借阅': print("❌ 该图书未被借出！"); return

            self.cursor.execute("UPDATE book SET status='可借阅' WHERE book_id=%s", (book_id,))
            return_date = datetime.date.today()
            self.cursor.execute("""UPDATE borrower SET return_date=%s, is_returned=1 
                                   WHERE book_id=%s AND is_returned=0 ORDER BY borrow_date DESC LIMIT 1""", (return_date, book_id))

            self.conn.commit()
            print(f"✅ 归还成功！《{book['title']}》已入库")
            write_log(f"归还图书：编号{book_id}", self.current_user)
        except Exception as e: self.conn.rollback(); print(f"❌ 归还失败: {e}")

    def show_borrowed_books(self):
        """展示所有已借出图书及借阅信息"""
        try:
            # 关联查询图书表和借阅者表，找出所有未归还的记录
            sql = """SELECT b.book_id, b.title, w.reader_id, w.reader_name, w.borrow_date 
                     FROM borrower w JOIN book b ON w.book_id = b.book_id 
                     WHERE w.is_returned = 0 
                     ORDER BY w.borrow_date DESC"""
            self.cursor.execute(sql)
            records = self.cursor.fetchall()

            if not records:
                print("\n✅ 当前没有借出的图书！")
            else:
                print(f"\n{'='*80}")
                print(f"  📕 当前借出图书列表 (共 {len(records)} 本)")
                print(f"{'='*80}")
                print(f"{'图书编号':<10}{'书名':<20}{'读者ID':<10}{'读者姓名':<10}{'借阅日期':<15}")
                print("-" * 80)
                for r in records:
                    print(f"{r['book_id']:<10}{r['title']:<20}{r['reader_id']:<10}{r['reader_name']:<10}{str(r['borrow_date']):<15}")
                print("=" * 80)
        except Exception as e:
            print(f"❌ 查询借阅信息失败: {e}")

    def show_overdue(self):
        """逾期提醒：借阅超过30天未还"""
        try:
            overdue_date = datetime.date.today() - datetime.timedelta(days=30)
            sql = """SELECT b.book_id, b.title, w.reader_id, w.reader_name, w.borrow_date 
                     FROM borrower w JOIN book b ON w.book_id = b.book_id 
                     WHERE w.is_returned = 0 AND w.borrow_date < %s"""
            self.cursor.execute(sql, (overdue_date,))
            records = self.cursor.fetchall()

            if not records:
                print("\n✅ 暂无逾期未还的图书！")
            else:
                print(f"\n{'='*80}\n ⚠️  逾期图书提醒 (借阅超过30天)\n{'='*80}")
                print(f"{'图书编号':<10}{'书名':<20}{'读者ID':<10}{'读者姓名':<10}{'借阅日期':<15}\n" + "-"*80)
                for r in records:
                    print(f"{r['book_id']:<10}{r['title']:<20}{r['reader_id']:<10}{r['reader_name']:<10}{str(r['borrow_date']):<15}")
                print("="*80)
        except Exception as e: print(f"❌ 查询逾期失败: {e}")

    # ------------------ 数据统计模块 ------------------

    def show_statistics(self):
        """数据统计面板"""
        try:
            self.cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status='已借出' THEN 1 ELSE 0 END) as borrowed, SUM(CASE WHEN status='可借阅' THEN 1 ELSE 0 END) as available FROM book")
            stat = self.cursor.fetchone()

            self.cursor.execute("""SELECT b.title, COUNT(w.id) as times FROM borrower w JOIN book b ON w.book_id = b.book_id 
                                   GROUP BY w.book_id ORDER BY times DESC LIMIT 3""")
            top3 = self.cursor.fetchall()

            print(f"\n{'='*40}")
            print("  📊 图书馆数据统计面板")
            print(f"{'='*40}")
            print(f"  📚 图书总数：{stat['total']} 本")
            print(f"  📕 已借出数：{stat['borrowed']} 本")
            print(f"  📗 可借阅数：{stat['available']} 本")
            print(f"{'-'*40}")
            print("  🔥 热门借阅 Top 3:")
            if not top3:
                print("     暂无借阅记录")
            else:
                for idx, t in enumerate(top3, 1):
                    print(f"     {idx}. 《{t['title']}》 - 被借 {t['times']} 次")
            print(f"{'='*40}")
        except Exception as e: print(f"❌ 统计失败: {e}")

    def close(self):
        """关闭数据库连接"""
        if self.cursor: self.cursor.close()
        if self.conn: self.conn.close()


# ====================== 主菜单流程 ======================

def main():
    """主程序入口"""
    login_result = login_system()
    if not login_result: print("👋 已退出系统，再见！"); return

    current_user, user_role = login_result
    bm = BookManager(current_user, user_role)
    if not bm.cursor: return

    while True:
        role_tag = "👑超管" if user_role == 'super' else "👤管员"
        print(f"\n{'=' * 50}")
        print(f"    📖 图书管理系统 【{role_tag}:{current_user}】")
        print(f"{'=' * 50}")
        print("  1.添加图书        6.借阅图书       11.修改密码")
        print("  2.查看所有图书     7.归还图书       12.管理员管理")
        print("  3.搜索图书        8.逾期提醒       13.批量导入图书")
        print("  4.修改图书        9.数据统计")
        print("  5.删除图书        10.查看已借图书    0.退出系统")
        print(f"{'=' * 50}")

        choice = input("请输入功能编号：").strip()

        if choice == "1":
            bid = input("编号：").strip()
            title = input("书名：").strip()
            author = input("作者：").strip()
            cat = input("分类：").strip()
            if bid and title and author and cat:
                bm.add_book(bid, title, author, cat)
            else:
                print("❌ 字段不能为空！")
        elif choice == "2":
            bm.show_all_books()
        elif choice == "3":
            bm.search_books()
        elif choice == "4":
            bm.update_book(input("修改编号：").strip())
        elif choice == "5":
            bm.delete_book(input("删除编号：").strip())
        elif choice == "6":
            bid = input("借阅编号：").strip()
            rid = input("读者ID：").strip()
            rname = input("读者姓名：").strip()
            if bid and rid and rname:
                bm.borrow_book(bid, rid, rname)
            else:
                print("❌ 不能为空！")
        elif choice == "7":
            bm.return_book(input("归还编号：").strip())
        elif choice == "8":
            bm.show_overdue()
        elif choice == "9":
            bm.show_statistics()
        elif choice == "10":
            bm.show_borrowed_books()  # 新增的菜单入口
        elif choice == "11":
            bm.change_password()
        elif choice == "12":
            bm.manage_admins()
        elif choice == "13":
            bm.batch_import_books()
        elif choice == "0":
            bm.close()
            write_log("退出系统", current_user)
            print("👋 系统退出，再见！")
            break
        else:
            print("❌ 无效输入")


if __name__ == "__main__":
    main()
