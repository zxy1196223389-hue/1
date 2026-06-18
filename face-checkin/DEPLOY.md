# Render 云部署 - 手把手教程

## 你需要准备
- 一个 GitHub 账号（免费注册：https://github.com/signup ）
- 一个 Render 账号（免费注册：https://render.com/ ，点 "Get Started" → 选 GitHub 登录）
- 把 face-checkin 文件夹上传到 GitHub

---

## 第一步：创建 GitHub 仓库并上传代码

### 1.1 注册 GitHub
打开 https://github.com/signup ，输入邮箱、密码、用户名，完成注册。

### 1.2 创建仓库
登录后，点右上角 **+** → **New repository**
- Repository name: `face-checkin`（或任意名字）
- 选 **Public**（免费必须公开）
- 不要勾选任何选项
- 点 **Create repository**

### 1.3 上传文件
创建后会跳到一个页面，上面写着 "Quick setup"。

**最简单的方法：直接把文件拖进去**

1. 在页面中间找到 "uploading an existing file" 这个链接，点进去
2. 打开你电脑上的 `face-checkin` 文件夹
3. 把里面的所有文件**全部拖到浏览器窗口**里
4. 文件列表应该包含：
   - `server.py`
   - `checkin.html`
   - `admin.html`
   - `leader.html`
   - `start.bat`
   - `requirements.txt`
5. 拖完后往下拉，点绿色的 **Commit changes** 按钮

---

## 第二步：连接 Render 部署

### 2.1 注册 Render
打开 https://render.com/ ，点 **Get Started for Free**

选择 **Sign in with GitHub**，授权 Render 访问你的 GitHub。

### 2.2 创建 Web Service
登录后进入 Dashboard，点 **New +** → **Web Service**

这时会要求你连接 GitHub 仓库：

1. 点 **Connect account**（如果还没连 GitHub）
2. 在列表中找到 `face-checkin` 仓库
3. 点 **Connect**

### 2.3 配置部署参数
连接后会进入配置页面，按以下填写：

| 字段 | 填写内容 |
|------|---------|
| **Name** | `face-checkin`（随便取名） |
| **Region** | `Singapore`（离中国最近） |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python3 server.py` |
| **Instance Type** | **Free**（免费） |

其他选项不用动。

### 2.4 设置端口
往下滚动，找到 **Advanced** 点开：
- 添加环境变量：
  - Key: `PORT`
  - Value: `8080`
  - Key: `RENDER_DATA_DIR`
  - Value: `/var/data`

> **重要：** `RENDER_DATA_DIR=/var/data` 表示数据存到 Render 持久磁盘，休眠重启后不会丢失！

### 2.5 开始部署
点页面底部的 **Create Web Service** 按钮。

Render 会自动：
1. 拉取你的 GitHub 代码
2. 安装 Python 依赖
3. 启动服务器

等待 2-5 分钟，看到 `Your service is live` 就成功了！

---

## 第三步：获取你的域名

部署成功后，页面顶部会显示你的域名，类似：
```
https://face-checkin-xxxx.onrender.com
```

这就是你的公网地址，7×24小时在线。

---

## 第四步：设置公网地址并生成二维码

1. 打开浏览器访问你的域名 + `/admin`，例如：
   ```
   https://face-checkin-xxxx.onrender.com/admin
   ```

2. 进入「🔗 二维码」页签

3. 在「公网地址」输入框中粘贴你的 Render 域名（注意用 `https://`）

4. 点「💾 保存」

5. 二维码自动更新，点「💾 下载」保存打印

---

## 第五步：使用

### 管理员
- 管理后台：`https://你的域名/admin`
- 录入员工人脸
- 下载打印二维码贴在打卡处

### 员工
- 微信扫二维码 → 自动人脸识别 → 打卡成功

### 领导
- 领导看板：`https://你的域名/leader`
- 实时查看谁已到、谁未到

---

## 注意事项

**关于休眠：**
Render 免费层 15 分钟无人访问会自动休眠。有人扫码时第一次打开可能等 30-50 秒（模型加载+唤醒），之后再访问就正常了。

**解决办法：**
可以用一个免费的定时访问服务（如 cron-job.org、uptimerobot.com），每 10 分钟访问一次你的网址，就不会休眠了。

**关于存储：**
Render 免费层的磁盘不持久，重启后数据会丢失。建议把 `data/` 文件夹的数据定期备份。

---

## 如果部署失败

常见问题：

1. **Build 失败** → 检查 `requirements.txt` 是否上传、GitHub 仓库是否完整
2. **启动失败** → 看 Render 日志（Dashboard → 点你的服务 → Logs），把报错发给我
3. **打不开网页** → 确认 PORT 环境变量设为 8080

把错误日志发给我，我帮你解决。
