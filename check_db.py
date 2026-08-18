from config import get_db

db = get_db()


cur = db.cursor()

cur.execute("SELECT COUNT(*) as cnt FROM products")
print("Total products:", cur.fetchone())

cur.execute("SELECT COUNT(*) as cnt FROM products WHERE status='active'")
print("Active products:", cur.fetchone())

cur.execute("SELECT id, name, status FROM products LIMIT 5")
for row in cur.fetchall():
    print(row)

db.close()
