# 贡献指南

感谢你对 Nooote 感兴趣。本文档说明如何搭建环境、运行测试和提交改动。

## 行为准则

参与本项目即表示你同意遵守 [行为准则](CODE_OF_CONDUCT.md)。

## 反馈问题

- **Bug**：在仓库 Issues → New issue 中选择「Bug 报告」模板，附上复现步骤和运行环境
- **功能建议**：在同一入口选择「功能建议」模板
- **安全漏洞**：不要公开提交 Issue，请按 [SECURITY.md](SECURITY.md) 私密报告

## 开发环境

需要 Python 3.12 和 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
uv run flask --app main run --debug
```

打开 <http://127.0.0.1:5000/console> 新建私有笔记开始调试。也可以直接运行 `uv run python main.py`。

数据库默认是 `instance/notes.db`，可通过 `DATABASE_URL` 覆盖。需要干净环境时删除该文件即可。

## 测试

```bash
uv run pytest
```

提交前请确保全部测试通过。只跑部分测试：

```bash
uv run pytest tests/test_notes.py -k save
```

## 质量门槛

### 覆盖率

Pull Request 需要同时满足以下两条：

- 总覆盖率不低于 **85%**
- 相对基线（最近一次 `known-good-*` 检查点记录的覆盖率）的降幅小于 **10%**（`drop < 10%`）

本地查看覆盖率：

```bash
uv run pytest --cov=nooote --cov-report=term-missing
```

覆盖率不达标或降幅过大时请补充测试；确实无法覆盖的分支，请在 PR 中说明原因。

### Known-good 检查点

合入默认分支并通过全部测试后，维护者创建一个 `known-good-yymmddhh` 格式的附注标签，标记一个已知可用的提交。其中 `yymmddhh` 依次是两位的年、月、日、时：

```bash
git tag -a known-good-26111015 -m "coverage 87%; Python 3.12; uv 0.9; Windows 11"
git push origin known-good-26111015
```

标签说明是可选的，建议附上当时的环境与质量信息，方便回滚和排查：

- 覆盖率：`uv run pytest --cov=nooote` 得到的总覆盖率
- 运行环境：Python、uv 版本和操作系统
- 浏览器与版本：手动验证预览功能时使用的浏览器
- 数据库：`DATABASE_URL` 或默认的 SQLite

检查点标签同时作为覆盖率基线的参考。

## 代码约定

- 遵循现有结构：后端保持轻量，只负责存储和 JSON API；Markdown 渲染、代码高亮、图表都在浏览器端完成
- 新增用户可见功能时，同步更新 [AGENTS.md](AGENTS.md) 并补充 pytest 测试
- 面向用户的文档同时维护中文 `README.md` 和英文 `README.en.md`，改动时保持两边一致
- 前端第三方库放入 `nooote/static/vendor/`，保留其 LICENSE 并在 vendor README 中登记，不要使用 CDN
- `static/vendor/` 已被 git 忽略：启动服务或运行 `uv run python -m nooote.vendor` 会自动下载缺失文件，新增或升级第三方库时同步更新 `nooote/vendor.py` 中的 URL 与 SHA-256；详见 [AGENTS.md](AGENTS.md#前端第三方库自动同步)
- Python 代码使用 3.12 语法和类型标注，保持与周围代码一致的风格
- 不要提交数据库、构建产物或任何密钥

## 提交 Pull Request

1. Fork 仓库并从默认分支创建分支，例如 `fix/autosave-race`
2. 保持改动聚焦，一个 PR 只做一件事
3. 运行 `uv run pytest` 并通过
4. 填写 PR 模板中的改动说明和验证方式
5. 描述里关联相关 Issue（如 `Closes #12`）

提交信息建议使用简短的中文或英文祈使句，说明改动目的，例如：

```text
修复连续输入时覆盖旧内容的问题
Add size limit to note API
```

## 许可证

提交的代码将以 [MIT](LICENSE) 许可发布。
