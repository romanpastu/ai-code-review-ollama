# 🚀 Getting Started

## 🛠️ Development Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🔨 Building the Project

To compile the source into an executable:

```bash
pyinstaller --onefile script.py
```

## 🚀 Deployment

To deploy the compiled source:

```bash
./review_deploy.sh
```

You must create a .env file with the following variables:

```
OLLAMA_HOST=
OLLAMA_MODEL=       
```