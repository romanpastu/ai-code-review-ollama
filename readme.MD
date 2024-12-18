# Git Diff Review Tool 🔍

Script to code review a branch with Ollama comparing it to the main branch.

## 🌟 Features

- Supports two connection modes:
  - HTTP mode (direct connection to Ollama API)
  - SSH mode (connects through SSH tunnel)
- Automatic git diff analysis
- AI-powered code review using Ollama

## 🚀 Getting Started

### 🛠️ Development Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### ⚙️ Configuration

Create a `.env` file with the following variables:

```bash
# Required for both modes
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2:13b

# Required only for SSH mode
SSH_HOST=your_server_ip
SSH_USER=your_username
SSH_PORT=22
```

### 📦 Deployment

You can deploy the tool in either HTTP or SSH mode:

For HTTP mode (default):
```bash
./review_deploy.sh
```

For SSH mode:
```bash
./review_deploy.sh -m ssh
```

## 🎯 Usage

After deployment, you can run the tool in any git repository:

```bash
review
```

The tool will:
1. Compare your current branch with main/master
2. Analyze the differences using Ollama
3. Report any potential issues or concerns

## 🔄 Connection Modes

### HTTP Mode
- Direct connection to Ollama API
- Use when Ollama is running locally or directly accessible
- Simpler setup, requires only OLLAMA_HOST and OLLAMA_MODEL

### SSH Mode
- Connects via SSH tunnel
- Use when Ollama is running on a remote server
- Requires SSH configuration (host, user, port)
- Automatically manages SSH tunnel

## 🔧 Troubleshooting

### HTTP Mode Issues
- Verify Ollama is running
- Check OLLAMA_HOST is correct
- Ensure network connectivity

### SSH Mode Issues
- Verify SSH credentials
- Ensure SSH server is running
- Check if port 11434 is available locally

## 📝 Notes

- The tool automatically detects the main/master branch
- SSH tunnel is automatically cleaned up after use
- Environment variables can be adjusted in the .env file
