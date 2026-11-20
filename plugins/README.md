# 插件目录

把插件包放在这里，应用启动时会自动发现并安装：

```
plugins/
└── hello/
    ├── __init__.py
    ├── templates/
    └── static/
```

每个插件包必须导出 `create_plugin()`，返回 `nooote.plugins.Plugin`。首次发现时会生成持久化 ID，并把所有路由挂载到 `/plug/<__id>`。

完整契约、示例和权限说明见 [docs/PLUGINS.md](../docs/PLUGINS.md)。
