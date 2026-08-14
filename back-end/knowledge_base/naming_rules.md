# 实体与字段命名规范

## 文档用途

本文档用于统一 `entityName`、`entityCode`、`fieldName`、`fieldCode` 和枚举值的命名，保证 AI 生成的 Schema 可读、稳定，并能通过 Pydantic 校验。

## 强制校验规则

`entityCode` 和 `fieldCode` 必须满足以下正则表达式：

```text
^[a-zA-Z][a-zA-Z0-9_]*$
```

这意味着编码：

- 必须以英文字母开头。
- 后续只能包含英文字母、数字或下划线。
- 不能包含中文、空格、短横线、点号或其他特殊字符。
- 长度必须为 1 到 50 个字符。

合法编码：`Customer`、`customerLevel`、`order_item2`。

非法编码：`客户`、`2customer`、`customer-level`、`customer level`。

## 推荐命名风格

Pydantic 只强制编码格式，不强制大小写风格。为了保持项目一致，生成时使用以下约定：

- `entityName`：简洁的中文业务实体名称，例如“客户”“销售订单”。
- `entityCode`：英文大驼峰 PascalCase，例如 `Customer`、`SalesOrder`。
- `fieldName`：清晰的中文业务字段名称，例如“客户等级”“注册时间”。
- `fieldCode`：英文小驼峰 camelCase，例如 `customerLevel`、`registeredAt`。
- 枚举 `value`：简短、稳定的小写英文编码；多词使用下划线，例如 `in_progress`。

## 实体命名规则

### entityName

- 使用业务人员熟悉的名词或名词短语。
- 避免“信息”“数据”“表”等没有区分度的后缀。
- 不使用完整句子。

推荐：`客户`、`合同`、`销售订单`。

不推荐：`客户信息表`、`用来保存订单的数据`。

### entityCode

- 根据 `entityName` 翻译为准确的英文业务名词。
- 使用单数形式表达一个实体，例如 `Customer`，而不是 `Customers`。
- 多个单词使用 PascalCase，不使用空格或短横线。
- 已存在实体的增量修改必须保留原 `entityCode`，除非用户明确要求重命名。

示例：

| entityName | entityCode |
| --- | --- |
| 客户 | `Customer` |
| 销售订单 | `SalesOrder` |
| 商品分类 | `ProductCategory` |
| 服务工单 | `ServiceTicket` |

## 字段命名规则

### fieldName

- 使用明确、无歧义的中文名称。
- 同一实体内不要出现同名但不同义的字段。
- 名称应体现单位或业务含义；例如金额字段优先命名为“订单金额”，不要只写“值”。
- 用户已有固定业务术语时优先保留用户术语。

### fieldCode

- 使用小驼峰 camelCase。
- 使用完整、常见的英文单词，避免只有团队内部才理解的缩写。
- 布尔字段推荐以 `is`、`has`、`can` 开头，例如 `isEnabled`。
- 日期字段可使用 `Date` 结尾，例如 `birthDate`。
- 日期时间字段可使用 `At` 或 `Time` 结尾，例如 `registeredAt`、`startTime`。
- 编码类字段使用 `Code`，名称类字段使用 `Name`，不要混用。

常见字段映射：

| fieldName | fieldCode | dataType |
| --- | --- | --- |
| 姓名 | `name` | `string` |
| 手机号 | `phoneNumber` | `string` |
| 客户等级 | `customerLevel` | `enum` |
| 注册时间 | `registeredAt` | `datetime` |
| 出生日期 | `birthDate` | `date` |
| 年龄 | `age` | `integer` |
| 订单金额 | `orderAmount` | `number` |
| 是否启用 | `isEnabled` | `boolean` |

## 编码唯一性

同一个实体的 `fields` 中，所有 `fieldCode` 必须唯一。发现重复时，应根据真实业务含义处理：

1. 两个字段含义相同：合并为一个字段。
2. 两个字段含义不同：使用更具体的编码区分，例如 `contactName` 和 `legalRepresentativeName`。
3. 不要仅通过添加无意义数字生成 `name1`、`name2`。

字段编码唯一性区分大小写，但不应通过 `name` 与 `Name` 绕过重复检查。

## 枚举命名规则

- `label` 使用用户可理解的展示文本，通常为中文。
- `value` 使用不会因展示文案调整而变化的英文业务编码。
- 同一枚举内的 `value` 不应重复。
- 增量修改时，已有枚举值应保持稳定，除非用户明确要求修改。
- 不使用数组序号 `1`、`2`、`3` 代替有业务含义的值，除非用户明确指定数字编码。

示例：

```json
[
  { "label": "未开始", "value": "not_started" },
  { "label": "进行中", "value": "in_progress" },
  { "label": "已完成", "value": "completed" }
]
```

## 增量修改中的命名原则

- 修改字段展示名称时，不自动修改 `fieldCode`。
- 修改实体展示名称时，不自动修改 `entityCode`。
- 新增字段时先检查现有 `fieldCode`，避免重复。
- 删除字段时只删除用户明确指定的目标字段。
- 用户说“把手机号改成联系电话”时，默认只修改 `fieldName`；如果是否需要修改编码不明确，在 `warnings` 中提示。

## 不明确命名的处理

如果一个中文词存在多种合理英文翻译，应选择最符合上下文的常见表达。仍无法确定时：

- 采用保守、通用的英文编码。
- 不虚构行业含义。
- 在 `warnings` 中说明命名假设，供用户确认。

