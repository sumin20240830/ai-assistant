# 实体字段类型规范

## 文档用途

本文档用于指导 AI 建模助手把自然语言中的业务字段映射为项目支持的 `dataType`。生成结果必须符合后端 `EntitySchema` 的定义，不能创造项目尚未支持的字段类型。

## 支持的字段类型

| dataType | 适用场景 | 典型字段 | 建模说明 |
| --- | --- | --- | --- |
| `string` | 普通文本、编码、手机号、邮箱、地址 | 姓名、手机号、订单号 | 即使内容只包含数字，只要不参与数学计算，通常仍使用 `string` |
| `number` | 允许小数的数值 | 金额、重量、折扣率 | 适用于需要计算且可能有小数的字段 |
| `integer` | 只允许整数的数值 | 年龄、数量、排序号 | 适用于计数、年龄等不应出现小数的字段 |
| `enum` | 取值范围固定且数量有限 | 客户等级、订单状态 | 必须同时提供非空 `enumOptions` |
| `date` | 只关心日期 | 出生日期、生效日期 | 推荐数据格式为 `YYYY-MM-DD` |
| `datetime` | 同时关心日期和时间 | 注册时间、创建时间 | 推荐使用 ISO 8601 日期时间格式 |
| `boolean` | 是/否、启用/禁用两种状态 | 是否启用、是否完成 | 不要用字符串 `"是"`、`"否"` 代替布尔值 |

## 类型选择规则

### 文本与数字的区分

字段看起来像数字，但只用于标识、展示、查询或保留前导零时，应使用 `string`。

- 手机号：`string`
- 身份证号：`string`
- 邮政编码：`string`
- 银行卡号：`string`
- 商品编码：`string`
- 年龄：`integer`
- 商品数量：`integer`
- 商品单价：`number`

### number 与 integer 的区分

- 明确表示数量、次数、年龄、排序并且不允许小数时，使用 `integer`。
- 表示金额、比例、长度、重量等可能包含小数的值时，使用 `number`。
- 用户描述不明确时，不要自行添加最小值、最大值等约束；可在 `warnings` 中提示需要确认。

### enum 的使用条件

当用户给出了固定选项，或业务含义明确要求从有限状态中选择时，使用 `enum`。

枚举字段必须提供 `enumOptions`，每一项都包含：

- `label`：展示给业务用户的名称，不能为空。
- `value`：持久化和接口传输使用的稳定编码，不能为空。

示例：

```json
{
  "fieldName": "客户等级",
  "fieldCode": "customerLevel",
  "dataType": "enum",
  "required": false,
  "constraints": null,
  "enumOptions": [
    { "label": "普通", "value": "normal" },
    { "label": "重要", "value": "important" },
    { "label": "VIP", "value": "vip" }
  ]
}
```

非 `enum` 字段的 `enumOptions` 必须为空数组或省略，不能填写枚举选项。

### date 与 datetime 的区分

- 只关心某一天，不关心具体时间，使用 `date`。
- 需要记录时、分、秒或事件发生时刻，使用 `datetime`。
- “注册时间”“创建时间”“更新时间”通常使用 `datetime`。
- “出生日期”“合同生效日期”通常使用 `date`。

### boolean 的使用条件

仅当字段本质上只有两个互斥状态时使用 `boolean`，例如“是否启用”。如果存在“未开始、进行中、已完成”等三个或更多状态，应使用 `enum`。

## 字段完整结构

每个字段使用以下结构：

```json
{
  "fieldName": "字段中文名称",
  "fieldCode": "fieldCode",
  "dataType": "string",
  "required": false,
  "constraints": null,
  "enumOptions": []
}
```

字段属性含义：

| 属性 | 是否必需 | 说明 |
| --- | --- | --- |
| `fieldName` | 是 | 业务展示名称，长度为 1 到 50 个字符 |
| `fieldCode` | 是 | 英文字段编码，长度为 1 到 50 个字符 |
| `dataType` | 是 | 只能使用本文档列出的七种类型 |
| `required` | 否 | 是否必填，默认值为 `false` |
| `constraints` | 否 | 当前支持 `pattern` 和 `patternMessage` |
| `enumOptions` | 否 | 枚举选项；`enum` 类型时不能为空 |

## 约束使用方式

当前字段约束支持：

- `pattern`：合法的正则表达式字符串。
- `patternMessage`：正则校验失败时展示给用户的信息。

手机号示例：

```json
{
  "fieldName": "手机号",
  "fieldCode": "phoneNumber",
  "dataType": "string",
  "required": true,
  "constraints": {
    "pattern": "^1[3-9]\\d{9}$",
    "patternMessage": "请输入正确的 11 位中国大陆手机号"
  },
  "enumOptions": []
}
```

只有用户明确提出校验要求，或规则属于无歧义的通用格式时，才添加约束。无法确定的校验规则应写入 `warnings`，不要猜测。

## 禁止的建模方式

- 不要使用 `text`、`varchar`、`decimal`、`timestamp`、`select`、`array`、`object` 等未支持的类型。
- 不要把手机号、证件号等标识字段建模为 `number` 或 `integer`。
- 不要给非枚举字段添加非空 `enumOptions`。
- 不要创建没有 `enumOptions` 的 `enum` 字段。
- 不要在用户未说明时擅自增加业务字段、必填规则或校验范围。

