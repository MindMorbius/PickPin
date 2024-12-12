from config.settings import TELEGRAM_USER_ID, GROUP_ID

admin_id = str(TELEGRAM_USER_ID)
group_id = str(GROUP_ID)

# 全局用户名单
USER_LISTS = {
    'whitelist': ['all'],  # 全局白名单，支持设置为 'all'
    'blacklist': [],  # 全局黑名单，支持设置为 'all'
    'admin_list': [admin_id],  # 管理员名单，
    'allowed_commands': [admin_id]
}

# 响应控制配置
RESPONSE_SETTINGS = {
    'private_chat': {
        'enabled': True,
        'allowed_commands': ['start', 'getid', 'analyze', 'summarize'],
    },
    'group_chat': {
        'enabled': True,
        'allowed_groups': [group_id],  # 允许响应的群组ID列表
        'respond_to_auto_forward': False,  # 是否响应自动转发
        'allowed_commands': ['getid', 'summarize'],
        'mention_required': True,
    },
    'channel_chat': {
        'enabled': False,
        'allowed_channels': [],  # 允许的频道ID列表
    }
}

# 响应优先级
RESPONSE_PRIORITY = {
    'commands': 1,  # 命令优先级最高
    'mention': 2,   # @机器人次之
    'reply': 3,     # 回复bot消息再次之
    'channel': 4,  # 新增频道优先级
    'text': 5       # 普通文本最低
} 