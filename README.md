# 百度指数爬取教程 2.0

> 基于 Scrapling 的百度指数爬虫 —— 反爬能力更强，长期维护更可靠

## 为什么从 qdata 换成 Scrapling？

**v1 版（qdata 库）** 的问题：
- qdata 用 `requests` 库发请求，容易被百度反爬识别
- 百度指数 API 经常更新加密逻辑，qdata 可能失效
- qdata 库本身可能停止维护

**v2 版（Scrapling 版）** 的优势：
- Scrapling 的 `FetcherSession` 使用 `curl_cffi` 库，模拟真实 Chrome 浏览器的 TLS 指纹
- 自动生成 stealth 请求头，看起来像真实浏览器访问
- 内置重试机制和超时控制
- 开发者活跃维护中

## 快速开始

### 1. 安装 Python 依赖

```bash
pip install scrapling[all,full]
```

这也会安装 `pycryptodome`（AES 加密解密需要）。

### 2. 获取百度 Cookie

1. 用 Chrome 打开 https://index.baidu.com 并登录你的百度账号
2. 按 `F12` 打开开发者工具
3. 切换到 **Application** → **Cookies** → `https://index.baidu.com`
4. 每个 Cookie 是一个键值对（如 `BIDUPSID=xxx`），**选中所有 Cookie 条目**
5. 复制全部内容，用分号 `;` 连接成一条字符串

示例 Cookie 字符串（脱敏）：
```
BIDUPSID=12345abc; PSTM=1234567890; BAIDUID=xxxx:FG=1; ...其他Cookie...
```

> **⚠️ Cookie 有效期**：百度 Cookie 通常持续几个小时到几天不等，过期后需要重新获取。

### 3. 配置 Cookie

打开 `src/baidu_index_scrapling.py`，找到 `COOKIE_LIST` 部分：

```python
COOKIE_LIST = [
    # 用三引号包裹你的 Cookie 字符串
    '''BIDUPSID=xxx; PSTM=xxx; BAIDUID=xxx:FG=1; ...完整Cookie...''',
    # 如果有多个百度账号，可以继续添加，随机轮询
    # '''BIDUPSID=yyy; PSTM=yyy; ...''',
]
```

为什么用三引号？

```
用单引号:   'BIDUPSID=xxx; PSTM=xxx; ...BAIDUID=xxx:FG=1...'
            可能出现引号冲突导致语法错误

用双引号:   "BIDUPSID=xxx; PSTM=xxx; ..."
            Cookie值中可能包含双引号

用三引号:   '''BIDUPSID=xxx; PSTM=xxx; ...'''
            一劳永逸，避免任何引号转义问题
```

### 4. 运行爬虫

```bash
cd src/
python baidu_index_scrapling.py --test        # 测试模式：只爬上海
python baidu_index_scrapling.py --city 北京    # 爬取单个城市
python baidu_index_scrapling.py               # 完整爬取（支持断点续爬）
```

## 功能特性

| 特性 | 描述 |
|------|------|
| **Scrapling 反爬** | 使用真实的 Chrome TLS 指纹 + stealth headers |
| **断点续爬** | 自动保存进度，中断后重跑自动跳过已完成的 |
| **多 Cookie 轮询** | 支持多个 Cookie 随机切换，降低限流风险 |
| **指数退避重试** | 遇到限流自动延后重试，减少被封概率 |
| **正态分布延时** | 请求间隔随机化，更像人类操作 |
| **数据格式对齐** | 输出 CSV 格式与 v1 版本兼容 |

## 项目结构

```
百度指数爬取教程2.0/
├── README.md                       # 本文件
├── src/
│   └── baidu_index_scrapling.py    # 主爬虫脚本
├── config/
│   └── keywords.txt                # 关键词配置文件（可选）
├── output/                         # 爬取结果输出目录
├── examples/
│   └── example_output.csv          # 示例输出数据
└── docs/
    ├── COOKIE_GUIDE.md             # Cookie 获取详细教程
    ├── DATA_FORMAT.md              # 数据格式说明
    └── TROUBLESHOOTING.md          # 常见问题排查
```

## 数据格式

每个城市输出一个独立的 CSV 文件，文件名格式：`{城市名}_baidu_index.csv`

字段说明：
- `date`：日期（YYYY-MM-DD）
- `keyword`：关键词名称
- `city`：城市名称
- `type`：指数类型（`all` 整体搜索指数 / `pc` PC端指数 / `wise` 移动端指数）
- `index`：百度指数数值

**注意事项**：
- 同一批次请求的关键词，百度 API 返回相同的指数值（这是 API 本身的特性）
- 指数为 `0` 表示该词在该时间点没有搜索数据
- 实际数据可能有部分缺失（百度未收录该词）

## 参数说明

| 参数 | 说明 |
|------|------|
| `--test` | 测试模式，只爬上海，验证 Cookie 是否有效 |
| `--city 北京` | 只爬取指定城市（支持城市名） |
| （无参数） | 完整模式，遍历所有城市，跳过已完成 |

## 配置自定义

### 修改关键词

直接编辑脚本中的 `KEYWORDS` 列表：

```python
KEYWORDS = [
    '人工智能', '新能源', '数字经济',
    # ... 添加或删除你的关键词
]
```

> **注意**：百度 API 每个请求最多接受 3 个关键词，脚本会自动分组。

### 修改城市列表

编辑 `CITY_LIST` 列表，格式为 `(城市名, 百度地区编码)` 的元组。

### 修改时间范围

```python
START_DATE = '2026-03-01'
END_DATE = '2026-03-15'
```

### 修改输出目录

```python
OUTPUT_DIR = "./output"    # 默认在脚本同目录下的 output/ 文件夹
```

## 技术架构

```
┌─────────────────────────────────────────────┐
│  baidu_index_scrapling.py                    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │  Scrapling FetcherSession            │    │
│  │  ┌──────────┐  ┌────────────────┐    │    │
│  │  │ chrome   │  │ stealth_headers│    │    │
│  │  │ TLS指纹  │  │ 生成的浏览器标头│   │    │
│  │  └──────────┘  └────────────────┘    │    │
│  └──────────────────────────────────────┘    │
│         ↓                                   │
│  ┌──────────────────────────────────────┐    │
│  │  百度指数 API 加密通信               │    │
│  │  ┌──────────┐  ┌────────────────┐    │    │
│  │  │Cipher-   │  │ uniqid 解密    │    │    │
│  │  │Text 加密 │  │ 映射解密       │    │    │
│  │  └──────────┘  └────────────────┘    │    │
│  └──────────────────────────────────────┘    │
│         ↓                                   │
│  ┌──────────────────────────────────────┐    │
│  │  CSV 输出                            │    │
│  │  按城市 × 关键词 × 日期 × 类型      │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

## 常见问题

详见 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## License

MIT
