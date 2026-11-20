# 插件

插件是本机 `plugins/` 目录下的 Python 包，用来给控制台增加页面和侧边栏入口。插件在应用启动时自动发现并安装，不需要改核心代码。

## 目录结构

```
plugins/
└── hello/
    ├── __init__.py       # 必须导出 create_plugin()
    ├── templates/        # 可选：Jinja 模板
    └── static/           # 可选：静态资源
```

插件文件夹名就是插件标识，必须是合法的 Python 标识符，且不能以下划线开头。包内拆分成多个模块时使用相对导入（如 `from .views import bp`），模块名由核心动态注册，不要按包名绝对导入。

## 插件契约

`__init__.py` 必须导出无参工厂 `create_plugin()`，返回 `nooote.plugins.Plugin`。每次启动应用都会重新调用工厂，因此蓝图必须是新实例。

```python
from flask import Blueprint, render_template

from nooote.permissions import permission_require
from nooote.plugins import Plugin


def create_plugin():
    bp = Blueprint("hello", __name__, template_folder="templates")

    @bp.route("")
    @permission_require(["plugin.access"])
    def index():
        return render_template("hello/index.html")

    return Plugin(
        name="hello",
        label="Hello",
        blueprint=bp,
    )
```

`Plugin` 字段：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `name` | 必填 | 必须与插件文件夹名一致 |
| `label` | 必填 | 侧边栏文字；会先经过 i18n 目录，找不到时原样显示 |
| `blueprint` | 必填 | 不能自带 `url_prefix`，由核心统一挂载 |
| `endpoint` | `"index"` | 蓝图内的落地页视图名，也是侧边栏链接目标 |
| `icon` | `fa-solid fa-puzzle-piece` | 侧边栏图标，Font Awesome 类名 |
| `description` | `""` | 预留描述字段 |
| `order` | `100` | 侧边栏排序，与内置菜单共用 |
| `permission` | `plugin.access` | 侧边栏可见所需权限；`None` 表示不检查 |
| `nav` | `True` | 设成 `False` 时不注册侧边栏入口 |
| `features` | `()` | 插件自带的子功能开关，见下文 |

## 路由与安装 ID

应用启动时会扫描 `plugins/`。第一次发现某个插件时自动生成 `__id` 并写入 `instance/plugins.json`，之后每次启动都复用同一个 ID，因此链接可以长期收藏。

插件的所有路由统一挂载在 `/plug/<__id>` 下：

- 落地页使用 `@bp.route("")`，地址正好是 `/plug/<__id>`
- 其他页面使用 `@bp.route("/widget")`，地址是 `/plug/<__id>/widget`
- 蓝图内用 `url_for("hello.index")` 生成链接或重定向，不要手写 ID

## 权限

插件路由同样受默认拒绝守卫约束，必须用 `@permission_require([...])` 声明权限。插件页面面向登录用户时使用 `plugin.access`（`member` 与 `admin` 都拥有）；如需更严格的权限，先在 `nooote/config.py` 中登记新权限并分配到权限组。

未声明的插件视图会被全局守卫拦下，`tests/test_permissions.py` 也会检查 `url_map` 中的每个视图。

## 功能开关

每个插件会自动获得一个总开关 `plugin.<插件名>`（关闭后插件所有页面不可访问、侧边栏入口隐藏）。插件还可以用 `Plugin.features` 声明更细的子功能开关，核心会命名空间化为 `plugin.<插件名>.<key>`，管理员在 `GET /manage` 的「功能开关」中分别启停。

```python
from nooote.features import Feature, feature_require, plugin_feature_key

WIDGETS = plugin_feature_key("hello", "widgets")


def create_plugin():
    bp = Blueprint("hello", __name__)

    @bp.route("/widgets")
    @permission_require(["plugin.access"])
    @feature_require(WIDGETS)
    def widgets():
        ...

    return Plugin(
        name="hello",
        label="Hello",
        blueprint=bp,
        features=(
            Feature("widgets", "Widgets", "额外的组件页面"),
        ),
    )
```

- `Feature` 的 `label` / `description` 会经过 i18n 目录，插件直接写文本即可原样显示
- 被关闭的功能统一返回 `403`：`/api/**` 返回 JSON，页面显示「功能已关闭」
- 子功能默认开启；关闭某个子功能只影响声明了它的视图，不会影响插件总开关和其他页面

## 模板与静态资源

- 模板放在插件包的 `templates/` 下；建议按插件名建子目录，例如 `hello/index.html`，避免与其他插件重名
- 页面可以继承 `console_base.html` 复用控制台外壳：

```html
{% extends "console_base.html" %}

{% block title %}Hello{% endblock %}
{% block crumb %}Hello{% endblock %}

{% block console_content %}
<p>Hello from the plugin.</p>
{% endblock %}
```

- 蓝图需要静态资源时传入 `static_folder="static"`，会自动挂在 `/plug/<__id>/static/...`；这些文件与核心静态资源一样无需登录即可访问
- 用户可见文案建议保持中英双语，但插件不会自动并入 `nooote/i18n.py`，可在模板中直接写两套文案或自带翻译逻辑

## 卸载与重新安装

删除插件文件夹后，`instance/plugins.json` 中的记录会保留；重新放回同名插件时会继续使用原来的 `__id`，已分享的链接不会失效。需要彻底重新生成 ID 时，删除登记文件中对应的条目即可。
