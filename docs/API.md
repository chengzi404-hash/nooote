# HTTP API

## 账号与认证

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET / POST` | `/register` | 注册账号并自动登录 |
| `GET / POST` | `/login` | 登录 |
| `POST` | `/logout` | 退出登录 |

密码只保存哈希值，不会以明文存储。

## 笔记与附件接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/console/notes/<note_id>` | 获取自己的私有笔记内容与公开状态 |
| `PUT` | `/api/console/notes/<note_id>` | 保存自己的私有笔记，JSON 请求体：`{"content": "..."}` |
| `GET` | `/api/share/<note_id>` | 读取已公开笔记（只读） |
| `POST` | `/api/console/attachments` | 上传附件，`multipart/form-data`，字段名为 `file` |
| `DELETE` | `/api/console/attachments/<attachment_id>` | 删除自己的附件 |
| `GET` | `/files/<attachment_id>` | 读取附件；图片内联显示，其他文件作为下载 |

公开笔记没有写入接口；编辑私有笔记后，`/share/<note_id>` 与 `/api/share/<note_id>` 会立即返回新内容。预览与代码高亮完全在浏览器端运行，不需要请求服务端渲染接口。

## 权限与错误响应

每个接口都声明了所需权限，校验结果如下：

| 情况 | `/api/**` | 页面请求 |
| --- | --- | --- |
| 未登录 | `401 {"error": "请先登录"}` | 重定向到 `/login` |
| 已登录但权限不足 | `403 {"error": "没有权限执行该操作"}` | 渲染 403 提示页 |

| 方法 | 路径 | 所需权限 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/api/console/notes/<note_id>` | `note.read` | 读取自己的私有笔记 |
| `PUT` | `/api/console/notes/<note_id>` | `note.write` | 保存自己的私有笔记 |
| `GET` | `/api/share/<note_id>` | `public.view` | 读取公开笔记 |
| `POST` | `/api/console/attachments` | `attachment.write` | 上传附件 |
| `DELETE` | `/api/console/attachments/<attachment_id>` | `attachment.delete` | 删除自己的附件 |
| `GET` | `/files/<attachment_id>` | `files.view` | 读取附件 |
| `GET` | `/manage` | `manage.view` | 站点数据总览与权限组管理 |
| `POST` | `/manage/users/<user_id>/role` | `manage.users.write` | 修改指定账号的权限组 |

权限组的定义与扩展方式见 [权限组](PERMISSIONS.md)。
