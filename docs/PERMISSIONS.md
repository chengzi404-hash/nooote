# 权限组

Nooote 的每个路由都声明了所需权限，由应用级的 `before_request` 钩子统一校验，默认拒绝（default-deny）。

## 权限组

| 权限组 | 说明 | 主要权限 |
| --- | --- | --- |
| `guest` | 未登录访客 | 浏览首页与公开笔记、登录注册、切换语言、读取附件链接 |
| `member` | 注册用户（默认） | 访客全部权限，加上笔记读写、公开/取消公开、删除、附件管理、个人设置 |
| `admin` | 管理员 | 全部权限，额外可访问 `GET /manage` 查看站点数据并管理账号权限组 |

权限组定义在 `nooote/config.py` 的 `ROLE_PERMISSIONS` 中，权限名是形如 `note.write` 的扁平键。

## 路由声明

每个视图函数都必须用 `@permission_require([...])` 声明所需权限：

```python
from ..permissions import permission_require


@bp.get("/console/notes/<note_id>")
@permission_require(["note.read"])
def edit_note(note_id: str):
    ...
```

请求通过的条件是：视图声明的所有权限都在当前账号所属权限组内。

- 未登录且权限不足：`/api/**` 返回 `401` JSON，页面请求重定向到 `/login`
- 已登录但权限不足：`/api/**` 返回 `403` JSON，页面请求渲染 `403` 提示页
- 忘记声明权限的视图会被默认拒绝（登录用户得到 `403`），新增路由时必须补上装饰器

`tests/test_permissions.py` 会遍历整个 `url_map`，确认没有视图漏掉权限声明。

## 管理员

注册时默认获得 `member`。通过环境变量 `NOOOTE_ADMIN_USERNAMES`（逗号分隔）指定用户名，这些账号注册后直接获得 `admin`：

```bash
NOOOTE_ADMIN_USERNAMES=alice,bob uv run flask --app main run
```

管理员可以在 `GET /manage` 为其他账号切换权限组，但不能修改自己的权限组，避免把自己锁在门外。也可以通过 `app.config["ADMIN_USERNAMES"]` 在应用工厂中覆盖。

## 站点管理页

`GET /manage` 需要 `manage.view` 权限（仅 `admin`），包含三块内容：

- **站点数据**：账号数、笔记数、公开/私有笔记数、附件数，以及笔记正文与附件的占用空间
- **权限组**：每组当前账号数与已授予的权限清单，便于核对 `ROLE_PERMISSIONS` 的实际效果
- **账号与权限组**：列出全部账号，可把其他账号切换到 `member` / `admin`；`POST /manage/users/<user_id>/role` 需要 `manage.users.write`

站点的语言、主题等个人偏好仍在 `/console/settings`，`/manage` 只处理全站层面的数据与权限。
