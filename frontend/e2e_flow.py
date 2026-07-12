"""前端用户流程联调模拟

按真实前端页面调用顺序逐个验证：
- LoginPage          → POST /auth/login
- ProfilesPage       → GET  /profiles
- ProfileEditPage    → POST /profiles  (如果没有)
- ListingListPage    → GET  /listings
- ListingDetailPage  → GET  /listings/{id} + GET /scores/{id}
- SearchPage         → GET  /search?q=...
- RecommendPage      → GET  /recommend?profile_id=...
- FavoritesPage      → POST /favorites + GET /favorites

前端通过 vite proxy /api → :8000，我们直接打 :5173 端口模拟浏览器。
"""
import httpx

FRONT = "http://localhost:5173"  # vite dev server（proxy /api → :8000）

passed, failed = 0, 0


def step(label, ok, extra=""):
    global passed, failed
    mark = "✓" if ok else "✗"
    passed += ok
    failed += not ok
    print(f"  {mark} {label}  {extra}")


print("=" * 60)
print("前端联调：通过 vite proxy 模拟用户流程")
print("=" * 60)

c = httpx.Client(base_url=FRONT, timeout=15)

# 1. 登录
print("\n[1] LoginPage → /auth/login")
r = c.post("/api/v1/auth/login", json={"account": "apismoke@test.com", "password": "Test1234!"})
token = r.json()["data"]["access_token"] if r.status_code == 200 else None
step(f"HTTP {r.status_code}", r.status_code == 200)
if not token:
    raise SystemExit("登录失败，无法继续")
headers = {"Authorization": f"Bearer {token}"}

# 2. 列画像（ProtectedRoute 进入 /profiles 时调）
print("\n[2] ProfilesPage → /profiles")
r = c.get("/api/v1/profiles", headers=headers)
profiles = r.json()["data"] if r.status_code == 200 else []
step(f"HTTP {r.status_code}", r.status_code == 200, f"已有 {len(profiles)} 个画像")

# 3. 创建画像（如果没有）
if not profiles:
    print("\n[3] ProfileEditPage → POST /profiles")
    r = c.post("/api/v1/profiles", headers=headers, json={
        "name": "前端联调画像",
        "city": "北京",
        "budget_min": 2000,
        "budget_max": 4000,
        "occupants": 1,
        "areas": ["朝阳区"],
        "layouts": ["一室一厅"],
        "commute": [{"location": "国贸", "max_time": 45, "weight": 1.0, "mode": "transit"}],
        "environment": {"quiet_required": True, "lighting_required": True},
        "keywords": {"must_have": ["电梯"], "exclude": ["隔断房"]},
        "size_range": [10, 30],
    })
    step(f"HTTP {r.status_code}", r.status_code in (200, 201))
    profiles = [r.json()["data"]] if r.status_code in (200, 201) else []
profile_id = profiles[0]["id"]

# 4. 列房源
print("\n[4] ListingListPage → /listings")
r = c.get("/api/v1/listings", headers=headers, params={"page": 1, "page_size": 5})
step(f"HTTP {r.status_code}", r.status_code == 200)
listings_data = r.json()["data"]
step(f"返回 {len(listings_data.get('items', []))} 套", listings_data.get("total", 0) > 0,
     f"total={listings_data.get('total')}")
first_listing = listings_data["items"][0]

# 5. 房源详情 + 评分
print(f"\n[5] ListingDetailPage → /listings/{{id}} + /scores/{{id}}")
r = c.get(f"/api/v1/listings/{first_listing['id']}", headers=headers)
step(f"GET /listings/{{id}} HTTP {r.status_code}", r.status_code == 200)
r = c.get(f"/api/v1/scores/{first_listing['id']}", headers=headers)
score_data = r.json()["data"] if r.status_code == 200 else {}
step(f"GET /scores/{{id}} HTTP {r.status_code}", r.status_code == 200,
     f"general={score_data.get('general_score')}")

# 6. 搜索（中文）
print("\n[6] SearchPage → /search?q=望京")
r = c.get("/api/v1/search", headers=headers, params={"q": "望京"})
hits = r.json()["data"]["total"] if r.status_code == 200 else 0
step(f"HTTP {r.status_code}", r.status_code == 200 and hits > 0, f"hits={hits}")

# 7. 推荐
print(f"\n[7] RecommendPage → /recommend?profile_id={profile_id[:8]}...")
r = c.get("/api/v1/recommend", headers=headers,
          params={"profile_id": profile_id, "page": 1, "page_size": 10})
rec_data = r.json()["data"] if r.status_code == 200 else {}
step(f"HTTP {r.status_code}", r.status_code == 200,
     f"total={rec_data.get('total')}, top={rec_data['items'][0]['personalized_score'] if rec_data.get('items') else 'N/A'}")

# 8. 收藏 → 列表 → 删除
print(f"\n[8] FavoritesPage → POST /favorites + GET /favorites")
r = c.post("/api/v1/favorites", headers=headers, json={
    "listing_id": first_listing["id"],
    "category": "待看",
    "note": "联调测试",
})
step(f"POST /favorites HTTP {r.status_code}", r.status_code in (200, 201))

r = c.get("/api/v1/favorites", headers=headers)
fav_data = r.json()["data"] if r.status_code == 200 else {}
step(f"GET  /favorites HTTP {r.status_code}", r.status_code == 200,
     f"total={fav_data.get('total', len(fav_data.get('items', [])))}")

r = c.delete(f"/api/v1/favorites/{first_listing['id']}", headers=headers)
step(f"DEL  /favorites HTTP {r.status_code}", r.status_code in (200, 204))

# 总结
print()
print("=" * 60)
print(f"前端联调: {passed} passed, {failed} failed → {'PASS ✓' if failed == 0 else 'FAIL ✗'}")
print("=" * 60)
