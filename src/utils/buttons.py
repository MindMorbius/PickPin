from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_content_options_buttons():
    """获取内容选项按钮 (自己看/投稿)"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("自己看", callback_data='keep_content'),
            InlineKeyboardButton("投个稿", callback_data='start_vote')
        ]
    ])

def get_vote_buttons():
    """获取投票按钮 (仅管理员操作)"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("管理员同意", callback_data='admin_approve'),
            InlineKeyboardButton("管理员拒绝", callback_data='admin_reject')
        ]
    ])

def get_prompt_selection_buttons():
    """获取提示词选择按钮"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("科技", callback_data='prompt_tech'),
            InlineKeyboardButton("新闻", callback_data='prompt_news')
        ],
        [
            InlineKeyboardButton("文化", callback_data='prompt_culture'),
            InlineKeyboardButton("知识", callback_data='prompt_knowledge')
        ],
        [
            InlineKeyboardButton("聊天", callback_data='prompt_chat')
        ]
    ]) 