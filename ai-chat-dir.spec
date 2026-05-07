# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 目录模式打包配置
"""

hidden_imports = [
    'ai_chat_cli.tools',
    'ai_chat_cli.tools.tool_base',
    'ai_chat_cli.tools.tool_manager',
    'ai_chat_cli.tools.builtin',
    'ai_chat_cli.tools.builtin.web_search',
    'ai_chat_cli.tools.builtin.get_current_time',
    'ai_chat_cli.tools.builtin.code_executor',
    'ai_chat_cli.tools.builtin.file_rw',
    'ai_chat_cli.tools.builtin.knowledge_store',
    'ai_chat_cli.tools.builtin.knowledge_search',
    'ai_chat_cli.core.chat.chat_client',
    'ai_chat_cli.core.chat.chat_session',
    'ai_chat_cli.core.chat.chat_config',
    'ai_chat_cli.core.chat.chat_history',
    'ai_chat_cli.core.chat.request_sender',
    'ai_chat_cli.core.chat.tool_executor',
    'ai_chat_cli.core.chat.token_tracker',
    'ai_chat_cli.core.chat.streaming',
    'ai_chat_cli.rag',
    'ai_chat_cli.rag.rag_manager',
    'ai_chat_cli.rag.document_loader',
    'ai_chat_cli.rag.text_splitter',
    'ai_chat_cli.rag.vector_store',
    'ai_chat_cli.rag.sparse_store',
    'ai_chat_cli.rag.hybrid_searcher',
    'ddgs',
    'duckduckgo_search',
    'chromadb',
    'fitz',
    'rank_bm25',
    'jieba',
    'jieba.analyse',
    'jieba.posseg',
]

a = Analysis(
    ['ai_chat_cli/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('ai_chat_cli/config/*.yaml', 'ai_chat_cli/config')],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ai-chat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ai-chat-dir',
)
