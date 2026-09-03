#!/bin/bash
# VS Code Ubuntu Integration Script
# Sets up LiteBotX for VS Code development on Ubuntu

echo "💻 LiteBotX VS Code Ubuntu Integration"
echo "====================================="

# Install VS Code if not present
if ! command -v code &> /dev/null; then
    echo "📥 Installing Visual Studio Code..."
    
    # Download and install VS Code
    wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
    sudo install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
    sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
    
    sudo apt update
    sudo apt install -y code
    
    echo "   ✅ VS Code installed successfully"
else
    echo "   ✅ VS Code already installed"
fi

# Install essential VS Code extensions
echo "🔌 Installing VS Code extensions..."

# Python extensions
code --install-extension ms-python.python
code --install-extension ms-python.pylint
code --install-extension ms-python.black-formatter
code --install-extension ms-python.isort

# General development
code --install-extension ms-vscode.vscode-json
code --install-extension redhat.vscode-yaml
code --install-extension ms-vscode.sublime-keybindings
code --install-extension ms-vscode-remote.remote-ssh

# Git integration
code --install-extension eamodio.gitlens
code --install-extension mhutchie.git-graph

# Markdown and documentation
code --install-extension yzhang.markdown-all-in-one
code --install-extension shd101wyy.markdown-preview-enhanced

# Themes and UI
code --install-extension dracula-theme.theme-dracula
code --install-extension pkief.material-icon-theme

echo "   ✅ VS Code extensions installed"

# Create VS Code workspace configuration
echo "⚙️ Creating VS Code workspace configuration..."

mkdir -p .vscode

# VS Code settings
cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "./litebotx_env/bin/python3",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=100"],
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.associations": {
        "*.py": "python",
        "*.md": "markdown",
        "*.json": "json",
        ".env*": "dotenv"
    },
    "terminal.integrated.defaultProfile.linux": "bash",
    "terminal.integrated.profiles.linux": {
        "bash": {
            "path": "/bin/bash",
            "args": []
        },
        "litebotx": {
            "path": "/bin/bash",
            "args": ["-c", "cd ${workspaceFolder} && source litebotx_env/bin/activate && bash"]
        }
    },
    "workbench.colorTheme": "Dracula",
    "workbench.iconTheme": "material-icon-theme",
    "explorer.confirmDelete": false,
    "git.autofetch": true,
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true
}
EOF

# VS Code tasks
cat > .vscode/tasks.json << 'EOF'
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start LiteBotX",
            "type": "shell",
            "command": "./start_ubuntu.sh",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "new"
            },
            "options": {
                "cwd": "${workspaceFolder}"
            },
            "problemMatcher": []
        },
        {
            "label": "Start Dashboard Only",
            "type": "shell", 
            "command": "./dashboard_only.sh",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "new"
            },
            "options": {
                "cwd": "${workspaceFolder}"
            },
            "problemMatcher": []
        },
        {
            "label": "Emergency Stop",
            "type": "shell",
            "command": "source litebotx_env/bin/activate && python3 stop_litebotx.py",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": true,
                "panel": "new"
            },
            "options": {
                "cwd": "${workspaceFolder}"
            },
            "problemMatcher": []
        },
        {
            "label": "Create Backup",
            "type": "shell",
            "command": "./create_backup.sh",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "new"
            },
            "options": {
                "cwd": "${workspaceFolder}"
            },
            "problemMatcher": []
        },
        {
            "label": "Install Dependencies",
            "type": "shell",
            "command": "source litebotx_env/bin/activate && pip install -r requirements.txt",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "new"
            },
            "options": {
                "cwd": "${workspaceFolder}"
            },
            "problemMatcher": []
        }
    ]
}
EOF

# VS Code launch configurations
cat > .vscode/launch.json << 'EOF'
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug LiteBotX",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/start_litebotx.py",
            "console": "integratedTerminal",
            "python": "${workspaceFolder}/litebotx_env/bin/python3",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Debug Dashboard",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/stock_dashboard.py",
            "console": "integratedTerminal", 
            "python": "${workspaceFolder}/litebotx_env/bin/python3",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Debug Trading Bot",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/automated_momentum_trader_v2.py",
            "console": "integratedTerminal",
            "python": "${workspaceFolder}/litebotx_env/bin/python3", 
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
EOF

# Create workspace file
cat > LiteBotX.code-workspace << 'EOF'
{
    "folders": [
        {
            "path": "."
        }
    ],
    "settings": {
        "python.defaultInterpreterPath": "./litebotx_env/bin/python3"
    },
    "extensions": {
        "recommendations": [
            "ms-python.python",
            "ms-python.pylint", 
            "ms-python.black-formatter",
            "dracula-theme.theme-dracula",
            "pkief.material-icon-theme",
            "eamodio.gitlens"
        ]
    }
}
EOF

echo "   ✅ VS Code workspace configured"

# Create requirements.txt
echo "📦 Creating requirements.txt..."
cat > requirements.txt << 'EOF'
# LiteBotX Dependencies
alpaca-py>=0.8.0
pandas>=1.5.0
numpy>=1.24.0
dash>=2.14.0
plotly>=5.15.0
dash-bootstrap-components>=1.4.0
requests>=2.31.0
python-dotenv>=1.0.0
schedule>=1.2.0
yfinance>=0.2.0
scikit-learn>=1.3.0
ta>=0.10.0
matplotlib>=3.7.0
seaborn>=0.12.0
psutil>=5.9.0

# Development dependencies
black>=23.0.0
pylint>=2.17.0
isort>=5.12.0
EOF

echo "   ✅ requirements.txt created"

echo ""
echo "=================================="
echo "✅ VS Code Integration Complete!"
echo "=================================="
echo ""
echo "🚀 Quick Start:"
echo "1. Open VS Code:           code ."
echo "2. Or open workspace:      code LiteBotX.code-workspace"
echo "3. Select Python interpreter: ./litebotx_env/bin/python3"
echo ""
echo "⚡ VS Code Features Available:"
echo "   • Task: Start LiteBotX (Ctrl+Shift+P → Tasks: Run Task)"
echo "   • Task: Dashboard Only" 
echo "   • Task: Emergency Stop"
echo "   • Task: Create Backup"
echo "   • Debug: LiteBotX, Dashboard, Trading Bot"
echo "   • Integrated Terminal with litebotx environment"
echo ""
echo "🔌 Extensions Installed:"
echo "   ✅ Python development suite"
echo "   ✅ Git integration (GitLens)"
echo "   ✅ Markdown support"
echo "   ✅ Dracula theme + Material icons"
echo ""
echo "⚙️ Configuration Files Created:"
echo "   ✅ .vscode/settings.json"
echo "   ✅ .vscode/tasks.json"
echo "   ✅ .vscode/launch.json"
echo "   ✅ LiteBotX.code-workspace"
echo "   ✅ requirements.txt"
echo ""
echo "💡 Pro Tips:"
echo "   • Use Ctrl+Shift+P to access command palette"
echo "   • F5 to start debugging"
echo "   • Ctrl+` to open integrated terminal"
echo "   • Use 'litebotx' terminal profile for activated environment"
echo ""
echo "📅 VS Code setup completed: $(date)"
