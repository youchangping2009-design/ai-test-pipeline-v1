# Structured PRD

## project_info
```json
{
  "project_code": "WX-YGJ",
  "project_name": "云挂机",
  "business_line": "云挂机",
  "prd_source": "PT083-01_副本.png; PT083-02_副本.png; PT083-03-01_副本.png; PT083-03-02_副本.png; PT083-03-03_副本.png; PT083-04_副本.png",
  "prd_version": "v1"
}
```

## requirement_info
```json
{
  "requirement_title": "云挂机购买页改版与云手机商品配置升级",
  "requirement_background": "当前云挂机前三日覆盖偏低，免费体验活动对新用户破冰和付费转化有明显拉动，但云挂机存在画面模糊、卡顿和尺寸不支持脚本接入的问题，因此需要同时优化购买页展示、后台配置能力和云机技术能力。",
  "requirement_goal": "让常规版/全新版购买页具备统一的宣传图、宣传专区和特价专区展示能力；让后台具备商品区和宣传内容的精细配置能力；通过更新SDK和固定720*1280尺寸改善实际体验并支持脚本接入。",
  "explicit_rules": [
    {
      "rule_id": "EXP-001",
      "rule_text": "云挂机购买页的常规版tab和全新版tab都需要展示改版后的宣传图区域。",
      "rule_type": "display_constraint",
      "priority": "high",
      "applies_to": "云挂机购买页",
      "expected_items": [
        "常规版tab",
        "全新版tab",
        "宣传图区域"
      ]
    },
    {
      "rule_id": "EXP-002",
      "rule_text": "宣传图片建议尺寸为1008*160，数据来源于盒子管理后台-云挂机-云手机商品管理-编辑宣传内容-宣传图片字段。",
      "rule_type": "data_rule",
      "priority": "high",
      "applies_to": "云挂机购买页宣传图",
      "fidelity_points": [
        {
          "constraint_type": "source_constraint",
          "value": "盒子管理后台-云挂机-云手机商品管理-编辑宣传内容-宣传图片字段",
          "must_preserve": true
        },
        {
          "constraint_type": "field_constraint",
          "value": "1008*160",
          "must_preserve": true
        }
      ]
    },
    {
      "rule_id": "EXP-003",
      "rule_text": "宣传专区展示宣传口号和性能参数，后台单行可配置20个字符，若C端展示超过一行则换行展示。",
      "rule_type": "display_constraint",
      "priority": "high",
      "applies_to": "云挂机购买页宣传专区",
      "fidelity_points": [
        {
          "constraint_type": "field_constraint",
          "value": "20个字符",
          "must_preserve": true
        },
        {
          "constraint_type": "style_constraint",
          "value": "超过一行则换行展示",
          "must_preserve": true
        }
      ]
    },
    {
      "rule_id": "EXP-004",
      "rule_text": "特价专区名称固定为特价专区，若后台无配置则不展示；横排展示，首屏展示2个半卡片，最多展示4个商品。",
      "rule_type": "display_constraint",
      "priority": "high",
      "applies_to": "云挂机购买页特价专区",
      "fidelity_points": [
        {
          "constraint_type": "copy_constraint",
          "value": "特价专区",
          "must_preserve": true
        },
        {
          "constraint_type": "selection_constraint",
          "value": "若后台无配置则不展示",
          "must_preserve": true
        },
        {
          "constraint_type": "quantity_constraint",
          "value": "首屏展示2个半卡片",
          "must_preserve": true
        },
        {
          "constraint_type": "quantity_constraint",
          "value": "最多展示4个商品",
          "must_preserve": true
        }
      ]
    },
    {
      "rule_id": "EXP-005",
      "rule_text": "原商品列表更名为限时购买，竖排展示，商品数量逻辑保持之前逻辑。",
      "rule_type": "display_constraint",
      "priority": "high",
      "applies_to": "云挂机购买页普通区",
      "fidelity_points": [
        {
          "constraint_type": "copy_constraint",
          "value": "限时购买",
          "must_preserve": true
        }
      ]
    },
    {
      "rule_id": "EXP-006",
      "rule_text": "添加云手机商品时，服务时长格式为n天x时，前项最大370，后项最大23，前后项不可同时为0。",
      "rule_type": "display_constraint",
      "priority": "high",
      "applies_to": "添加云手机商品弹窗"
    },
    {
      "rule_id": "EXP-007",
      "rule_text": "商品区字段为单选，content为特殊区、普通区；若特殊区生效商品数量超过4个，则不可保存并提示“特殊区只能展示4个商品，当前字段的配置数量已超过4个，请关闭之前的商品或调整配置”。",
      "rule_type": "state_constraint",
      "priority": "high",
      "applies_to": "添加云手机商品弹窗"
    },
    {
      "rule_id": "EXP-008",
      "rule_text": "盒子内排序字段为正整数，数值上限1000；若盒子内排序值相同，则按创建时间倒序排列。",
      "rule_type": "order_constraint",
      "priority": "high",
      "applies_to": "添加云手机商品弹窗"
    },
    {
      "rule_id": "EXP-009",
      "rule_text": "库存预警值字段每20分钟校验库存是否小于等于所配置数量；若校验失败，C端商品隐藏且不给用户分配云机，并触发机器人报警。",
      "rule_type": "state_constraint",
      "priority": "high",
      "applies_to": "添加云手机商品弹窗"
    },
    {
      "rule_id": "EXP-010",
      "rule_text": "编辑宣传内容时，所有云机类型都需要配置宣传内容，且云机类型不重复；若校验失败，点击确定后不可保存并提示“所有云机类型都需要配置宣传内容，且云机类型不重复！”。",
      "rule_type": "state_constraint",
      "priority": "high",
      "applies_to": "编辑宣传内容弹窗"
    },
    {
      "rule_id": "EXP-011",
      "rule_text": "宣传图片最多上传5张，支持gif/jpg/jpeg/png，单文件最大不超过500k，建议尺寸1008*160。",
      "rule_type": "display_constraint",
      "priority": "high",
      "applies_to": "编辑宣传内容弹窗"
    },
    {
      "rule_id": "EXP-012",
      "rule_text": "点击新增后新增一条宣传内容配置，最多新增额外1条，内容达到2条时禁用新增按钮，所配置内容C端全部展示。",
      "rule_type": "extensibility_constraint",
      "priority": "high",
      "applies_to": "编辑宣传内容弹窗"
    },
    {
      "rule_id": "EXP-013",
      "rule_text": "云机SDK需要更新，云机画面尺寸需要调整为720*1280。",
      "rule_type": "extensibility_constraint",
      "priority": "high",
      "applies_to": "云机能力"
    }
  ],
  "scope": {
    "in_scope": [
      "云挂机购买页双tab宣传图展示",
      "宣传专区展示规则",
      "特价专区商品列表展示规则",
      "普通区商品列表更名与布局",
      "云手机商品管理后台入口与列表字段",
      "添加云手机商品弹窗字段约束",
      "编辑宣传内容弹窗字段约束",
      "云机SDK更新与720*1280尺寸适配"
    ],
    "out_of_scope": [
      "支付链路内部扣款逻辑",
      "云机分配服务端具体实现代码",
      "编辑商品顺序弹窗的详细规则",
      "未在截图中给出的展示用户、商品标签类型和购买次数枚举明细"
    ]
  }
}
```

## pages
```json
[
  {
    "page_name": "云机技术约束",
    "page_desc": "需求背景、目标以及云机SDK与尺寸改造约束。",
    "sections": [
      {
        "section_name": "背景与目标",
        "section_type": "display_area",
        "section_desc": "说明本次改版的业务背景和目标。",
        "module_name": "云机能力约束",
        "feature_names": [
          "SDK更新与720*1280适配"
        ],
        "section_rules": [
          "通过免费体验提升云机覆盖率",
          "通过更新SDK改善画面模糊和卡顿",
          "通过720*1280固定尺寸支持脚本接入"
        ]
      },
      {
        "section_name": "SDK与尺寸约束",
        "section_type": "display_area",
        "section_desc": "云机SDK更新与尺寸固定约束。",
        "module_name": "云机能力约束",
        "feature_names": [
          "SDK更新与720*1280适配"
        ],
        "section_rules": [
          "云机SDK需要更新",
          "云机画面尺寸需要调整为720*1280"
        ]
      }
    ]
  },
  {
    "page_name": "云挂机购买页",
    "page_desc": "C端云挂机购买页，需在常规版和全新版两个tab下统一展示宣传图、宣传专区、特价专区和限时购买区。",
    "sections": [
      {
        "section_name": "顶部tab与宣传图区域",
        "section_type": "tab_area",
        "section_desc": "常规版/全新版tab及其共享宣传图区域",
        "module_name": "云挂机购买页展示",
        "feature_names": [
          "常规版/全新版tab与宣传图展示"
        ],
        "section_rules": [
          "双tab均展示宣传图区域",
          "宣传图尺寸建议1008*160"
        ],
        "field_refs": [
          "promo_image"
        ]
      },
      {
        "section_name": "宣传专区",
        "section_type": "display_area",
        "section_desc": "展示宣传口号和性能参数",
        "module_name": "云挂机购买页展示",
        "feature_names": [
          "宣传专区文案展示"
        ],
        "section_rules": [
          "展示宣传口号和性能参数",
          "C端超一行换行展示"
        ],
        "field_refs": [
          "promo_slogan",
          "performance_params"
        ]
      },
      {
        "section_name": "特价专区商品列表",
        "section_type": "list_area",
        "section_desc": "特价专区的商品卡片列表",
        "module_name": "云挂机购买页展示",
        "feature_names": [
          "特价专区商品列表"
        ],
        "section_rules": [
          "无配置则隐藏",
          "首屏展示2个半卡片",
          "最多4个商品"
        ]
      },
      {
        "section_name": "限时购买商品列表",
        "section_type": "list_area",
        "section_desc": "普通区商品列表更名后的主列表",
        "module_name": "云挂机购买页展示",
        "feature_names": [
          "限时购买商品列表"
        ],
        "section_rules": [
          "列表标题更名为限时购买",
          "竖排展示"
        ]
      }
    ]
  },
  {
    "page_name": "云手机商品管理页",
    "page_desc": "后台云手机商品管理列表页，提供添加、编辑宣传内容和排序等入口。",
    "sections": [
      {
        "section_name": "商品类型筛选区",
        "section_type": "filter_area",
        "section_desc": "云手机商品类型筛选器",
        "module_name": "云手机商品管理后台",
        "feature_names": [
          "商品列表与管理入口"
        ],
        "section_rules": [
          "支持按云手机商品类型筛选"
        ]
      },
      {
        "section_name": "管理操作区",
        "section_type": "action_area",
        "section_desc": "编辑商品顺序、添加和编辑宣传内容按钮区",
        "module_name": "云手机商品管理后台",
        "feature_names": [
          "商品列表与管理入口"
        ],
        "section_rules": [
          "点击添加进入商品配置界面",
          "编辑宣传图按钮更名为编辑宣传内容"
        ]
      },
      {
        "section_name": "商品列表区",
        "section_type": "list_area",
        "section_desc": "展示商品字段和操作列",
        "module_name": "云手机商品管理后台",
        "feature_names": [
          "商品列表与管理入口"
        ],
        "section_rules": [
          "列表新增商品区字段",
          "操作列保留编辑与删除"
        ],
        "field_refs": [
          "product_area"
        ]
      },
      {
        "section_name": "编辑同构弹窗待确认",
        "section_type": "edit_modal",
        "section_desc": "列表存在编辑入口，预计字段结构与添加弹窗同构，待补截图确认。",
        "module_name": "云手机商品管理后台",
        "feature_names": [
          "添加云手机商品"
        ],
        "section_rules": [
          "编辑入口存在且预计指向与添加弹窗同构的商品配置界面"
        ]
      }
    ]
  },
  {
    "page_name": "添加云手机商品弹窗",
    "page_desc": "后台添加云手机商品的配置弹窗。",
    "sections": [
      {
        "section_name": "添加云手机商品表单",
        "section_type": "edit_modal",
        "section_desc": "配置商品基础字段、排序、库存预警和状态",
        "module_name": "云手机商品管理后台",
        "feature_names": [
          "添加云手机商品"
        ],
        "section_rules": [
          "服务时长为必填",
          "商品区为必填",
          "盒子内排序为必填"
        ],
        "field_refs": [
          "service_duration",
          "product_area",
          "inside_sort_order",
          "inventory_warning_threshold",
          "purchase_quantity_alert_users"
        ]
      },
      {
        "section_name": "添加云手机商品字段说明表",
        "section_type": "field_rule_table",
        "section_desc": "新增或变更字段约束表",
        "module_name": "云手机商品管理后台",
        "feature_names": [
          "添加云手机商品"
        ],
        "field_rule_table_refs": [
          "添加云手机商品字段说明表"
        ]
      }
    ]
  },
  {
    "page_name": "编辑宣传内容弹窗",
    "page_desc": "后台编辑宣传内容的配置弹窗。",
    "sections": [
      {
        "section_name": "编辑宣传内容表单",
        "section_type": "edit_modal",
        "section_desc": "配置云机类型、宣传图片、宣传口号和性能参数",
        "module_name": "云手机商品管理后台",
        "feature_names": [
          "编辑宣传内容"
        ],
        "section_rules": [
          "云机类型必填",
          "宣传图片必传",
          "宣传口号与性能参数必填"
        ],
        "field_refs": [
          "cloud_type",
          "promo_image",
          "promo_slogan",
          "performance_params"
        ]
      },
      {
        "section_name": "编辑宣传内容字段说明表",
        "section_type": "field_rule_table",
        "section_desc": "宣传内容配置字段约束表",
        "module_name": "云手机商品管理后台",
        "feature_names": [
          "编辑宣传内容"
        ],
        "field_rule_table_refs": [
          "编辑宣传内容字段说明表"
        ]
      }
    ]
  }
]
```

## modules
```json
[
  {
    "module_name": "云挂机购买页展示",
    "module_desc": "云挂机购买页中的tab、宣传区、特价专区和普通区商品展示能力。",
    "features": [
      {
        "feature_name": "常规版/全新版tab与宣传图展示",
        "page_name": "云挂机购买页",
        "section_name": "顶部tab与宣传图区域",
        "feature_desc": "常规版和全新版tab都展示相同的改版宣传图区域。",
        "actors": [
          "用户"
        ],
        "entry_conditions": [
          "用户进入云挂机购买页"
        ],
        "rules": [
          "云挂机购买页的常规版tab和全新版tab都需要展示改版后的宣传图区域。",
          "宣传图片建议尺寸为1008*160，数据来源于盒子管理后台-云挂机-云手机商品管理-编辑宣传内容-宣传图片字段。",
          {
            "rule_id": "R-002",
            "name": "promo_image_size",
            "rule_type": "value_constraint",
            "field_name": "promo_image",
            "rule_text": "宣传图片建议尺寸为1008*160。"
          }
        ],
        "field_definitions": [
          {
            "field_name": "promo_image",
            "display_name": "宣传图片",
            "description": "双tab共享的宣传图展示资源。",
            "data_type": "image",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "data_source": "盒子管理后台-云挂机-云手机商品管理-编辑宣传内容-宣传图片字段",
            "terminal": "小程序",
            "name": "promo_image",
            "type": "display_text",
            "default": "",
            "display": "宣传图片"
          }
        ],
        "visible_elements": [
          "常规版tab",
          "全新版tab",
          "宣传图区域"
        ],
        "interactive_entries": [
          "切换常规版tab",
          "切换全新版tab"
        ],
        "fields": [
          {
            "field_name": "promo_image",
            "display_name": "宣传图片",
            "description": "双tab共享的宣传图展示资源。",
            "data_type": "image",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "data_source": "盒子管理后台-云挂机-云手机商品管理-编辑宣传内容-宣传图片字段",
            "terminal": "小程序",
            "name": "promo_image",
            "type": "display_text",
            "default": "",
            "display": "宣传图片"
          }
        ],
        "field_rules": [
          {
            "rule_id": "R-002",
            "field_name": "promo_image",
            "rule_text": "宣传图片建议尺寸为1008*160。",
            "rule_type": "range_constraint",
            "must_cover": true
          }
        ]
      },
      {
        "feature_name": "宣传专区文案展示",
        "page_name": "云挂机购买页",
        "section_name": "宣传专区",
        "feature_desc": "展示宣传口号和性能参数。",
        "actors": [
          "用户"
        ],
        "entry_conditions": [
          "购买页已加载改版内容"
        ],
        "rules": [
          "宣传专区展示宣传口号和性能参数，后台单行可配置20个字符，若C端展示超过一行则换行展示。",
          {
            "rule_id": "R-003",
            "name": "promo_slogan_wrap",
            "rule_type": "value_constraint",
            "field_name": "promo_slogan",
            "max_length": 20,
            "rule_text": "宣传口号后台单行可配置20个字符，C端展示超过一行时换行。"
          },
          {
            "rule_id": "R-004",
            "name": "performance_params_wrap",
            "rule_type": "value_constraint",
            "field_name": "performance_params",
            "max_length": 20,
            "rule_text": "性能参数后台单行可配置20个字符，C端展示超过一行时换行。"
          }
        ],
        "field_definitions": [
          {
            "field_name": "promo_slogan",
            "display_name": "宣传口号",
            "description": "购买页宣传专区文案。",
            "data_type": "string",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "data_source": "盒子管理后台-云挂机-云手机商品管理-编辑宣传内容-宣传口号",
            "length_rule": "20个字符，超一行换行",
            "terminal": "小程序",
            "name": "promo_slogan",
            "type": "display_text",
            "default": "",
            "display": "宣传口号"
          },
          {
            "field_name": "performance_params",
            "display_name": "性能参数",
            "description": "购买页宣传专区性能参数。",
            "data_type": "string",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "data_source": "盒子管理后台-云挂机-云手机商品管理-编辑宣传内容-性能参数",
            "length_rule": "20个字符，超一行换行",
            "terminal": "小程序",
            "name": "performance_params",
            "type": "display_text",
            "default": "",
            "display": "性能参数"
          }
        ],
        "visible_elements": [
          "宣传口号",
          "性能参数"
        ],
        "fields": [
          {
            "field_name": "promo_slogan",
            "display_name": "宣传口号",
            "description": "购买页宣传专区文案。",
            "data_type": "string",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "data_source": "盒子管理后台-云挂机-云手机商品管理-编辑宣传内容-宣传口号",
            "length_rule": "20个字符，超一行换行",
            "terminal": "小程序",
            "name": "promo_slogan",
            "type": "display_text",
            "default": "",
            "display": "宣传口号"
          },
          {
            "field_name": "performance_params",
            "display_name": "性能参数",
            "description": "购买页宣传专区性能参数。",
            "data_type": "string",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "data_source": "盒子管理后台-云挂机-云手机商品管理-编辑宣传内容-性能参数",
            "length_rule": "20个字符，超一行换行",
            "terminal": "小程序",
            "name": "performance_params",
            "type": "display_text",
            "default": "",
            "display": "性能参数"
          }
        ],
        "field_rules": [
          {
            "rule_id": "R-003",
            "field_name": "promo_slogan",
            "rule_text": "宣传口号后台单行可配置20个字符，C端展示超过一行时换行。",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "R-004",
            "field_name": "performance_params",
            "rule_text": "性能参数后台单行可配置20个字符，C端展示超过一行时换行。",
            "rule_type": "range_constraint",
            "must_cover": true
          }
        ]
      },
      {
        "feature_name": "特价专区商品列表",
        "page_name": "云挂机购买页",
        "section_name": "特价专区商品列表",
        "feature_desc": "展示特价专区商品列表及其布局约束。",
        "actors": [
          "用户"
        ],
        "entry_conditions": [
          "后台存在商品区配置"
        ],
        "rules": [
          "特价专区名称固定为特价专区，若后台无配置则不展示；横排展示，首屏展示2个半卡片，最多展示4个商品。",
          {
            "rule_id": "R-005",
            "name": "special_area_visibility",
            "rule_type": "conditional_visibility",
            "target": "special_area_list",
            "visible_when": "后台至少存在1个商品区=特殊区且状态为开启的商品",
            "rule_text": "后台无特殊区配置时，特价专区不展示。"
          },
          {
            "rule_id": "R-006",
            "name": "special_area_layout",
            "rule_type": "display_constraint",
            "target": "special_area_list",
            "rule_text": "特价专区横排展示，首屏展示2个半卡片。"
          },
          {
            "rule_id": "R-007",
            "name": "special_area_max_count",
            "rule_type": "max_count_constraint",
            "target": "special_area_list",
            "max_count": 4,
            "rule_text": "特价专区最多展示4个商品。"
          },
          {
            "name": "special_area_list_value_constraint",
            "rule_type": "value_constraint",
            "field_name": "special_area_list",
            "max_count": 4,
            "rule_text": "special_area_list; value_constraint; max_count=4"
          }
        ],
        "field_definitions": [
          {
            "field_name": "special_area_list",
            "display_name": "特价专区商品列表",
            "description": "展示现价、原价、商品名称和商品标签类型。",
            "data_type": "array",
            "control_type": "display_text",
            "required": false,
            "editable": false,
            "default_value": "",
            "max_count": 4,
            "terminal": "小程序",
            "name": "special_area_list",
            "type": "display_text",
            "default": "",
            "display": "特价专区商品列表"
          }
        ],
        "visible_elements": [
          "特价专区标题",
          "商品卡片",
          "现价",
          "原价",
          "商品名称",
          "商品标签类型"
        ],
        "fields": [
          {
            "field_name": "special_area_list",
            "display_name": "特价专区商品列表",
            "description": "展示现价、原价、商品名称和商品标签类型。",
            "data_type": "array",
            "control_type": "display_text",
            "required": false,
            "editable": false,
            "default_value": "",
            "max_count": 4,
            "terminal": "小程序",
            "name": "special_area_list",
            "type": "display_text",
            "default": "",
            "display": "特价专区商品列表"
          }
        ],
        "field_rules": [
          {
            "rule_id": "",
            "field_name": "special_area_list",
            "rule_text": "special_area_list; value_constraint; max_count=4",
            "rule_type": "range_constraint",
            "must_cover": true
          }
        ]
      },
      {
        "feature_name": "限时购买商品列表",
        "page_name": "云挂机购买页",
        "section_name": "限时购买商品列表",
        "feature_desc": "普通区商品列表更名为限时购买并保持原有数量逻辑。",
        "actors": [
          "用户"
        ],
        "entry_conditions": [
          "后台存在普通区商品"
        ],
        "rules": [
          "原商品列表更名为限时购买，竖排展示，商品数量逻辑保持之前逻辑。",
          "普通区商品列表保持竖排展示。",
          "普通区商品数量逻辑保持原逻辑不变。",
          "首屏普通区商品列表展示两个及以上商品。"
        ],
        "field_definitions": [
          {
            "field_name": "normal_area_list",
            "display_name": "限时购买商品列表",
            "description": "原普通区商品列表。",
            "data_type": "array",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "terminal": "小程序",
            "name": "normal_area_list",
            "type": "display_text",
            "default": "",
            "display": "限时购买商品列表"
          }
        ],
        "visible_elements": [
          "限时购买标题",
          "数量选择器",
          "确认支付按钮"
        ],
        "fields": [
          {
            "field_name": "normal_area_list",
            "display_name": "限时购买商品列表",
            "description": "原普通区商品列表。",
            "data_type": "array",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "terminal": "小程序",
            "name": "normal_area_list",
            "type": "display_text",
            "default": "",
            "display": "限时购买商品列表"
          }
        ],
        "field_rules": []
      },
      {
        "feature_name": "商品选择与结算区",
        "page_name": "云挂机购买页",
        "section_name": "限时购买商品列表",
        "feature_desc": "基于购买页视觉布局补充的C端场景，用户可选择商品、调整数量并查看结算信息。",
        "actors": [
          "用户"
        ],
        "entry_conditions": [
          "购买页已展示特价专区或限时购买商品"
        ],
        "rules": [
          "C端商品卡片展示商品标签、商品名称、现价、原价和按天价格。",
          "点击特价专区或限时购买区商品卡片后，当前商品进入选中态并同步到结算区。",
          "底部结算区展示数量选择器、合计金额和确认支付按钮。",
          "调整购买数量后合计金额按当前选中商品价格实时变化。",
          "用户可点击确认支付继续后续购买流程。"
        ],
        "field_definitions": [
          {
            "field_name": "selected_product",
            "display_name": "当前选中商品",
            "description": "当前用于结算的商品卡片。",
            "data_type": "string",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "terminal": "小程序",
            "name": "selected_product",
            "type": "display_text",
            "default": "",
            "display": "当前选中商品"
          },
          {
            "field_name": "purchase_quantity",
            "display_name": "购买数量",
            "description": "底部结算区数量选择值。",
            "data_type": "integer",
            "control_type": "number_input",
            "required": true,
            "editable": true,
            "default_value": 1,
            "terminal": "小程序",
            "name": "purchase_quantity",
            "type": "number_input",
            "default": 1,
            "display": "购买数量"
          },
          {
            "field_name": "total_amount",
            "display_name": "合计金额",
            "description": "底部结算区实时展示的合计价格。",
            "data_type": "float",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "terminal": "小程序",
            "name": "total_amount",
            "type": "display_text",
            "default": "",
            "display": "合计金额"
          },
          {
            "field_name": "confirm_pay_button",
            "display_name": "确认支付按钮",
            "description": "用户继续购买流程的入口按钮。",
            "data_type": "string",
            "control_type": "button",
            "required": true,
            "editable": false,
            "default_value": "确认支付",
            "terminal": "小程序",
            "name": "confirm_pay_button",
            "type": "button",
            "default": "确认支付",
            "display": "确认支付按钮"
          }
        ],
        "visible_elements": [
          "商品标签",
          "商品名称",
          "现价",
          "原价",
          "按天价格",
          "数量选择器",
          "合计金额",
          "确认支付按钮"
        ],
        "interactive_entries": [
          "点击特价专区商品卡片",
          "点击限时购买商品卡片",
          "点击数量减号",
          "点击数量加号",
          "点击确认支付"
        ],
        "fields": [
          {
            "field_name": "selected_product",
            "display_name": "当前选中商品",
            "description": "当前用于结算的商品卡片。",
            "data_type": "string",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "terminal": "小程序",
            "name": "selected_product",
            "type": "display_text",
            "default": "",
            "display": "当前选中商品"
          },
          {
            "field_name": "purchase_quantity",
            "display_name": "购买数量",
            "description": "底部结算区数量选择值。",
            "data_type": "integer",
            "control_type": "number_input",
            "required": true,
            "editable": true,
            "default_value": 1,
            "terminal": "小程序",
            "name": "purchase_quantity",
            "type": "number_input",
            "default": 1,
            "display": "购买数量"
          },
          {
            "field_name": "total_amount",
            "display_name": "合计金额",
            "description": "底部结算区实时展示的合计价格。",
            "data_type": "float",
            "control_type": "display_text",
            "required": true,
            "editable": false,
            "default_value": "",
            "terminal": "小程序",
            "name": "total_amount",
            "type": "display_text",
            "default": "",
            "display": "合计金额"
          },
          {
            "field_name": "confirm_pay_button",
            "display_name": "确认支付按钮",
            "description": "用户继续购买流程的入口按钮。",
            "data_type": "string",
            "control_type": "button",
            "required": true,
            "editable": false,
            "default_value": "确认支付",
            "terminal": "小程序",
            "name": "confirm_pay_button",
            "type": "button",
            "default": "确认支付",
            "display": "确认支付按钮"
          }
        ],
        "field_rules": []
      }
    ]
  },
  {
    "module_name": "云手机商品管理后台",
    "module_desc": "后台云手机商品列表、添加商品和编辑宣传内容能力。",
    "features": [
      {
        "feature_name": "商品列表与管理入口",
        "page_name": "云手机商品管理页",
        "section_name": "管理操作区",
        "feature_desc": "列表页新增商品区列，并提供添加和编辑宣传内容入口。",
        "actors": [
          "运营后台管理员"
        ],
        "entry_conditions": [
          "进入云手机商品管理页面"
        ],
        "rules": [
          "点击添加按钮进入添加云手机商品弹窗。",
          "编辑宣传图按钮更名为编辑宣传内容。",
          "点击编辑宣传内容按钮进入编辑宣传内容弹窗。",
          "商品列表新增商品区字段。",
          "列表操作列保留编辑和删除入口。"
        ],
        "field_definitions": [
          {
            "field_name": "product_area",
            "display_name": "商品区",
            "description": "列表新增字段，展示商品属于特殊区还是普通区。",
            "data_type": "enum",
            "control_type": "display_text",
            "required": false,
            "editable": false,
            "default_value": "",
            "enum_values": [
              "特殊区",
              "普通区"
            ],
            "terminal": "后台",
            "name": "product_area",
            "type": "display_text",
            "default": "",
            "display": "商品区"
          }
        ],
        "visible_elements": [
          "编辑商品顺序按钮",
          "添加按钮",
          "编辑宣传内容按钮",
          "商品区列"
        ],
        "interactive_entries": [
          "点击添加",
          "点击编辑宣传内容",
          "点击编辑",
          "点击删除"
        ],
        "fields": [
          {
            "field_name": "product_area",
            "display_name": "商品区",
            "description": "列表新增字段，展示商品属于特殊区还是普通区。",
            "data_type": "enum",
            "control_type": "display_text",
            "required": false,
            "editable": false,
            "default_value": "",
            "enum_values": [
              "特殊区",
              "普通区"
            ],
            "terminal": "后台",
            "name": "product_area",
            "type": "display_text",
            "default": "",
            "display": "商品区"
          }
        ],
        "field_rules": []
      },
      {
        "feature_name": "添加云手机商品",
        "page_name": "添加云手机商品弹窗",
        "section_name": "添加云手机商品表单",
        "feature_desc": "在后台添加云手机商品并配置商品区、排序、预警和状态。",
        "actors": [
          "运营后台管理员"
        ],
        "entry_conditions": [
          "点击添加按钮打开弹窗"
        ],
        "rules": [
          "添加云手机商品时，服务时长格式为n天x时，前项最大370，后项最大23，前后项不可同时为0。",
          "商品区字段为单选，content为特殊区、普通区；若特殊区生效商品数量超过4个，则不可保存并提示“特殊区只能展示4个商品，当前字段的配置数量已超过4个，请关闭之前的商品或调整配置”。",
          "盒子内排序字段为正整数，数值上限1000；若盒子内排序值相同，则按创建时间倒序排列。",
          "库存预警值字段每20分钟校验库存是否小于等于所配置数量；若校验失败，C端商品隐藏且不给用户分配云机，并触发机器人报警。",
          {
            "rule_id": "R-008",
            "name": "service_duration_constraint",
            "rule_type": "value_constraint",
            "field_name": "service_duration",
            "min": 0,
            "max": 370,
            "integer_only": true,
            "rule_text": "服务时长格式为n天x时，前项最大370，后项最大23，前后项不可同时为0。"
          },
          {
            "rule_id": "R-009",
            "name": "product_area_limit",
            "rule_type": "state_constraint",
            "target": "product_area",
            "rule_text": "商品区为单选，content为特殊区、普通区；若特殊区配置数量超过4个，则不可保存并提示精确toast。"
          },
          {
            "rule_id": "R-010",
            "name": "inside_sort_order_constraint",
            "rule_type": "value_constraint",
            "field_name": "inside_sort_order",
            "min": 1,
            "max": 1000,
            "integer_only": true,
            "rule_text": "盒子内排序为正整数，数值上限1000。"
          },
          {
            "rule_id": "R-011",
            "name": "inside_sort_order_tie_breaker",
            "rule_type": "order_constraint",
            "field_name": "inside_sort_order",
            "rule_text": "若盒子内排序值相同，则按创建时间倒序排列。"
          },
          {
            "rule_id": "R-012",
            "name": "inventory_warning_threshold_constraint",
            "rule_type": "value_constraint",
            "field_name": "inventory_warning_threshold",
            "min": 1,
            "max": 200,
            "integer_only": true,
            "rule_text": "库存预警值为正整数，数值上限200。"
          },
          {
            "rule_id": "R-013",
            "name": "inventory_warning_effect",
            "rule_type": "state_constraint",
            "target": "inventory_warning_threshold",
            "rule_text": "库存预警值每20分钟校验库存；校验失败时前台隐藏该商品且不给用户分配云机，并发送报警。"
          },
          {
            "rule_id": "R-014",
            "name": "purchase_quantity_alert_users_source",
            "rule_type": "data_source_constraint",
            "field_name": "purchase_quantity_alert_users",
            "data_source": "盒子后台管理员列表",
            "rule_text": "购买数量报警通知人为必填单选字段，数据源为盒子后台管理员列表。"
          },
          {
            "name": "service_duration_value_constraint",
            "rule_type": "value_constraint",
            "field_name": "service_duration",
            "min": 0,
            "max": 370,
            "integer_only": true,
            "formats": [
              "n天x时"
            ],
            "rule_text": "service_duration; value_constraint; min=0; max=370; integer_only=True"
          },
          {
            "name": "inside_sort_order_value_constraint",
            "rule_type": "value_constraint",
            "field_name": "inside_sort_order",
            "min": 1,
            "max": 1000,
            "integer_only": true,
            "rule_text": "inside_sort_order; value_constraint; min=1; max=1000; integer_only=True"
          },
          {
            "name": "inventory_warning_threshold_value_constraint",
            "rule_type": "value_constraint",
            "field_name": "inventory_warning_threshold",
            "min": 1,
            "max": 200,
            "integer_only": true,
            "rule_text": "inventory_warning_threshold; value_constraint; min=1; max=200; integer_only=True"
          },
          {
            "name": "purchase_quantity_alert_users_data_source_constraint",
            "rule_type": "data_source_constraint",
            "field_name": "purchase_quantity_alert_users",
            "data_source": "盒子后台管理员列表",
            "display": "购买数量报警通知人",
            "rule_text": "purchase_quantity_alert_users; data_source_constraint; data_source=盒子后台管理员列表"
          }
        ],
        "field_definitions": [
          {
            "field_name": "cloud_phone_product_category",
            "display_name": "云手机商品类型",
            "description": "弹窗中的商品类型选择字段。",
            "data_type": "enum",
            "control_type": "select_single",
            "required": true,
            "editable": true,
            "default_value": "",
            "name": "cloud_phone_product_category",
            "type": "select_single",
            "default": "",
            "display": "云手机商品类型"
          },
          {
            "field_name": "cloud_type",
            "display_name": "云机类型",
            "description": "弹窗中的云机类型选择字段。",
            "data_type": "enum",
            "control_type": "select_single",
            "required": true,
            "editable": true,
            "default_value": "",
            "name": "cloud_type",
            "type": "select_single",
            "default": "",
            "display": "云机类型"
          },
          {
            "field_name": "product_name",
            "display_name": "商品名称",
            "description": "商品名称输入框。",
            "data_type": "string",
            "control_type": "text_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "name": "product_name",
            "type": "text_input",
            "default": "",
            "display": "商品名称"
          },
          {
            "field_name": "original_price",
            "display_name": "原价",
            "description": "已有功能，数值限制修改为大于等于0.00。",
            "data_type": "float",
            "control_type": "number_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "min": 0,
            "name": "original_price",
            "type": "number_input",
            "default": "",
            "display": "原价"
          },
          {
            "field_name": "current_price",
            "display_name": "现价",
            "description": "已有功能，数值限制修改为大于等于0.00。",
            "data_type": "float",
            "control_type": "number_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "min": 0,
            "name": "current_price",
            "type": "number_input",
            "default": "",
            "display": "现价"
          },
          {
            "field_name": "service_duration",
            "display_name": "服务时长",
            "description": "以天和小时组成的服务时长。",
            "data_type": "range",
            "control_type": "number_input_pair",
            "required": true,
            "editable": true,
            "default_value": "",
            "format_rule": "n天x时；前后项仅非负整数；前项最大370；后项最大23；前后项不可同时为0",
            "min": 0,
            "max": 370,
            "integer_only": true,
            "name": "service_duration",
            "type": "number_input_pair",
            "default": "",
            "formats": [
              "n天x时"
            ],
            "display": "服务时长"
          },
          {
            "field_name": "product_area",
            "display_name": "商品区",
            "description": "决定前台商品进入特价专区还是普通区。",
            "data_type": "enum",
            "control_type": "select_single",
            "required": true,
            "editable": true,
            "default_value": "",
            "enum_values": [
              "特殊区",
              "普通区"
            ],
            "name": "product_area",
            "type": "select_single",
            "default": "",
            "display": "商品区",
            "content_values": [
              "特殊区",
              "普通区"
            ]
          },
          {
            "field_name": "inside_sort_order",
            "display_name": "盒子内排序",
            "description": "决定同一区域内展示顺序。",
            "data_type": "integer",
            "control_type": "number_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "min": 1,
            "max": 1000,
            "integer_only": true,
            "name": "inside_sort_order",
            "type": "number_input",
            "default": "",
            "display": "盒子内排序",
            "format_rule": "正整数，数值上限1000",
            "formats": [
              "正整数，数值上限1000"
            ]
          },
          {
            "field_name": "product_display_duration",
            "display_name": "商品展示时间",
            "description": "未配置时长期展示；鼠标悬浮问号展示提示。",
            "data_type": "string",
            "control_type": "text_input",
            "required": false,
            "editable": true,
            "default_value": "",
            "name": "product_display_duration",
            "type": "text_input",
            "default": "",
            "display": "商品展示时间"
          },
          {
            "field_name": "inventory_warning_threshold",
            "display_name": "库存预警值",
            "description": "低库存时触发前台隐藏和报警。",
            "data_type": "integer",
            "control_type": "number_input",
            "required": false,
            "editable": true,
            "default_value": "",
            "min": 1,
            "max": 200,
            "integer_only": true,
            "name": "inventory_warning_threshold",
            "type": "number_input",
            "default": "",
            "display": "库存预警值",
            "format_rule": "正整数，数值上限200",
            "formats": [
              "正整数，数值上限200"
            ]
          },
          {
            "field_name": "purchase_quantity_alert_users",
            "display_name": "购买数量报警通知人",
            "description": "报警接收人。",
            "data_type": "array",
            "control_type": "select_single",
            "required": true,
            "editable": true,
            "default_value": "",
            "data_source": "盒子后台管理员列表",
            "name": "purchase_quantity_alert_users",
            "type": "select_single",
            "default": "",
            "display": "购买数量报警通知人"
          },
          {
            "field_name": "status",
            "display_name": "状态",
            "description": "商品上下架状态。",
            "data_type": "enum",
            "control_type": "radio",
            "required": true,
            "editable": true,
            "default_value": "关闭",
            "enum_values": [
              "开启",
              "关闭"
            ],
            "name": "status",
            "type": "radio",
            "default": "关闭",
            "display": "状态"
          }
        ],
        "field_rule_tables": [
          {
            "field_name": "cloud_phone_product",
            "table_name": "添加云手机商品字段说明表",
            "table_desc": "截图中右侧字段说明表",
            "rows": [
              {
                "row_id": "ROW-001",
                "row_name": "服务时长",
                "rule_text": "时间格式n天x时，前后项仅非负整数，前项最大370，后项最大23，前后项不可同时为0",
                "expected_effect": "输入非法值或0天0小时不可保存"
              },
              {
                "row_id": "ROW-002",
                "row_name": "商品区",
                "rule_text": "单选，content为特殊区、普通区；特殊区配置数量需小于等于4",
                "expected_effect": "超过4个特殊区商品时阻止保存并提示精确toast"
              },
              {
                "row_id": "ROW-003",
                "row_name": "盒子内排序",
                "rule_text": "正整数，数值上限1000；排序值相同按创建时间倒序",
                "expected_effect": "排序字段校验通过后按新顺序展示"
              },
              {
                "row_id": "ROW-004",
                "row_name": "商品展示时间",
                "rule_text": "若无配置，云挂机商品长期展示；鼠标悬浮问号展示提示内容",
                "expected_effect": "未配置时按长期展示逻辑处理"
              },
              {
                "row_id": "ROW-005",
                "row_name": "库存预警值",
                "rule_text": "正整数，数值上限200；每20分钟校验库存，失败时隐藏商品并触发报警",
                "expected_effect": "库存不足时前台不展示该商品且不给用户分配云机"
              },
              {
                "row_id": "ROW-006",
                "row_name": "购买数量报警通知人",
                "rule_text": "单选，content为盒子后台管理员列表",
                "expected_effect": "报警接收人必须来自后台管理员列表"
              }
            ]
          }
        ],
        "visible_elements": [
          "商品区",
          "库存预警值",
          "购买数量报警通知人"
        ],
        "interactive_entries": [
          "点击确定保存商品",
          "切换状态"
        ],
        "abnormal_scenarios": [
          "特殊区数量超过4个时点击确定不可保存并提示精确toast。",
          "服务时长输入0天0小时不可保存。"
        ],
        "boundary_scenarios": [
          "盒子内排序输入1001不可保存。",
          "库存预警值输入201不可保存。"
        ],
        "fields": [
          {
            "field_name": "cloud_phone_product_category",
            "display_name": "云手机商品类型",
            "description": "弹窗中的商品类型选择字段。",
            "data_type": "enum",
            "control_type": "select_single",
            "required": true,
            "editable": true,
            "default_value": "",
            "name": "cloud_phone_product_category",
            "type": "select_single",
            "default": "",
            "display": "云手机商品类型"
          },
          {
            "field_name": "cloud_type",
            "display_name": "云机类型",
            "description": "弹窗中的云机类型选择字段。",
            "data_type": "enum",
            "control_type": "select_single",
            "required": true,
            "editable": true,
            "default_value": "",
            "name": "cloud_type",
            "type": "select_single",
            "default": "",
            "display": "云机类型"
          },
          {
            "field_name": "product_name",
            "display_name": "商品名称",
            "description": "商品名称输入框。",
            "data_type": "string",
            "control_type": "text_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "name": "product_name",
            "type": "text_input",
            "default": "",
            "display": "商品名称"
          },
          {
            "field_name": "original_price",
            "display_name": "原价",
            "description": "已有功能，数值限制修改为大于等于0.00。",
            "data_type": "float",
            "control_type": "number_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "min": 0,
            "name": "original_price",
            "type": "number_input",
            "default": "",
            "display": "原价"
          },
          {
            "field_name": "current_price",
            "display_name": "现价",
            "description": "已有功能，数值限制修改为大于等于0.00。",
            "data_type": "float",
            "control_type": "number_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "min": 0,
            "name": "current_price",
            "type": "number_input",
            "default": "",
            "display": "现价"
          },
          {
            "field_name": "service_duration",
            "display_name": "服务时长",
            "description": "以天和小时组成的服务时长。",
            "data_type": "range",
            "control_type": "number_input_pair",
            "required": true,
            "editable": true,
            "default_value": "",
            "format_rule": "n天x时；前后项仅非负整数；前项最大370；后项最大23；前后项不可同时为0",
            "min": 0,
            "max": 370,
            "integer_only": true,
            "name": "service_duration",
            "type": "number_input_pair",
            "default": "",
            "formats": [
              "n天x时"
            ],
            "display": "服务时长"
          },
          {
            "field_name": "product_area",
            "display_name": "商品区",
            "description": "决定前台商品进入特价专区还是普通区。",
            "data_type": "enum",
            "control_type": "select_single",
            "required": true,
            "editable": true,
            "default_value": "",
            "enum_values": [
              "特殊区",
              "普通区"
            ],
            "name": "product_area",
            "type": "select_single",
            "default": "",
            "display": "商品区",
            "content_values": [
              "特殊区",
              "普通区"
            ]
          },
          {
            "field_name": "inside_sort_order",
            "display_name": "盒子内排序",
            "description": "决定同一区域内展示顺序。",
            "data_type": "integer",
            "control_type": "number_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "min": 1,
            "max": 1000,
            "integer_only": true,
            "name": "inside_sort_order",
            "type": "number_input",
            "default": "",
            "display": "盒子内排序",
            "format_rule": "正整数，数值上限1000",
            "formats": [
              "正整数，数值上限1000"
            ]
          },
          {
            "field_name": "product_display_duration",
            "display_name": "商品展示时间",
            "description": "未配置时长期展示；鼠标悬浮问号展示提示。",
            "data_type": "string",
            "control_type": "text_input",
            "required": false,
            "editable": true,
            "default_value": "",
            "name": "product_display_duration",
            "type": "text_input",
            "default": "",
            "display": "商品展示时间"
          },
          {
            "field_name": "inventory_warning_threshold",
            "display_name": "库存预警值",
            "description": "低库存时触发前台隐藏和报警。",
            "data_type": "integer",
            "control_type": "number_input",
            "required": false,
            "editable": true,
            "default_value": "",
            "min": 1,
            "max": 200,
            "integer_only": true,
            "name": "inventory_warning_threshold",
            "type": "number_input",
            "default": "",
            "display": "库存预警值",
            "format_rule": "正整数，数值上限200",
            "formats": [
              "正整数，数值上限200"
            ]
          },
          {
            "field_name": "purchase_quantity_alert_users",
            "display_name": "购买数量报警通知人",
            "description": "报警接收人。",
            "data_type": "array",
            "control_type": "select_single",
            "required": true,
            "editable": true,
            "default_value": "",
            "data_source": "盒子后台管理员列表",
            "name": "purchase_quantity_alert_users",
            "type": "select_single",
            "default": "",
            "display": "购买数量报警通知人"
          },
          {
            "field_name": "status",
            "display_name": "状态",
            "description": "商品上下架状态。",
            "data_type": "enum",
            "control_type": "radio",
            "required": true,
            "editable": true,
            "default_value": "关闭",
            "enum_values": [
              "开启",
              "关闭"
            ],
            "name": "status",
            "type": "radio",
            "default": "关闭",
            "display": "状态"
          }
        ],
        "field_rules": [
          {
            "rule_id": "R-008",
            "field_name": "service_duration",
            "rule_text": "服务时长格式为n天x时，前项最大370，后项最大23，前后项不可同时为0。",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "R-010",
            "field_name": "inside_sort_order",
            "rule_text": "盒子内排序为正整数，数值上限1000。",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "R-011",
            "field_name": "inside_sort_order",
            "rule_text": "若盒子内排序值相同，则按创建时间倒序排列。",
            "rule_type": "other",
            "must_cover": true
          },
          {
            "rule_id": "R-012",
            "field_name": "inventory_warning_threshold",
            "rule_text": "库存预警值为正整数，数值上限200。",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "R-014",
            "field_name": "purchase_quantity_alert_users",
            "rule_text": "购买数量报警通知人为必填单选字段，数据源为盒子后台管理员列表。",
            "rule_type": "data_source_constraint",
            "must_cover": true
          },
          {
            "rule_id": "",
            "field_name": "service_duration",
            "rule_text": "service_duration; value_constraint; min=0; max=370; integer_only=True",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "",
            "field_name": "inside_sort_order",
            "rule_text": "inside_sort_order; value_constraint; min=1; max=1000; integer_only=True",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "",
            "field_name": "inventory_warning_threshold",
            "rule_text": "inventory_warning_threshold; value_constraint; min=1; max=200; integer_only=True",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "",
            "field_name": "purchase_quantity_alert_users",
            "rule_text": "purchase_quantity_alert_users; data_source_constraint; data_source=盒子后台管理员列表",
            "rule_type": "data_source_constraint",
            "must_cover": true
          }
        ]
      },
      {
        "feature_name": "编辑宣传内容",
        "page_name": "编辑宣传内容弹窗",
        "section_name": "编辑宣传内容表单",
        "feature_desc": "配置云机类型对应的宣传图片、宣传口号和性能参数。",
        "actors": [
          "运营后台管理员"
        ],
        "entry_conditions": [
          "点击编辑宣传内容按钮打开弹窗"
        ],
        "rules": [
          "编辑宣传内容时，所有云机类型都需要配置宣传内容，且云机类型不重复；若校验失败，点击确定后不可保存并提示“所有云机类型都需要配置宣传内容，且云机类型不重复！”。",
          "宣传图片最多上传5张，支持gif/jpg/jpeg/png，单文件最大不超过500k，建议尺寸1008*160。",
          "宣传图片最多上传5张图，支持gif/jpg/jpeg/png，单文件最大500k，建议尺寸1008*160，文本长度20个字符，内容达到2条时禁用新增按钮。",
          "点击新增后新增一条宣传内容配置，最多新增额外1条，内容达到2条时禁用新增按钮，所配置内容C端全部展示。",
          {
            "rule_id": "R-015",
            "name": "cloud_type_complete_and_unique",
            "rule_type": "state_constraint",
            "target": "cloud_type",
            "rule_text": "所有云机类型都需要配置宣传内容，且云机类型不重复。"
          },
          {
            "rule_id": "R-016",
            "name": "promo_image_upload_limit",
            "rule_type": "value_constraint",
            "field_name": "promo_image",
            "max_count": 5,
            "rule_text": "宣传图片最多上传5张，支持删除重新上传。"
          },
          {
            "rule_id": "R-017",
            "name": "promo_image_upload_format",
            "rule_type": "value_constraint",
            "field_name": "promo_image",
            "rule_text": "宣传图片支持gif/jpg/jpeg/png，单文件最大不超过500k，建议尺寸1008*160。"
          },
          {
            "rule_id": "R-018",
            "name": "promo_slogan_length",
            "rule_type": "value_constraint",
            "field_name": "promo_slogan",
            "max_length": 20,
            "rule_text": "宣传口号文本长度20个字符，C端超一行换行展示。"
          },
          {
            "rule_id": "R-019",
            "name": "performance_params_length",
            "rule_type": "value_constraint",
            "field_name": "performance_params",
            "max_length": 20,
            "rule_text": "性能参数文本长度20个字符，C端超一行换行展示。"
          },
          {
            "rule_id": "R-020",
            "name": "promo_content_add_limit",
            "rule_type": "max_count_constraint",
            "target": "promo_content_group",
            "max_count": 2,
            "rule_text": "点击新增后最多形成2条宣传内容配置，达到2条时禁用新增按钮。"
          },
          {
            "name": "promo_image_value_constraint",
            "rule_type": "value_constraint",
            "field_name": "promo_image",
            "formats": [
              "gif",
              "jpg",
              "jpeg",
              "png"
            ],
            "max_count": 5,
            "rule_text": "promo_image; value_constraint; max_count=5"
          },
          {
            "name": "promo_slogan_value_constraint",
            "rule_type": "value_constraint",
            "field_name": "promo_slogan",
            "max_length": 20,
            "rule_text": "promo_slogan; value_constraint; max_length=20"
          },
          {
            "name": "performance_params_value_constraint",
            "rule_type": "value_constraint",
            "field_name": "performance_params",
            "max_length": 20,
            "rule_text": "performance_params; value_constraint; max_length=20"
          }
        ],
        "field_definitions": [
          {
            "field_name": "cloud_type",
            "display_name": "云机类型",
            "description": "宣传内容对应的云机类型。",
            "data_type": "enum",
            "control_type": "select_single",
            "required": true,
            "editable": true,
            "default_value": "",
            "enum_values": [
              "全新版",
              "常规版"
            ],
            "name": "cloud_type",
            "type": "select_single",
            "default": "",
            "display": "云机类型"
          },
          {
            "field_name": "promo_image",
            "display_name": "宣传图片",
            "description": "购买页宣传图资源。",
            "data_type": "image",
            "control_type": "upload_image",
            "required": true,
            "editable": true,
            "default_value": "",
            "formats": [
              "gif",
              "jpg",
              "jpeg",
              "png"
            ],
            "max_count": 5,
            "name": "promo_image",
            "type": "upload_image",
            "default": "",
            "display": "宣传图片",
            "format_rule": "支持gif/jpg/jpeg/png，单文件最大500k，建议尺寸1008*160"
          },
          {
            "field_name": "promo_slogan",
            "display_name": "宣传口号",
            "description": "购买页宣传专区展示文案。",
            "data_type": "string",
            "control_type": "text_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "max_length": 20,
            "name": "promo_slogan",
            "type": "text_input",
            "default": "",
            "display": "宣传口号",
            "length_rule": "文本长度20个字符，C端超一行换行"
          },
          {
            "field_name": "performance_params",
            "display_name": "性能参数",
            "description": "购买页宣传专区性能参数文案。",
            "data_type": "string",
            "control_type": "text_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "max_length": 20,
            "name": "performance_params",
            "type": "text_input",
            "default": "",
            "display": "性能参数",
            "length_rule": "文本长度20个字符，C端超一行换行"
          }
        ],
        "field_rule_tables": [
          {
            "field_name": "promo_content",
            "table_name": "编辑宣传内容字段说明表",
            "table_desc": "截图中右侧说明表",
            "rows": [
              {
                "row_id": "ROW-101",
                "row_name": "云机类型",
                "rule_text": "所有云机类型都需要配置内容，且云机类型不重复",
                "expected_effect": "缺失配置或重复时点击确定不可保存并提示精确toast"
              },
              {
                "row_id": "ROW-102",
                "row_name": "宣传图片",
                "rule_text": "最多上传5张，支持gif/jpg/jpeg/png，单文件最大500k，建议尺寸1008*160",
                "expected_effect": "不满足格式、大小或数量限制时不可继续保存"
              },
              {
                "row_id": "ROW-103",
                "row_name": "宣传口号",
                "rule_text": "文本长度20个字符，C端超一行换行展示",
                "expected_effect": "前台折行展示"
              },
              {
                "row_id": "ROW-104",
                "row_name": "性能参数",
                "rule_text": "文本长度20个字符，C端超一行换行展示",
                "expected_effect": "前台折行展示"
              },
              {
                "row_id": "ROW-105",
                "row_name": "新增",
                "rule_text": "点击后新增一条内容配置，最多新增额外1条，内容达到2条时禁用新增按钮",
                "expected_effect": "达到2条内容后新增按钮不可点击"
              }
            ]
          }
        ],
        "visible_elements": [
          "云机类型",
          "宣传图片",
          "宣传口号",
          "性能参数",
          "新增按钮"
        ],
        "interactive_entries": [
          "上传宣传图片",
          "点击新增",
          "删除宣传内容",
          "点击确定保存宣传内容"
        ],
        "boundary_scenarios": [
          "宣传图片上传第6张时不可继续添加。",
          "宣传口号输入超过20字符时不可直接通过。"
        ],
        "fields": [
          {
            "field_name": "cloud_type",
            "display_name": "云机类型",
            "description": "宣传内容对应的云机类型。",
            "data_type": "enum",
            "control_type": "select_single",
            "required": true,
            "editable": true,
            "default_value": "",
            "enum_values": [
              "全新版",
              "常规版"
            ],
            "name": "cloud_type",
            "type": "select_single",
            "default": "",
            "display": "云机类型"
          },
          {
            "field_name": "promo_image",
            "display_name": "宣传图片",
            "description": "购买页宣传图资源。",
            "data_type": "image",
            "control_type": "upload_image",
            "required": true,
            "editable": true,
            "default_value": "",
            "formats": [
              "gif",
              "jpg",
              "jpeg",
              "png"
            ],
            "max_count": 5,
            "name": "promo_image",
            "type": "upload_image",
            "default": "",
            "display": "宣传图片",
            "format_rule": "支持gif/jpg/jpeg/png，单文件最大500k，建议尺寸1008*160"
          },
          {
            "field_name": "promo_slogan",
            "display_name": "宣传口号",
            "description": "购买页宣传专区展示文案。",
            "data_type": "string",
            "control_type": "text_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "max_length": 20,
            "name": "promo_slogan",
            "type": "text_input",
            "default": "",
            "display": "宣传口号",
            "length_rule": "文本长度20个字符，C端超一行换行"
          },
          {
            "field_name": "performance_params",
            "display_name": "性能参数",
            "description": "购买页宣传专区性能参数文案。",
            "data_type": "string",
            "control_type": "text_input",
            "required": true,
            "editable": true,
            "default_value": "",
            "max_length": 20,
            "name": "performance_params",
            "type": "text_input",
            "default": "",
            "display": "性能参数",
            "length_rule": "文本长度20个字符，C端超一行换行"
          }
        ],
        "field_rules": [
          {
            "rule_id": "R-016",
            "field_name": "promo_image",
            "rule_text": "宣传图片最多上传5张，支持删除重新上传。",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "R-017",
            "field_name": "promo_image",
            "rule_text": "宣传图片支持gif/jpg/jpeg/png，单文件最大不超过500k，建议尺寸1008*160。",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "R-018",
            "field_name": "promo_slogan",
            "rule_text": "宣传口号文本长度20个字符，C端超一行换行展示。",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "R-019",
            "field_name": "performance_params",
            "rule_text": "性能参数文本长度20个字符，C端超一行换行展示。",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "",
            "field_name": "promo_image",
            "rule_text": "promo_image; value_constraint; max_count=5",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "",
            "field_name": "promo_slogan",
            "rule_text": "promo_slogan; value_constraint; max_length=20",
            "rule_type": "range_constraint",
            "must_cover": true
          },
          {
            "rule_id": "",
            "field_name": "performance_params",
            "rule_text": "performance_params; value_constraint; max_length=20",
            "rule_type": "range_constraint",
            "must_cover": true
          }
        ]
      }
    ]
  },
  {
    "module_name": "云机能力约束",
    "module_desc": "影响最终体验和脚本接入的技术约束。",
    "features": [
      {
        "feature_name": "SDK更新与720*1280适配",
        "feature_desc": "更新云机SDK并将画面尺寸调整为720*1280。",
        "actors": [
          "系统"
        ],
        "entry_conditions": [
          "完成云机能力升级"
        ],
        "rules": [
          "云机SDK需要更新，云机画面尺寸需要调整为720*1280。",
          "云机SDK需要更新。",
          "云机画面尺寸需要固定为720*1280。"
        ],
        "visible_elements": [
          "SDK更新要求",
          "720*1280尺寸要求"
        ],
        "field_rules": []
      }
    ]
  }
]
```

## flows
```json
[
  {
    "flow_id": "FLOW-001",
    "flow_name": "后台完成商品与宣传内容配置后前台购买页生效",
    "flow_type": "main_flow",
    "business_goal": "确保后台商品区和宣传内容配置完成后，云挂机购买页在常规版和全新版tab下都按新规则展示宣传图、宣传专区、特价专区和限时购买区。",
    "trigger": "运营后台管理员在云手机商品管理页完成商品配置和宣传内容配置。",
    "preconditions": [
      "后台管理员有云手机商品管理权限。",
      "云挂机购买页可访问。",
      "云机能力已支持720*1280尺寸。"
    ],
    "steps": [
      {
        "step_no": 1,
        "step_name": "进入云手机商品管理页并打开添加弹窗",
        "step_type": "operation",
        "module_name": "云手机商品管理后台",
        "feature_name": "商品列表与管理入口",
        "actor": "运营后台管理员",
        "action": "进入云手机商品管理页，确认列表存在商品区字段，并点击添加按钮打开添加云手机商品弹窗。",
        "expected_result": "商品列表可见商品区字段，点击添加后打开添加云手机商品弹窗。",
        "checkpoints": [
          "商品区字段可见",
          "添加按钮可点击",
          "弹窗被打开"
        ],
        "rule_references": [
          "点击添加按钮进入商品配置界面。",
          "商品列表新增商品区字段。"
        ],
        "is_key_checkpoint": true
      },
      {
        "step_no": 2,
        "step_name": "配置商品区和排序等关键字段",
        "step_type": "operation",
        "module_name": "云手机商品管理后台",
        "feature_name": "添加云手机商品",
        "actor": "运营后台管理员",
        "action": "在添加云手机商品弹窗中配置商品区、服务时长、盒子内排序、库存预警值和购买数量报警通知人，并保存商品。",
        "expected_result": "关键字段校验通过后商品被保存，可用于前台商品展示。",
        "checkpoints": [
          "商品区字段可选择特殊区或普通区",
          "服务时长符合n天x时约束",
          "盒子内排序和库存预警值通过数值校验"
        ],
        "rule_references": [
          "服务时长格式为n天x时，前项最大370，后项最大23，前后项不可同时为0。",
          "商品区为单选，content为特殊区、普通区；若特殊区配置数量超过4个，则不可保存。",
          "盒子内排序为正整数，数值上限1000。"
        ],
        "is_key_checkpoint": true
      },
      {
        "step_no": 3,
        "step_name": "配置宣传内容",
        "step_type": "operation",
        "module_name": "云手机商品管理后台",
        "feature_name": "编辑宣传内容",
        "actor": "运营后台管理员",
        "action": "点击编辑宣传内容按钮，按云机类型补齐宣传图片、宣传口号和性能参数，确保云机类型不重复后保存。",
        "expected_result": "宣传内容配置被保存，且覆盖全部云机类型。",
        "checkpoints": [
          "编辑宣传内容按钮可点击",
          "云机类型配置完整且不重复",
          "宣传图片和文案字段校验通过"
        ],
        "rule_references": [
          "所有云机类型都需要配置宣传内容，且云机类型不重复。",
          "宣传图片最多上传5张，支持gif/jpg/jpeg/png，单文件最大不超过500k，建议尺寸1008*160。",
          "点击新增后最多形成2条宣传内容配置。"
        ],
        "is_key_checkpoint": true
      },
      {
        "step_no": 4,
        "step_name": "查看前台购买页生效结果",
        "step_type": "system_response",
        "module_name": "云挂机购买页展示",
        "feature_name": "常规版/全新版tab与宣传图展示",
        "actor": "用户",
        "action": "进入云挂机购买页并分别查看常规版和全新版tab，再检查宣传专区、特价专区和限时购买区。",
        "expected_result": "双tab下的宣传图、宣传专区、特价专区和限时购买区按配置生效并展示。",
        "state_transition": {
          "from": "后台配置完成",
          "to": "前台展示生效"
        },
        "checkpoints": [
          "常规版和全新版tab下均展示宣传图",
          "宣传专区展示宣传口号和性能参数",
          "特价专区和限时购买区展示符合新规则"
        ],
        "rule_references": [
          "常规版tab和全新版tab都需要展示改版后的宣传图区域。",
          "宣传专区展示宣传口号和性能参数。",
          "特价专区若后台无配置则不展示；横排展示，首屏展示2个半卡片，最多展示4个商品。",
          "原商品列表更名为限时购买，竖排展示。"
        ],
        "is_key_checkpoint": true
      }
    ],
    "postconditions": [
      "前台购买页展示已与后台最新配置同步。"
    ],
    "success_criteria": [
      "后台商品配置可影响前台特价专区和限时购买区。",
      "后台宣传内容配置可影响双tab宣传图和宣传专区。",
      "购买页按720*1280能力适配后的展示规则落地。"
    ],
    "related_modules": [
      "云手机商品管理后台",
      "云挂机购买页展示"
    ],
    "priority": "P0",
    "tags": [
      "核心链路",
      "黄金流程",
      "前后台联动"
    ]
  }
]
```
