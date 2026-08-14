# Schema 校验规则

## 文档用途

本文档描述 AI 建模助手生成结果必须满足的结构规则。后端会使用 Pydantic `EntitySchema` 校验模型输出；任何未通过校验的结果都不能作为成功结果返回前端。

## 顶层 EntitySchema 规则

完整 Schema 包含以下属性：

| 属性 | 类型 | 规则 |
| --- | --- | --- |
| `entityName` | string | 必填，长度 1 到 50 |
| `entityCode` | string | 必填，长度 1 到 50，匹配英文编码正则 |
| `version` | integer | 可省略，默认 1；必须大于或等于 1 |
| `fields` | array | 必填，至少包含一个字段 |
| `warnings` | string[] | 可省略，默认空数组 |

顶层及所有子对象都采用 `extra="forbid"`：出现模型中未定义的多余属性会校验失败。

合法顶层结构示例：

```json
{
  "entityName": "客户",
  "entityCode": "Customer",
  "version": 1,
  "fields": [],
  "warnings": []
}
```

注意：上面的结构只用于展示顶层属性，实际结果中的 `fields` 不能为空。

## FieldSchema 规则

每个字段包含：

| 属性 | 类型 | 规则 |
| --- | --- | --- |
| `fieldName` | string | 必填，长度 1 到 50 |
| `fieldCode` | string | 必填，长度 1 到 50，匹配英文编码正则 |
| `dataType` | string | 必填，只能取七种受支持类型之一 |
| `required` | boolean | 可省略，默认 `false` |
| `constraints` | object 或 null | 可省略，支持正则约束 |
| `enumOptions` | array | 可省略，默认空数组 |

`dataType` 只允许：

```text
string、number、integer、enum、date、datetime、boolean
```

## 编码格式规则

`entityCode` 和 `fieldCode` 必须匹配：

```text
^[a-zA-Z][a-zA-Z0-9_]*$
```

校验失败示例及修复：

| 错误值 | 错误原因 | 修复示例 |
| --- | --- | --- |
| `客户` | 包含中文 | `Customer` |
| `2name` | 以数字开头 | `name2` |
| `phone-number` | 包含短横线 | `phoneNumber` |
| `customer level` | 包含空格 | `customerLevel` |

## 字段编码唯一性

同一个实体中不能存在重复的 `fieldCode`。

错误示例：

```json
{
  "fields": [
    { "fieldName": "联系人姓名", "fieldCode": "name", "dataType": "string" },
    { "fieldName": "客户姓名", "fieldCode": "name", "dataType": "string" }
  ]
}
```

应根据业务含义合并字段，或分别使用有含义的唯一编码。

## 枚举校验规则

### enum 字段

当 `dataType` 为 `enum` 时，`enumOptions` 必须至少包含一个选项。

每个选项必须包含：

- 非空 `label`。
- 非空 `value`。

正确示例：

```json
{
  "fieldName": "状态",
  "fieldCode": "status",
  "dataType": "enum",
  "required": true,
  "constraints": null,
  "enumOptions": [
    { "label": "启用", "value": "enabled" },
    { "label": "停用", "value": "disabled" }
  ]
}
```

### 非 enum 字段

当 `dataType` 不是 `enum` 时，`enumOptions` 必须省略或为空数组。非空会校验失败。

## 正则约束规则

`constraints` 当前支持：

```json
{
  "pattern": "正则表达式",
  "patternMessage": "校验失败提示"
}
```

规则：

- `pattern` 必须能被 Python 正则引擎编译。
- JSON 字符串中的反斜杠必须正确转义，例如正则 `\d` 在 JSON 源文本中写成 `\\d`。
- 提供 `pattern` 时应同时提供易理解的 `patternMessage`。
- 用户未提出规则且业务规则不明确时，不要擅自添加正则。

手机号约束示例：

```json
{
  "pattern": "^1[3-9]\\d{9}$",
  "patternMessage": "请输入正确的 11 位中国大陆手机号"
}
```

## warnings 使用规则

`warnings` 用于记录生成过程中无法从需求确定、需要用户确认的事项。它不是校验错误列表。

适合写入 `warnings` 的内容：

- 用户说“手机号需要校验”，但没有说明适用国家或地区。
- 用户要求金额字段，但没有说明币种或精度。
- 用户要求状态字段，但没有给出完整状态集合。
- 某个业务名称存在多种合理理解。

不应写入 `warnings` 的内容：

- 已经能从需求明确确定的规则。
- Pydantic 校验错误。
- 与当前需求无关的通用建议。
- 为掩盖模型擅自添加内容而编写的说明。

## 需求忠实性规则

通过结构校验不等于业务建模正确。生成时还必须遵守：

- 用户明确要求必填的字段，`required` 必须为 `true`。
- 用户未要求必填的字段，默认 `required` 为 `false`。
- 用户给出的字段不能遗漏。
- 不擅自增加用户未要求的字段。
- 固定选项必须完整转换为 `enumOptions`。
- 增量修改只改变用户指定内容，保留无关字段和约束。

## 自动修复规则

模型输出的处理顺序：

1. 去除可能出现的 Markdown 代码块标记。
2. 使用 `json.loads` 解析 JSON。
3. 使用 `EntitySchema.model_validate` 进行 Pydantic 校验。
4. 校验通过则返回结果。
5. 校验失败则把原始需求、上次输出和结构化错误发给模型修复。
6. 最多自动修复两次，即首次生成加两次修复，总计最多调用模型三次。
7. 两次修复后仍失败，返回真实错误，不伪造成功 Schema。

修复时必须返回完整 Schema，只修复错误，不删除原本正确的字段。

## 完整合法示例

```json
{
  "entityName": "客户",
  "entityCode": "Customer",
  "version": 1,
  "fields": [
    {
      "fieldName": "姓名",
      "fieldCode": "name",
      "dataType": "string",
      "required": true,
      "constraints": null,
      "enumOptions": []
    },
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
  ],
  "warnings": []
}
```

