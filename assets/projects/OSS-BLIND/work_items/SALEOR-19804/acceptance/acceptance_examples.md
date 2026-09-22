# Acceptance Examples

| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |
|---|---|---|---|---|---|---|---|---|---|
| AE-001 | TG-001 | 复用已有标签时追加新礼品卡并保留历史成员 | 已有标签 T 与历史礼品卡 A 建立关联。 | 调用 `giftCardBulkCreate` 创建新礼品卡 B 并复用标签 T。 | 标签 T 同时关联历史礼品卡 A 和新礼品卡 B。<br>历史礼品卡 A 与标签 T 的关系未被移除。 | GraphQL API 与数据层 | linkage | confirmed |  |
| AE-002 | TG-002 | 批量创建时新建标签并关联当前批次礼品卡 | 输入标签 N 尚不存在。 | 调用 `giftCardBulkCreate` 创建一批礼品卡并指定标签 N。 | 系统创建标签 N。<br>标签 N 关联本次成功创建的全部礼品卡。 | GraphQL API 与数据层 | linkage | confirmed |  |
| AE-003 | TG-003 | 四个连续批次后每个标签的成员集合等于批次并集 | 第一批创建礼品卡 G1、G2 并指定标签 {red, blue}。<br>第二批创建 G3、G4 并指定相同标签 {red, blue}。<br>第三批创建 G5、G6 并指定部分重叠标签 {blue, green}。<br>第四批创建 G7、G8 并指定完全不同标签 {yellow}。 | 按第一批至第四批的顺序连续调用 `giftCardBulkCreate`。 | 标签 {red} 的成员集合精确等于 {G1,G2,G3,G4}。<br>标签 {blue} 的成员集合精确等于 {G1,G2,G3,G4,G5,G6}。<br>标签 {green} 的成员集合精确等于 {G5,G6}。<br>标签 {yellow} 的成员集合精确等于 {G7,G8}。 | GraphQL API 与数据层 | linkage | confirmed |  |
| AE-004 | TG-004 | 新旧标签混合输入时当前批次只获得指定标签 | 已有标签 T1 及其历史礼品卡关系，输入同时包含已有标签 T1 和新标签 T2。 | 调用 `giftCardBulkCreate` 创建当前批次礼品卡。 | 当前批次每张礼品卡只关联输入指定的 T1 和 T2。<br>T1 的历史礼品卡关系继续保留，T2 创建后仅建立本次所需关系。 | GraphQL API 与数据层 | linkage | confirmed |  |
| AE-005 | TG-005 | 批量创建成功响应与实际新建礼品卡数量一致 | 已准备合法的 `giftCardBulkCreate` 输入及标签数据。 | 调用接口批量创建指定数量的礼品卡。 | 响应 `count` 等于数据库实际新建的礼品卡数量。<br>仅当响应 `errors` 为空时判定本次批量创建成功，标签结果符合既有接口契约。 | GraphQL API 与数据层 | business_behavior | confirmed |  |
| AE-006 | TG-007 | 权限、非法输入及非批量礼品卡接口行为不回退 | 分别准备无权限请求、非法输入，以及 `giftCardCreate` 和 `giftCardUpdate` 的既有合法调用。 | 依次执行上述礼品卡接口调用。 | 无权限和非法输入继续返回各自既有错误结果。<br>`giftCardCreate` 与 `giftCardUpdate` 的成功结果和标签关系行为保持不变。 | GraphQL API 与数据层 | business_behavior | confirmed |  |
| AE-007 | TG-019 | 已有标签的大小写变体复用同一小写记录 | 数据库中已存在唯一标签 {vip}。 | 调用 `giftCardBulkCreate` 并输入标签 {VIP}。 | 系统复用已有的 {vip} 标签。<br>数据库中标签名称归一为 {vip}，且仍只有一条该名称记录。 | GraphQL API 与数据层 | linkage | confirmed |  |
| AE-008 | TG-019 | 重复输入的新标签只创建一条小写记录 | 数据库中不存在标签 {new}。 | 调用 `giftCardBulkCreate` 并在同一请求输入标签 {New,new,NEW}。 | 数据库只新增一条名称为 {new} 的标签记录。 | GraphQL API 与数据层 | business_behavior | confirmed |  |
| AE-009 | TG-019 | 大小写变体和重复标签只建立一次礼品卡关系 | 已准备一个批量创建请求，其中同一标签以大小写变体重复出现。 | 调用 `giftCardBulkCreate` 创建当前批次礼品卡。 | 每张当前批次礼品卡与归一后的标签只存在一条关系。<br>重复输入不会增加重复关系或重复返回标签。 | GraphQL API 与数据层 | linkage | confirmed |  |
