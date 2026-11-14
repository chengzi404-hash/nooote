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
