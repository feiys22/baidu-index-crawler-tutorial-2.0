# Cookie 获取详细教程

> 百度指数需要登录才能访问 API，Cookie 是你的"门票"

## 获取方式（详细图文步骤）

### 方法一：Chrome 开发者工具（推荐）

1. **打开百度指数并登录**
   - Chrome 访问 https://index.baidu.com
   - 点击右上角"登录"，用百度账号登录
   - 确保页面加载完整，能正常看到搜索框

2. **打开开发者工具**
   - 按 `F12` 或 `Ctrl+Shift+I`（Mac: `Cmd+Option+I`）

3. **定位到 Cookie**
   - 切换到 **Application** 标签页（如果没看到，点 `»` 展开）
   - 左侧导航栏展开 **Cookies**
   - 点击 `https://index.baidu.com`

4. **复制 Cookie 字符串**
   - 你会看到一个表格，每一行是一个 Cookie
   - **不要手动复制每一行！** 正确的做法：
     - **方法A（推荐）**：在任意 Cookie 上右键 → "Show Decoded" → 全选所有文本 → 复制
     - **方法B**：在 Console 运行：
       ```javascript
       copy(document.cookie)
       ```
   - 得到一个以分号 `;` 分隔的字符串

5. **填入脚本**
   ```python
   COOKIE_LIST = [
       '''这里放你的 Cookie 字符串''',
   ]
   ```

## Cookie 里有什么？

一个典型的百度 Cookie 字符串长这样：

```
BIDUPSID=6569AF53050B113CC957BEE8126B2F1B; 
PSTM=1776938545; 
BAIDUID=6569AF53050B113C64E5B2D2161F4EF0:FG=1; 
BDUSS=dGWXA0UEZ3OW5kVUp...;
...（还有几十个）
```

**关键字段**：
- `BDUSS`：最重要的登录凭证，一般很长
- `PSTM`：时间戳
- `BAIDUID`：设备标识

## 为什么 Cookie 会失效？

- **手动登出**：点击百度账号的"退出登录"
- **过期**：百度 Cookie 一般持续数小时到数天
- **异地登录**：在其他设备登录可能导致当前 Cookie 失效
- **频繁请求**：被百度反爬检测到时，Cookie 被标记

**失效表现**：API 返回 `status: 10000`（未登录）

## 多 Cookie 轮询

如果你有多个百度账号，可以都获取 Cookie 填入：

```python
COOKIE_LIST = [
    '''BIDUPSID=xxx; PSTM=xxx; ...账号1的完整Cookie...''',
    '''BIDUPSID=yyy; PSTM=yyy; ...账号2的完整Cookie...''',
    '''BIDUPSID=zzz; PSTM=zzz; ...账号3的完整Cookie...''',
]
```

脚本会在每次请求时随机选一个 Cookie，降低单个账号的请求压力。
