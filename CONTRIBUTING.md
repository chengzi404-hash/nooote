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

打开 <http://127.0.0.1:5000/world/hello> 开始调试。也可以直接运行 `uv run python main.py`。

数据库默认是 `instance/notes.db`，可通过 `DATABASE_URL` 覆盖。需要干净环境时删除该文件即可。

## 测试

```bash
uv run pytest
```

提交前请确保全部测试通过。只跑部分测试：

```bash
uv run pytest tests/test_notes.py -k save
```

## 代码约定

- 遵循现有结构：后端保持轻量，只负责存储和 JSON API；Markdown 渲染、代码高亮、语法检查都在浏览器端完成
- 新增用户可见功能时，同步更新 README 并补充 pytest 测试
- 前端第三方库放入 `nooote/static/vendor/`，保留其 LICENSE 并在 vendor README 中登记，不要使用 CDN
- 浏览器端静态检查 bundle 的源码在 `tools/checks/`，重建方法见 [tools/checks/README.md](tools/checks/README.md)
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
