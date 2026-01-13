# 📦 Deep Agents Wheel Distribution

## Files trong package này:

- `deepagents-0.3.5-py3-none-any.whl` - Core library
- `deepagents_cli-0.0.12-py3-none-any.whl` - CLI application

## 🚀 Quick Install (3 steps)

### 1. Tạo virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# hoặc: source venv/bin/activate  # Linux/Mac
```

### 2. Cài đặt wheels
```bash
pip install deepagents-0.3.5-py3-none-any.whl
pip install deepagents_cli-0.0.12-py3-none-any.whl
```

### 3. Setup và chạy
```bash
# Tạo file .env với API key
echo OPENAI_API_KEY=sk-or-v1-your-key > .env
echo OPENAI_BASE_URL=https://openrouter.ai/api/v1 >> .env

# Chạy
deepagents --model openai/gpt-4o
```

## 📋 Requirements

- Python >= 3.11
- Internet connection (để download dependencies)
- API key từ OpenRouter/Anthropic/OpenAI/Google

## 🎯 Models có thể dùng (với OpenRouter)

```bash
# Claude (tốt nhất cho coding)
deepagents --model anthropic/claude-3.5-sonnet

# GPT (nhanh, tốt)
deepagents --model openai/gpt-4o
deepagents --model openai/gpt-4-turbo

# DeepSeek (rẻ, tốt)
deepagents --model deepseek/deepseek-chat

# Gemini
deepagents --model google/gemini-pro-1.5
```

## 💡 Commands

```bash
# Start interactive session
deepagents

# With specific model
deepagents --model openai/gpt-4o

# Auto-approve tools
deepagents --auto-approve

# Resume last session
deepagents -r

# Show help
deepagents help

# Show version
deepagents --version
```

## 📚 Documentation

Xem chi tiết:
- https://docs.langchain.com/oss/python/deepagents/overview
- https://github.com/langchain-ai/deepagents

## 🔗 Get API Keys

- OpenRouter: https://openrouter.ai/ (khuyên dùng - 1 key cho tất cả models)
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys
- Google: https://makersuite.google.com/app/apikey

---

Built with ❤️ using LangChain and LangGraph
