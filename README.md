# EduPal
SJTU's Teaching Agent Project

```
git clone 本项目后。
请手动从 [github] 下载 CosyVoice 模型。
将下载的文件解压并放置到 EduPal/models/CosyVoice/ 目录下。
对其他模型做同样的操作。
```

```
my_project/
├── backend/                  <-- 存放所有后端Flask代码
│   ├── app/                  <-- Flask应用的核心代码
│   │   ├── __init__.py       <-- 创建Flask app工厂
│   │   ├── apis/             <-- 按功能划分的API蓝图 (Blueprint)
│   │   │   ├── __init__.py
│   │   │   ├── paper_processing.py
│   │   │   └── video_generation.py
│   │   ├── services/         <-- 调用外部模型服务的逻辑
│   │   │   ├── __init__.py
│   │   │   ├── cosyvoice_client.py
│   │   │   └── rag_client.py
│   │   ├── static/           <-- 存放CSS, JS等静态文件
│   │   └── templates/        <-- 存放HTML模板
│   ├── run.py                <-- 启动Flask应用的入口文件
│   ├── config.py             <-- 配置文件 (数据库URI, 密钥等)
│   ├── requirements.txt      <-- 后端Python依赖
│   └── Dockerfile            <-- 用于构建后端服务的Docker镜像
│
├── services/                 <-- 存放各个模型服务的启动和封装代码
│   ├── cosyvoice/
│   │   ├── run_service.py    <-- 启动CosyVoice API服务的脚本
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── mineru/
│   │   ├── run_service.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── RAG/
│       └── ... (索引文件等)
│
├── models/                   <-- !! 关键：存放下载的大模型文件，此目录会被Git忽略
│   ├── CosyVoice/
│   │   └── ... (几个G的模型文件)
│   ├── MinerU/
│   │   └── ... (几个G的模型文件)
│   └── ...
│
├── scripts/                  <-- 存放各种辅助脚本
│   ├── activate_edu.sh
│   ├── complete_pipeline.sh
│   └── ...
│
├── docker-compose.yml        <-- 核心！用于一键启动所有服务(后端, 模型服务)
├── .gitignore                <-- 告诉Git哪些文件/文件夹不需要追踪
└── README.md                 <-- 项目说明书，非常重要！
```