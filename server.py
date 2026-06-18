#!/usr/bin/env python3
import http.server, json, os, socket, subprocess, sys, threading, time, base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
import qrcode

PORT = int(os.environ.get("PORT", 8080))
TZ = timezone(timedelta(hours=8))  # 北京时间 UTC+8
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = Path(os.environ.get("RENDER_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(exist_ok=True)
RECORDS_FILE = DATA_DIR / "records.json"
STAFF_FILE = DATA_DIR / "staff.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

def lj(p, d):
    try: return json.loads(Path(p).read_text("utf-8"))
    except: return d
def sj(p, d): Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=2), "utf-8")
def lr(): return lj(RECORDS_FILE, [])
def sr(r): sj(RECORDS_FILE, r)
def ls(): return lj(STAFF_FILE, [])
def ss(s): sj(STAFF_FILE, s)
def lset(): return lj(SETTINGS_FILE, {"project_name": "默认项目"})
def sset(s): sj(SETTINGS_FILE, s)

def checkin(name):
    """签到：同一人同一天只记录第一次，重复不计"""
    recs = lr(); n = datetime.now(TZ)
    today_str = n.strftime("%Y-%m-%d")
    # 检查今天是否已经签到
    for r in recs:
        if r["name"] == name.strip() and r["date"] == today_str:
            return r  # 已签到，返回已有记录
    r = {"id": n.strftime("%Y%m%d%H%M%S")+str(n.microsecond//1000).zfill(3),
         "name": name.strip(), "timestamp": n.isoformat(), "date": today_str,
         "time": n.strftime("%H:%M:%S"), "weekday": n.strftime("%A")}
    recs.insert(0, r); sr(recs)
    stf = ls()
    if not any(s["name"] == name.strip() for s in stf):
        stf.append({"id": n.strftime("%Y%m%d%H%M%S"), "name": name.strip(), "dept": "", "photo": None}); ss(stf)
    return r

def grd(d): return [r for r in lr() if r["date"] == d]
def grr(s, e): return [r for r in lr() if s <= r["date"] <= e]

# ngrok
_ngp = None; _ngu = None
def fng():
    for nm in ["ngrok.exe", "ngrok"]:
        if (BASE_DIR/nm).exists(): return str(BASE_DIR/nm)
    for nm in ["ngrok", "ngrok.exe"]:
        try:
            if subprocess.run([nm, "version"], capture_output=True, timeout=5).returncode == 0: return nm
        except: pass
    return None
def sng():
    global _ngp, _ngu
    p = fng()
    if not p: return False
    try:
        _ngp = subprocess.Popen([p, "http", str(PORT), "--log=stdout"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(4); _ngu = fnu(); return _ngu is not None
    except: return False
def fnu():
    try:
        import urllib.request
        r = urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=3)
        for t in json.loads(r.read()).get("tunnels", []):
            if t.get("proto") == "https": return t["public_url"]
    except: pass
    return None
def gnu():
    global _ngu
    u = fnu()
    if u: _ngu = u
    return _ngu
def kng():
    global _ngp
    if _ngp:
        try: _ngp.terminate(); _ngp.wait(timeout=5)
        except:
            try: _ngp.kill()
            except: pass
        _ngp = None
def gip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"
def gpu():
    u = lset().get("public_url", "").strip()
    if u: return u.rstrip("/")
    nu = gnu()
    if nu: return nu
    return f"http://{gip()}:{PORT}"
def rqr():
    try: qrcode.make(gpu(), border=3).save(BASE_DIR/"checkin_qr.png")
    except: pass

def api(data):
    m = data.get("method", "")
    try:
        if m == "checkin":
            n = data.get("name", "").strip()
            if not n: return {"ok": False, "error": "姓名不能为空"}
            if len(n) > 30: return {"ok": False, "error": "姓名过长"}
            r = checkin(n)
            # 如果返回的 record 时间不是刚刚（意味着已签到过），标记 duplicate
            now = datetime.now(TZ)
            rt = datetime.fromisoformat(r["timestamp"])
            is_dup = (now - rt).seconds > 5  # 超过5秒说明是旧记录
            return {"ok": True, "record": r, "today": grd(now.strftime("%Y-%m-%d")),
                    "duplicate": is_dup, "message": "今日已签到" if is_dup else "签到成功"}
        elif m == "get_today":
            return {"ok": True, "records": grd(datetime.now(TZ).strftime("%Y-%m-%d"))}
        elif m == "get_records_by_date":
            return {"ok": True, "records": grd(data.get("date", datetime.now(TZ).strftime("%Y-%m-%d")))}
        elif m == "get_records_by_range":
            return {"ok": True, "records": grr(data.get("start",""), data.get("end",""))}
        elif m == "get_all_records":
            return {"ok": True, "records": lr()}
        elif m == "get_staff":
            return {"ok": True, "staff": ls()}
        elif m == "get_staff_with_stats":
            stf = ls(); recs = lr()
            ts = datetime.now(TZ).strftime("%Y-%m-%d")
            ms = (datetime.now(TZ) - timedelta(days=datetime.now(TZ).weekday())).strftime("%Y-%m-%d")
            mf = datetime.now(TZ).strftime("%Y-%m") + "-01"
            res = []
            for s in stf:
                nm = s["name"]
                tc = sum(1 for r in recs if r["name"]==nm and r["date"]==ts)
                wc = sum(1 for r in recs if r["name"]==nm and r["date"]>=ms)
                mc = sum(1 for r in recs if r["name"]==nm and r["date"]>=mf)
                ac = sum(1 for r in recs if r["name"]==nm)
                hp = bool(s.get("photo"))
                res.append({**s, "today": tc, "week": wc, "month": mc, "total": ac, "has_photo": hp, "photo": s.get("photo") if hp else None})
            return {"ok": True, "staff": res}
        elif m == "add_staff":
            n = data.get("name","").strip()
            if not n: return {"ok": False, "error": "姓名不能为空"}
            stf = ls()
            if any(s["name"]==n for s in stf): return {"ok": False, "error": "该员工已存在"}
            stf.append({"id": datetime.now(TZ).strftime("%Y%m%d%H%M%S"), "name": n, "dept": data.get("dept","").strip(), "photo": None})
            ss(stf); return {"ok": True}
        elif m == "remove_staff":
            n = data.get("name","").strip()
            ss([s for s in ls() if s["name"] != n]); return {"ok": True}
        elif m == "upload_photo":
            n = data.get("name","").strip(); p = data.get("photo","")
            if not n: return {"ok": False, "error": "姓名不能为空"}
            stf = ls(); found = False
            for s in stf:
                if s["name"]==n: s["photo"]=p; found=True; break
            if not found: return {"ok": False, "error": "未找到该员工"}
            ss(stf); return {"ok": True, "message": f"照片已保存: {n}"}
        elif m == "get_photo":
            n = data.get("name","").strip()
            for s in ls():
                if s["name"]==n and s.get("photo"): return {"ok": True, "photo": s["photo"]}
            return {"ok": False, "error": "无照片"}
        elif m == "remove_photo":
            n = data.get("name","").strip()
            stf = ls()
            for s in stf:
                if s["name"]==n: s["photo"]=None; break
            ss(stf); return {"ok": True}
        elif m == "register_face":
            """录入人脸：管理员为员工上传/拍照的人脸特征向量"""
            n = data.get("name","").strip()
            embedding = data.get("embedding")
            if not n or not embedding: return {"ok": False, "error": "缺少姓名或人脸数据"}
            if not isinstance(embedding, list) or len(embedding) != 128:
                return {"ok": False, "error": "人脸数据格式错误(需128维特征向量)"}
            stf = ls(); found = False
            for s in stf:
                if s["name"] == n:
                    s["face_embedding"] = embedding
                    s["registered_at"] = datetime.now(TZ).isoformat()
                    found = True; break
            if not found:
                stf.append({"id": datetime.now(TZ).strftime("%Y%m%d%H%M%S"), "name": n,
                            "dept": "", "photo": None,
                            "face_embedding": embedding,
                            "registered_at": datetime.now(TZ).isoformat()})
            ss(stf); return {"ok": True, "message": f"人脸录入成功: {n}"}
        elif m == "get_face_embeddings":
            """返回所有人脸特征向量(给打卡页面做匹配用)"""
            stf = ls(); res = []
            for s in stf:
                if s.get("face_embedding"):
                    res.append({"name": s["name"], "dept": s.get("dept",""),
                                "embedding": s["face_embedding"]})
            return {"ok": True, "embeddings": res, "count": len(res)}
        elif m == "remove_face":
            n = data.get("name","").strip()
            stf = ls()
            for s in stf:
                if s["name"]==n: s["face_embedding"]=None; s["registered_at"]=None; break
            ss(stf); return {"ok": True}
        elif m == "get_settings":
            return {"ok": True, **lset()}
        elif m == "update_settings":
            st = lset()
            for k in ["project_name", "public_url"]:
                if k in data: st[k] = data[k]
            sset(st); rqr(); return {"ok": True}
        elif m == "get_ngrok_status":
            u = gnu(); return {"ok": True, "ngrok_url": u, "enabled": u is not None}
        elif m == "auto_detect_ngrok":
            u = gnu()
            if u:
                st = lset(); st["public_url"]=u; sset(st); rqr()
                return {"ok": True, "ngrok_url": u, "message": f"已自动配置: {u}"}
            return {"ok": False, "error": "未检测到 ngrok"}
        elif m == "get_stats":
            stf = ls(); recs = lr(); ts = datetime.now(TZ).strftime("%Y-%m-%d")
            td = [r for r in recs if r["date"]==ts]
            return {"ok": True, "today_count": len(td), "today_uniq": len(set(r["name"] for r in td)),
                    "total_records": len(recs), "total_staff": len(stf)}
        elif m == "get_leaderboard":
            """领导看板数据：今日出勤概览、员工列表、签到情况"""
            stf = ls(); recs = lr()
            ts = datetime.now(TZ).strftime("%Y-%m-%d")
            today_recs = [r for r in recs if r["date"]==ts]
            today_names = {r["name"]: r["time"] for r in today_recs}
            # 全部员工及其今日状态
            emp_status = []
            present = 0; absent = 0
            for s in stf:
                nm = s["name"]
                has_face = bool(s.get("face_embedding"))
                if nm in today_names:
                    emp_status.append({"name": nm, "dept": s.get("dept",""), "status": "已签到",
                                       "time": today_names[nm], "has_face": has_face})
                    present += 1
                else:
                    emp_status.append({"name": nm, "dept": s.get("dept",""), "status": "未签到",
                                       "time": None, "has_face": has_face})
                    absent += 1
            return {"ok": True, "project_name": lset().get("project_name",""),
                    "today": ts, "total": len(stf), "present": present, "absent": absent,
                    "employees": emp_status, "today_records": today_recs}
        elif m == "get_leaderboard_week":
            """领导看板：本周考勤表"""
            stf = ls(); recs = lr()
            monday = datetime.now(TZ) - timedelta(days=datetime.now(TZ).weekday())
            ms = monday.strftime("%Y-%m-%d")
            # 本周7天
            days = []
            for i in range(7):
                d = monday + timedelta(days=i)
                days.append(d.strftime("%Y-%m-%d"))
            # 构建考勤表
            table = []
            for s in stf:
                nm = s["name"]
                row = {"name": nm, "dept": s.get("dept","")}
                cnt = 0
                for dd in days:
                    matched = [r for r in recs if r["name"]==nm and r["date"]==dd]
                    row[dd] = matched[0]["time"] if matched else None
                    if matched: cnt += 1
                row["total"] = cnt
                table.append(row)
            return {"ok": True, "days": days, "table": table, "total_staff": len(stf)}
        else:
            return {"ok": False, "error": f"未知方法: {m}"}
    except Exception as e:
        import traceback; traceback.print_exc(); return {"ok": False, "error": str(e)}

# 自动唤醒：服务器启动后30秒开始定期自检
def start_keepalive():
    def _ping():
        while True:
            time.sleep(600)  # 每10分钟自检一次
            try:
                import urllib.request
                settings = load_settings()
                url = settings.get("public_url", f"http://localhost:{PORT}")
                urllib.request.urlopen(f"{url}/api", data=b'{}', timeout=10)
            except Exception:
                pass
    t = threading.Thread(target=_ping, daemon=True)
    t.start()

def load_html(name):
    p = BASE_DIR / name
    if p.exists(): return p.read_text("utf-8")
    return "<h1>Not found</h1>"

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, f, *a): print(f"[{datetime.now(TZ).strftime('%H:%M:%S')}] {a[0]}")
    def do_GET(self):
        pt = self.path.split("?")[0]
        if pt == "/" or pt == "/checkin": self._html(load_html("checkin.html"))
        elif pt == "/admin": self._html(load_html("admin.html"))
        elif pt == "/leader": self._html(load_html("leader.html"))
        elif pt == "/qr.png": self._qr()
        else: self.send_error(404)
    def do_POST(self):
        if self.path == "/api":
            try: d = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
            except: d = {}
            self._json(api(d))
        else: self.send_error(404)
    def do_OPTIONS(self):
        self.send_response(200); self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type"); self.end_headers()
    def _html(self, c):
        self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Cache-Control","no-cache"); self.end_headers()
        self.wfile.write(c.encode("utf-8"))
    def _json(self, d):
        self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Cache-Control","no-cache")
        self.send_header("Access-Control-Allow-Origin","*"); self.end_headers()
        self.wfile.write(json.dumps(d, ensure_ascii=False).encode("utf-8"))
    def _qr(self):
        img = qrcode.make(gpu(), border=3); buf = __import__("io").BytesIO(); img.save(buf, format="PNG")
        self.send_response(200); self.send_header("Content-Type","image/png")
        self.send_header("Cache-Control","no-cache"); self.end_headers(); self.wfile.write(buf.getvalue())

def main():
    ip = gip(); st = lset(); lu = f"http://{ip}:{PORT}"
    print("="*60)
    print("   Face Recognition Checkin System")
    print("="*60)
    print()
    print("   Checking ngrok...")
    ok = sng()
    pu = st.get("public_url","").strip()
    if ok and gnu() and not pu:
        st["public_url"]=gnu(); sset(st); pu=gnu()
    if ok: print(f"   ngrok: {gnu()}")
    else: print("   ngrok not found")
    print()
    du = pu if pu else lu; rqr()
    print(f"   Checkin:   {du}")
    print(f"   Admin:     {lu}/admin")
    print(f"   Leader:    {lu}/leader")
    print(f"   QR Code:   {lu}/qr.png")
    print()
    print("   Steps:")
    print("      1. Admin -> Add Staff -> Register Face")
    print("      2. Staff scan QR -> Face Recognition -> Checkin")
    print("      3. Leader view: /leader")
    print(f"\n   Server started (port {PORT})\n"+"="*60+"\n")
    def w():
        while True:
            try:
                u = fnu()
                if u and u != _ngu:
                    _ngu = u; s = lset()
                    if not s.get("public_url"): s["public_url"]=u; sset(s); rqr()
            except: pass
            time.sleep(10)
    threading.Thread(target=w, daemon=True).start()
    start_keepalive()
    print("   Auto-keepalive enabled (10min interval)")
    srv = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    try: srv.serve_forever()
    except KeyboardInterrupt: print("Stopped"); kng(); srv.shutdown()
