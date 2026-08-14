# B 端实体建模示例

## 文档用途

本文档提供从自然语言需求到完整 `EntitySchema` 的参考案例。检索时应优先选择与当前用户需求业务语义和字段类型相近的案例，但不能照搬案例中用户未要求的字段或规则。

## 示例一：客户实体

### 用户需求

创建一个客户实体，包含姓名、手机号、客户等级、注册时间；手机号必填且需要校验，客户等级包含普通、重要、VIP 三种取值。

### 建模结果

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
      "required": false,
      "constraints": null,
      "enumOptions": []
    },
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
    },
    {
      "fieldName": "注册时间",
      "fieldCode": "registeredAt",
      "dataType": "datetime",
      "required": false,
      "constraints": null,
      "enumOptions": []
    }
  ],
  "warnings": [
    "手机号校验按中国大陆 11 位手机号规则生成，如适用于其他国家或地区请调整规则。"
  ]
}
```

### 建模要点

- 手机号用于标识和联系，不参与数学计算，因此使用 `string`。
- “注册时间”需要记录具体时刻，因此使用 `datetime`。
- 用户只明确手机号必填，其他字段保持默认非必填。
- 手机号适用地区存在假设，因此写入 `warnings`。

## 示例二：销售订单实体

### 用户需求

创建销售订单，包含订单编号、客户名称、商品数量、订单金额、下单时间和订单状态。订单编号和客户名称必填；订单状态包括待支付、已支付、已取消。

### 建模结果

```json
{
  "entityName": "销售订单",
  "entityCode": "SalesOrder",
  "version": 1,
  "fields": [
    {
      "fieldName": "订单编号",
      "fieldCode": "orderCode",
      "dataType": "string",
      "required": true,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "客户名称",
      "fieldCode": "customerName",
      "dataType": "string",
      "required": true,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "商品数量",
      "fieldCode": "productQuantity",
      "dataType": "integer",
      "required": false,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "订单金额",
      "fieldCode": "orderAmount",
      "dataType": "number",
      "required": false,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "下单时间",
      "fieldCode": "orderedAt",
      "dataType": "datetime",
      "required": false,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "订单状态",
      "fieldCode": "orderStatus",
      "dataType": "enum",
      "required": false,
      "constraints": null,
      "enumOptions": [
        { "label": "待支付", "value": "pending_payment" },
        { "label": "已支付", "value": "paid" },
        { "label": "已取消", "value": "cancelled" }
      ]
    }
  ],
  "warnings": [
    "需求未说明订单金额的币种与精度，需要业务方确认。"
  ]
}
```

### 建模要点

- 订单编号可能包含字母或前导零，因此使用 `string`。
- 商品数量不应出现小数，使用 `integer`。
- 订单金额可能包含小数，使用 `number`。
- 不在用户未要求时自行添加收货地址、支付方式等字段。

## 示例三：员工档案实体

### 用户需求

建立员工档案，字段包括员工编号、姓名、年龄、出生日期、入职时间和是否在职。员工编号和姓名必填。

### 建模结果

```json
{
  "entityName": "员工档案",
  "entityCode": "EmployeeProfile",
  "version": 1,
  "fields": [
    {
      "fieldName": "员工编号",
      "fieldCode": "employeeCode",
      "dataType": "string",
      "required": true,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "姓名",
      "fieldCode": "name",
      "dataType": "string",
      "required": true,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "年龄",
      "fieldCode": "age",
      "dataType": "integer",
      "required": false,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "出生日期",
      "fieldCode": "birthDate",
      "dataType": "date",
      "required": false,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "入职时间",
      "fieldCode": "joinedAt",
      "dataType": "datetime",
      "required": false,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "是否在职",
      "fieldCode": "isEmployed",
      "dataType": "boolean",
      "required": false,
      "constraints": null,
      "enumOptions": []
    }
  ],
  "warnings": []
}
```

### 建模要点

- “出生日期”只关心日期，使用 `date`。
- “入职时间”通常需要记录具体时刻，使用 `datetime`。
- “是否在职”只有两个状态，使用 `boolean`。
- 未知的员工编号格式不添加正则。

## 示例四：服务工单实体

### 用户需求

创建服务工单，包含工单标题、问题描述、优先级、计划完成日期、处理状态。标题必填，优先级有低、中、高，处理状态有待处理、处理中、已完成。

### 建模结果

```json
{
  "entityName": "服务工单",
  "entityCode": "ServiceTicket",
  "version": 1,
  "fields": [
    {
      "fieldName": "工单标题",
      "fieldCode": "title",
      "dataType": "string",
      "required": true,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "问题描述",
      "fieldCode": "description",
      "dataType": "string",
      "required": false,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "优先级",
      "fieldCode": "priority",
      "dataType": "enum",
      "required": false,
      "constraints": null,
      "enumOptions": [
        { "label": "低", "value": "low" },
        { "label": "中", "value": "medium" },
        { "label": "高", "value": "high" }
      ]
    },
    {
      "fieldName": "计划完成日期",
      "fieldCode": "plannedCompletionDate",
      "dataType": "date",
      "required": false,
      "constraints": null,
      "enumOptions": []
    },
    {
      "fieldName": "处理状态",
      "fieldCode": "processingStatus",
      "dataType": "enum",
      "required": false,
      "constraints": null,
      "enumOptions": [
        { "label": "待处理", "value": "pending" },
        { "label": "处理中", "value": "in_progress" },
        { "label": "已完成", "value": "completed" }
      ]
    }
  ],
  "warnings": []
}
```

### 建模要点

- “计划完成日期”不需要具体时刻时使用 `date`。
- 优先级和处理状态都有三个固定选项，因此使用 `enum`，而不是 `boolean`。
- 枚举 `value` 使用稳定英文编码，展示文案放在 `label`。

## 示例五：增量修改

### 当前 Schema 摘要

客户实体已有姓名、手机号、客户等级和注册时间，当前版本为 1。

### 修改指令

新增“邮箱”字段并设为必填，同时给客户等级增加“战略客户”选项。

### 预期变更

- 保留所有已有字段、约束和枚举选项。
- 新增 `email` 字段，类型为 `string`，`required` 为 `true`。
- `customerLevel.enumOptions` 追加 `{ "label": "战略客户", "value": "strategic" }`。
- `version` 更新为 2。
- 不修改手机号校验，不删除注册时间。

邮箱字段示例：

```json
{
  "fieldName": "邮箱",
  "fieldCode": "email",
  "dataType": "string",
  "required": true,
  "constraints": null,
  "enumOptions": []
}
```

需求只说新增邮箱且必填，没有明确要求邮箱格式校验，因此不要擅自添加正则；如产品要求自动采用通用邮箱格式，应先把该规则写入明确的业务规范。

