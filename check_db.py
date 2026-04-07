import MySQLdb
import MySQLdb.cursors

db = MySQLdb.connect(
    host='localhost', user='root', passwd='7486',
    db='akhgam_herbals', charset='utf8mb4',
    cursorclass=MySQLdb.cursors.DictCursor
)
cur = db.cursor()

cur.execute("SELECT COUNT(*) as cnt FROM products")
print("Total products:", cur.fetchone())

cur.execute("SELECT COUNT(*) as cnt FROM products WHERE status='active'")
print("Active products:", cur.fetchone())

cur.execute("SELECT id, name, status FROM products LIMIT 5")
for row in cur.fetchall():
    print(row)

db.close()
