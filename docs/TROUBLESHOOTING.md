# 常见问题排查

## 1. `ModuleNotFoundError: No module named 'scrapling'`

**原因**：未安装 Scrapling 库。

**解决**：
```bash
pip install scrapling[all,full]
```

如果提示 `--break-system-packages`，加上：
```bash
pip install scrapling[all,full] --break-system-packages
```

## 2. `ModuleNotFoundError: No module named 'Crypto'`

**原因**：缺少 pycryptodome 库（AES 加密需要）。

**解决**：
```bash
pip install pycryptodome
```

## 3. `API 返回 status: 10000`

**原因**：Cookie 过期或无效，百度显示"未登录"。

**解决**：
1. 在 Chrome 中重新打开 https://index.baidu.com
2. 重新登录百度账号
3. 再次获取 Cookie 并更新到脚本中
4. 如果经常失效，建议准备多个百度账号的 Cookie

## 4. 部分关键词缺失（数据行数少于预期）

**原因**：
- API 限制每个请求最多 3 个关键词（脚本已自动处理）
- 某些关键词在百度指数中无数据
- Cookie 突然失效导致部分请求失败

**排查方法**：
```bash
python baidu_index_scrapling.py --test
```
看输出中是否有 "失败" 字样。

## 5. `HTTP 403` 或 `REQUEST_LIMITED`

**原因**：请求过于频繁，触发百度限流。

**解决**：
- 脚本已带自动重试和延时，通常等待后会自动恢复
- 如果持续限流，增加 `COOKIE_LIST` 中的 Cookie 数量（多账号轮询）
- 如果只是测试，用 `--test` 模式，减少请求量

## 6. 爬虫跑一半中断了

**原因**：网络波动、Cookie 过期、电脑休眠等。

**解决**：重新运行即可。脚本支持断点续爬（按城市粒度保存进度），已完成的城市不会重复爬取。

## 7. `Permission denied: .../output/上海_baidu_index.csv`

**原因**：Windows 上文件被其他程序（如 Excel）占用。

**解决**：
- 关闭所有打开了该 CSV 文件的程序
- 手动删除 output 目录下的对应文件
- 或者修改 OUTPUT_DIR 换个输出路径

## 8. 爬取完成后数据都是 0

**原因**：
- Cookie 无效（API 返回了空数据）
- 关键词本身在百度指数中无收录
- 时间范围内没有搜索数据

**检查方法**：在浏览器打开 https://index.baidu.com，手动搜索你的关键词，看是否有数据。

## 9. 脚本报错 `'list' object has no attribute 'replace'`

**原因**：之前版本的 bug，已修复。

**解决**：确保下载的是最新版本的 `baidu_index_scrapling.py`。
